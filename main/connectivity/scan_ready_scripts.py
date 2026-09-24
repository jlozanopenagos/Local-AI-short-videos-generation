#!/usr/bin/env python3
"""
scan_ready_scripts.py — Interactive CLI for Scanning Ready Scripts (Columns E through H).

Scans Google Sheets for rows where script_ready is True (and video_ready is False),
extracts ID and expression, and groups them into date-named CSV tracking files:
D:\\AI\\output\\connectivity\\ready_scripts\\<YYYY-MM-DD>_ready_scripts.csv

Usage:
  # Interactive mode:
  py main/connectivity/scan_ready_scripts.py

  # Scan all sheets non-interactively:
  py main/connectivity/scan_ready_scripts.py --all

  # Scan a specific sheet:
  py main/connectivity/scan_ready_scripts.py -l french -t expression
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.core.endpoints import ENDPOINT_REGISTRY
from connectivity.ready_scripts.scanner import (
    DEFAULT_READY_SCRIPTS_DIR,
    resolve_ready_scripts_output_dir,
    save_ready_scripts_by_date,
    save_ready_scripts_to_work_with_by_date,
    scan_all_sheets_ready_scripts,
    scan_sheet_ready_scripts,
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


def print_banner(output_dir: Path) -> None:
    print("=" * 66)
    print("       LINGOVERSE — SCAN READY SCRIPTS BY DATE (FEATURE 5)")
    print("=" * 66)
    print(" Target Rule     : script_ready is TRUE and video_ready is FALSE")
    print(" Exclusion Rule  : video_ready is TRUE (already completed video)")
    print(f" Output Directory: {output_dir}")
    print(" Output Schema   : ID, expression")
    print(" Naming Format   : <YYYY-MM-DD>_ready_scripts.csv")
    print("-" * 66)


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


def prompt_export_work_with_scripts() -> bool:
    """Prompt the user via terminal whether they also want to generate a CSV with ID and SCRIPT_CHANGE."""
    if not sys.stdin.isatty():
        return False
    try:
        choice = (
            input(
                "\nDo you also want to create a CSV with ID and SCRIPT_CHANGE (ready_scripts_to_work_with)? [y/N]: "
            )
            .strip()
            .lower()
        )
        return choice in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        return False


def export_work_with_scripts_if_requested(
    date_groups: dict,
    output_dir: Optional[Path] = None,
    work_with_flag: Optional[bool] = None,
) -> None:
    """Export <date>_ready_scripts_to_work_with.csv and error_report.csv if requested."""
    if not date_groups:
        return

    should_export = work_with_flag
    if should_export is None:
        should_export = prompt_export_work_with_scripts()

    if not should_export:
        return

    dest_dir = resolve_ready_scripts_output_dir(output_dir)
    print("\n" + "-" * 66)
    print(" [EXPORTING] Generating ready_scripts_to_work_with CSV(s)...")
    res = save_ready_scripts_to_work_with_by_date(date_groups, output_dir=dest_dir)

    print("\n" + "=" * 66)
    print(" [SUCCESS] Ready scripts to work with exported!")
    print("=" * 66)
    for d_key, f_info in res.get("saved_files", {}).items():
        if f_info.get("is_undated"):
            print(f"  [SAVED] {f_info['file_name']:<40} : {f_info['total_items']} script(s) [UNDATED]")
        else:
            print(f"  [SAVED] {f_info['file_name']:<40} : {f_info['total_items']} script(s)")
        print(f"          -> {f_info['file_path']}")

    if res.get("errors_count", 0) > 0:
        print(f"\n  [!] WARNING: {res['errors_count']} script(s) had an empty SCRIPT_CHANGE column.")
        print(f"      Logged into error report: {res.get('error_file')}")
        for err in res.get("errors", [])[:5]:
            print(f"        - ID {err['ID']}: {err['problem']}")
        if res.get("errors_count", 0) > 5:
            print(f"        ... and {res['errors_count'] - 5} more.")
    print("=" * 66)


def run_all_sheets_flow(
    output_dir: Optional[Path] = None,
    work_with_flag: Optional[bool] = None,
) -> None:
    dest_dir = resolve_ready_scripts_output_dir(output_dir)
    print("\n[STARTING] Scanning all 16 Google Sheets for ready scripts...")
    print(f"           Destination: {dest_dir}\n")

    summary = scan_all_sheets_ready_scripts()

    print("-" * 66)
    for s in summary.get("sheet_summaries", []):
        lang = s["language"].title()
        vtype = s["video_type"].title()
        ready = s["ready_count"]
        skipped = s["video_ready_excluded_count"]
        print(f"  [{lang} - {vtype:<10}] Ready: {ready:<3} | Completed Videos Skipped: {skipped}")

    if summary.get("errors"):
        print("\n  [ERRORS]:")
        for err in summary["errors"]:
            print(f"    - {err['language'].title()} {err['video_type'].title()}: {err['error']}")

    date_groups = summary.get("date_groups", {})
    if not date_groups:
        print("\n" + "=" * 66)
        print(" [INFO] No ready scripts found across any sheet.")
        print(f" Evaluated {summary['total_evaluated']} rows across {summary['successful_sheets']} sheets.")
        print(f" (Total completed videos skipped: {summary['total_video_ready_excluded']})")
        print("=" * 66)
        return

    # Save grouped records to disk
    save_result = save_ready_scripts_by_date(date_groups, output_dir=dest_dir)

    print("\n" + "=" * 66)
    print(" [SUCCESS] Ready scripts exported by date!")
    print("=" * 66)
    print(f"  Sheets Scanned         : {summary['successful_sheets']}/{summary['total_sheets']}")
    print(f"  Total Rows Evaluated   : {summary['total_evaluated']}")
    print(f"  Completed Videos Skips : {summary['total_video_ready_excluded']} (video_ready == True)")
    print(f"  Total Ready Scripts    : {summary['total_ready']}")
    print(f"  Daily Files Created    : {save_result['total_files']}")
    print("-" * 66)

    undated_warning = False
    for d_key, f_info in save_result.get("saved_files", {}).items():
        if f_info.get("is_undated"):
            undated_warning = True
            print(f"  [SAVED] {f_info['file_name']:<30} : {f_info['total_items']} script(s) [UNDATED]")
        else:
            print(f"  [SAVED] {f_info['file_name']:<30} : {f_info['total_items']} script(s)")
        print(f"          -> {f_info['file_path']}")

    if undated_warning:
        print("\n  [!] WARNING: Some scripts had script_ready checked but empty script_date cells.")
        print("      They were saved into 'undated_ready_scripts.csv' so no tracking data is lost.")
    print("=" * 66)

    # Prompt or export ready_scripts_to_work_with
    export_work_with_scripts_if_requested(
        date_groups, output_dir=dest_dir, work_with_flag=work_with_flag
    )


def run_single_sheet_flow(
    output_dir: Optional[Path] = None,
    work_with_flag: Optional[bool] = None,
) -> None:
    lang = select_language()
    vtype = select_video_type()
    dest_dir = resolve_ready_scripts_output_dir(output_dir)

    print(f"\n[SCANNING] Fetching ready scripts for [{lang.title()} - {vtype.title()}]...")
    try:
        res = scan_sheet_ready_scripts(lang, vtype)
    except Exception as err:
        print(f"\n[ERROR] Failed to fetch sheet: {err}")
        return

    ready_records = res.get("ready_records", [])
    print("\n" + "=" * 66)
    print(f"  Sheet                  : {lang.title()} - {vtype.title()}")
    print(f"  Spreadsheet ID         : {res.get('spreadsheet_id')}")
    print(f"  Rows Evaluated         : {res.get('total_evaluated')}")
    print(f"  Completed Videos Skips : {res.get('video_ready_excluded_count')}")
    print(f"  Ready Scripts Found    : {len(ready_records)}")
    print("-" * 66)

    if not ready_records:
        print("  [INFO] No ready scripts to export for this sheet.")
        print("=" * 66)
        return

    # Group by date
    date_groups = {}
    for r in ready_records:
        d = r.get("script_date", "undated")
        if d not in date_groups:
            date_groups[d] = []
        date_groups[d].append(r)

    save_result = save_ready_scripts_by_date(date_groups, output_dir=dest_dir)
    print("  Exported Daily Files:")
    for d_key, f_info in save_result.get("saved_files", {}).items():
        print(f"    - {f_info['file_name']}: {f_info['total_items']} script(s)")
        print(f"      -> {f_info['file_path']}")
    print("=" * 66)

    # Prompt or export ready_scripts_to_work_with
    export_work_with_scripts_if_requested(
        date_groups, output_dir=dest_dir, work_with_flag=work_with_flag
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LingoVerse Google Sheets Connectivity: Scan Ready Scripts by Date (Feature 5)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all 16 Google Sheets and export daily CSV tracking files non-interactively",
    )
    parser.add_argument(
        "-l", "--language",
        choices=["french", "spanish", "english", "italian"],
        help="Target language for single sheet scan",
    )
    parser.add_argument(
        "-t", "--video-type",
        choices=["expression", "fun_facts", "game", "roleplay"],
        help="Target video type for single sheet scan",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Custom destination directory (default: D:\\AI\\output\\connectivity\\ready_scripts)",
    )
    work_group = parser.add_mutually_exclusive_group()
    work_group.add_argument(
        "-w", "--work-with",
        dest="work_with",
        action="store_true",
        default=None,
        help="Also export ready_scripts_to_work_with.csv (ID, SCRIPT_CHANGE) without prompting",
    )
    work_group.add_argument(
        "--no-work-with",
        dest="work_with",
        action="store_false",
        help="Do not export ready_scripts_to_work_with.csv",
    )

    args = parser.parse_args()
    custom_dest = Path(args.output_dir) if args.output_dir else None
    resolved_dest = resolve_ready_scripts_output_dir(custom_dest)

    # CLI flag mode
    if args.all:
        print_banner(resolved_dest)
        run_all_sheets_flow(output_dir=custom_dest, work_with_flag=args.work_with)
        return

    if args.language and args.video_type:
        print_banner(resolved_dest)
        try:
            res = scan_sheet_ready_scripts(args.language, args.video_type)
            ready_records = res.get("ready_records", [])
            print(f"[OK] Fetched {len(ready_records)} ready script(s) for {args.language.title()} {args.video_type.title()}.")
            if ready_records:
                date_groups = {}
                for r in ready_records:
                    d = r.get("script_date", "undated")
                    date_groups.setdefault(d, []).append(r)
                saved = save_ready_scripts_by_date(date_groups, output_dir=custom_dest)
                for d_k, info in saved.get("saved_files", {}).items():
                    print(f" [SAVED] {info['file_name']} -> {info['file_path']}")
                export_work_with_scripts_if_requested(
                    date_groups, output_dir=custom_dest, work_with_flag=args.work_with
                )
        except Exception as e:
            print(f"[ERROR] Scan failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Interactive menu
    print_banner(resolved_dest)
    print("Select an operation:")
    print("  [1] Scan ALL 16 Google Sheets and export by date (Default)")
    print("  [2] Scan a specific sheet")
    print("  [0] Exit")

    while True:
        try:
            choice = input("\nEnter choice (0-2) [default: 1]: ").strip()
            if not choice or choice == "1":
                run_all_sheets_flow(output_dir=custom_dest, work_with_flag=args.work_with)
                break
            elif choice == "2":
                run_single_sheet_flow(output_dir=custom_dest, work_with_flag=args.work_with)
                break
            elif choice == "0":
                print("Exiting.")
                break
            else:
                print("Invalid choice. Please enter 0, 1, or 2.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            break


if __name__ == "__main__":
    main()
