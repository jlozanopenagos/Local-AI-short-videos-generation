"""
poster.py — Service for posting scripts from D:\\AI\\output\\scripts_to_see to Google Sheets.

Safety Guarantee:
- Only modifies Columns A (ID), B (expression), and C (script).
- Preserves Column D (SCRIPT_CHANGED) without modification.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from connectivity.core.endpoints import (
    ENDPOINT_REGISTRY,
    MASTER_WEBAPP_URL,
    build_fetch_url,
    extract_spreadsheet_id,
    get_endpoint,
)
from connectivity.core.client import post_sheet_rows

# Default source directory for scripts to see
DEFAULT_SCRIPTS_TO_SEE_DIR = Path(r"D:\AI\output\scripts_to_see")


def get_source_csv_path(language: str, video_type: str, base_dir: Optional[Path] = None) -> Path:
    """
    Returns the expected CSV path for a language and video type in scripts_to_see.
    Example: D:\\AI\\output\\scripts_to_see\\french\\expression\\french_expression_scripts.csv
    """
    root = Path(base_dir) if base_dir else DEFAULT_SCRIPTS_TO_SEE_DIR
    lang = language.strip().lower()
    vtype = video_type.strip().lower()
    return root / lang / vtype / f"{lang}_{vtype}_scripts.csv"


def load_source_scripts_csv(csv_path: Path | str) -> List[Dict[str, str]]:
    """
    Loads and normalizes script rows from a CSV in scripts_to_see.
    Uses 'utf-8-sig' to automatically handle UTF-8 BOM.
    Guarantees output keys: 'ID', 'expression', 'script'.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Source scripts CSV not found at: {path}")

    rows: List[Dict[str, str]] = []
    with path.open(mode="r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return rows

        for row in reader:
            record: Dict[str, str] = {"ID": "", "expression": "", "script": ""}
            for k, v in row.items():
                if not k:
                    continue
                k_clean = str(k).strip().upper()
                v_clean = str(v).strip() if v is not None else ""

                if k_clean == "ID":
                    record["ID"] = v_clean
                elif k_clean in ("EXPRESSION", "TOPIC", "SUBJECT"):
                    record["expression"] = v_clean
                elif k_clean in ("SCRIPT", "ORIGINAL_SCRIPT", "TEXT"):
                    record["script"] = v_clean

            if record["ID"]:
                rows.append(record)

    return rows


def parse_range_spec(range_spec: str) -> Tuple[int, int]:
    """
    Parses a range string like '10-20', '01-50', or 'FE10-FE20' into integer (start, end).
    """
    cleaned = range_spec.strip()
    match = re.match(r"^[A-Za-z]*(\d+)\s*[-–—:]\s*[A-Za-z]*(\d+)$", cleaned)
    if not match:
        raise ValueError(
            f"Invalid range format '{range_spec}'. Expected formats: '10-20', '01-50', or 'FE10-FE20'."
        )
    start_val = int(match.group(1))
    end_val = int(match.group(2))
    if start_val > end_val:
        start_val, end_val = end_val, start_val
    return start_val, end_val


def filter_scripts(
    rows: List[Dict[str, str]],
    mode: str = "all",
    range_spec: Optional[str] = None,
    ids: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """
    Filters a list of script rows by mode:
    - 'all': returns all rows.
    - 'range': filters rows whose ID numeric digits (or 1-based index) fall within range_spec.
    - 'ids': filters rows matching any of the provided IDs.
    """
    clean_mode = (mode or "all").strip().lower()

    if clean_mode == "all":
        return list(rows)

    if clean_mode in ("range", "by_range"):
        if not range_spec:
            raise ValueError("range_spec is required when filtering by range (e.g. '10-20').")
        start_idx, end_idx = parse_range_spec(range_spec)

        filtered: List[Dict[str, str]] = []
        for i, row in enumerate(rows, start=1):
            row_id = row.get("ID", "")
            # Try extracting digits from the ID
            digits = re.findall(r"\d+", row_id)
            if digits:
                id_num = int(digits[-1])
                if start_idx <= id_num <= end_idx:
                    filtered.append(row)
                    continue

            # Fallback to row index in CSV
            if start_idx <= i <= end_idx:
                filtered.append(row)

        return filtered

    if clean_mode in ("ids", "by_ids"):
        if not ids:
            raise ValueError("ids list is required when filtering by IDs.")

        normalized_ids: Set[str] = set()
        numeric_ids: Set[int] = set()

        for item in ids:
            # Handle comma/space separated sub-strings
            parts = re.split(r"[\s,]+", str(item).strip())
            for part in parts:
                p = part.strip().upper()
                if p:
                    normalized_ids.add(p)
                    # If digits only, store numeric form too
                    if p.isdigit():
                        numeric_ids.add(int(p))

        filtered = []
        for row in rows:
            row_id = row.get("ID", "").strip().upper()
            if row_id in normalized_ids:
                filtered.append(row)
                continue

            # Numeric comparison fallback
            digits = re.findall(r"\d+", row_id)
            if digits and int(digits[-1]) in numeric_ids:
                filtered.append(row)

        return filtered

    raise ValueError(f"Unknown filter mode '{mode}'. Choose from 'all', 'range', or 'ids'.")


def post_single_sheet(
    language: str,
    video_type: str,
    mode: str = "all",
    range_spec: Optional[str] = None,
    ids: Optional[List[str]] = None,
    source_dir: Optional[Path] = None,
    endpoint_url: Optional[str] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Posts scripts for a single sheet (language and video type) to Google Sheets.
    Affects only Columns A, B, and C. Preserves Column D.

    Returns:
        Dict[str, Any]: Summary of operation including counts and target details.
    """
    csv_path = get_source_csv_path(language, video_type, base_dir=source_dir)
    all_rows = load_source_scripts_csv(csv_path)

    filtered_rows = filter_scripts(
        all_rows,
        mode=mode,
        range_spec=range_spec,
        ids=ids,
    )

    if not filtered_rows:
        return {
            "status": "success",
            "language": language,
            "video_type": video_type,
            "csv_path": str(csv_path),
            "total_in_csv": len(all_rows),
            "filtered_count": 0,
            "updated_count": 0,
            "appended_count": 0,
            "total_affected": 0,
            "message": "No rows matched the filter criteria.",
        }

    # Resolve target endpoint and spreadsheet ID
    lang_key = language.strip().lower()
    type_key = video_type.strip().lower()

    if endpoint_url:
        configured_url = endpoint_url
    else:
        _, _, configured_url = get_endpoint(lang_key, type_key)

    raw_target = ENDPOINT_REGISTRY.get((lang_key, type_key), "")
    spreadsheet_id = extract_spreadsheet_id(raw_target) or extract_spreadsheet_id(configured_url)

    # Use master URL for POST if configured_url points to master router
    post_url = MASTER_WEBAPP_URL
    if configured_url and "script.google.com" in configured_url and "?" not in configured_url:
        post_url = configured_url

    api_response = post_sheet_rows(
        endpoint_url=post_url,
        rows=filtered_rows,
        spreadsheet_id=spreadsheet_id,
        timeout=timeout,
    )

    return {
        "status": "success",
        "language": lang_key,
        "video_type": type_key,
        "csv_path": str(csv_path),
        "spreadsheet_id": spreadsheet_id,
        "post_url": post_url,
        "total_in_csv": len(all_rows),
        "filtered_count": len(filtered_rows),
        "updated_count": api_response.get("updated_count", 0),
        "appended_count": api_response.get("appended_count", 0),
        "total_affected": api_response.get("total_affected", len(filtered_rows)),
        "api_response": api_response,
    }


def post_all_sheets(
    source_dir: Optional[Path] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Posts all rows from all 16 scripts_to_see CSVs to their corresponding Google Sheets.
    """
    results: List[Dict[str, Any]] = []
    total_updated = 0
    total_appended = 0
    total_posted = 0
    errors: List[Dict[str, str]] = []

    for (lang, vtype) in ENDPOINT_REGISTRY.keys():
        try:
            res = post_single_sheet(
                language=lang,
                video_type=vtype,
                mode="all",
                source_dir=source_dir,
                timeout=timeout,
            )
            results.append(res)
            total_updated += res.get("updated_count", 0)
            total_appended += res.get("appended_count", 0)
            total_posted += res.get("filtered_count", 0)
        except Exception as e:
            errors.append({
                "language": lang,
                "video_type": vtype,
                "error": str(e),
            })

    return {
        "status": "success" if not errors else "partial_success",
        "total_sheets": len(ENDPOINT_REGISTRY),
        "successful_sheets": len(results),
        "failed_sheets": len(errors),
        "total_posted": total_posted,
        "total_updated": total_updated,
        "total_appended": total_appended,
        "results": results,
        "errors": errors,
    }
