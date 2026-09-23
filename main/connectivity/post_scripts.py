#!/usr/bin/env python3
"""
post_scripts.py — Interactive CLI for Posting Scripts to Google Sheets.

Pushes script data from D:\\AI\\output\\scripts_to_see back to Google Sheets.
Safety Guarantee:
- Only updates Columns A (ID), B (expression), and C (script).
- Column D (SCRIPT_CHANGED) and subsequent columns are NEVER touched.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.core.endpoints import (
    ENDPOINT_REGISTRY,
    MASTER_WEBAPP_URL,
    extract_spreadsheet_id,
    get_endpoint,
)
from connectivity.post_scripts.poster import (
    DEFAULT_SCRIPTS_TO_SEE_DIR,
    filter_scripts,
    get_source_csv_path,
    load_source_scripts_csv,
    parse_operation_input,
    parse_range_spec,
    post_all_sheets,
    post_single_sheet,
    prompt_column_option,
)

# Reconfigure streams to avoid Windows charmap encoding issues
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SUPPORTED_LANGUAGES = [
    ("1", "French", "french"),
    ("2", "Spanish", "spanish"),
    ("3", "English", "english"),
    ("4", "Italian", "italian"),
]

SUPPORTED_TYPES = [
    ("1", "Expression", "expression"),
    ("2", "Fun Facts", "fun_facts"),
    ("3", "Game", "game"),
    ("4", "Roleplay", "roleplay"),
]


def print_banner() -> None:
    print("=" * 64)
    print("       LINGOVERSE — POST SCRIPTS TO GOOGLE SHEETS")
    print("=" * 64)
    print(" Source Priority : D:\\AI\\output\\connectivity\\scripts_to_post")
    print("                   (Fallback: D:\\AI\\output\\scripts_to_see)")
    print(" Mode Options    : 3 columns (A:C) or 4 columns (A:D with SCRIPT_CHANGED)")
    print(" Safety Guarantee: Column D is preserved untouched unless 4-column mode is chosen")
    print("-" * 64)


def print_operations_menu() -> None:
    print("Select an operation:")
    print("  [1] Update a specific sheet (all entries)")
    print("\t1) ID, expression, script columns")
    print("\t2) ID, expression, script and script_changed columns")
    print("  [2] Update a specific sheet by range (e.g. 10-20)")
    print("\t1) ID, expression, script columns")
    print("\t2) ID, expression, script and script_changed columns")
    print("  [3] Update a specific sheet by ID(s) (e.g. FE01, FE05)")
    print("\t1) ID, expression, script columns")
    print("\t2) ID, expression, script and script_changed columns")
    print("  [4] Update ALL languages and types (all 16 sheets)")
    print("\t1) ID, expression, script columns")
    print("\t2) ID, expression, script and script_changed columns")
    print("  [0] Exit")


def select_language() -> str:
    print("\nSelect Language:")
    for num, label, _ in SUPPORTED_LANGUAGES:
        print(f"  [{num}] {label}")
    while True:
        choice = input("Enter choice (1-4) [default: 1 (French)]: ").strip()
        if not choice:
            return "french"
        for num, _, key in SUPPORTED_LANGUAGES:
            if choice == num or choice.lower() == key:
                return key
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def select_video_type() -> str:
    print("\nSelect Video Type:")
    for num, label, _ in SUPPORTED_TYPES:
        print(f"  [{num}] {label}")
    while True:
        choice = input("Enter choice (1-4) [default: 1 (Expression)]: ").strip()
        if not choice:
            return "expression"
        for num, _, key in SUPPORTED_TYPES:
            if choice == num or choice.lower() == key:
                return key
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def prompt_range() -> str:
    while True:
        range_input = input("\nEnter range (e.g. 10-20, 01-50, or FE10-FE20): ").strip()
        if not range_input:
            print("Range cannot be empty. Please enter a range like '10-20'.")
            continue
        try:
            start_num, end_num = parse_range_spec(range_input)
            print(f"Parsed range: {start_num} to {end_num}")
            return range_input
        except ValueError as err:
            print(f"Error: {err}")


def prompt_ids() -> List[str]:
    while True:
        ids_input = input("\nEnter ID(s) separated by commas or spaces (e.g. FE01, FE04, FE12): ").strip()
        if not ids_input:
            print("IDs cannot be empty. Please enter at least one ID.")
            continue
        import re
        parts = [p.strip().upper() for p in re.split(r"[\s,]+", ids_input) if p.strip()]
        if parts:
            print(f"Parsed ID(s): {', '.join(parts)}")
            return parts


def preview_and_confirm(
    language: str,
    video_type: str,
    rows: List[dict],
    total_in_csv: int,
    spreadsheet_id: str,
    include_script_changed: bool = False,
    csv_path: Optional[Path | str] = None,
) -> bool:
    cols_desc = "4 columns (A:D - includes SCRIPT_CHANGED)" if include_script_changed else "3 columns (A:C - ID, expression, script)"
    print("\n" + "=" * 64)
    print("                    POST PREVIEW")
    print("=" * 64)
    print(f"  Language        : {language.title()}")
    print(f"  Video Type      : {video_type.title()}")
    print(f"  Columns Mode    : {cols_desc}")
    print(f"  Spreadsheet ID  : {spreadsheet_id}")
    if csv_path:
        print(f"  Source CSV      : {csv_path}")
    print(f"  Rows to Update  : {len(rows)} (out of {total_in_csv} in source CSV)")
    print("-" * 64)

    if not rows:
        print("  [!] No matching rows to update.")
        print("=" * 64)
        return False

    preview_count = min(len(rows), 3)
    print(f"  Previewing first {preview_count} record(s):")
    for idx, r in enumerate(rows[:preview_count], 1):
        id_val = r.get("ID", "")
        expr_val = r.get("expression", "")[:30]
        script_val = r.get("script", "").replace("\n", " ")[:35]
        if include_script_changed:
            sc_val = r.get("SCRIPT_CHANGED", "").replace("\n", " ")[:25]
            print(f"    {idx}. [{id_val}] {expr_val} | {script_val}... | changed: {sc_val}...")
        else:
            print(f"    {idx}. [{id_val}] {expr_val} | {script_val}...")

    print("=" * 64)
    confirm = input("Proceed with updating Google Sheet? (y/n) [default: y]: ").strip().lower()
    return confirm in ("", "y", "yes")


def handle_single_sheet_flow(mode: str, include_script_changed: bool = False) -> None:
    range_spec = None
    ids = None

    if mode == "range":
        range_spec = prompt_range()
    elif mode == "ids":
        ids = prompt_ids()

    lang = select_language()
    vtype = select_video_type()

    csv_path = get_source_csv_path(lang, vtype, include_script_changed=include_script_changed)
    if not csv_path.exists():
        print(f"\n[ERROR] Source CSV not found at: {csv_path}")
        if include_script_changed:
            print(r"Please check that connectivity data with 4 columns exists in D:\AI\output\connectivity\_4_columns.")
        else:
            print(r"Please check that scripts have been generated in D:\AI\output\connectivity\scripts_to_post or D:\AI\output\scripts_to_see.")
        return

    try:
        all_rows = load_source_scripts_csv(csv_path, include_script_changed=include_script_changed)
    except Exception as e:
        print(f"\n[ERROR] Could not read source CSV: {e}")
        return

    filtered_rows = filter_scripts(all_rows, mode=mode, range_spec=range_spec, ids=ids)
    endpoint = get_endpoint(lang, vtype)
    spreadsheet_id = extract_spreadsheet_id(endpoint)

    if not preview_and_confirm(lang, vtype, filtered_rows, len(all_rows), spreadsheet_id, include_script_changed=include_script_changed, csv_path=csv_path):
        print("\nOperation cancelled by user.")
        return

    cols_desc = "4 columns (A:D)" if include_script_changed else "3 columns (A:C)"
    print(f"\n[POSTING] Sending {len(filtered_rows)} record(s) to Google Sheets ({cols_desc})...")
    print(f"          Target Sheet: [{lang.title()} - {vtype.title()}] (ID: {spreadsheet_id})")

    try:
        res = post_single_sheet(
            language=lang,
            video_type=vtype,
            mode=mode,
            range_spec=range_spec,
            ids=ids,
            include_script_changed=include_script_changed,
        )
        print("\n" + "=" * 64)
        print(" [SUCCESS] Google Sheet successfully updated!")
        print("=" * 64)
        print(f"  Target Sheet    : {lang.title()} - {vtype.title()}")
        print(f"  Spreadsheet ID  : {res.get('spreadsheet_id')}")
        print(f"  Columns Posted  : {cols_desc}")
        print(f"  In-place Updated: {res.get('updated_count')} rows")
        print(f"  Appended New    : {res.get('appended_count')} rows")
        print(f"  Total Affected  : {res.get('total_affected')} rows")
        if include_script_changed:
            print("  Column D Status : SCRIPT_CHANGED updated/appended.")
        else:
            print("  Column D Status : SCRIPT_CHANGED preserved (untouched).")
        print("=" * 64)

    except Exception as err:
        print(f"\n[ERROR] Failed to post scripts to Google Sheets: {err}")


def handle_all_sheets_flow(include_script_changed: bool = False) -> None:
    cols_desc = "4 columns (A:D, including SCRIPT_CHANGED)" if include_script_changed else "3 columns (A:C, ID, expression, script)"
    source_desc = (
        r"D:\AI\output\connectivity\_4_columns (fallback: scripts_to_post)"
        if include_script_changed
        else r"D:\AI\output\connectivity\scripts_to_post (fallback: scripts_to_see)"
    )

    print("\n" + "=" * 64)
    print("          BATCH POST: ALL 16 GOOGLE SHEETS")
    print("=" * 64)
    print(" This will update ALL 16 Google Sheets from:")
    print(f"   {source_desc}")
    print(f" Columns: {cols_desc}")
    if include_script_changed:
        print(" Columns A, B, C, and D (SCRIPT_CHANGED) will be updated in each sheet.")
    else:
        print(" Columns A, B, and C will be updated in each sheet.")
        print(" Column D (SCRIPT_CHANGED) will be preserved in all sheets.")
    print("-" * 64)

    confirm = input("Are you sure you want to update ALL 16 sheets? (y/n) [default: n]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("\nBatch update cancelled.")
        return

    print(f"\n[STARTING] Posting data to 16 Google Sheets ({cols_desc})...")
    summary = post_all_sheets(include_script_changed=include_script_changed)

    print("\n" + "=" * 64)
    if summary["status"] == "success":
        print(" [SUCCESS] All 16 Google Sheets updated successfully!")
    else:
        print(f" [PARTIAL] Completed with {summary['failed_sheets']} error(s).")
    print("=" * 64)
    print(f"  Columns Posted         : {cols_desc}")
    print(f"  Total Sheets Processed : {summary['successful_sheets']}/{summary['total_sheets']}")
    print(f"  Total Rows Posted      : {summary['total_posted']}")
    print(f"  In-place Updated       : {summary['total_updated']}")
    print(f"  Appended New           : {summary['total_appended']}")

    if summary.get("errors"):
        print("\n  Errors encountered:")
        for err in summary["errors"]:
            print(f"   - [{err['language'].title()} - {err['video_type'].title()}]: {err['error']}")
    print("=" * 64)


OPERATION_TITLES = {
    "1": "Update a specific sheet (all entries)",
    "2": "Update a specific sheet by range (e.g. 10-20)",
    "3": "Update a specific sheet by ID(s) (e.g. FE01, FE05)",
    "4": "Update ALL languages and types (all 16 sheets)",
}


def main() -> None:
    print_banner()
    print_operations_menu()

    while True:
        raw_choice = input("\nEnter selection (0-4, or e.g. 1.1 / 1.2) [default: 1]: ").strip()
        parsed = parse_operation_input(raw_choice)
        if parsed is None:
            print("Invalid choice. Please enter 0, 1, 2, 3, or 4.")
            continue

        op, sub = parsed
        if op == "0":
            print("Exiting.")
            sys.exit(0)

        # Resolve column option if not given in compound syntax
        if sub is None:
            include_script_changed = prompt_column_option(OPERATION_TITLES.get(op, ""))
        else:
            include_script_changed = sub

        if op == "1":
            handle_single_sheet_flow(mode="all", include_script_changed=include_script_changed)
            break
        elif op == "2":
            handle_single_sheet_flow(mode="range", include_script_changed=include_script_changed)
            break
        elif op == "3":
            handle_single_sheet_flow(mode="ids", include_script_changed=include_script_changed)
            break
        elif op == "4":
            handle_all_sheets_flow(include_script_changed=include_script_changed)
            break
        else:
            print("Invalid choice. Please enter 0, 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
