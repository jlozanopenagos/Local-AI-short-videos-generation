"""
client.py — HTTP Client for communicating with Google Apps Script Web App endpoints.

Handles:
- HTTP 302 redirects to script.googleusercontent.com
- User-Agent header and timeout management
- JSON error response and HTML error page parsing
- Row normalization for columns A, B, C, D (ID, expression, script, SCRIPT_CHANGED)
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def fetch_raw_sheet_rows(endpoint_url: str, timeout: float = 60.0) -> List[Dict[str, Any]]:
    """
    Fetches raw rows from Google Apps Script Web App endpoint.
    Automatically follows HTTP 302 redirects to script.googleusercontent.com.

    Returns:
        List[Dict[str, Any]]: Raw row objects from the 'data' array.
    """
    if not endpoint_url or not endpoint_url.strip():
        raise ValueError("No endpoint URL provided for Google Sheets client.")

    url = endpoint_url.strip()

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LingoVerse-Shorts-Automation/1.0"}
    )

    import time

    last_error: Optional[Exception] = None
    raw_text: Optional[str] = None

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                if status_code not in (200, 201):
                    raise ValueError(f"HTTP Error {status_code} received from Google Apps Script endpoint.")

                raw_bytes = response.read()
                raw_text = raw_bytes.decode("utf-8-sig")
                break
        except (urllib.error.HTTPError, urllib.error.URLError, ConnectionError) as err:
            last_error = err
            if attempt < 3:
                time.sleep(1.5 * attempt)
            else:
                if isinstance(err, urllib.error.HTTPError):
                    raise ConnectionError(f"Google Apps Script HTTP Error {err.code}: {err.reason}") from err
                raise ConnectionError(f"Could not connect to Google Apps Script endpoint: {err}") from err

    if raw_text is None:
        raise ConnectionError(f"Could not connect to Google Apps Script endpoint: {last_error}")

    # Parse JSON response
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as je:
        if raw_text.lstrip().startswith(("<", "<!DOCTYPE")):
            body_match = re.search(r'<body[^>]*>(.*?)</body>', raw_text, re.IGNORECASE | re.DOTALL)
            if body_match:
                clean_err = re.sub(r'<[^>]+>', ' ', body_match.group(1)).strip()
                clean_err = " ".join(clean_err.split())
                raise RuntimeError(
                    f"Google Apps Script returned an error page: '{clean_err}'. "
                    f"Please ensure you pasted the Apps Script code (main/connectivity/google_apps_script.js) "
                    f"into Extensions > Apps Script and deployed a new version."
                )
        raise ValueError(f"Endpoint returned invalid JSON: {je}. Preview: {raw_text[:200]}") from je

    if isinstance(payload, list):
        raw_rows = payload
    elif isinstance(payload, dict):
        if payload.get("status") == "error":
            raise RuntimeError(f"Google Apps Script reported an error: {payload.get('message')}")
        raw_rows = payload.get("data", [])
        if not isinstance(raw_rows, list):
            raw_rows = []
    else:
        raise ValueError("Unexpected JSON structure from endpoint: expected list or dict with 'data' array.")

    return [r for r in raw_rows if isinstance(r, dict)]


def normalize_sheet_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Normalizes rows into guaranteed keys:
    - 'ID'
    - 'expression'
    - 'script'
    - 'SCRIPT_CHANGED'
    """
    normalized_records: List[Dict[str, str]] = []

    for row in raw_rows:
        if not isinstance(row, dict):
            continue

        record: Dict[str, str] = {
            "ID": "",
            "expression": "",
            "script": "",
            "SCRIPT_CHANGED": "",
        }

        for k, v in row.items():
            k_upper = str(k).strip().upper()
            val = str(v).strip() if v is not None else ""

            if k_upper == "ID":
                record["ID"] = val.upper()
            elif k_upper in ("EXPRESSION", "TOPIC", "SUBJECT"):
                record["expression"] = val
            elif k_upper in ("SCRIPT", "ORIGINAL_SCRIPT"):
                record["script"] = val
            elif k_upper in ("SCRIPT_CHANGED", "SCRIPT CHANGED", "NEW_SCRIPT", "CORRECTED_SCRIPT"):
                record["SCRIPT_CHANGED"] = val

        # Fallback script to SCRIPT_CHANGED if original script is empty
        if not record["script"] and record["SCRIPT_CHANGED"]:
            record["script"] = record["SCRIPT_CHANGED"]

        # Only retain rows where ID is present
        if record["ID"]:
            normalized_records.append(record)

    return normalized_records


def post_sheet_rows(
    endpoint_url: str,
    rows: List[Dict[str, Any]],
    spreadsheet_id: Optional[str] = None,
    sheet_tab: Optional[str] = None,
    timeout: float = 60.0
) -> Dict[str, Any]:
    """
    Sends rows to Google Apps Script Web App (doPost) to update Columns A, B, and C.
    Automatically follows HTTP 302 redirects to script.googleusercontent.com.
    Retries up to 3 times on transient network drops with backoff.

    Args:
        endpoint_url: Web App execution URL
        rows: List of dicts with keys 'ID', 'expression', 'script'
        spreadsheet_id: Optional target spreadsheet ID
        sheet_tab: Optional tab name
        timeout: Request timeout in seconds

    Returns:
        Dict[str, Any]: Response from Google Apps Script with updated/appended counts.
    """
    import time
    import requests

    if not endpoint_url or not endpoint_url.strip():
        raise ValueError("No endpoint URL provided for Google Sheets client.")

    if not rows:
        return {
            "status": "success",
            "message": "No rows to post.",
            "updated_count": 0,
            "appended_count": 0,
            "total_affected": 0,
        }

    payload: Dict[str, Any] = {
        "action": "update_scripts",
        "rows": rows,
    }
    if spreadsheet_id and spreadsheet_id.strip():
        payload["spreadsheet_id"] = spreadsheet_id.strip()
    if sheet_tab and sheet_tab.strip():
        payload["sheet"] = sheet_tab.strip()

    url = endpoint_url.strip()
    last_error: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"User-Agent": "LingoVerse-Shorts-Automation/1.0"},
                timeout=timeout,
                allow_redirects=True,
            )

            raw_text = resp.text

            # Check if an HTML error page was returned
            if raw_text.lstrip().startswith(("<", "<!DOCTYPE")):
                body_match = re.search(r'<body[^>]*>(.*?)</body>', raw_text, re.IGNORECASE | re.DOTALL)
                clean_err = raw_text[:200]
                if body_match:
                    clean_err = re.sub(r'<[^>]+>', ' ', body_match.group(1)).strip()
                    clean_err = " ".join(clean_err.split())
                raise RuntimeError(
                    f"Google Apps Script returned an error page: '{clean_err}'. "
                    f"Please ensure you pasted the updated Apps Script code (main/connectivity/google_apps_script.js) "
                    f"with 'doPost' into Extensions > Apps Script and deployed a New version."
                )

            if resp.status_code not in (200, 201):
                raise ValueError(f"HTTP Error {resp.status_code} received from Google Apps Script endpoint: {raw_text[:300]}")

            try:
                data = resp.json()
            except Exception as je:
                raise ValueError(f"Endpoint returned non-JSON response: {je}. Preview: {raw_text[:200]}") from je

            if isinstance(data, dict):
                if data.get("status") == "error":
                    raise RuntimeError(f"Google Apps Script reported an error: {data.get('message')}")
                return data

            raise ValueError(f"Unexpected JSON response from endpoint: expected dict, got {type(data).__name__}")

        except (requests.RequestException, RuntimeError, ValueError) as err:
            last_error = err
            if isinstance(err, RuntimeError) and "Google Apps Script returned an error page" in str(err):
                # Don't retry configuration/deployment errors
                raise err
            if attempt < 3:
                time.sleep(1.5 * attempt)
            else:
                raise ConnectionError(f"Could not update Google Sheets endpoint: {err}") from err

    raise ConnectionError(f"Could not update Google Sheets endpoint: {last_error}")

