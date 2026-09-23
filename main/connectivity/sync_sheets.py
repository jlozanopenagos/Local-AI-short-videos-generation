#!/usr/bin/env python3
"""
sync_sheets.py — Primary CLI for fetching and syncing data from Google Sheets to local connectivity storage.

Usage:
  # Fetch all sheets (interactive 3 vs 4 column choice)
  py main/connectivity/sync_sheets.py --all

  # Fetch all sheets with 4 columns (including SCRIPT_CHANGED)
  py main/connectivity/sync_sheets.py --all --four-columns

  # Fetch specific language and video type
  py main/connectivity/sync_sheets.py --language french --video-type expression

  # List registered endpoints
  py main/connectivity/sync_sheets.py --list
"""

import argparse
import sys
from pathlib import Path

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.core.endpoints import list_registered_endpoints, get_endpoint
from connectivity.sheet_sync.sync_service import (
    sync_sheet,
    sync_all_sheets,
    resolve_connectivity_output_dir,
    TARGET_COLUMNS,
    FOUR_COLUMNS,
)

# Reconfigure streams if supported to prevent Windows charmap encoding errors
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


def prompt_include_script_changed() -> bool:
    """
    Asks the user via terminal whether to include the 4th column (SCRIPT_CHANGED)
    along with ID, expression, and script.
    """
    print("\n" + "=" * 62)
    print("      GOOGLE SHEETS SYNC — COLUMN CONFIGURATION")
    print("=" * 62)
    print("Select columns to export:")
    print("  [1] 3 columns: ID, expression, script (Standard) -> _3_columns/")
    print("  [2] 4 columns: ID, expression, script, SCRIPT_CHANGED -> _4_columns/")
    print("-" * 62)
    while True:
        try:
            choice = input("Do you also want to get the 4th column (SCRIPT_CHANGED)? [1/2 or y/N] (default: 1): ").strip().lower()
            if not choice or choice in ("1", "n", "no", "3"):
                return False
            if choice in ("2", "y", "yes", "4"):
                return True
            print("  [!] Invalid choice. Enter 1 (or 'n') for 3 columns, or 2 (or 'y') for 4 columns.")
        except (KeyboardInterrupt, EOFError):
            print("\n[INFO] Operation cancelled by user.")
            sys.exit(0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LingoVerse Google Sheets Connectivity: Fetch & Sync Script Columns (ID, expression, script, [SCRIPT_CHANGED])"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Fetch all registered sheets across all languages and video types"
    )
    parser.add_argument(
        "--language", "-l",
        type=str,
        default=None,
        choices=["all", "french", "english", "spanish", "italian"],
        help="Target language (default: all)"
    )
    parser.add_argument(
        "--video-type", "-t",
        type=str,
        default=None,
        choices=["all", "expression", "roleplay", "game", "fun_facts"],
        help="Target video type (default: all)"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default=None,
        help="Custom Google Apps Script Web App URL override"
    )
    parser.add_argument(
        "--sheet-id", "-s",
        type=str,
        default=None,
        help="Google Spreadsheet ID or URL to query via the Master Web App"
    )
    parser.add_argument(
        "--tab",
        type=str,
        default=None,
        help="Specific sheet/tab name inside the spreadsheet"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Custom destination directory (default: D:\\AI\\output\\connectivity or OUTPUT_DIR/connectivity)"
    )
    parser.add_argument(
        "--include-script-changed", "--four-columns", "-4",
        action="store_true",
        dest="include_script_changed",
        default=None,
        help="Include 4th column (SCRIPT_CHANGED) alongside ID, expression, script (saves to _4_columns/)"
    )
    parser.add_argument(
        "--three-columns", "-3",
        action="store_true",
        dest="three_columns",
        default=False,
        help="Export only 3 standard columns (ID, expression, script) (saves to _3_columns/), skipping terminal prompt"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Non-interactive mode (use default 3 columns without terminal prompt)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered endpoints"
    )
    args = parser.parse_args()

    if args.list:
        print("\n=======================================================")
        print("  REGISTERED GOOGLE SHEETS ENDPOINTS")
        print("=======================================================")
        endpoints = list_registered_endpoints()
        if not endpoints:
            print("No endpoints registered.")
        for ep in endpoints:
            print(f"  * {ep['language'].capitalize()} - {ep['video_type'].upper()}:")
            print(f"    Target:   {ep.get('target', ep.get('url', ''))}")
            print(f"    Endpoint: {ep.get('resolved_url', ep.get('url', ''))}")
        print("=======================================================\n")
        return 0

    # Determine column mode (3 columns vs 4 columns)
    if args.three_columns:
        include_script_changed = False
    elif args.include_script_changed is not None:
        include_script_changed = args.include_script_changed
    elif args.yes or not (sys.stdin and sys.stdin.isatty()):
        include_script_changed = False
    else:
        include_script_changed = prompt_include_script_changed()

    # Determine if this is a batch sync (all sheets, or all types for a language, etc.)
    is_batch = (
        args.all
        or (args.language == "all")
        or (args.video_type == "all")
        or (not args.language and not args.video_type and not args.url and not args.sheet_id)
        or (args.language and not args.video_type and not args.url and not args.sheet_id)
        or (args.video_type and not args.language and not args.url and not args.sheet_id)
    )

    try:
        if is_batch:
            result = sync_all_sheets(
                language=args.language,
                video_type=args.video_type,
                output_dir=args.output_dir,
                include_script_changed=include_script_changed,
            )
            return 0 if result.get("failed_count", 0) == 0 else 1
        else:
            lang = args.language or "french"
            vtype = args.video_type or "expression"
            result = sync_sheet(
                language=lang,
                video_type=vtype,
                url=args.url,
                output_dir=args.output_dir,
                sheet_id=args.sheet_id,
                tab=args.tab,
                include_script_changed=include_script_changed,
            )
            col_msg = "4 columns" if include_script_changed else "3 columns"
            print(f"\n[SUCCESS] Connectivity sync complete! Fetched {result['count']} items ({col_msg}).")
            return 0
    except Exception as e:
        print(f"\n[ERROR] Connectivity sync failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
