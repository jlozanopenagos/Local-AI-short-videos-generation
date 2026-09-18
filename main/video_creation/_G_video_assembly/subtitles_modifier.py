import argparse
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root, video_creation, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import BASE_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, get_script_output_dir
from state_manager import StateManager

try:
    from main import process_script
    from core.transcriber import Transcriber
    from core.subtitle_builder import SubtitleBuilder
    from core.video_assembler import VideoAssembler
except ImportError:
    from video_creation._G_video_assembly.main import process_script
    from video_creation._G_video_assembly.core.transcriber import Transcriber
    from video_creation._G_video_assembly.core.subtitle_builder import SubtitleBuilder
    from video_creation._G_video_assembly.core.video_assembler import VideoAssembler


def get_ass_path(script_id: str, base_dir: Path = BASE_DIR, language: str = None) -> Path:
    return get_script_output_dir(script_id, language, base_dir) / f"script_{script_id}_subtitles.ass"


def inspect_subtitles(ass_path: Path) -> List[Tuple[str, str, str]]:
    """Parses Dialogue lines from an ASS file into (start, end, text) tuples."""
    if not ass_path.exists():
        print(f"[ERROR] Subtitle file not found: {ass_path}")
        return []

    dialogues = []
    with ass_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("Dialogue:"):
                # Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    start_time = parts[1].strip()
                    end_time = parts[2].strip()
                    text = parts[9].rstrip("\r\n")
                    # Strip ASS inline override tags like {\k10} or {\b1}
                    clean_text = re.sub(r"\{.*?\}", "", text)
                    dialogues.append((start_time, end_time, clean_text))
    return dialogues


def print_subtitles_table(dialogues: List[Tuple[str, str, str]], max_items: int = 40):
    if not dialogues:
        print("No dialogue events found in subtitles file.")
        return

    print("\n" + "=" * 60)
    print(f"{'START':<12} {'END':<12} {'TEXT'}")
    print("-" * 60)
    for idx, (start, end, text) in enumerate(dialogues):
        if idx >= max_items:
            print(f"... and {len(dialogues) - max_items} more words/lines.")
            break
        print(f"{start:<12} {end:<12} {text}")
    print("=" * 60 + "\n")


def find_and_replace_in_ass(ass_path: Path, find_text: str, replace_text: str, case_sensitive: bool = False) -> int:
    """Finds and replaces text specifically in the Text field of Dialogue lines in the ASS file."""
    if not ass_path.exists():
        print(f"[ERROR] Subtitle file not found: {ass_path}")
        return 0

    if not find_text:
        print("[ERROR] Search term cannot be empty.")
        return 0

    with ass_path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    modified_lines = []
    total_replacements = 0

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(find_text), flags)

    for line in lines:
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) >= 10:
                header = ",".join(parts[:9]) + ","
                dialogue_text = parts[9]
                new_text, count = pattern.subn(replace_text, dialogue_text)
                if count > 0:
                    total_replacements += count
                    line = header + new_text
        modified_lines.append(line)

    if total_replacements > 0:
        with ass_path.open("w", encoding="utf-8") as f:
            f.writelines(modified_lines)
        print(f"[SUCCESS] Replaced {total_replacements} occurrence(s) of '{find_text}' with '{replace_text}'.")
    else:
        print(f"[NOTICE] No occurrences of '{find_text}' found in subtitle dialogues.")

    return total_replacements


def open_file_in_editor(file_path: Path):
    """Attempts to open the file in the default editor on Windows or system fallback."""
    if not file_path.exists():
        print(f"[ERROR] File does not exist: {file_path}")
        return

    print(f"Opening {file_path.name} in text editor...")
    try:
        if sys.platform == "win32":
            os.startfile(str(file_path.resolve()))
        else:
            subprocess.run(["xdg-open", str(file_path.resolve())], check=False)
    except Exception as exc:
        print(f"[WARNING] Could not launch default editor: {exc}")
        print(f"You can manually edit the file at: {file_path.resolve()}")


def list_available_scripts(state_manager: StateManager) -> List[Dict]:
    """Returns all scripts that have master audio and images ready."""
    all_scripts = state_manager.get_all_scripts()
    valid = []
    for s in all_scripts:
        status = s.get("status", {})
        if status.get("voice_generation") == "done" and status.get("image_generation") == "done":
            valid.append(s)
    # Sort numerically by script ID if digit, otherwise alphabetically
    valid.sort(key=lambda s: (0, int(s["id"])) if str(s["id"]).isdigit() else (1, str(s["id"])))
    return valid


def interactive_script_menu(script_data: Dict, state_manager: StateManager, base_dir: Path):
    script_id = script_data["id"]
    label = script_data.get("metadata", {}).get("LABEL") or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE", "english")
    script_output_dir = get_script_output_dir(script_id, label, base_dir)
    ass_path = script_output_dir / f"script_{script_id}_subtitles.ass"

    while True:
        has_subtitles = ass_path.exists()
        has_video = (script_output_dir / f"script_{script_id}_final.mp4").exists()

        sub_status = "EXISTS" if has_subtitles else "NOT FOUND"
        vid_status = "DONE" if has_video else "PENDING"

        expression = (
            script_data.get("prompt_params", {}).get("EXPRESSION")
            or script_data.get("content_metadata", {}).get("topic")
            or "Unknown"
        )
        video_type = (
            script_data.get("content_metadata", {}).get("video_type")
            or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
            or "SHORT"
        )

        print("\n" + "=" * 60)
        print(f"SCRIPT {script_id}: {expression} ({video_type})")
        print(f"Subtitles: [{sub_status}] | Final Video: [{vid_status}]")
        print(f"Subtitle File: {ass_path}")
        print("=" * 60)
        print("  [1] Re-assemble video using current/edited subtitles (.ass)")
        print("  [2] Inspect subtitle lines and timings")
        print("  [3] Find & replace words/phrases in subtitles")
        print("  [4] Re-generate fresh subtitles from master audio (Whisper)")
        print("  [5] Open .ass file in text editor")
        print("  [b] Back to script list")
        print("  [q] Quit")
        print("-" * 60)

        try:
            choice = input("Select an option: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return False

        if choice in ["q", "quit", "exit"]:
            print("Goodbye!")
            return False
        elif choice in ["b", "back"]:
            return True
        elif choice == "1":
            if not has_subtitles:
                print(f"[NOTICE] No existing subtitles found for script {script_id}. Fresh transcription will run.")
                regenerate = True
            else:
                regenerate = False

            print(f"\nStarting video assembly for script {script_id} (regenerate_subtitles={regenerate})...")
            success = process_script(
                script_data=script_data,
                state_manager=state_manager,
                base_dir=base_dir,
                regenerate_subtitles=regenerate,
                ass_path=ass_path
            )
            if success:
                print(f"\n[SUCCESS] Video successfully assembled for script {script_id}!")
            else:
                print(f"\n[ERROR] Video assembly failed for script {script_id}.")

        elif choice == "2":
            if not has_subtitles:
                print(f"[ERROR] No subtitles found. Use Option [4] first to transcribe audio.")
                continue
            dialogues = inspect_subtitles(ass_path)
            print_subtitles_table(dialogues)

        elif choice == "3":
            if not has_subtitles:
                print(f"[ERROR] No subtitles found. Use Option [4] first to transcribe audio.")
                continue
            try:
                find_txt = input("Enter text/word to find: ").strip()
                if not find_txt:
                    print("Cancelled.")
                    continue
                replace_txt = input("Enter replacement text: ").strip()
                case_choice = input("Case-sensitive search? [y/N]: ").strip().lower()
                case_sensitive = case_choice in ["y", "yes"]
                find_and_replace_in_ass(ass_path, find_txt, replace_txt, case_sensitive=case_sensitive)
            except (KeyboardInterrupt, EOFError):
                print("\nAction cancelled.")

        elif choice == "4":
            print(f"\nRe-generating fresh subtitles from master audio with Whisper...")
            success = process_script(
                script_data=script_data,
                state_manager=state_manager,
                base_dir=base_dir,
                regenerate_subtitles=True,
                ass_path=ass_path
            )
            if success:
                print(f"\n[SUCCESS] Subtitles regenerated and video re-assembled for script {script_id}!")
            else:
                print(f"\n[ERROR] Failed to regenerate subtitles and assemble video for script {script_id}.")

        elif choice == "5":
            if not has_subtitles:
                print(f"[ERROR] No subtitles found. Use Option [4] first to transcribe audio.")
                continue
            open_file_in_editor(ass_path)
        else:
            print(f"Invalid option '{choice}'. Please select 1-5, 'b', or 'q'.")

    return True


def main():
    parser = argparse.ArgumentParser(description="Interactive Subtitle Modifier and Video Re-assembler")
    parser.add_argument("script_id_pos", nargs="?", default=None, help="Script ID to modify (optional positional argument)")
    parser.add_argument("--script-id", type=str, default=None, help="Script ID to modify")
    parser.add_argument("--keep-subtitles", "--skip-transcribe", dest="keep_subtitles", action="store_true", help="Keep existing .ass subtitles without Whisper re-transcription")
    parser.add_argument("--force-transcribe", action="store_true", help="Force Whisper re-transcription even if subtitles exist")
    args = parser.parse_args()

    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)

    target_script_id = args.script_id or args.script_id_pos

    # Non-interactive CLI execution mode
    if target_script_id is not None:
        clean_id = target_script_id.replace("script_", "").replace(".json", "").strip()
        script_data = state_manager.get_script_state(clean_id)
        if not script_data or not script_data.get("script_text"):
            print(f"[ERROR] Script '{clean_id}' not found in state.")
            return 1

        ass_path = get_ass_path(clean_id, base_dir)
        regenerate = True
        if args.keep_subtitles:
            regenerate = False
        elif not args.force_transcribe and ass_path.exists():
            regenerate = False

        print(f"Processing script {clean_id} non-interactively (regenerate_subtitles={regenerate})...")
        success = process_script(
            script_data=script_data,
            state_manager=state_manager,
            base_dir=base_dir,
            regenerate_subtitles=regenerate,
            ass_path=ass_path
        )
        return 0 if success else 1

    # Interactive Loop
    while True:
        available = list_available_scripts(state_manager)
        if not available:
            print("[NOTICE] No scripts with voice and image generation completed found.")
            return 0

        print("\n" + "=" * 60)
        print("SUBTITLES & ASSEMBLY MODIFIER - AVAILABLE SCRIPTS")
        print("=" * 60)
        for s in available:
            sid = s["id"]
            topic = s.get("prompt_params", {}).get("EXPRESSION") or s.get("content_metadata", {}).get("topic") or ""
            vtype = s.get("content_metadata", {}).get("video_type") or s.get("prompt_params", {}).get("VIDEO_TYPE") or "SHORT"
            ass_file = get_ass_path(sid, base_dir)
            ass_status = "ASS: OK" if ass_file.exists() else "ASS: Missing"
            video_done = "Video: DONE" if s.get("status", {}).get("video_assembly") == "done" else "Video: PENDING"
            print(f"  [{sid}] {topic:<24} ({vtype:<10}) [{ass_status} | {video_done}]")
        print("=" * 60)

        try:
            user_input = input("Enter script number to modify (e.g. 1) [or 'q' to quit]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if user_input.lower() in ["q", "quit", "exit"]:
            print("Goodbye!")
            break

        clean_id = user_input.replace("script_", "").replace(".json", "").strip()
        script_data = state_manager.get_script_state(clean_id)
        if not script_data.get("script_text"):
            print(f"[ERROR] Script '{clean_id}' not found.")
            continue

        keep_running = interactive_script_menu(script_data, state_manager, base_dir)
        if not keep_running:
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
