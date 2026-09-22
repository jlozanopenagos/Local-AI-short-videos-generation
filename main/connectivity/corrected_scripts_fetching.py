#!/usr/bin/env python3
"""
corrected_scripts_fetching.py — Interactive CLI for Fetching Corrected Scripts (Column D).

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
            # Split by hyphen, comma, or whitespace
            import re
            parts = re.findall(r"\d+", val)
            if len(parts) >= 2:
                start = int(parts[0])
                end = int(parts[1])
                if start <= end:
                    return start, end
                return end, start
            elif len(parts) == 1:
                return 1, int(parts[0])
            print("Please enter two numbers, e.g. 01-50.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(0)


def prompt_ids() -> list[str]:
    """Prompts user for specific script IDs."""
    print("\nEnter target ID(s). You can enter multiple separated by commas, or press Enter when done:")
    collected: list[str] = []
    while True:
        try:
            val = input("Target ID(s): ").strip()
            if not val:
                if collected:
                    break
                print("Please enter at least one ID (e.g. EE01).")
                continue
            # Split comma/space separated
            parts = [p.strip().upper() for p in val.replace(",", " ").split() if p.strip()]
            collected.extend(parts)
            print(f"  Current queue: {', '.join(collected)}")
            more = input("Add more IDs? (y/N): ").strip().lower()
            if more not in ("y", "yes"):
                break
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(0)
    return collected


def main() -> int:
    print("\n=======================================================")
    print("   CORRECTED SCRIPTS FETCHER (GOOGLE SHEETS -> CSV)   ")
    print("=======================================================")
    print("Pulls Column D (SCRIPT_CHANGED) into:")
    print(f"  {DEFAULT_OUTPUT_DIR}\\<lang>_<type>_script_to_change.csv")
    print("-------------------------------------------------------")

    print("\nChoose Operation Mode:")
    print("  [1] Specific Sheet (Select Language & Video Type) [Default]")
    print("  [2] All Sheets (Fetch all entries across all 16 sheets)")
    mode = prompt_choice("Select Mode (1-2)", ["1", "2"], default="1")

    if mode == "2":
        # Mode 2: All sheets
        results = fetch_all_sheets_corrected_scripts(require_non_empty_script=True)
        print("\n[SUCCESS] Batch fetch across all sheets completed!")
        return 0

    # Mode 1: Specific sheet
    print("\n-------------------------------------------------------")
    print("Select Language:")
    print("  [1] English [Default]")
    print("  [2] French")
    print("  [3] Spanish")
    print("  [4] Italian")
    lang_choice = prompt_choice("Language (1-4)", ["1", "2", "3", "4"], default="1")
    lang_map = {"1": "english", "2": "french", "3": "spanish", "4": "italian"}
    selected_language = lang_map[lang_choice]

    print("\n-------------------------------------------------------")
    print("Select Video Type:")
    print("  [1] Expression [Default]")
    print("  [2] Game")
    print("  [3] Roleplay")
    print("  [4] Fun Facts")
    type_choice = prompt_choice("Video Type (1-4)", ["1", "2", "3", "4"], default="1")
    type_map = {"1": "expression", "2": "game", "3": "roleplay", "4": "fun_facts"}
    selected_type = type_map[type_choice]

    print("\n-------------------------------------------------------")
    print(f"Target Sheet: {selected_language.capitalize()} - {selected_type.upper()}")
    print("Select Scope:")
    print("  [1] All changed scripts in this sheet [Default]")
    print("  [2] By Number Range (e.g. 01 - 50)")
    print("  [3] By specific ID(s) (enter one by one or comma-separated)")
    print("  [4] By CSV list (reads IDs from input/csv/script_to_change/ids_to_fetch.csv)")
    scope_choice = prompt_choice("Scope (1-4)", ["1", "2", "3", "4"], default="1")

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
