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
from connectivity.sheets_fetcher import sync_sheet, resolve_connectivity_output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LingoVerse Google Sheets Connectivity: Fetch & Sync Script Columns (ID, expression, SCRIPT_CHANGED)"
    )
    parser.add_argument(
        "--language", "-l",
        type=str,
        default="french",
        choices=["french", "english", "spanish", "italian"],
        help="Target language (default: french)"
    )
    parser.add_argument(
        "--video-type", "-t",
        type=str,
        default="expression",
        choices=["expression", "roleplay", "game", "fun_facts"],
        help="Target video type (default: expression)"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default=None,
        help="Custom Google Apps Script Web App URL override"
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
            print(f"    {ep['url']}")
        print("=======================================================\n")
        return 0

    try:
        result = sync_sheet(
            language=args.language,
            video_type=args.video_type,
            url=args.url,
            output_dir=args.output_dir,
        )
        print(f"\n[SUCCESS] Connectivity sync complete! Fetched {result['count']} items.")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Connectivity sync failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
