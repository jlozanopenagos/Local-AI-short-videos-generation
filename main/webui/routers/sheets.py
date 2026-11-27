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
from contextvars import ContextVar, copy_context
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# pyrefly: ignore[missing-import]
from fastapi import APIRouter, HTTPException, Request
# pyrefly: ignore[missing-import]
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from connectivity.corrected_scripts.fetcher import fetch_all_sheets_corrected_scripts
from tools.check_script_changes import audit_script_changes
from video_creation._A_video_scripts.script_modifier import modify_video_script
from webui.routers.scripts import _get_indexed_scripts

router = APIRouter(prefix="/api/sheets", tags=["Google Sheets Sync"])
logger = logging.getLogger("webui.sheets")

_INITIAL_SYNC_STATE: Dict[str, Any] = {
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



@dataclass
class SheetsWorkspace:
    state: dict = field(default_factory=lambda: {**_INITIAL_SYNC_STATE, "logs": []})
    lock: threading.Lock = field(default_factory=threading.Lock)


_workspace = ContextVar("sheets_workspace", default=SheetsWorkspace())


class SheetsSyncRequest(BaseModel):
    clean_cache: bool = Field(default=True, description="Purge old CSV files in script_to_change/ before fetching.")
    apply_changes: bool = Field(default=True, description="Automatically update local State JSONs with detected changes.")


class ThumbnailTitlesSyncRequest(BaseModel):
    apply_changes: bool = Field(default=True, description="Automatically update content_metadata.thumbnail_title in local State JSONs.")


def _add_log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    clean = f"[{ts}] {msg}"
    with _workspace.get().lock:
        _workspace.get().state["logs"].append(clean)
        # Limit in-memory logs to latest 1000 lines
        if len(_workspace.get().state["logs"]) > 1000:
            _workspace.get().state["logs"] = _workspace.get().state["logs"][-1000:]
    logger.info(clean)


def _count_existing_csvs(base_dir: Path = BASE_DIR) -> int:
    csv_dir = base_dir / "input" / "csv" / "script_to_change"
    if not csv_dir.exists():
        return 0
    return len([f for f in csv_dir.glob("*.csv") if not f.name.startswith("model_")])


def _run_sheets_sync_worker(clean_cache: bool, apply_changes: bool, base_dir: Path = BASE_DIR) -> None:

    csv_dir = base_dir / "input" / "csv" / "script_to_change"
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
        with _workspace.get().lock:
            _workspace.get().state["current_step"] = "Cleaning cached CSV files..."
            _workspace.get().state["step_number"] = 1
            _workspace.get().state["progress"] = 15

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
        with _workspace.get().lock:
            _workspace.get().state["current_step"] = "Fetching corrected scripts from Google Sheets..."
            _workspace.get().state["step_number"] = 2
            _workspace.get().state["progress"] = 35

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
        with _workspace.get().lock:
            _workspace.get().state["current_step"] = "Auditing differences against local State JSONs..."
            _workspace.get().state["step_number"] = 3
            _workspace.get().state["progress"] = 65

        _add_log("🔍 Step 3/4: Comparing fetched CSV rows against local State JSONs...")
        changed_records, identical_records, missing_ids = audit_script_changes(base_dir=base_dir)

        _add_log(
            f"   ✓ Audit complete: {len(changed_records)} script(s) with differences, "
            f"{len(identical_records)} already in sync, {len(missing_ids)} missing state files."
        )

        # ==========================================
        # STEP 4: Update State JSONs
        # ==========================================
        if apply_changes and changed_records:
            with _workspace.get().lock:
                _workspace.get().state["current_step"] = f"Updating {len(changed_records)} State JSON file(s)..."
                _workspace.get().state["step_number"] = 4
                _workspace.get().state["progress"] = 80

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
                        base_dir=base_dir,
                        auto_update_csv=False,
                        new_expression=item.get("new_expression"),
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
                    base_dir=base_dir,
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
            "sync_mode": "scripts",
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

        with _workspace.get().lock:
            _workspace.get().state["status"] = "completed"
            _workspace.get().state["progress"] = 100
            _workspace.get().state["current_step"] = "Completed successfully"
            _workspace.get().state["result"] = final_result
            _workspace.get().state["finished_at"] = time.time()

        _add_log("🎉 Google Sheets synchronization completed successfully!")

    except Exception as exc:
        logger.exception("Error during Google Sheets synchronization: %s", exc)
        _add_log(f"💥 Fatal error during sync: {exc}")
        with _workspace.get().lock:
            _workspace.get().state["status"] = "failed"
            _workspace.get().state["error"] = str(exc)
            _workspace.get().state["current_step"] = f"Error: {exc}"
            _workspace.get().state["finished_at"] = time.time()


@router.get("/status")
def get_sheets_sync_status(request: Request = None) -> Dict[str, Any]:
    """Returns the current state, progress, and logs of the Google Sheets sync worker."""
    with _workspace.get().lock:
        state_copy = dict(_workspace.get().state)
    base_dir = request.app.state.base_dir if request else None
    state_copy["existing_csv_count"] = _count_existing_csvs(base_dir or BASE_DIR)
    return state_copy


@router.post("/sync")
def start_sheets_sync(payload: SheetsSyncRequest, request: Request) -> Dict[str, Any]:
    """
    Triggers the automated Google Sheets sync workflow:
    1. Delete stale CSVs in script_to_change/ (if clean_cache is True)
    2. Fetch Column D changes across all 16 sheets
    3. Audit differences against local State JSONs
    4. Apply updates to State JSONs and reset downstream stages
    """
    with _workspace.get().lock:
        if _workspace.get().state["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail="A Google Sheets synchronization job is already running.",
            )

        _workspace.get().state["status"] = "running"
        _workspace.get().state["progress"] = 5
        _workspace.get().state["current_step"] = "Initializing synchronization..."
        _workspace.get().state["step_number"] = 0
        _workspace.get().state["logs"] = []
        _workspace.get().state["result"] = None
        _workspace.get().state["error"] = None
        _workspace.get().state["started_at"] = time.time()
        _workspace.get().state["finished_at"] = None

    thread = threading.Thread(
        target=copy_context().run,
        args=(_run_sheets_sync_worker, payload.clean_cache, payload.apply_changes, request.app.state.base_dir or BASE_DIR),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "message": "Google Sheets synchronization job started."}


def _run_thumbnail_titles_sync_worker(apply_changes: bool, base_dir: Path = BASE_DIR) -> None:
    """Fetches Column J (THUMBNAIL_TITLE) across all 16 sheets and updates content_metadata.thumbnail_title."""
    from connectivity.core import ENDPOINT_REGISTRY, fetch_raw_sheet_rows, get_endpoint, normalize_sheet_rows
    from core.state_manager import StateManager
    from video_creation._F_thumbnail_image_generation.core.thumbnail_renderer import extract_thumbnail_title

    state_mgr = StateManager(base_dir=base_dir)
    fetched_files: List[Dict[str, Any]] = []
    total_fetched = 0
    changed_records: List[Dict[str, Any]] = []
    identical_records: List[Dict[str, Any]] = []
    missing_ids: List[str] = []
    updated_records: List[Dict[str, Any]] = []
    failed_count = 0

    try:
        with _workspace.get().lock:
            _workspace.get().state["total_steps"] = 3
            _workspace.get().state["step_number"] = 1
            _workspace.get().state["progress"] = 15
            _workspace.get().state["current_step"] = "Fetching Column J thumbnail titles from Google Sheets..."

        _add_log("🖼️ Step 1/3: Fetching thumbnail titles (Column J) across all 16 Google Sheets...")

        targets = sorted([(l, t) for (l, t), u in ENDPOINT_REGISTRY.items() if u])
        all_rows_with_titles: List[Dict[str, str]] = []
        logged_sample_headers = False

        for idx, (lang, vtype) in enumerate(targets, start=1):
            label = f"{lang}_{vtype}"
            try:
                _, _, endpoint_url = get_endpoint(language=lang, video_type=vtype)
                raw_rows = fetch_raw_sheet_rows(endpoint_url, timeout=60.0)
                if raw_rows and not logged_sample_headers:
                    _add_log(f"   ℹ️ Detected sheet columns ({label}): {list(raw_rows[0].keys())}")
                    logged_sample_headers = True

                normalized = normalize_sheet_rows(raw_rows)
                sheet_count = 0
                for rec in normalized:
                    sid = (rec.get("ID") or "").strip().upper()
                    thumb_title = (rec.get("THUMBNAIL_TITLE") or "").strip()
                    if sid and thumb_title:
                        all_rows_with_titles.append({
                            "id": sid,
                            "file": label,
                            "thumbnail_title": thumb_title,
                        })
                        sheet_count += 1

                if sheet_count > 0:
                    fetched_files.append({"filename": label, "count": sheet_count})
                    total_fetched += sheet_count
                    _add_log(f"   ✓ [{idx}/{len(targets)}] {label}: {sheet_count} thumbnail title(s) found.")
                else:
                    _add_log(f"   · [{idx}/{len(targets)}] {label}: 0 thumbnail titles in Column J.")
            except Exception as err:
                _add_log(f"   ⚠️ [{idx}/{len(targets)}] Failed to fetch {label}: {err}")

            pct = 15 + int((idx / max(len(targets), 1)) * 45)
            with _workspace.get().lock:
                _workspace.get().state["progress"] = pct

        if total_fetched == 0:
            _add_log(
                "   ⚠️ No Column J thumbnail titles were returned by the sheets. "
                "Make sure Column J has a Row 1 header (e.g. THUMBNAIL_TITLE) and your Apps Script doGet() includes Column J."
            )

        # Step 2: Audit differences against local State JSONs
        with _workspace.get().lock:
            _workspace.get().state["step_number"] = 2
            _workspace.get().state["progress"] = 70
            _workspace.get().state["current_step"] = "Comparing Column J titles against local State JSONs..."

        _add_log(f"🔍 Step 2/3: Auditing {len(all_rows_with_titles)} thumbnail title(s) against local State JSONs...")

        for item in all_rows_with_titles:
            sid = item["id"]
            new_title = item["thumbnail_title"]
            if not state_mgr.script_exists(sid):
                missing_ids.append(sid)
                continue

            state = state_mgr.get_script_state(sid)
            content_meta = state.get("content_metadata") or {}
            curr_explicit = str(content_meta.get("thumbnail_title") or "").strip()
            curr_effective = curr_explicit or extract_thumbnail_title(state)

            if curr_explicit == new_title:
                identical_records.append(item)
            else:
                changed_records.append({
                    **item,
                    "old_title": curr_effective,
                    "old_explicit": curr_explicit,
                    "diff_preview": f"- {curr_effective}\n+ {new_title}",
                })

        _add_log(
            f"   ✓ Audit complete: {len(changed_records)} title(s) to update, "
            f"{len(identical_records)} already in sync, {len(missing_ids)} missing state files."
        )

        # Step 3: Apply updates to content_metadata.thumbnail_title ONLY (never resets voice/images/assembly)
        with _workspace.get().lock:
            _workspace.get().state["step_number"] = 3
            _workspace.get().state["progress"] = 85
            _workspace.get().state["current_step"] = "Updating thumbnail_title in local State JSONs..."

        if apply_changes and changed_records:
            _add_log(f"🚀 Step 3/3: Updating thumbnail_title in {len(changed_records)} State JSON file(s)...")
            for item in changed_records:
                sid = item["id"]
                new_title = item["thumbnail_title"]
                old_title = item["old_title"]
                try:
                    state = state_mgr.get_script_state(sid)
                    state.setdefault("content_metadata", {})["thumbnail_title"] = new_title
                    state.setdefault("status", {})["thumbnail_generation"] = "pending"
                    state_mgr.save_script_state(sid, state)

                    updated_records.append({
                        "id": sid,
                        "file": item["file"],
                        "words_current": len(old_title.split()),
                        "words_new": len(new_title.split()),
                        "delta_words": f"{len(new_title.split()) - len(old_title.split()):+d}w",
                        "old_title": old_title,
                        "new_title": new_title,
                        "diff_preview": item["diff_preview"],
                        "status": "updated",
                    })
                    _add_log(f"   ✅ {sid}: \"{old_title}\" -> \"{new_title}\" (thumbnail_generation reset to pending)")
                except Exception as err:
                    failed_count += 1
                    updated_records.append({
                        "id": sid,
                        "file": item["file"],
                        "words_current": 0,
                        "words_new": 0,
                        "delta_words": "err",
                        "old_title": old_title,
                        "new_title": new_title,
                        "diff_preview": str(err),
                        "status": "failed",
                    })
                    _add_log(f"   ❌ Failed to update {sid}: {err}")

            try:
                _get_indexed_scripts(force_refresh=True)
                _add_log("   ✓ WebUI script catalog index refreshed.")
            except Exception as e:
                logger.warning("Could not refresh script index cache: %s", e)

        elif not apply_changes and changed_records:
            _add_log(f"ℹ️ Preview-only mode: Skipped updating {len(changed_records)} thumbnail title(s).")
            for item in changed_records:
                old_title = item["old_title"]
                new_title = item["thumbnail_title"]
                updated_records.append({
                    "id": item["id"],
                    "file": item["file"],
                    "words_current": len(old_title.split()),
                    "words_new": len(new_title.split()),
                    "delta_words": f"{len(new_title.split()) - len(old_title.split()):+d}w",
                    "old_title": old_title,
                    "new_title": new_title,
                    "diff_preview": item["diff_preview"],
                    "status": "pending",
                })
        else:
            _add_log("✨ All fetched Column J thumbnail titles are already synchronized with local State JSONs!")

        final_result = {
            "sync_mode": "thumbnails",
            "purged_csvs": [],
            "fetched_files": fetched_files,
            "total_fetched": total_fetched,
            "changed_count": len(changed_records),
            "identical_count": len(identical_records),
            "updated_count": len([r for r in updated_records if r["status"] == "updated"]),
            "failed_count": failed_count,
            "updated_records": updated_records,
            "missing_ids": missing_ids,
        }

        with _workspace.get().lock:
            _workspace.get().state["status"] = "completed"
            _workspace.get().state["progress"] = 100
            _workspace.get().state["current_step"] = "Thumbnail titles sync completed"
            _workspace.get().state["result"] = final_result
            _workspace.get().state["finished_at"] = time.time()

        _add_log("🎉 Thumbnail titles (Column J) synchronization completed!")

    except Exception as exc:
        logger.exception("Error during thumbnail titles synchronization: %s", exc)
        _add_log(f"💥 Fatal error during thumbnail titles sync: {exc}")
        with _workspace.get().lock:
            _workspace.get().state["status"] = "failed"
            _workspace.get().state["error"] = str(exc)
            _workspace.get().state["current_step"] = f"Error: {exc}"
            _workspace.get().state["finished_at"] = time.time()


@router.post("/sync-thumbnails")
def start_thumbnail_titles_sync(payload: ThumbnailTitlesSyncRequest, request: Request) -> Dict[str, Any]:
    """
    Fetches thumbnail titles from Column J across all 16 Google Sheets and updates
    content_metadata.thumbnail_title in local State JSONs (marking thumbnail_generation pending).
    """
    with _workspace.get().lock:
        if _workspace.get().state["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail="A Google Sheets synchronization job is already running.",
            )

        _workspace.get().state["status"] = "running"
        _workspace.get().state["progress"] = 5
        _workspace.get().state["current_step"] = "Initializing thumbnail titles sync (Column J)..."
        _workspace.get().state["step_number"] = 0
        _workspace.get().state["total_steps"] = 3
        _workspace.get().state["logs"] = []
        _workspace.get().state["result"] = None
        _workspace.get().state["error"] = None
        _workspace.get().state["started_at"] = time.time()
        _workspace.get().state["finished_at"] = None

    thread = threading.Thread(
        target=copy_context().run,
        args=(_run_thumbnail_titles_sync_worker, payload.apply_changes, request.app.state.base_dir or BASE_DIR),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "message": "Thumbnail titles (Column J) synchronization started."}


@router.post("/reset")
def reset_sheets_sync_status() -> Dict[str, Any]:
    """Resets the sheets sync state back to idle."""
    with _workspace.get().lock:
        if _workspace.get().state["status"] == "running":
            raise HTTPException(status_code=400, detail="Cannot reset while a job is running.")
        _workspace.get().state["status"] = "idle"
        _workspace.get().state["progress"] = 0
        _workspace.get().state["current_step"] = "Ready to sync"
        _workspace.get().state["step_number"] = 0
        _workspace.get().state["logs"] = []
        _workspace.get().state["result"] = None
        _workspace.get().state["error"] = None
        _workspace.get().state["started_at"] = None
        _workspace.get().state["finished_at"] = None

    return {"status": "reset", "message": "Sheets sync status reset to idle."}

