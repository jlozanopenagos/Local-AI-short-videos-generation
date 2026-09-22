"""
sheets_fetcher.py — Fetch and process data from Google Sheets Apps Script Web App endpoints.

Fetches 3 target columns: 'ID', 'expression', 'SCRIPT_CHANGED'
Saves output to: D:\\AI\\output\\connectivity (or configured OUTPUT_DIR / connectivity)
"""

from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from config import OUTPUT_DIR, BASE_DIR
except (ImportError, ModuleNotFoundError):
    BASE_DIR = Path(__file__).resolve().parents[2]
    OUTPUT_DIR = Path("D:/AI/output") if Path("D:/AI/output").exists() else (BASE_DIR / "output")

try:
    from connectivity.endpoints import get_endpoint, DEFAULT_FRENCH_EXPRESSION_URL
except (ImportError, ModuleNotFoundError):
    try:
        from main.connectivity.endpoints import get_endpoint, DEFAULT_FRENCH_EXPRESSION_URL
    except (ImportError, ModuleNotFoundError):
        from endpoints import get_endpoint, DEFAULT_FRENCH_EXPRESSION_URL


# Default expected columns
TARGET_COLUMNS = ["ID", "expression", "SCRIPT_CHANGED"]


def resolve_connectivity_output_dir(custom_dir: Optional[Path | str] = None) -> Path:
    """
    Resolves the destination directory for connectivity data.
    Preferred location: D:\\AI\\output\\connectivity
    Fallback: OUTPUT_DIR / connectivity
    """
    if custom_dir:
        out = Path(custom_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        return out

    # Check preferred D: drive path
    d_drive_target = Path("D:/AI/output/connectivity")
    try:
        if Path("D:/AI/output").exists() or Path("D:/").exists():
            d_drive_target.mkdir(parents=True, exist_ok=True)
            return d_drive_target
    except Exception:
        pass

    # Fallback to configured OUTPUT_DIR
    fallback_target = OUTPUT_DIR / "connectivity"
    fallback_target.mkdir(parents=True, exist_ok=True)
    return fallback_target


def fetch_sheet_data(endpoint_url: str, timeout: float = 30.0) -> List[Dict[str, str]]:
    """
    Fetches data from the Google Apps Script Web App endpoint.
    Automatically follows HTTP 302 redirects to script.googleusercontent.com.

    Returns:
        List[Dict[str, str]]: Records containing keys 'ID', 'expression', 'SCRIPT_CHANGED'.
    """
    if not endpoint_url or not endpoint_url.strip():
        raise ValueError("No endpoint URL provided for Google Sheets fetcher.")

    url = endpoint_url.strip()

    # Build request with user-agent to avoid generic bot blocks
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LingoVerse-Shorts-Automation/1.0"}
    )

    try:
        # urllib.request.urlopen automatically follows standard HTTP redirects (301, 302, 307)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            if status_code not in (200, 201):
                raise ValueError(f"HTTP Error {status_code} received from Google Apps Script endpoint.")

            raw_bytes = response.read()
            raw_text = raw_bytes.decode("utf-8-sig")

    except urllib.error.HTTPError as he:
        raise ConnectionError(f"Google Apps Script HTTP Error {he.code}: {he.reason}") from he
    except urllib.error.URLError as ue:
        raise ConnectionError(f"Could not connect to Google Apps Script endpoint: {ue.reason}") from ue

    # Parse JSON response
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as je:
        if raw_text.lstrip().startswith(("<", "<!DOCTYPE")):
            import re
            body_match = re.search(r'<body[^>]*>(.*?)</body>', raw_text, re.IGNORECASE | re.DOTALL)
            if body_match:
                # Strip tags and excess whitespace
                clean_err = re.sub(r'<[^>]+>', ' ', body_match.group(1)).strip()
                clean_err = " ".join(clean_err.split())
                raise RuntimeError(
                    f"Google Apps Script returned an error page: '{clean_err}'. "
                    f"Please ensure you pasted the Apps Script code (main/connectivity/google_apps_script.js) "
                    f"into Extensions > Apps Script and deployed a new version."
                )
        raise ValueError(f"Endpoint returned invalid JSON: {je}. Preview: {raw_text[:200]}") from je

    # Extract list of rows from response
    if isinstance(payload, list):
        raw_rows = payload
    elif isinstance(payload, dict):
        if payload.get("status") == "error":
            raise RuntimeError(f"Google Apps Script reported an error: {payload.get('message')}")
        raw_rows = payload.get("data", [])
        if not isinstance(raw_rows, list):
            raw_rows = []
    else:
        raise ValueError(f"Unexpected JSON structure from endpoint: expected list or dict with 'data' array.")

    # Normalize rows to guarantee 'ID', 'expression', 'SCRIPT_CHANGED'
    normalized_records: List[Dict[str, str]] = []

    for row in raw_rows:
        if not isinstance(row, dict):
            continue

        # Case-insensitive lookup for the 3 target columns
        record: Dict[str, str] = {
            "ID": "",
            "expression": "",
            "SCRIPT_CHANGED": "",
        }

        for k, v in row.items():
            k_upper = str(k).strip().upper()
            val = str(v).strip() if v is not None else ""

            if k_upper == "ID":
                record["ID"] = val.upper()
            elif k_upper in ("EXPRESSION", "TOPIC", "SUBJECT"):
                record["expression"] = val
            elif k_upper in ("SCRIPT_CHANGED", "SCRIPT CHANGED", "NEW_SCRIPT", "SCRIPT"):
                record["SCRIPT_CHANGED"] = val

        # Retain row only if ID is present
        if record["ID"]:
            normalized_records.append(record)

    return normalized_records


def save_connectivity_data(
    records: List[Dict[str, str]],
    language: str = "french",
    video_type: str = "expression",
    output_dir: Optional[Path | str] = None,
) -> Tuple[Path, Path]:
    """
    Saves the fetched records to both CSV and JSON formats inside the connectivity output directory.

    Output files:
    - <output_dir>/<lang>_<type>_connectivity.csv
    - <output_dir>/<lang>_<type>_connectivity.json

    Returns:
        Tuple[Path, Path]: (csv_path, json_path)
    """
    dest_dir = resolve_connectivity_output_dir(output_dir)

    lang_clean = language.strip().lower()
    type_clean = video_type.strip().lower()
    filename_base = f"{lang_clean}_{type_clean}_connectivity"

    csv_path = dest_dir / f"{filename_base}.csv"
    json_path = dest_dir / f"{filename_base}.json"

    # 1. Write CSV
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TARGET_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow({col: rec.get(col, "") for col in TARGET_COLUMNS})

    # 2. Write JSON
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "language": lang_clean,
                "video_type": type_clean,
                "count": len(records),
                "records": records,
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    return csv_path, json_path


def sync_sheet(
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    url: Optional[str] = None,
    output_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    High-level modular orchestration function:
    1. Resolves target endpoint URL.
    2. Fetches data with automatic 302 redirect handling.
    3. Normalizes 'ID', 'expression', 'SCRIPT_CHANGED' columns.
    4. Saves to D:\\AI\\output\\connectivity (or fallback).

    Returns:
        Dict[str, Any] summary of the sync operation.
    """
    resolved_lang, resolved_type, endpoint_url = get_endpoint(
        language=language,
        video_type=video_type,
        custom_url=url,
    )

    # Reconfigure streams if supported to prevent Windows charmap encoding errors
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(f"\n[CONNECTIVITY] Connecting to Google Sheets [{resolved_lang.capitalize()} - {resolved_type.upper()}]...")
    print(f"   Endpoint: {endpoint_url}")

    records = fetch_sheet_data(endpoint_url)
    print(f"   [OK] Successfully fetched {len(records)} record(s) from sheet.")

    csv_file, json_file = save_connectivity_data(
        records=records,
        language=resolved_lang,
        video_type=resolved_type,
        output_dir=output_dir,
    )

    print(f"   [SAVED] CSV:  {csv_file}")
    print(f"   [SAVED] JSON: {json_file}")

    return {
        "status": "success",
        "language": resolved_lang,
        "video_type": resolved_type,
        "count": len(records),
        "csv_path": str(csv_file),
        "json_path": str(json_file),
        "records": records,
    }
