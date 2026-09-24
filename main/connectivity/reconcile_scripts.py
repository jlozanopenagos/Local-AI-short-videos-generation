#!/usr/bin/env python3
"""
reconcile_scripts.py — Interactive CLI for Auditing & Reorganizing Scripts.

Checks local script files in D:\\AI\\output\\scripts_to_see against Google Sheets
reference data in D:\\AI\\output\\connectivity\\synced_sheets\\_3_columns.
Reorganizes matching entries to strictly follow Google Sheets order, preserves
Google Sheets canonical expression names, appends new local entries to the end,
and outputs clean CSVs to D:\\AI\\output\\connectivity\\scripts_to_post for mass posting.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.reconcile.service import (
    DEFAULT_CONNECTIVITY_DIR,
    DEFAULT_SCRIPTS_TO_POST_DIR,
    DEFAULT_SCRIPTS_TO_SEE_DIR,
    LANGUAGES,
    VIDEO_TYPES,
    reconcile_all_sheets,
    reconcile_single_sheet,
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
    print("=" * 68)
    print("       LINGOVERSE — RECONCILE & REORGANIZE SCRIPTS FOR POSTING")
    print("=" * 68)
    print(f" Local Source (Scripts) : {DEFAULT_SCRIPTS_TO_SEE_DIR}")
    print(f" Sheet Reference (Order): {DEFAULT_CONNECTIVITY_DIR}")
    print(f" Reconciled Output      : {DEFAULT_SCRIPTS_TO_POST_DIR}")
    print(" Strategy               : Keep Google Sheet order & names, append new rows")
    print("-" * 68)


def print_operations_menu() -> None:
    print("Select an operation:")
    print("  [1] Check & audit differences across all 16 sheets (Dry Run)")
    print("  [2] Reorganize ALL 16 sheets and save to scripts_to_post")
    print("  [3] Check & reorganize a specific sheet")
    print("  [4] Reorganize ALL sheets and immediately launch post_scripts.py")
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


def print_sheet_audit_result(res: Dict[str, Any], show_details: bool = True) -> None:
    lang = res["language"].title()
    vtype = res["video_type"].title()
    print(f"\n--- [{lang} - {vtype}] ---")
    print(f"  Sheet Rows: {res['total_sheet_rows']:3d} | Local Rows: {res['total_local_rows']:3d} | Output: {res['total_reconciled']:3d}")
    print(f"  Exact Matches         : {res['exact_matches']}")
    print(f"  Sheet Names Preserved : {res['canonical_updates']}")
    print(f"  New Local Appended    : {res['new_local_appended']}")
    print(f"  Sheet-Only Preserved  : {res['sheet_only_preserved']}")

    if show_details and res.get("diff_details"):
        details = res["diff_details"]
        display_count = min(len(details), 5)
        print(f"  Differences preview ({len(details)} total, showing first {display_count}):")
        for d in details[:display_count]:
            stat = d["status"]
            gid = d["ID"]
            if stat == "SHEET_NAME_PRESERVED":
                print(f"    [{gid}] Sheet: '{d['sheet_expression'][:25]}' <-- Local: '{d['local_expression'][:25]}'")
            elif stat == "NEW_LOCAL_APPENDED_TO_END":
                print(f"    [{gid}] NEW ENTRY APPENDED TO END: '{d['local_expression'][:35]}'")
            elif stat == "SHEET_ONLY_PRESERVED":
                print(f"    [{gid}] SHEET ONLY PRESERVED: '{d['sheet_expression'][:35]}'")


def print_batch_summary(summary: Dict[str, Any]) -> None:
    print("\n" + "=" * 68)
    print("                    RECONCILIATION SUMMARY")
    print("=" * 68)
    print(f" Total Sheets Processed      : {summary['total_sheets']}")
    print(f" Sheets with Differences     : {summary['sheets_with_differences']}")
    print(f" Total Reconciled Rows       : {summary['total_reconciled_rows']}")
    print(f" Total New Local Appended    : {summary['total_new_local_appended']}")
    print(f" Total Canonical Names Kept  : {summary['total_canonical_updated']}")
    mode_desc = "DRY RUN (no files modified)" if summary["dry_run"] else f"SAVED -> {DEFAULT_SCRIPTS_TO_POST_DIR}"
    print(f" Execution Mode              : {mode_desc}")
    print("=" * 68)


def handle_audit_flow() -> None:
    print("\n[RUNNING] Auditing all 16 sheets against Google Sheets reference data...")
    summary = reconcile_all_sheets(dry_run=True)
    for res in summary["results"]:
        if res["has_differences"]:
            print_sheet_audit_result(res, show_details=True)
        else:
            print(f"  [OK] {res['language'].title():7} - {res['video_type'].title():10}: Perfectly aligned ({res['total_reconciled']} rows)")
    print_batch_summary(summary)


def handle_all_reorganize_flow() -> None:
    print(f"\n[RUNNING] Reorganizing ALL 16 sheets to: {DEFAULT_SCRIPTS_TO_POST_DIR}...")
    summary = reconcile_all_sheets(dry_run=False)
    for res in summary["results"]:
        status_marker = "[UPDATED]" if res["has_differences"] else "[ALIGNED]"
        print(f"  {status_marker} {res['language'].title():7} - {res['video_type'].title():10}: {res['total_reconciled']} rows (new: {res['new_local_appended']}, preserved sheet names: {res['canonical_updates']})")
    print_batch_summary(summary)
    print(f"\n[SUCCESS] All CSVs generated in: {DEFAULT_SCRIPTS_TO_POST_DIR}")
    print("You can now post these scripts to Google Sheets using post_scripts.py!")


def handle_single_sheet_flow() -> None:
    lang = select_language()
    vtype = select_video_type()

    print(f"\n[RUNNING] Reconciling [{lang.title()} - {vtype.title()}]...")
    res = reconcile_single_sheet(language=lang, video_type=vtype, dry_run=False)
    print_sheet_audit_result(res, show_details=True)
    print("\n" + "=" * 68)
    print(f" [SUCCESS] Reorganized file saved to:")
    print(f"   {res['output_path']}")
    print("=" * 68)


def handle_reorganize_and_post_flow() -> None:
    handle_all_reorganize_flow()
    confirm = input("\nDo you want to launch post_scripts.py now? (y/n) [default: y]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        post_script_path = Path(__file__).resolve().parent / "post_scripts.py"
        try:
            subprocess.run([sys.executable, str(post_script_path)], check=True)
        except Exception as e:
            print(f"[ERROR] Could not launch post_scripts.py: {e}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit and reorganize local scripts to match Google Sheets order."
    )
    parser.add_argument("--all", "-a", action="store_true", help="Reorganize all 16 sheets")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Audit only (no files written)")
    parser.add_argument("--language", "-l", help="Language (e.g. french, spanish)")
    parser.add_argument("--type", "-t", help="Video type (e.g. expression, fun_facts)")
    parser.add_argument("--post", "-p", action="store_true", help="Launch post_scripts.py after reconciling")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm all prompts")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    # CLI automated execution
    if args.dry_run or args.all or args.language:
        print_banner()
        if args.language and args.type:
            res = reconcile_single_sheet(
                language=args.language,
                video_type=args.type,
                dry_run=args.dry_run,
            )
            print_sheet_audit_result(res, show_details=True)
            return
        elif args.dry_run:
            handle_audit_flow()
            return
        elif args.all:
            handle_all_reorganize_flow()
            if args.post:
                handle_reorganize_and_post_flow()
            return

    # Interactive menu
    print_banner()
    print_operations_menu()

    while True:
        choice = input("\nEnter selection (0-4) [default: 1]: ").strip()
        if not choice:
            choice = "1"

        if choice == "0":
            print("Exiting.")
            sys.exit(0)
        elif choice == "1":
            handle_audit_flow()
            break
        elif choice == "2":
            handle_all_reorganize_flow()
            break
        elif choice == "3":
            handle_single_sheet_flow()
            break
        elif choice == "4":
            handle_reorganize_and_post_flow()
            break
        else:
            print("Invalid choice. Please enter 0, 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
