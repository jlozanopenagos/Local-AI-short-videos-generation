"""
fetcher.py — Fetch corrected scripts (Column D: SCRIPT_CHANGED) from Google Sheets.

Exports columns: 'ID', 'NEW_SCRIPT'
Destination: C:\\AI\\shorts_automation\\main\\input\\csv\\script_to_change\\<language>_<video_type>_script_to_change.csv
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from config import INPUT_CSV_DIR
    DEFAULT_OUTPUT_DIR = INPUT_CSV_DIR / "script_to_change"
except (ImportError, ModuleNotFoundError):
    REPO_ROOT = Path(__file__).resolve().parents[3]
    DEFAULT_OUTPUT_DIR = REPO_ROOT / "main" / "input" / "csv" / "script_to_change"

try:
    from connectivity.core import (
        get_endpoint,
        ENDPOINT_REGISTRY,
        fetch_raw_sheet_rows,
        normalize_sheet_rows,
    )
except (ImportError, ModuleNotFoundError):
    from main.connectivity.core import (
        get_endpoint,
        ENDPOINT_REGISTRY,
        fetch_raw_sheet_rows,
        normalize_sheet_rows,
    )

TARGET_COLUMNS = ["ID", "NEW_SCRIPT"]


def extract_numeric_id(script_id: str) -> Optional[int]:
    """Extracts integer number from script ID (e.g. 'FE05' -> 5, 'EE119' -> 119)."""
    match = re.search(r"\d+", script_id)
    return int(match.group()) if match else None


def load_ids_from_csv(csv_path: Path | str) -> Set[str]:
    """Reads a CSV file and extracts all IDs from an 'ID' column."""
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"Target IDs CSV file not found: {p}")

    ids: Set[str] = set()
    with p.open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return ids

        # Find ID column index
        id_idx = 0
        for idx, col_name in enumerate(header):
            if str(col_name).strip().upper() == "ID":
                id_idx = idx
                break

        for row in reader:
            if row and len(row) > id_idx:
                val = str(row[id_idx]).strip().upper()
                if val:
                    ids.add(val)

    return ids


def fetch_raw_corrected_records(endpoint_url: str, timeout: float = 60.0) -> List[Dict[str, str]]:
    """
    Fetches rows from sheet endpoint and extracts:
    - ID
    - NEW_SCRIPT (from Column D 'SCRIPT_CHANGED' or fallback)
    """
    raw_rows = fetch_raw_sheet_rows(endpoint_url, timeout=timeout)
    normalized = normalize_sheet_rows(raw_rows)

    records: List[Dict[str, str]] = []
    for row in normalized:
        row_id = row.get("ID", "").strip().upper()
        # SCRIPT_CHANGED is column D
        script_changed = row.get("SCRIPT_CHANGED", "").strip()

        if row_id:
            records.append({
                "ID": row_id,
                "NEW_SCRIPT": script_changed,
            })

    return records


def filter_corrected_records(
    records: List[Dict[str, str]],
    scope: str = "all",
    start_num: Optional[int] = None,
    end_num: Optional[int] = None,
    target_ids: Optional[Set[str] | List[str]] = None,
    require_non_empty_script: bool = True,
) -> List[Dict[str, str]]:
    """
    Filters records by scope:
    - 'all': All records in sheet (optionally filtered by non-empty script).
    - 'range': Records with numeric ID between start_num and end_num (inclusive).
    - 'ids': Records matching the set of target IDs.
    """
    scope_clean = scope.strip().lower()
    filtered: List[Dict[str, str]] = []

    id_set = {str(i).strip().upper() for i in (target_ids or []) if str(i).strip()}

    for rec in records:
        rec_id = rec["ID"]
        script = rec.get("NEW_SCRIPT", "")

        # Optional check: require non-empty changed script
        if require_non_empty_script and not script.strip():
            # If specifically targeted by ID, we still might want it, but by default skip empty
            if scope_clean not in ("ids", "range"):
                continue

        if scope_clean == "all":
            filtered.append(rec)

        elif scope_clean == "range":
            num = extract_numeric_id(rec_id)
            if num is not None:
                in_range = True
                if start_num is not None and num < start_num:
                    in_range = False
                if end_num is not None and num > end_num:
                    in_range = False
                if in_range:
                    filtered.append(rec)

        elif scope_clean == "ids":
            if rec_id in id_set:
                filtered.append(rec)

        else:
            filtered.append(rec)

    return filtered


def save_corrected_scripts_csv(
    records: List[Dict[str, str]],
    language: str,
    video_type: str,
    output_dir: Optional[Path | str] = None,
) -> Path:
    """
    Saves records to CSV:
    <output_dir>/<language>_<video_type>_script_to_change.csv
    Columns: ID, NEW_SCRIPT
    """
    dest_dir = Path(output_dir).resolve() if output_dir else DEFAULT_OUTPUT_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    lang_clean = language.strip().lower()
    type_clean = video_type.strip().lower()
    filename = f"{lang_clean}_{type_clean}_script_to_change.csv"
    dest_file = dest_dir / filename

    with dest_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TARGET_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "ID": rec.get("ID", ""),
                "NEW_SCRIPT": rec.get("NEW_SCRIPT", ""),
            })

    return dest_file


def fetch_and_save_corrected_scripts(
    language: str,
    video_type: str,
    scope: str = "all",
    start_num: Optional[int] = None,
    end_num: Optional[int] = None,
    target_ids: Optional[Set[str] | List[str]] = None,
    csv_file: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
    require_non_empty_script: bool = True,
) -> Tuple[Path, int]:
    """
    Orchestrates fetching corrected scripts for a specific sheet:
    1. Resolves endpoint URL.
    2. Fetches records with ID and SCRIPT_CHANGED.
    3. Applies scope filtering (all, range, IDs, or CSV file).
    4. Writes CSV to main/input/csv/script_to_change/<language>_<type>_script_to_change.csv.

    Returns:
        Tuple[Path, int]: (path_to_csv, number_of_records_saved)
    """
    resolved_lang, resolved_type, endpoint_url = get_endpoint(
        language=language,
        video_type=video_type,
    )

    print(f"\n[CORRECTED SCRIPTS] Connecting to [{resolved_lang.capitalize()} - {resolved_type.upper()}]...")
    print(f"   Endpoint: {endpoint_url}")

    records = fetch_raw_corrected_records(endpoint_url)

    # If CSV scope requested, read IDs from CSV
    if scope == "csv" and csv_file:
        loaded_ids = load_ids_from_csv(csv_file)
        filtered = filter_corrected_records(
            records=records,
            scope="ids",
            target_ids=loaded_ids,
            require_non_empty_script=False,
        )
    else:
        filtered = filter_corrected_records(
            records=records,
            scope=scope,
            start_num=start_num,
            end_num=end_num,
            target_ids=target_ids,
            require_non_empty_script=require_non_empty_script,
        )

    out_csv = save_corrected_scripts_csv(
        records=filtered,
        language=resolved_lang,
        video_type=resolved_type,
        output_dir=output_dir,
    )

    print(f"   [SAVED] {len(filtered)} script(s) -> {out_csv}")
    return out_csv, len(filtered)


def fetch_all_sheets_corrected_scripts(
    output_dir: Optional[Path | str] = None,
    require_non_empty_script: bool = True,
) -> List[Tuple[Path, int]]:
    """
    Fetches changed scripts across all 16 registered sheets.
    Generates a `<language>_<type>_script_to_change.csv` for each sheet that contains changes.
    """
    results: List[Tuple[Path, int]] = []

    print("\n=======================================================")
    print("  FETCHING CORRECTED SCRIPTS ACROSS ALL 16 SHEETS")
    print("=======================================================")

    for (lang, vtype), url in sorted(ENDPOINT_REGISTRY.items()):
        if not url:
            continue
        try:
            csv_path, count = fetch_and_save_corrected_scripts(
                language=lang,
                video_type=vtype,
                scope="all",
                output_dir=output_dir,
                require_non_empty_script=require_non_empty_script,
            )
            if count > 0:
                results.append((csv_path, count))
        except Exception as e:
            print(f"   [ERROR] Failed to fetch {lang} - {vtype}: {e}", file=sys.stderr)

    print("\n=======================================================")
    total_scripts = sum(cnt for _, cnt in results)
    print(f"  ALL SHEETS FETCH COMPLETED: {len(results)} files generated ({total_scripts} total scripts)")
    print("=======================================================\n")

    return results
