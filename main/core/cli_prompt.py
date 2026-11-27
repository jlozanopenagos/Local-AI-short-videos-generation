"""
cli_prompt.py — Interactive CLI prompts with countdown timers for shorts_automation.
"""

from __future__ import annotations

import sys
import time
from typing import Optional, List


def timed_input(
    prompt: str,
    timeout: float = 10.0,
    default: str = "",
    default_msg: Optional[str] = None,
) -> str:
    """
    Prompts for interactive console input with a countdown timer.
    Automatically defaults to `default` when timeout expires without input.
    If the user starts typing, the countdown is paused to let them complete their input.
    """
    if not sys.stdin.isatty():
        return default

    clean_prompt = prompt.rstrip()
    if clean_prompt.endswith(":"):
        clean_prompt = clean_prompt[:-1].rstrip()

    if sys.platform == "win32":
        import msvcrt
        start_time = time.time()
        user_chars: List[str] = []
        last_sec = -1

        while True:
            elapsed = time.time() - start_time
            remaining = max(0, int(timeout - elapsed) + 1)

            if not user_chars:
                if remaining != last_sec:
                    last_sec = remaining
                    sys.stdout.write(f"\r{clean_prompt} (auto in {remaining:2d}s): ")
                    sys.stdout.flush()

                if elapsed >= timeout:
                    print()
                    if default_msg:
                        print(f"[Timer: {int(timeout)}s elapsed] {default_msg}")
                    else:
                        shown = repr(default) if default else "default"
                        print(f"[Timer: {int(timeout)}s elapsed] Automatically selecting [{shown}].")
                    return default

            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    print()
                    val = "".join(user_chars).strip()
                    return val if val else default
                elif ch == "\x03":  # Ctrl+C
                    raise KeyboardInterrupt
                elif ch in ("\x00", "\xe0"):  # Extended key prefix on Windows (arrows, F-keys)
                    if msvcrt.kbhit():
                        msvcrt.getwch()  # Consume scan code
                    continue
                elif ch in ("\b", "\x08", "\x7f"):  # Backspace
                    if user_chars:
                        user_chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                        if not user_chars:
                            # Reset countdown if user cleared input
                            start_time = time.time()
                            last_sec = -1
                elif ch == "\x1b":  # Escape: clear input
                    if user_chars:
                        padding = " " * len(user_chars)
                        sys.stdout.write("\b" * len(user_chars) + padding + "\b" * len(user_chars))
                        sys.stdout.flush()
                        user_chars.clear()
                        start_time = time.time()
                        last_sec = -1
                else:
                    if not user_chars:
                        # Clear countdown line before writing user's characters
                        padding = " " * (len(clean_prompt) + 30)
                        sys.stdout.write(f"\r{padding}\r{clean_prompt}: ")
                        sys.stdout.flush()
                    user_chars.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()

            time.sleep(0.04)

    # Unix fallback using select
    import select
    print(f"{clean_prompt} (auto in {int(timeout)}s): ", end="", flush=True)
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        val = sys.stdin.readline().strip()
        return val if val else default
    else:
        print()
        if default_msg:
            print(f"[Timer: {int(timeout)}s elapsed] {default_msg}")
        else:
            shown = repr(default) if default else "default"
            print(f"[Timer: {int(timeout)}s elapsed] Automatically selecting [{shown}].")
        return default


def prompt_fun_facts_cards_variant(
    script_data: dict,
    auto: bool = False,
    remembered_dialects: Optional[dict] = None,
) -> Optional[str]:
    """
    Prompts the user before video assembly to choose the opening & closure card version,
    EXCLUSIVELY for Fun Facts scripts in English or Spanish.
    - English: [1] American English, [2] British English
    - Spanish: [1] Latin American, [2] Spain / Peninsular Spanish
    - French / Italian or other formats (Expression, Game, Roleplay): returns None without prompting.
    """
    if not isinstance(script_data, dict):
        return None

    try:
        from config.settings import resolve_script_language, resolve_script_video_type
    except (ImportError, ModuleNotFoundError):
        try:
            from config import resolve_script_language, resolve_script_video_type
        except (ImportError, ModuleNotFoundError):
            return None

    vtype = resolve_script_video_type(script_data)
    if vtype not in ("fun_facts", "funfacts"):
        return None

    lang = resolve_script_language(script_data)
    if lang not in ("english", "spanish"):
        return None

    script_id = script_data.get("id", "UNKNOWN")

    # Use remembered batch default if previously set
    if remembered_dialects and lang in remembered_dialects:
        selected = remembered_dialects[lang]
        label = (
            "American English" if selected == "american"
            else "British English" if selected == "british"
            else "Latin American" if selected == "latin_american"
            else "Spain / Peninsular Spanish"
        )
        print(f"[{script_id}] Using batch-selected card version: '{label}'.")
        return selected

    if auto or not sys.stdin.isatty():
        return "american" if lang == "english" else "latin_american"

    print("\n" + "=" * 65)
    print(f"  OPENING & CLOSURE CARD SELECTION: {script_id} ({lang.title()} Fun Facts)")
    print("=" * 65)

    if lang == "english":
        print("Choose version for opening/closure cards:")
        print("  [1] American English (Default)")
        print("  [2] British English")
        print("  (Tip: add 'a' to apply to all remaining English scripts, e.g. '1a' or '2a')")
        print("-" * 65)
        try:
            raw = input("Choice [1/2] (Default [1]): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

        apply_all = "a" in raw
        choice = raw.replace("a", "").strip()

        if choice == "2":
            dialect = "british"
            label = "British English"
        else:
            dialect = "american"
            label = "American English"

        if apply_all and remembered_dialects is not None:
            remembered_dialects["english"] = dialect
            print(f"-> Applied '{label}' to all remaining English Fun Facts scripts in this batch.")
        else:
            print(f"-> Selected '{label}' for script {script_id}.")

        print("=" * 65 + "\n")
        return dialect

    elif lang == "spanish":
        print("Choose version for opening/closure cards:")
        print("  [1] Latin American (Default)")
        print("  [2] Spain / Peninsular Spanish")
        print("  (Tip: add 'a' to apply to all remaining Spanish scripts, e.g. '1a' or '2a')")
        print("-" * 65)
        try:
            raw = input("Choice [1/2] (Default [1]): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

        apply_all = "a" in raw
        choice = raw.replace("a", "").strip()

        if choice == "2":
            dialect = "spain"
            label = "Spain / Peninsular Spanish"
        else:
            dialect = "latin_american"
            label = "Latin American"

        if apply_all and remembered_dialects is not None:
            remembered_dialects["spanish"] = dialect
            print(f"-> Applied '{label}' to all remaining Spanish Fun Facts scripts in this batch.")
        else:
            print(f"-> Selected '{label}' for script {script_id}.")

        print("=" * 65 + "\n")
        return dialect

    return None
