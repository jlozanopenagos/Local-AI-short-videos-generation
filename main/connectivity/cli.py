#!/usr/bin/env python3
"""
cli.py — Command-line interface for Google Sheets connectivity.

Usage:
  # Fetch default (French Expression)
  py main/connectivity/cli.py

  # Fetch by language and video type
  py main/connectivity/cli.py --language french --video-type expression

  # Fetch from a specific custom endpoint URL
  py main/connectivity/cli.py --url "https://script.google.com/macros/s/.../exec"

  # List registered endpoints
  py main/connectivity/cli.py --list
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

from connectivity.endpoints import list_registered_endpoints, get_endpoint
from connectivity.sheets_fetcher import sync_sheet, sync_all_sheets, resolve_connectivity_output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LingoVerse Google Sheets Connectivity: Fetch & Sync Script Columns (ID, expression, script)"
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
        "--list",
        action="store_true",
        help="List all registered endpoints"
    )
    args = parser.parse_args()

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
            )
            print(f"\n[SUCCESS] Connectivity sync complete! Fetched {result['count']} items.")
            return 0
    except Exception as e:
        print(f"\n[ERROR] Connectivity sync failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
