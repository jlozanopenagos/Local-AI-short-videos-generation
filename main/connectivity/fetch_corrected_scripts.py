#!/usr/bin/env python3
"""
fetch_corrected_scripts.py — Interactive CLI for Fetching Corrected Scripts (Column D).

Connects to Google Sheets and exports corrected scripts (Column D SCRIPT_CHANGED)
directly into C:\\AI\\shorts_automation\\main\\input\\csv\\script_to_change\\<language>_<video_type>_script_to_change.csv
with schema: 'ID, NEW_SCRIPT'.
"""

import sys
from pathlib import Path

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.corrected_scripts.fetcher import (
    fetch_and_save_corrected_scripts,
    fetch_all_sheets_corrected_scripts,
    DEFAULT_OUTPUT_DIR,
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


def prompt_choice(prompt_text: str, valid_choices: list[str], default: str) -> str:
    """Prompts user for a choice with a default value."""
    while True:
        try:
            val = input(f"{prompt_text} [{default}]: ").strip()
            if not val:
                return default
            if val in valid_choices:
                return val
            print(f"Invalid option. Please choose from: {', '.join(valid_choices)}")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)


def prompt_range() -> tuple[int, int]:
    """Prompts user for numeric start and end range."""
    while True:
        try:
            val = input("Enter number range (e.g. '01-50' or '1 20'): ").strip()
            import re
            parts = re.split(r"[\s,\-]+", val)
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                s, e = int(parts[0]), int(parts[1])
                if s > e:
                    s, e = e, s
                return s, e
            print("Please enter two numbers separated by hyphen or space (e.g. 10-20).")
        except ValueError:
            print("Invalid input. Please enter numbers only.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)


def prompt_ids() -> list[str]:
    """Prompts user for a list of IDs separated by space or commas."""
    while True:
        try:
            val = input("Enter specific IDs separated by comma or space (e.g. 'FE01, FE03, FE10'): ").strip()
            if not val:
                print("Please enter at least one ID.")
                continue
            import re
            parts = [p.strip().upper() for p in re.split(r"[\s,]+", val) if p.strip()]
            if parts:
                return parts
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)


def main() -> int:
    print("=" * 64)
    print("      FETCH CORRECTED SCRIPTS FROM GOOGLE SHEETS (COLUMN D)")
    print("=" * 64)

    # 1. Operation Mode
    print("\nSelect operation mode:")
    print("  [1] Fetch ALL 16 Google Sheets (Batch)")
    print("  [2] Fetch a Single specific sheet")
    mode_choice = prompt_choice("Enter choice (1-2)", ["1", "2"], "1")

    if mode_choice == "1":
        print("\nFetching corrected scripts for ALL 16 Google Sheets...")
        try:
            summary = fetch_all_sheets_corrected_scripts()
            print("\n" + "=" * 64)
            print("  BATCH FETCH COMPLETE")
            print("=" * 64)
            print(f"  Total sheets checked:   {summary['total_sheets']}")
            print(f"  Total scripts fetched:  {summary['total_fetched']}")
            print(f"  Output directory:       {summary['output_dir']}")
            print("=" * 64 + "\n")
            return 0
        except Exception as e:
            print(f"\n[ERROR] Batch fetch failed: {e}", file=sys.stderr)
            return 1

    # 2. Select Language
    print("\nSelect Language:")
    print("  [1] French")
    print("  [2] Spanish")
    print("  [3] English")
    print("  [4] Italian")
    lang_map = {"1": "french", "2": "spanish", "3": "english", "4": "italian"}
    lang_choice = prompt_choice("Enter language (1-4)", ["1", "2", "3", "4"], "1")
    selected_language = lang_map[lang_choice]

    # 3. Select Video Type
    print("\nSelect Video Type:")
    print("  [1] Expression")
    print("  [2] Fun Facts")
    print("  [3] Game")
    print("  [4] Roleplay")
    type_map = {"1": "expression", "2": "fun_facts", "3": "game", "4": "roleplay"}
    type_choice = prompt_choice("Enter video type (1-4)", ["1", "2", "3", "4"], "1")
    selected_type = type_map[type_choice]

    # 4. Scope Selection
    print("\nSelect Scope:")
    print("  [1] All records (only those where SCRIPT_CHANGED is non-empty)")
    print("  [2] By Number Range (e.g. 01-50)")
    print("  [3] Specific ID(s) (e.g. FE01, FE03)")
    print("  [4] From CSV list file")
    scope_choice = prompt_choice("Enter scope (1-4)", ["1", "2", "3", "4"], "1")

    start_num, end_num = None, None
    target_ids = None
    csv_file = None
    scope_name = "all"

    if scope_choice == "1":
        scope_name = "all"

    elif scope_choice == "2":
        scope_name = "range"
        start_num, end_num = prompt_range()
        print(f"  Target range set to numbers: {start_num} .. {end_num}")

    elif scope_choice == "3":
        scope_name = "ids"
        target_ids = prompt_ids()
        print(f"  Target IDs set to: {', '.join(target_ids)}")

    elif scope_choice == "4":
        scope_name = "csv"
        default_csv = DEFAULT_OUTPUT_DIR / "ids_to_fetch.csv"
        print(f"  Default CSV file: {default_csv}")
        custom_csv = input(f"Enter CSV path or press Enter for default: ").strip()
        csv_file = Path(custom_csv).resolve() if custom_csv else default_csv
        if not csv_file.exists():
            print(f"[ERROR] Specified CSV file does not exist: {csv_file}", file=sys.stderr)
            return 1
        print(f"  Using CSV: {csv_file}")

    try:
        out_csv, count = fetch_and_save_corrected_scripts(
            language=selected_language,
            video_type=selected_type,
            scope=scope_name,
            start_num=start_num,
            end_num=end_num,
            target_ids=target_ids,
            csv_file=csv_file,
            require_non_empty_script=(scope_name == "all"),
        )

        print("\n=======================================================")
        print(f"  DONE: Successfully saved {count} script(s)!")
        print(f"  Destination: {out_csv}")
        print("=======================================================\n")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Fetching corrected scripts failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
