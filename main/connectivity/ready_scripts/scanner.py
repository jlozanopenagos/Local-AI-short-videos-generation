"""
scanner.py — Service for scanning Google Sheets for ready scripts (Columns E through H).

Rules:
1. Scans Google Sheets (all 16 sheets or a single targeted sheet).
2. Checks Column E (script_ready) and Column G (video_ready).
3. If video_ready is checked (True), the row is strictly SKIPPED (already completed).
4. If script_ready is checked (True) and video_ready is not checked (False), extracts:
   - ID (Column A)
   - expression (Column B)
   - script_date (Column F)
5. Groups records by normalized script_date (YYYY-MM-DD).
   - If script_date is blank, groups into 'undated'.
6. Writes clean CSV files to D:\\AI\\output\\connectivity\\ready_scripts\\:
   - <YYYY-MM-DD>_ready_scripts.csv
   - undated_ready_scripts.csv (if any scripts lack dates)
   - Schema: ID, expression
7. Merges with existing records in destination files by ID without duplicate entries.
"""

from __future__ import annotations

import csv
import datetime
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from connectivity.core.client import fetch_raw_sheet_rows
from connectivity.core.endpoints import (
    ENDPOINT_REGISTRY,
    extract_spreadsheet_id,
    get_endpoint,
)

DEFAULT_READY_SCRIPTS_DIR = Path(r"D:\AI\output\connectivity\ready_scripts")


def resolve_ready_scripts_output_dir(output_dir: Optional[Path | str] = None) -> Path:
    """
    Resolves destination directory for ready scripts.
    Priority:
    1. Explicit output_dir argument
    2. OUTPUT_DIR env var -> <OUTPUT_DIR>/connectivity/ready_scripts
    3. Fallback: D:\\AI\\output\\connectivity\\ready_scripts
    """
    if output_dir:
        return Path(output_dir)

    env_output = os.getenv("OUTPUT_DIR", "").strip()
    if env_output:
        resolved = Path(env_output) / "connectivity" / "ready_scripts"
        return resolved

    return DEFAULT_READY_SCRIPTS_DIR


def is_checkbox_checked(val: Any) -> bool:
    """
    Determines whether a Google Sheets cell value represents a checked checkbox.
    Supports booleans, numeric 1/0, and diverse string truthy representations.
    """
    if val is True:
        return True
    if val is False or val is None:
        return False
    if isinstance(val, (int, float)):
        return bool(val)

    val_str = str(val).strip().lower()
    return val_str in ("true", "1", "yes", "checked", "x", "t", "v", "si", "oui")


def normalize_date_str(val: Any) -> str:
    """
    Normalizes a cell date value into canonical YYYY-MM-DD string.
    Handles:
    - datetime / date objects
    - ISO strings (e.g. 2026-09-23T05:00:00.000Z)
    - YYYY-MM-DD / YYYY/MM/DD
    - DD/MM/YYYY / MM/DD/YYYY
    - DD-MM-YYYY / MM-DD-YYYY
    Returns empty string if blank or unrecognizable.
    """
    if not val:
        return ""

    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.strftime("%Y-%m-%d")

    val_str = str(val).strip()
    if not val_str:
        return ""

    # ISO format match (e.g. 2026-09-23T...)
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:T|\s|$)", val_str)
    if iso_match:
        year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            d = datetime.date(year, month, day)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try standard string date formats
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ):
        try:
            parsed = datetime.datetime.strptime(val_str, fmt).date()
            return parsed.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

    # RegEx fallback for slash or dash dates: e.g. 23/09/2026 or 09/23/2026
    slash_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", val_str)
    if slash_match:
        p1, p2, year = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        # If p1 > 12, it must be DD/MM/YYYY
        if p1 > 12 and p2 <= 12:
            day, month = p1, p2
        elif p2 > 12 and p1 <= 12:
            month, day = p1, p2
        else:
            # Default to DD/MM/YYYY
            day, month = p1, p2
        try:
            d = datetime.date(year, month, day)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def filter_ready_scripts(raw_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Filters raw sheet records according to readiness criteria:
    - Included: script_ready is True AND video_ready is False.
    - Excluded: video_ready is True (already completed video).
    - Excluded: script_ready is False (script not ready).

    Returns:
        Dict with ready records list and filtering statistics.
    """
    ready_records: List[Dict[str, str]] = []
    total_count = 0
    video_ready_excluded_count = 0
    not_script_ready_count = 0
    missing_id_count = 0

    for row in raw_records:
        if not isinstance(row, dict):
            continue

        # Locate ID
        id_val = ""
        for k in ("ID", "SCRIPT_ID", "id"):
            if k in row and row[k]:
                id_val = str(row[k]).strip().upper()
                break

        if not id_val:
            missing_id_count += 1
            continue

        total_count += 1

        # Locate video_ready checkbox
        video_ready_val = False
        for k in ("video_ready", "VIDEO_READY", "VIDEO READY", "READY_VIDEO", "VIDEO_DONE"):
            if k in row:
                video_ready_val = is_checkbox_checked(row[k])
                break

        # If video_ready is checked, SKIP immediately
        if video_ready_val:
            video_ready_excluded_count += 1
            continue

        # Locate script_ready checkbox
        script_ready_val = False
        for k in ("script_ready", "SCRIPT_READY", "SCRIPT READY", "READY_SCRIPT", "READY"):
            if k in row:
                script_ready_val = is_checkbox_checked(row[k])
                break

        # If script_ready is not checked, SKIP
        if not script_ready_val:
            not_script_ready_count += 1
            continue

        # Extract expression
        expr_val = ""
        for k in ("expression", "EXPRESSION", "TOPIC", "SUBJECT"):
            if k in row and row[k]:
                expr_val = str(row[k]).strip()
                break

        # Extract script_date
        raw_date = ""
        for k in ("script_date", "SCRIPT_DATE", "SCRIPT DATE", "DATE"):
            if k in row and row[k]:
                raw_date = row[k]
                break

        normalized_date = normalize_date_str(raw_date)
        date_key = normalized_date if normalized_date else "undated"

        ready_records.append({
            "ID": id_val,
            "expression": expr_val,
            "script_date": date_key,
        })

    return {
        "ready_records": ready_records,
        "total_evaluated": total_count,
        "ready_count": len(ready_records),
        "video_ready_excluded_count": video_ready_excluded_count,
        "not_script_ready_count": not_script_ready_count,
        "missing_id_count": missing_id_count,
    }


def scan_sheet_ready_scripts(
    language: str,
    video_type: str,
    custom_url: Optional[str] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Connects to Google Sheets for a specific language and video type,
    fetches raw records, and filters for ready scripts.
    """
    lang_key = language.strip().lower()
    type_key = video_type.strip().lower()

    _, _, fetch_url = get_endpoint(lang_key, type_key, custom_url=custom_url)
    raw_target = ENDPOINT_REGISTRY.get((lang_key, type_key), "")
    spreadsheet_id = extract_spreadsheet_id(raw_target) or extract_spreadsheet_id(fetch_url)

    raw_rows = fetch_raw_sheet_rows(fetch_url, timeout=timeout)
    filtering_result = filter_ready_scripts(raw_rows)

    return {
        "status": "success",
        "language": lang_key,
        "video_type": type_key,
        "spreadsheet_id": spreadsheet_id,
        "endpoint_url": fetch_url,
        "total_evaluated": filtering_result["total_evaluated"],
        "ready_count": filtering_result["ready_count"],
        "video_ready_excluded_count": filtering_result["video_ready_excluded_count"],
        "not_script_ready_count": filtering_result["not_script_ready_count"],
        "ready_records": filtering_result["ready_records"],
    }


def scan_all_sheets_ready_scripts(
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Scans all 16 registered Google Sheets, filters for ready scripts,
    and groups all ready records across sheets by script_date.

    Returns:
        Dict containing aggregated date groups, statistics, and individual sheet summaries.
    """
    sheet_summaries: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    date_groups: Dict[str, List[Dict[str, str]]] = {}

    total_evaluated = 0
    total_ready = 0
    total_video_ready_excluded = 0
    successful_sheets = 0

    for (lang, vtype) in ENDPOINT_REGISTRY.keys():
        try:
            res = scan_sheet_ready_scripts(lang, vtype, timeout=timeout)
            successful_sheets += 1
            total_evaluated += res["total_evaluated"]
            total_ready += res["ready_count"]
            total_video_ready_excluded += res["video_ready_excluded_count"]
            sheet_summaries.append(res)

            # Group ready records by date
            for rec in res["ready_records"]:
                d_key = rec.get("script_date", "undated")
                if d_key not in date_groups:
                    date_groups[d_key] = []
                date_groups[d_key].append(rec)

        except Exception as err:
            errors.append({
                "language": lang,
                "video_type": vtype,
                "error": str(err),
            })

    # Sort records inside each date group by ID
    for d_key in date_groups:
        date_groups[d_key].sort(key=lambda r: r["ID"])

    return {
        "status": "success" if not errors else ("partial" if successful_sheets > 0 else "error"),
        "total_sheets": len(ENDPOINT_REGISTRY),
        "successful_sheets": successful_sheets,
        "failed_sheets": len(errors),
        "total_evaluated": total_evaluated,
        "total_ready": total_ready,
        "total_video_ready_excluded": total_video_ready_excluded,
        "date_groups": date_groups,
        "sheet_summaries": sheet_summaries,
        "errors": errors,
    }


def save_ready_scripts_by_date(
    date_groups: Dict[str, List[Dict[str, str]]],
    output_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Saves grouped ready script records into daily CSV files in output_dir.
    Files:
      - <YYYY-MM-DD>_ready_scripts.csv
      - undated_ready_scripts.csv (for items without dates)

    Schema: ID, expression
    Deduplication: Merges with existing IDs in the target file to avoid duplicates on multiple runs.

    Returns:
        Dict mapping date keys to file save information.
    """
    target_dir = resolve_ready_scripts_output_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files: Dict[str, Dict[str, Any]] = {}

    for date_key, records in date_groups.items():
        if not records:
            continue

        if date_key == "undated":
            file_name = "undated_ready_scripts.csv"
        else:
            file_name = f"{date_key}_ready_scripts.csv"

        file_path = target_dir / file_name

        # Merge with existing records in file if it already exists
        existing_records: List[Dict[str, str]] = []
        seen_ids = set()

        if file_path.exists():
            try:
                with file_path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        rid = str(row.get("ID", "")).strip().upper()
                        if rid:
                            existing_records.append({
                                "ID": rid,
                                "expression": str(row.get("expression", "")).strip(),
                            })
                            seen_ids.add(rid)
            except Exception:
                existing_records = []
                seen_ids = set()

        # Update existing records or append new records
        merged_map: Dict[str, str] = {r["ID"]: r["expression"] for r in existing_records}
        for rec in records:
            rid = rec["ID"]
            expr = rec["expression"]
            merged_map[rid] = expr
            if rid not in seen_ids:
                seen_ids.add(rid)
                existing_records.append({"ID": rid, "expression": expr})
            else:
                # Update expression in-place
                for ex in existing_records:
                    if ex["ID"] == rid:
                        ex["expression"] = expr
                        break

        # Write merged records
        with file_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "expression"])
            writer.writeheader()
            for r in existing_records:
                writer.writerow(r)

        saved_files[date_key] = {
            "file_path": str(file_path),
            "file_name": file_name,
            "total_items": len(existing_records),
            "new_items_added": len(records),
            "is_undated": (date_key == "undated"),
        }

    return {
        "status": "success",
        "output_dir": str(target_dir),
        "saved_files": saved_files,
        "total_files": len(saved_files),
    }
