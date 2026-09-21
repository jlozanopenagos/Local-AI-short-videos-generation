"""
cli_prompt.py — Interactive CLI prompts with countdown timers for shorts_automation.
"""

from __future__ import annotations

import sys
import time
import re
from pathlib import Path
from typing import Optional, List, Union, Tuple


def _timed_choice(timeout: float = 10.0, default: str = "1", valid_choices: tuple = ("1", "2", "3")) -> str:
    """
    Waits for user to press a valid choice key within timeout seconds.
    Defaults to `default` (e.g. '1') if timeout expires without keypress.
    """
    choices_str = "/".join(valid_choices)
    if sys.platform == "win32":
        import msvcrt
        start_time = time.time()
        last_sec = -1

        while True:
            elapsed = time.time() - start_time
            remaining = max(0, int(timeout - elapsed) + 1)

            if remaining != last_sec:
                last_sec = remaining
                sys.stdout.write(f"\rChoice [{choices_str}] (auto [{default}] in {remaining:2d}s): ")
                sys.stdout.flush()

            if elapsed >= timeout:
                print(f"\n[Timer: {int(timeout)}s elapsed] Automatically selected option [{default}] (Mass-produce).")
                return default

            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    print()
                    return default
                elif ch in valid_choices:
                    print(ch)
                    return ch
                elif ch == "\x03":  # Ctrl+C
                    raise KeyboardInterrupt

            time.sleep(0.05)

    # Unix fallback using select
    import select
    print(f"Choice [{choices_str}] (auto [{default}] in {int(timeout)}s): ", end="", flush=True)
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        val = sys.stdin.readline().strip()
        return val if val in valid_choices else default
    else:
        print(f"\n[Timer: {int(timeout)}s elapsed] Automatically selected option [{default}].")
        return default


def _check_script_state_exists(script_id: str, base_dir: Optional[Path] = None) -> bool:
    """Checks if state JSON file exists for the given script_id."""
    try:
        from core.state_manager import StateManager
        if base_dir is None:
            try:
                from config.settings import BASE_DIR
                base_dir = BASE_DIR
            except ImportError:
                base_dir = Path(__file__).resolve().parent.parent
        mgr = StateManager(base_dir)
        return mgr.script_exists(script_id)
    except Exception:
        return True


def prompt_group_range(
    require_existing_state: bool = False,
    base_dir: Optional[Path] = None,
) -> Optional[List[str]]:
    """
    Prompts user for language and a number range (e.g. 10 - 20 inclusive).
    Generates IDs for EXPRESSION ('E'), GAME ('G'), and ROLEPLAY ('R') (excluding FUN_FACTS 'F').
    E.g. English 10-20 -> EE10..EE20, EG10..EG20, ER10..ER20.
    """
    print("\n" + "-" * 55)
    print("  GROUP RANGE CONFIGURATION")
    print("-" * 55)

    # 1. Select Language
    print("Select Language:")
    print("  [1] English (E)  [Default]")
    print("  [2] French (F)")
    print("  [3] Spanish (S)")
    print("  [4] Italian (I)")
    print("  [5] All languages (English, French, Spanish, Italian)")

    lang_map = {
        "1": [("E", "English")],
        "2": [("F", "French")],
        "3": [("S", "Spanish")],
        "4": [("I", "Italian")],
        "5": [("E", "English"), ("F", "French"), ("S", "Spanish"), ("I", "Italian")],
    }

    try:
        lang_choice = input("Choice [1-5] (default [1]): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        sys.exit(0)

    selected_langs = lang_map.get(lang_choice, lang_map["1"])

    # 2. Enter Number Range
    while True:
        try:
            raw_range = input("\nEnter number range (e.g. 10-20 or 10 20): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

        if not raw_range:
            print("[Warning] No range entered. Please enter a valid range (e.g. 10-20).")
            continue

        nums = [int(x) for x in re.findall(r"\d+", raw_range)]
        if not nums:
            print("[Error] Could not find any numbers in your input. Try e.g. 10-20.")
            continue
        elif len(nums) == 1:
            start_num, end_num = nums[0], nums[0]
        else:
            start_num, end_num = nums[0], nums[1]

        if start_num > end_num:
            start_num, end_num = end_num, start_num

        break

    # 3. Generate IDs: EXPRESSION ('E'), GAME ('G'), ROLEPLAY ('R') (excluding FUN_FACTS 'F')
    video_types = [
        ("E", "EXPRESSION"),
        ("G", "GAME"),
        ("R", "ROLEPLAY"),
    ]

    queued_ids: List[str] = []
    for lang_code, lang_name in selected_langs:
        for type_code, type_name in video_types:
            for num in range(start_num, end_num + 1):
                sid = f"{lang_code}{type_code}{num:02d}"
                if sid not in queued_ids:
                    if require_existing_state and not _check_script_state_exists(sid, base_dir):
                        continue
                    queued_ids.append(sid)

    print(f"\n[Group Range] Generated {len(queued_ids)} target script ID(s) for numbers {start_num} to {end_num} (excluding FUN_FACTS):")
    for lang_code, lang_name in selected_langs:
        for type_code, type_name in video_types:
            type_ids = [s for s in queued_ids if s.startswith(f"{lang_code}{type_code}")]
            if type_ids:
                print(f"  - {lang_name} {type_name}: {type_ids[0]} .. {type_ids[-1]} ({len(type_ids)} scripts)")
    print()

    return queued_ids if queued_ids else None


def prompt_fun_facts_mode(
    require_existing_state: bool = False,
    base_dir: Optional[Path] = None,
) -> Optional[List[str]]:
    """
    Prompts user for language and scope (all pending or number range) for FUN_FACTS scripts ('F').
    E.g.:
      - English All -> EF01..EF15
      - Spanish 1-5 -> SF01..SF05
      - All languages -> EF.., FF.., SF.., IF..
    """
    import csv

    if base_dir is None:
        try:
            from config.settings import BASE_DIR
            base_dir = BASE_DIR
        except ImportError:
            try:
                from config import BASE_DIR
                base_dir = BASE_DIR
            except ImportError:
                base_dir = Path(__file__).resolve().parent.parent

    print("\n" + "-" * 55)
    print("  FUN FACTS CONFIGURATION")
    print("-" * 55)

    # 1. Select Language
    print("Select Language:")
    print("  [1] All languages (English, French, Spanish, Italian) [Default]")
    print("  [2] English (EF)")
    print("  [3] French (FF)")
    print("  [4] Spanish (SF)")
    print("  [5] Italian (IF)")

    all_langs = [("E", "English"), ("F", "French"), ("S", "Spanish"), ("I", "Italian")]
    lang_map = {
        "1": all_langs,
        "2": [("E", "English")],
        "3": [("F", "French")],
        "4": [("S", "Spanish")],
        "5": [("I", "Italian")],
    }

    try:
        lang_choice = input("Choice [1-5] (default [1]): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        sys.exit(0)

    selected_langs = lang_map.get(lang_choice, all_langs)

    # 2. Select Scope
    print("\nSelect Scope:")
    print("  [1] All pending Fun Facts in selected language(s) [Default]")
    print("  [2] Specific number range (e.g. 1-10)")

    try:
        scope_choice = input("Choice [1/2] (default [1]): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        sys.exit(0)

    if scope_choice != "2":
        queued_ids: List[str] = []
        for lang_code, lang_name in selected_langs:
            csv_path = base_dir / "input" / "csv" / lang_name.lower() / "expressions_list" / f"{lang_name.upper()}_READY_PROMPTS_FUN_FACTS.csv"
            if csv_path.exists():
                with csv_path.open("r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sid = str(row.get("ID", "")).strip().upper()
                        if sid and sid not in queued_ids:
                            if require_existing_state and not _check_script_state_exists(sid, base_dir):
                                continue
                            queued_ids.append(sid)
            else:
                for num in range(1, 16):
                    sid = f"{lang_code}F{num:02d}"
                    if sid not in queued_ids:
                        if require_existing_state and not _check_script_state_exists(sid, base_dir):
                            continue
                        queued_ids.append(sid)

        print(f"\n[Fun Facts] Queued {len(queued_ids)} target Fun Facts script(s):")
        for lang_code, lang_name in selected_langs:
            type_ids = [s for s in queued_ids if s.startswith(f"{lang_code}F")]
            if type_ids:
                print(f"  - {lang_name} Fun Facts: {type_ids[0]} .. {type_ids[-1]} ({len(type_ids)} scripts)")
        print()
        return queued_ids if queued_ids else None

    # Number Range Scope
    while True:
        try:
            raw_range = input("\nEnter number range (e.g. 1-10 or 1 5): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

        if not raw_range:
            print("[Warning] No range entered. Please enter a valid range (e.g. 1-10).")
            continue

        nums = [int(x) for x in re.findall(r"\d+", raw_range)]
        if not nums:
            print("[Error] Could not find any numbers in your input. Try e.g. 1-10.")
            continue
        elif len(nums) == 1:
            start_num, end_num = nums[0], nums[0]
        else:
            start_num, end_num = nums[0], nums[1]

        if start_num > end_num:
            start_num, end_num = end_num, start_num

        break

    queued_ids = []
    for lang_code, lang_name in selected_langs:
        for num in range(start_num, end_num + 1):
            sid = f"{lang_code}F{num:02d}"
            if sid not in queued_ids:
                if require_existing_state and not _check_script_state_exists(sid, base_dir):
                    continue
                queued_ids.append(sid)

    print(f"\n[Fun Facts Range] Generated {len(queued_ids)} target script ID(s) for numbers {start_num} to {end_num}:")
    for lang_code, lang_name in selected_langs:
        type_ids = [s for s in queued_ids if s.startswith(f"{lang_code}F")]
        if type_ids:
            print(f"  - {lang_name} Fun Facts: {type_ids[0]} .. {type_ids[-1]} ({len(type_ids)} scripts)")
    print()

    return queued_ids if queued_ids else None


def prompt_production_mode(
    stage_title: str,
    asset_name: str,
    timeout: float = 10.0,
    script_id_arg: Optional[Union[str, List[str]]] = None,
    auto: bool = False,
    require_existing_state: bool = False,
    base_dir: Optional[Path] = None,
    return_mode: bool = False,
    allow_fun_facts_mode: bool = False,
) -> Union[Optional[List[str]], Tuple[Optional[List[str]], str]]:
    """
    Prompts the user in the terminal to choose between:
      [1] Mass-producing all pending assets (default if timeout expires or chosen)
      [2] Selecting specific script(s) by ID to produce in a custom queue
      [3] Producing by Number Range / Group (e.g. 10 - 20)
      [4] Fun Facts only (produce only Fun Facts scripts, if allow_fun_facts_mode is True)

    Args:
        stage_title: Human-readable stage title (e.g. "Part B: Voice Generation").
        asset_name: Descriptive noun for the assets (e.g. "voiceovers / audios").
        timeout: Countdown timeout in seconds (default 10.0s).
        script_id_arg: If --script-id was already provided via CLI, bypasses prompt and returns that list.
        auto: If True, bypasses prompt and defaults to mass-produce (or script_id_arg).
        require_existing_state: If True, checks that state/<lang>/<type>/script_<ID>.json exists before queueing.
        base_dir: Base project directory for state checks.
        return_mode: If True, returns (target_ids, mode) tuple where mode is 'mass', 'specific', 'group_range', or 'fun_facts'.
        allow_fun_facts_mode: If True, adds Option [4] for Fun Facts only production.

    Returns:
        Optional[List[str]] or Tuple[Optional[List[str]], str]:
            - None or (None, 'mass'): Proceed with mass-production of all pending scripts.
            - List[str] or (List[str], mode): Canonical Script IDs to process in order.
    """
    if script_id_arg:
        if isinstance(script_id_arg, (list, tuple, set)):
            target_ids = [str(x).strip().upper() for x in script_id_arg if str(x).strip()]
        else:
            target_ids = [x.strip().upper() for x in str(script_id_arg).split(",") if x.strip()]

        if target_ids:
            print(f"\n[CLI Override] Script ID(s) specified via command line: {', '.join(target_ids)}")
            if require_existing_state:
                missing = [sid for sid in target_ids if not _check_script_state_exists(sid, base_dir)]
                if missing:
                    print(f"[Warning] Note: State JSON not found for: {', '.join(missing)}")
            return (target_ids, "specific") if return_mode else target_ids

    if auto or not sys.stdin.isatty():
        print(f"\n[Auto Mode] Defaulting to mass-producing all pending {asset_name}.")
        return (None, "mass") if return_mode else None

    valid_choices = ("1", "2", "3", "4") if allow_fun_facts_mode else ("1", "2", "3")

    print("\n" + "=" * 65)
    print(f"  {stage_title.upper()}")
    print("=" * 65)
    print(f"Choose production mode for {asset_name}:")
    print(f"  [1] Mass-produce all pending assets (Default in {int(timeout)}s)")
    print( "  [2] Select specific script(s) by ID to produce")
    print( "  [3] Produce by Number Range / Group (e.g. 10 - 20)")
    if allow_fun_facts_mode:
        print("  [4] Fun Facts only (produce only Fun Facts scripts)")
    print("-" * 65)

    choice = _timed_choice(timeout=timeout, default="1", valid_choices=valid_choices)

    if choice == "1":
        print(f"[Selected Mode] Mass-producing all pending {asset_name}.\n")
        return (None, "mass") if return_mode else None

    if choice == "3":
        group_ids = prompt_group_range(require_existing_state=require_existing_state, base_dir=base_dir)
        if group_ids:
            return (group_ids, "group_range") if return_mode else group_ids
        else:
            print("[Warning] No valid script IDs generated from range. Defaulting to mass-production.\n")
            return (None, "mass") if return_mode else None

    if choice == "4" and allow_fun_facts_mode:
        fun_facts_ids = prompt_fun_facts_mode(require_existing_state=require_existing_state, base_dir=base_dir)
        if fun_facts_ids:
            return (fun_facts_ids, "fun_facts") if return_mode else fun_facts_ids
        else:
            print("[Warning] No valid Fun Facts script IDs queued. Defaulting to mass-production.\n")
            return (None, "mass") if return_mode else None

    # Choice == "2": Interactive queue construction
    queued_ids: List[str] = []
    print("\n--- Enter Target Script IDs for Production ---")
    print("(You may enter single IDs e.g. 'EE01', or comma-separated e.g. 'EE01, EE02')\n")

    while True:
        try:
            prompt_label = f"Enter Script ID #{len(queued_ids) + 1}: " if queued_ids else "Enter Target Script ID: "
            raw_input = input(prompt_label).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

        if raw_input:
            parts = [p.strip().upper() for p in raw_input.split(",") if p.strip()]
            for sid in parts:
                if sid in queued_ids:
                    print(f"  [Info] '{sid}' is already in the queue.")
                    continue

                if require_existing_state and not _check_script_state_exists(sid, base_dir):
                    print(f"  [Warning] State file for script '{sid}' was not found in 'state/'! (script_{sid}.json missing)")
                    try:
                        confirm = input(f"  Queue '{sid}' anyway? [y/N]: ").strip().lower()
                    except (KeyboardInterrupt, EOFError):
                        print("\nOperation cancelled by user.")
                        sys.exit(0)
                    if confirm not in ("y", "yes"):
                        print(f"  Skipped '{sid}'.")
                        continue

                queued_ids.append(sid)
                print(f"  -> Added '{sid}' to queue (total: {len(queued_ids)} script(s) queued).")
        else:
            if not queued_ids:
                print("[Warning] No ID entered.")

        # Ask if the user wants to add another script
        try:
            add_more = input("\nAdd another script to produce? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

        if add_more not in ("y", "yes"):
            break
        print()

    if queued_ids:
        print(f"\n[Selected Mode] Starting production for {len(queued_ids)} queued script(s): {', '.join(queued_ids)}\n")
        return (queued_ids, "specific") if return_mode else queued_ids
    else:
        print("[Warning] No valid script IDs queued. Defaulting to mass-production.\n")
        return (None, "mass") if return_mode else None
