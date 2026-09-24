"""
service.py — Reconcile service for auditing and reorganizing local scripts against Google Sheets data.

Compares:
- Local scripts: D:\\AI\\output\\scripts_to_see\\<lang>\\<type>\\<lang>_<type>_scripts.csv
- Google Sheets snapshot: D:\\AI\\output\\connectivity\\_3_columns\\<lang>\\<type>\\<lang>_<type>_connectivity.csv

Reorganization rules:
1. Preserves the exact ordering of Google Sheets.
2. For matching IDs, uses Google Sheets canonical expression name, and updates the script from local.
3. For local entries not in Google Sheets (e.g. FF06-FF15), appends them to the end of the file.
4. For Google Sheets entries not in local, preserves them in place.
5. Saves clean result to D:\\AI\\output\\connectivity\\scripts_to_post\\<lang>\\<type>\\<lang>_<type>_scripts.csv
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_SCRIPTS_TO_SEE_DIR = Path(r"D:\AI\output\scripts_to_see")
DEFAULT_CONNECTIVITY_DIR = Path(r"D:\AI\output\connectivity\synced_sheets\_3_columns")
DEFAULT_SCRIPTS_TO_POST_DIR = Path(r"D:\AI\output\connectivity\scripts_to_post")

LANGUAGES = ["french", "spanish", "english", "italian"]
VIDEO_TYPES = ["expression", "fun_facts", "game", "roleplay"]


def normalize_text(text: Optional[str]) -> str:
    """Normalizes whitespace, smart quotes, and lowercases text for comparison."""
    if not text:
        return ""
    s = str(text).strip()
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def load_csv_records(csv_path: Path | str) -> List[Dict[str, str]]:
    """
    Loads and normalizes script rows from a CSV.
    Guarantees keys: 'ID', 'expression', 'script'.
    """
    path = Path(csv_path)
    if not path.exists():
        return []

    rows: List[Dict[str, str]] = []
    with path.open(mode="r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return rows

        for row in reader:
            record = {"ID": "", "expression": "", "script": ""}
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


def reconcile_sheet_data(
    local_rows: List[Dict[str, str]],
    sheet_rows: List[Dict[str, str]],
    language: str = "",
    video_type: str = "",
) -> Dict[str, Any]:
    """
    Reconciles local script rows against Google Sheet reference rows.

    Rules:
    - Target order follows sheet_rows.
    - If ID matches: retains sheet's canonical expression name, uses local row's script.
    - If local row ID does not exist in sheet_rows: appends to the end of the file.
    - If sheet row ID does not exist in local_rows: retains sheet row as-is.

    Returns dictionary with reconciled rows, statistics, and audit differences.
    """
    # Index local rows by ID (case-insensitive key)
    local_by_id: Dict[str, Dict[str, str]] = {}
    for r in local_rows:
        rid = r["ID"].strip().upper()
        if rid:
            local_by_id[rid] = r

    # Index sheet rows by ID
    sheet_ids = set(r["ID"].strip().upper() for r in sheet_rows if r.get("ID"))

    reconciled_rows: List[Dict[str, str]] = []
    exact_matches = 0
    canonical_updates = 0
    sheet_only_preserved = 0
    handled_local_ids = set()
    diff_details: List[Dict[str, Any]] = []

    # 1. Iterate through Google Sheet rows in their exact order
    for g_row in sheet_rows:
        gid = g_row["ID"].strip().upper()
        g_exp = g_row["expression"].strip()
        g_script = g_row["script"].strip()

        if gid in local_by_id:
            l_row = local_by_id[gid]
            handled_local_ids.add(gid)
            l_exp = l_row["expression"].strip()
            l_script = l_row["script"].strip()

            norm_g = normalize_text(g_exp)
            norm_l = normalize_text(l_exp)

            if g_exp == l_exp:
                status = "EXACT_MATCH"
                exact_matches += 1
            elif norm_g == norm_l:
                status = "NORMALIZED_MATCH"
                exact_matches += 1
            else:
                status = "EXPRESSION_VARIATION"
                canonical_updates += 1
                diff_details.append({
                    "ID": gid,
                    "sheet_expression": g_exp,
                    "local_expression": l_exp,
                    "status": "SHEET_NAME_PRESERVED",
                })

            # Use Google Sheet's canonical expression name, update with latest local script
            reconciled_rows.append({
                "ID": g_row["ID"].strip(),
                "expression": g_exp,
                "script": l_script,
            })
        else:
            # Sheet row not present in local: preserve in place
            sheet_only_preserved += 1
            reconciled_rows.append({
                "ID": g_row["ID"].strip(),
                "expression": g_exp,
                "script": g_script,
            })
            diff_details.append({
                "ID": gid,
                "sheet_expression": g_exp,
                "local_expression": None,
                "status": "SHEET_ONLY_PRESERVED",
            })

    # 2. Append local rows not in Google Sheets to the end of the list
    new_local_appended = 0
    for l_row in local_rows:
        lid = l_row["ID"].strip().upper()
        if lid not in sheet_ids:
            new_local_appended += 1
            reconciled_rows.append({
                "ID": l_row["ID"].strip(),
                "expression": l_row["expression"].strip(),
                "script": l_row["script"].strip(),
            })
            diff_details.append({
                "ID": l_row["ID"].strip(),
                "sheet_expression": None,
                "local_expression": l_row["expression"].strip(),
                "status": "NEW_LOCAL_APPENDED_TO_END",
            })

    return {
        "language": language.lower(),
        "video_type": video_type.lower(),
        "reconciled_rows": reconciled_rows,
        "total_reconciled": len(reconciled_rows),
        "total_sheet_rows": len(sheet_rows),
        "total_local_rows": len(local_rows),
        "exact_matches": exact_matches,
        "canonical_updates": canonical_updates,
        "sheet_only_preserved": sheet_only_preserved,
        "new_local_appended": new_local_appended,
        "has_differences": (canonical_updates > 0 or sheet_only_preserved > 0 or new_local_appended > 0),
        "diff_details": diff_details,
    }


def save_reconciled_csv(output_path: Path | str, rows: List[Dict[str, str]]) -> Path:
    """
    Saves reconciled rows to CSV with UTF-8 BOM encoding and standard fields.
    """
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with dest.open(mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "expression", "script"])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "ID": r.get("ID", ""),
                "expression": r.get("expression", ""),
                "script": r.get("script", ""),
            })

    return dest


def reconcile_single_sheet(
    language: str,
    video_type: str,
    scripts_dir: Optional[Path] = None,
    connectivity_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Reconciles a single sheet pair between local scripts and Google Sheets data.
    """
    lang = language.strip().lower()
    vtype = video_type.strip().lower()

    s_dir = Path(scripts_dir) if scripts_dir else DEFAULT_SCRIPTS_TO_SEE_DIR
    if connectivity_dir:
        c_dir = Path(connectivity_dir)
        if (c_dir / "synced_sheets" / "_3_columns").exists():
            c_dir = c_dir / "synced_sheets" / "_3_columns"
        elif (c_dir / "_3_columns").exists():
            c_dir = c_dir / "_3_columns"
    else:
        if DEFAULT_CONNECTIVITY_DIR.exists():
            c_dir = DEFAULT_CONNECTIVITY_DIR
        elif Path(r"D:\AI\output\connectivity\_3_columns").exists():
            c_dir = Path(r"D:\AI\output\connectivity\_3_columns")
        else:
            c_dir = DEFAULT_CONNECTIVITY_DIR
    o_dir = Path(output_dir) if output_dir else DEFAULT_SCRIPTS_TO_POST_DIR

    local_path = s_dir / lang / vtype / f"{lang}_{vtype}_scripts.csv"
    sheet_path = c_dir / lang / vtype / f"{lang}_{vtype}_connectivity.csv"
    out_path = o_dir / lang / vtype / f"{lang}_{vtype}_scripts.csv"

    local_rows = load_csv_records(local_path)
    sheet_rows = load_csv_records(sheet_path)

    result = reconcile_sheet_data(
        local_rows=local_rows,
        sheet_rows=sheet_rows,
        language=lang,
        video_type=vtype,
    )
    result["local_path"] = str(local_path)
    result["sheet_path"] = str(sheet_path)
    result["output_path"] = str(out_path)
    result["saved"] = False

    if not dry_run and result["reconciled_rows"]:
        save_reconciled_csv(out_path, result["reconciled_rows"])
        result["saved"] = True

    return result


def reconcile_all_sheets(
    scripts_dir: Optional[Path] = None,
    connectivity_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Reconciles all 16 sheets across English, French, Italian, and Spanish.
    """
    results: List[Dict[str, Any]] = []
    total_reconciled = 0
    total_new_appended = 0
    total_canonical_updated = 0
    sheets_with_diffs = 0

    for lang in LANGUAGES:
        for vtype in VIDEO_TYPES:
            res = reconcile_single_sheet(
                language=lang,
                video_type=vtype,
                scripts_dir=scripts_dir,
                connectivity_dir=connectivity_dir,
                output_dir=output_dir,
                dry_run=dry_run,
            )
            results.append(res)
            total_reconciled += res["total_reconciled"]
            total_new_appended += res["new_local_appended"]
            total_canonical_updated += res["canonical_updates"]
            if res["has_differences"]:
                sheets_with_diffs += 1

    return {
        "status": "success",
        "dry_run": dry_run,
        "total_sheets": len(results),
        "sheets_with_differences": sheets_with_diffs,
        "total_reconciled_rows": total_reconciled,
        "total_new_local_appended": total_new_appended,
        "total_canonical_updated": total_canonical_updated,
        "results": results,
    }
