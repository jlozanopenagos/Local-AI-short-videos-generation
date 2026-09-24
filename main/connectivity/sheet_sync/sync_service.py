"""
sync_service.py — Synchronization service for exporting Google Sheets data to D:\\AI\\output\\connectivity.

Exports 3 columns: 'ID', 'expression', 'script'
Destination: D:\\AI\\output\\connectivity\\<language>\\<video_type>\\<language>_<video_type>_connectivity.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from config import OUTPUT_DIR, BASE_DIR
except (ImportError, ModuleNotFoundError):
    BASE_DIR = Path(__file__).resolve().parents[3]
    OUTPUT_DIR = Path("D:/AI/output") if Path("D:/AI/output").exists() else (BASE_DIR / "output")

try:
    from connectivity.core import (
        get_endpoint,
        ENDPOINT_REGISTRY,
        fetch_raw_sheet_rows,
        normalize_sheet_rows,
    )
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from main.connectivity.core import (
        get_endpoint,
        ENDPOINT_REGISTRY,
        fetch_raw_sheet_rows,
        normalize_sheet_rows,
    )

TARGET_COLUMNS = ["ID", "expression", "script"]
FOUR_COLUMNS = ["ID", "expression", "script", "SCRIPT_CHANGED"]


def resolve_connectivity_output_dir(
    custom_dir: Optional[Path | str] = None,
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    include_script_changed: bool = False,
) -> Path:
    """
    Resolves destination directory for connectivity data, organized by column mode, language and video type.
    Preferred location:
      - 3 columns: D:\\AI\\output\\connectivity\\_3_columns\\<language>\\<video_type>
      - 4 columns: D:\\AI\\output\\connectivity\\_4_columns\\<language>\\<video_type>
    Fallback: OUTPUT_DIR / connectivity / (_3_columns or _4_columns) / <language> / <video_type>
    """
    col_subdir = "_4_columns" if include_script_changed else "_3_columns"

    if custom_dir:
        base = Path(custom_dir).resolve()
        if base.name in ("_3_columns", "_4_columns"):
            pass
        elif base.name == "synced_sheets":
            base = base / col_subdir
        else:
            base = base / "synced_sheets" / col_subdir
    else:
        d_drive_target = Path("D:/AI/output/connectivity/synced_sheets")
        try:
            if Path("D:/AI/output").exists() or Path("D:/").exists():
                d_drive_target.mkdir(parents=True, exist_ok=True)
                base = d_drive_target / col_subdir
            else:
                base = OUTPUT_DIR / "connectivity" / "synced_sheets" / col_subdir
        except Exception:
            base = OUTPUT_DIR / "connectivity" / "synced_sheets" / col_subdir

    if language and video_type:
        dest = base / language.strip().lower() / video_type.strip().lower()
    elif language:
        dest = base / language.strip().lower()
    else:
        dest = base

    dest.mkdir(parents=True, exist_ok=True)
    return dest


def fetch_sheet_data(endpoint_url: str, timeout: float = 60.0) -> List[Dict[str, str]]:
    """Fetches sheet rows and normalizes target columns (ID, expression, script, SCRIPT_CHANGED)."""
    raw_rows = fetch_raw_sheet_rows(endpoint_url, timeout=timeout)
    return normalize_sheet_rows(raw_rows)


def save_connectivity_data(
    records: List[Dict[str, str]],
    language: str = "french",
    video_type: str = "expression",
    output_dir: Optional[Path | str] = None,
    include_script_changed: bool = False,
    columns: Optional[List[str]] = None,
) -> Path:
    """
    Saves fetched records to CSV format inside:
    <output_dir>/<_3_columns or _4_columns>/<language>/<video_type>/<language>_<video_type>_connectivity.csv
    """
    lang_clean = language.strip().lower()
    type_clean = video_type.strip().lower()

    dest_dir = resolve_connectivity_output_dir(
        custom_dir=output_dir,
        language=lang_clean,
        video_type=type_clean,
        include_script_changed=include_script_changed,
    )

    filename_base = f"{lang_clean}_{type_clean}_connectivity"
    csv_path = dest_dir / f"{filename_base}.csv"

    if columns is not None:
        target_cols = columns
    elif include_script_changed:
        target_cols = FOUR_COLUMNS
    else:
        target_cols = TARGET_COLUMNS

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=target_cols)
        writer.writeheader()
        for rec in records:
            writer.writerow({col: rec.get(col, "") for col in target_cols})

    return csv_path


def sync_sheet(
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    url: Optional[str] = None,
    output_dir: Optional[Path | str] = None,
    sheet_id: Optional[str] = None,
    tab: Optional[str] = None,
    include_script_changed: bool = False,
) -> Dict[str, Any]:
    """Syncs a single sheet to D:\\AI\\output\\connectivity."""
    resolved_lang, resolved_type, endpoint_url = get_endpoint(
        language=language,
        video_type=video_type,
        custom_url=url,
        sheet_id=sheet_id,
        tab=tab,
    )

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    col_desc = "4 columns (ID, expression, script, SCRIPT_CHANGED)" if include_script_changed else "3 columns (ID, expression, script)"
    print(f"\n[CONNECTIVITY] Connecting to Google Sheets [{resolved_lang.capitalize()} - {resolved_type.upper()}]...")
    print(f"   Mode:     {col_desc}")
    print(f"   Endpoint: {endpoint_url}")

    records = fetch_sheet_data(endpoint_url)
    print(f"   [OK] Successfully fetched {len(records)} record(s) from sheet.")

    csv_file = save_connectivity_data(
        records=records,
        language=resolved_lang,
        video_type=resolved_type,
        output_dir=output_dir,
        include_script_changed=include_script_changed,
    )

    col_count = 4 if include_script_changed else 3
    print(f"   [SAVED] CSV ({col_count} cols): {csv_file}")

    return {
        "status": "success",
        "language": resolved_lang,
        "video_type": resolved_type,
        "count": len(records),
        "columns": FOUR_COLUMNS if include_script_changed else TARGET_COLUMNS,
        "include_script_changed": include_script_changed,
        "csv_path": str(csv_file),
        "records": records,
    }


def sync_all_sheets(
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    output_dir: Optional[Path | str] = None,
    include_script_changed: bool = False,
) -> Dict[str, Any]:
    """Syncs multiple Google Sheets in batch."""
    targets: List[Tuple[str, str]] = []
    lang_filter = language.strip().lower() if language and language.strip().lower() != "all" else None
    type_filter = video_type.strip().lower() if video_type and video_type.strip().lower() != "all" else None

    for (l, t), url in sorted(ENDPOINT_REGISTRY.items()):
        if not url:
            continue
        if lang_filter and l != lang_filter:
            continue
        if type_filter and t != type_filter:
            continue
        targets.append((l, t))

    col_str = "4 columns (ID, expression, script, SCRIPT_CHANGED) -> synced_sheets/_4_columns" if include_script_changed else "3 columns (ID, expression, script) -> synced_sheets/_3_columns"
    print(f"\n=======================================================")
    print(f"  BATCH GOOGLE SHEETS SYNC: {len(targets)} sheet(s) queued")
    print(f"  Export Mode: {col_str}")
    print(f"=======================================================")

    results = []
    failed = []
    total_records = 0

    for idx, (l, t) in enumerate(targets, 1):
        print(f"\n[{idx}/{len(targets)}] Syncing {l.capitalize()} - {t.upper()}...")
        try:
            res = sync_sheet(
                language=l,
                video_type=t,
                output_dir=output_dir,
                include_script_changed=include_script_changed,
            )
            results.append(res)
            total_records += res.get("count", 0)
        except Exception as e:
            print(f"   [ERROR] Failed to sync {l} - {t}: {e}", file=sys.stderr)
            failed.append({"language": l, "video_type": t, "error": str(e)})

    print(f"\n=======================================================")
    print(f"  BATCH SYNC FINISHED: {len(results)}/{len(targets)} succeeded, {len(failed)} failed.")
    print(f"  Total records fetched: {total_records}")
    print(f"=======================================================")

    return {
        "status": "success" if not failed else "partial",
        "total_sheets": len(targets),
        "succeeded_count": len(results),
        "failed_count": len(failed),
        "total_records": total_records,
        "include_script_changed": include_script_changed,
        "results": results,
        "failed": failed,
    }
