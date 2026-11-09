"""
webui/routers/sheets.py — Endpoints for synchronizing Google Sheets corrections to local State JSONs.
Handles:
1. Purging stale CSV files in main/input/csv/script_to_change/
2. Fetching Column D (SCRIPT_CHANGED) across Google Sheets endpoints
3. Auditing differences against local State JSON files
4. Updating State JSON files and resetting downstream pipeline stages
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# pyrefly: ignore[missing-import]
from fastapi import APIRouter, HTTPException
# pyrefly: ignore[missing-import]
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from connectivity.corrected_scripts.fetcher import (
    DEFAULT_OUTPUT_DIR,
    fetch_all_sheets_corrected_scripts,
)
from tools.check_script_changes import audit_script_changes
from video_creation._A_video_scripts.script_modifier import modify_video_script
from webui.routers.scripts import _get_indexed_scripts

router = APIRouter(prefix="/api/sheets", tags=["Google Sheets Sync"])
logger = logging.getLogger("webui.sheets")

_LOCK = threading.Lock()

_SHEETS_SYNC_STATE: Dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "failed"
    "progress": 0,
    "current_step": "Ready to sync",
    "step_number": 0,
    "total_steps": 4,
    "logs": [],
    "result": None,
    "error": None,
    "started_at": None,
    "finished_at": None,
}


class SheetsSyncRequest(BaseModel):
    clean_cache: bool = Field(default=True, description="Purge old CSV files in script_to_change/ before fetching.")
    apply_changes: bool = Field(default=True, description="Automatically update local State JSONs with detected changes.")


def _add_log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    clean = f"[{ts}] {msg}"
    with _LOCK:
        _SHEETS_SYNC_STATE["logs"].append(clean)
        # Limit in-memory logs to latest 1000 lines
        if len(_SHEETS_SYNC_STATE["logs"]) > 1000:
            _SHEETS_SYNC_STATE["logs"] = _SHEETS_SYNC_STATE["logs"][-1000:]
    logger.info(clean)


def _count_existing_csvs() -> int:
    csv_dir = BASE_DIR / "input" / "csv" / "script_to_change"
    if not csv_dir.exists():
        return 0
    return len([f for f in csv_dir.glob("*.csv") if not f.name.startswith("model_")])


def _run_sheets_sync_worker(clean_cache: bool, apply_changes: bool) -> None:
    global _SHEETS_SYNC_STATE

    csv_dir = BASE_DIR / "input" / "csv" / "script_to_change"
    csv_dir.mkdir(parents=True, exist_ok=True)

    purged_csvs: List[str] = []
    fetched_files: List[Dict[str, Any]] = []
    total_fetched = 0
    changed_records: List[Dict[str, Any]] = []
    identical_records: List[Dict[str, Any]] = []
    missing_ids: List[str] = []
    updated_records: List[Dict[str, Any]] = []
    failed_count = 0

    try:
        # ==========================================
        # STEP 1: Purge stale CSV cache
        # ==========================================
        with _LOCK:
            _SHEETS_SYNC_STATE["current_step"] = "Cleaning cached CSV files..."
            _SHEETS_SYNC_STATE["step_number"] = 1
            _SHEETS_SYNC_STATE["progress"] = 15

        if clean_cache and csv_dir.exists():
            _add_log("🧹 Step 1/4: Purging cached CSV files in input/csv/script_to_change/...")
            for f in sorted(csv_dir.glob("*.csv")):
                if f.name.startswith("model_"):
                    continue
                try:
                    f.unlink()
                    purged_csvs.append(f.name)
                except Exception as err:
                    _add_log(f"   ⚠️ Could not delete {f.name}: {err}")
            _add_log(f"   ✓ Purged {len(purged_csvs)} existing CSV file(s) to guarantee fresh sync.")
        else:
            _add_log("⏭️ Step 1/4: Cache purge skipped.")

        # ==========================================
        # STEP 2: Fetch Column D across all 16 sheets
        # ==========================================
        with _LOCK:
            _SHEETS_SYNC_STATE["current_step"] = "Fetching corrected scripts from Google Sheets..."
            _SHEETS_SYNC_STATE["step_number"] = 2
            _SHEETS_SYNC_STATE["progress"] = 35

        _add_log("📥 Step 2/4: Connecting to Google Sheets API (all 16 sheets)...")

        # Custom stdout interceptor to stream fetcher print statements into logs
        class FetchStream:
            def write(self, s: str):
                line = s.strip()
                if line and not (line.startswith("=") and len(line) > 10):
                    _add_log(line)
            def flush(self):
                pass

        old_stdout = sys.stdout
        try:
            sys.stdout = FetchStream()
            results = fetch_all_sheets_corrected_scripts(
                output_dir=csv_dir,
                require_non_empty_script=True,
            )
        finally:
            sys.stdout = old_stdout

        for path, count in results:
            fetched_files.append({"filename": path.name, "count": count})
            total_fetched += count

        _add_log(f"   ✓ Finished fetching: {len(fetched_files)} CSV files generated with {total_fetched} total scripts.")

        # ==========================================
        # STEP 3: Audit differences against State JSONs
        # ==========================================
        with _LOCK:
            _SHEETS_SYNC_STATE["current_step"] = "Auditing differences against local State JSONs..."
            _SHEETS_SYNC_STATE["step_number"] = 3
            _SHEETS_SYNC_STATE["progress"] = 65

        _add_log("🔍 Step 3/4: Comparing fetched CSV rows against local State JSONs...")
        changed_records, identical_records, missing_ids = audit_script_changes(base_dir=BASE_DIR)

        _add_log(
            f"   ✓ Audit complete: {len(changed_records)} script(s) with differences, "
            f"{len(identical_records)} already in sync, {len(missing_ids)} missing state files."
        )

        # ==========================================
        # STEP 4: Update State JSONs
        # ==========================================
        if apply_changes and changed_records:
            with _LOCK:
                _SHEETS_SYNC_STATE["current_step"] = f"Updating {len(changed_records)} State JSON file(s)..."
                _SHEETS_SYNC_STATE["step_number"] = 4
                _SHEETS_SYNC_STATE["progress"] = 80

            _add_log(f"🚀 Step 4/4: Applying script updates to {len(changed_records)} State JSON file(s)...")

            for item in changed_records:
                sid = item["id"]
                raw_text = item["new_script"]
                delta = item["words_new"] - item["words_current"]
                delta_str = f"+{delta}w" if delta >= 0 else f"{delta}w"

                _add_log(f"   Updating {sid} ({item['file']}): {item['words_current']}w -> {item['words_new']}w ({delta_str})...")
                try:
                    ok = modify_video_script(
                        script_id=sid,
                        raw_script_text=raw_text,
                        reset_downstream=True,
                        base_dir=BASE_DIR,
                        auto_update_csv=False,
                    )
                    if ok:
                        updated_records.append({
                            "id": sid,
                            "file": item["file"],
                            "words_current": item["words_current"],
                            "words_new": item["words_new"],
                            "delta_words": delta_str,
                            "diff_preview": item.get("diff_preview", "Content modified"),
                            "status": "updated",
                        })
                        _add_log(f"   ✅ [SUCCESS] {sid} updated successfully. Downstream stages reset to 'pending'.")
                    else:
                        failed_count += 1
                        updated_records.append({
                            "id": sid,
                            "file": item["file"],
                            "words_current": item["words_current"],
                            "words_new": item["words_new"],
                            "delta_words": delta_str,
                            "diff_preview": item.get("diff_preview", ""),
                            "status": "failed",
                        })
                        _add_log(f"   ❌ [FAILED] Could not modify script state for {sid}.")
                except Exception as err:
                    failed_count += 1
                    updated_records.append({
                        "id": sid,
                        "file": item["file"],
                        "words_current": item["words_current"],
                        "words_new": item["words_new"],
                        "delta_words": delta_str,
                        "diff_preview": str(err),
                        "status": "failed",
                    })
                    _add_log(f"   ❌ [ERROR] Exception modifying {sid}: {err}")

            # Invalidate and refresh web UI script index cache so Dashboard sees new text immediately
            try:
                _get_indexed_scripts(force_refresh=True)
                _add_log("   ✓ WebUI script catalog index refreshed.")
            except Exception as e:
                logger.warning("Could not refresh script index cache: %s", e)

            # Auto-update review CSV in scripts_to_see once for batch
            try:
                from tools.auditing.scrapper_script import process_scripts
                process_scripts(
                    base_dir=BASE_DIR,
                    include_tags=False,
                    include_title=False,
                )
                _add_log("   ✓ Review CSVs in scripts_to_see refreshed.")
            except Exception as se:
                logger.warning("Could not auto-update review CSVs: %s", se)

        elif not apply_changes and changed_records:
            _add_log(f"ℹ️ Audit-only mode: Skipped updating {len(changed_records)} script(s).")
            for item in changed_records:
                delta = item["words_new"] - item["words_current"]
                delta_str = f"+{delta}w" if delta >= 0 else f"{delta}w"
                updated_records.append({
                    "id": item["id"],
                    "file": item["file"],
                    "words_current": item["words_current"],
                    "words_new": item["words_new"],
                    "delta_words": delta_str,
                    "diff_preview": item.get("diff_preview", ""),
                    "status": "pending",
                })
        else:
            _add_log("✨ All checked scripts are already 100% synchronized with local State JSONs!")

        # Finalize success
        final_result = {
            "purged_csvs": purged_csvs,
            "fetched_files": fetched_files,
            "total_fetched": total_fetched,
            "changed_count": len(changed_records),
            "identical_count": len(identical_records),
            "updated_count": len([r for r in updated_records if r["status"] == "updated"]),
            "failed_count": failed_count,
            "updated_records": updated_records,
            "missing_ids": missing_ids,
        }

        with _LOCK:
            _SHEETS_SYNC_STATE["status"] = "completed"
            _SHEETS_SYNC_STATE["progress"] = 100
            _SHEETS_SYNC_STATE["current_step"] = "Completed successfully"
            _SHEETS_SYNC_STATE["result"] = final_result
            _SHEETS_SYNC_STATE["finished_at"] = time.time()

        _add_log("🎉 Google Sheets synchronization completed successfully!")

    except Exception as exc:
        logger.exception("Error during Google Sheets synchronization: %s", exc)
        _add_log(f"💥 Fatal error during sync: {exc}")
        with _LOCK:
            _SHEETS_SYNC_STATE["status"] = "failed"
            _SHEETS_SYNC_STATE["error"] = str(exc)
            _SHEETS_SYNC_STATE["current_step"] = f"Error: {exc}"
            _SHEETS_SYNC_STATE["finished_at"] = time.time()


@router.get("/status")
def get_sheets_sync_status() -> Dict[str, Any]:
    """Returns the current state, progress, and logs of the Google Sheets sync worker."""
    with _LOCK:
        state_copy = dict(_SHEETS_SYNC_STATE)
    state_copy["existing_csv_count"] = _count_existing_csvs()
    return state_copy


@router.post("/sync")
def start_sheets_sync(payload: SheetsSyncRequest) -> Dict[str, Any]:
    """
    Triggers the automated Google Sheets sync workflow:
    1. Delete stale CSVs in script_to_change/ (if clean_cache is True)
    2. Fetch Column D changes across all 16 sheets
    3. Audit differences against local State JSONs
    4. Apply updates to State JSONs and reset downstream stages
    """
    with _LOCK:
        if _SHEETS_SYNC_STATE["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail="A Google Sheets synchronization job is already running.",
            )

        _SHEETS_SYNC_STATE["status"] = "running"
        _SHEETS_SYNC_STATE["progress"] = 5
        _SHEETS_SYNC_STATE["current_step"] = "Initializing synchronization..."
        _SHEETS_SYNC_STATE["step_number"] = 0
        _SHEETS_SYNC_STATE["logs"] = []
        _SHEETS_SYNC_STATE["result"] = None
        _SHEETS_SYNC_STATE["error"] = None
        _SHEETS_SYNC_STATE["started_at"] = time.time()
        _SHEETS_SYNC_STATE["finished_at"] = None

    thread = threading.Thread(
        target=_run_sheets_sync_worker,
        args=(payload.clean_cache, payload.apply_changes),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "message": "Google Sheets synchronization job started."}


@router.post("/reset")
def reset_sheets_sync_status() -> Dict[str, Any]:
    """Resets the sheets sync state back to idle."""
    with _LOCK:
        if _SHEETS_SYNC_STATE["status"] == "running":
            raise HTTPException(status_code=400, detail="Cannot reset while a job is running.")
        _SHEETS_SYNC_STATE["status"] = "idle"
        _SHEETS_SYNC_STATE["progress"] = 0
        _SHEETS_SYNC_STATE["current_step"] = "Ready to sync"
        _SHEETS_SYNC_STATE["step_number"] = 0
        _SHEETS_SYNC_STATE["logs"] = []
        _SHEETS_SYNC_STATE["result"] = None
        _SHEETS_SYNC_STATE["error"] = None
        _SHEETS_SYNC_STATE["started_at"] = None
        _SHEETS_SYNC_STATE["finished_at"] = None

    return {"status": "reset", "message": "Sheets sync status reset to idle."}

