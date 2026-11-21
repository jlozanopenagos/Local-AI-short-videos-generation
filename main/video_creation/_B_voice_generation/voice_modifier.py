import argparse
import random
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root, video_creation, core, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    # pyrefly: ignore [missing-import]
    from core.cli_prompt import timed_input
except (ImportError, ModuleNotFoundError):
    try:
        # pyrefly: ignore [missing-import]
        from cli_prompt import timed_input
    except (ImportError, ModuleNotFoundError):
        def timed_input(prompt: str, timeout: float = 10.0, default: str = "", default_msg: str = None) -> str:
            try:
                val = input(prompt).strip()
                return val if val else default
            except (KeyboardInterrupt, EOFError):
                return default

# pyrefly: ignore [missing-import]
import config
# pyrefly: ignore [missing-import]
from config import (
    BASE_DIR,
    COMFY_API_URL, COMFY_OUTPUT_DIR, COMFY_INPUT_DIR,
    VOICE_WORKFLOW_PATH, OPEN_SWARA_DIR, STATIC_NARRATOR_PERSONALITY,
    require_services, get_script_output_dir
)

try:
    # pyrefly: ignore [missing-import]
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from state_manager import StateManager, resolve_lang_and_type

try:
    from video_creation._B_voice_generation.core.script_parser import get_script_segments
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient
    from video_creation._B_voice_generation.core.voice_manager import VoiceManager
    from video_creation._B_voice_generation.voice.common.orchestrator import (
        is_stress_pronunciation_vital,
        EMOTION_TRANSLATION_MAP,
        infer_dialogue_emotion,
        map_emotion_to_energy,
        synthesize_script_voice,
    )
except (ImportError, ModuleNotFoundError):
    from core.script_parser import get_script_segments
    from core.comfy_client import ComfyClient
    from core.voice_manager import VoiceManager
    from voice.common.orchestrator import (  # type: ignore[no-redef]
        is_stress_pronunciation_vital,
        EMOTION_TRANSLATION_MAP,
        infer_dialogue_emotion,
        map_emotion_to_energy,
        synthesize_script_voice,
    )


def resolve_user_script_id(raw_input: str, state_manager: StateManager) -> Optional[str]:
    """Resolves raw user input into a valid canonical Script ID (e.g. ER114, EE01, 114)."""
    cleaned = raw_input.strip().upper().replace("SCRIPT_", "").replace(".JSON", "")
    if not cleaned:
        return None

    if state_manager.script_exists(cleaned):
        return cleaned

    # Match numeric indices (e.g. '114' or '04')
    if cleaned.isdigit():
        padded = f"{int(cleaned):02d}"
        all_scripts = state_manager.get_all_scripts()
        matches = [
            s.get("id") for s in all_scripts
            if s.get("id") and s.get("id").endswith(padded)
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"\nMultiple scripts match index '{cleaned}': {', '.join(matches[:8])}")
            print("Please enter the full canonical ID (e.g. ER114, EE04).")

    return None


def parse_gender_token(token: str, default: str = "male") -> str:
    """Normalizes raw input tokens ('m', 'f', 'male', 'female', etc.) to 'male' or 'female'."""
    t = str(token).strip().lower()
    if t in ("f", "female", "girl", "woman"):
        return "female"
    if t in ("m", "male", "boy", "man"):
        return "male"
    return default


def prompt_speaker_genders(
    unique_speakers: List[str],
    current_genders: Dict[str, str],
    video_type: str,
    cli_genders: Optional[str] = None
) -> Dict[str, str]:
    """Interactively prompts the user to select the gender ('genre') for each speaker.
    Users only choose genders; reference voices are automatically randomized from the pool.
    """
    # Separate characters from narrator for structured roleplay prompts
    characters = [s for s in unique_speakers if "narrator" not in s.lower()]
    narrators = [s for s in unique_speakers if "narrator" in s.lower()]
    ordered_speakers = characters + narrators

    # 1. Handle CLI override if supplied (e.g. --genders "male, female" or --genders "f")
    if cli_genders:
        tokens = [t.strip().lower() for t in cli_genders.split(",") if t.strip()]
        result = {}
        for idx, spk in enumerate(ordered_speakers):
            fallback = current_genders.get(spk, "female" if "two" in spk.lower() else "male")
            if idx < len(tokens):
                result[spk] = parse_gender_token(tokens[idx], fallback)
            else:
                result[spk] = fallback
        return result

    # 2. Interactive display and prompting
    print("\n" + "-" * 60)
    print("SPEAKER GENDER SELECTION (Voices will be randomly cast):")
    for idx, spk in enumerate(ordered_speakers, 1):
        curr = current_genders.get(spk, "female" if "two" in spk.lower() else "male").lower()
        role_label = " (Dialogue Character)" if "narrator" not in spk.lower() else " (Storyteller / Mentor)"
        print(f"  [{idx}] {spk:12s}: {curr.upper()}{role_label}")
    print("-" * 60)

    selected_genders = {}

    if video_type == "ROLEPLAY" and len(characters) >= 2:
        default_str = ", ".join(
            current_genders.get(s, "female" if "two" in s.lower() else "male").lower()
            for s in ordered_speakers
        )
        try:
            prompt_msg = (
                f"Enter genders for [{', '.join(ordered_speakers)}]\n"
                f"  (e.g. 'm, f, m' or 'male, female, female', Enter to keep [{default_str.upper()}]): "
            )
            raw_input = timed_input(prompt_msg, timeout=30.0, default="").strip()
            if raw_input:
                tokens = [t.strip().lower() for t in raw_input.split(",") if t.strip()]
                if len(tokens) == len(ordered_speakers):
                    for idx, spk in enumerate(ordered_speakers):
                        selected_genders[spk] = parse_gender_token(tokens[idx], current_genders.get(spk, "male"))
                    return selected_genders
        except (KeyboardInterrupt, EOFError):
            pass

    # Step-by-step fallback / confirmation per speaker
    for spk in ordered_speakers:
        curr = current_genders.get(spk, "female" if "two" in spk.lower() else "male").lower()
        prompt_msg = f"  Gender for '{spk}' [m = Male / f = Female, Enter to keep '{curr.upper()}']: "
        try:
            choice = timed_input(prompt_msg, timeout=20.0, default=curr).strip().lower()
            selected_genders[spk] = parse_gender_token(choice, curr)
        except (KeyboardInterrupt, EOFError):
            selected_genders[spk] = curr

    return selected_genders


def main():
    parser = argparse.ArgumentParser(description="Modify or regenerate voice for a specific script.")
    parser.add_argument("--script-id", type=str, default=None, help="Script ID to modify (e.g. ER114, EE04)")
    parser.add_argument("--genders", type=str, default=None, help="Comma-separated genders for speakers (e.g. 'male, female' or 'm, f, m')")
    parser.add_argument("--candidates", type=int, default=None, help="Number of candidate takes to generate for stress-vital segments (default: 2)")
    parser.add_argument("--accent", type=str, default=None, help="Optional neutral accent override (e.g. es_latam_neutral, es_spain_castilian)")
    parser.add_argument("--engine", type=str, default=None, choices=["typed", "legacy"], help="Voice engine mode override")
    args = parser.parse_args()

    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)

    print("\n" + "=" * 64)
    print("               VOICE MODIFIER & RANDOM RECASTER")
    print("=" * 64)

    # 1. Pre-flight Connection Checks (MUST run before any prompt)
    print("\n" + "=" * 64)
    print("Pre-flight Connection Checks:")
    try:
        # pyrefly: ignore[missing-import]
        from core.llama_manager import ensure_llama_stopped
        ensure_llama_stopped()
    except Exception:
        pass

    comfy_client = None
    try:
        require_services(comfy=True)
        comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
        print("  [OK] Qwen3-TTS ComfyUI connected")
    except ConnectionError as e:
        print(f"  [ERROR] {e}")
        return
    print("=" * 64 + "\n")

    # 2. Resolve Script ID
    script_id = None
    if args.script_id:
        script_id = resolve_user_script_id(args.script_id, state_manager)
        if not script_id:
            print(f"Error: Script '{args.script_id}' not found.")
            return
    else:
        while not script_id:
            try:
                raw = input("Enter Video ID to modify (e.g. ER114, EE01, FG02) [or 'q' to quit]: ").strip()
            except (KeyboardInterrupt, EOFError):
                return
            if raw.lower() in ("q", "quit", "exit"):
                print("Exiting.")
                return
            script_id = resolve_user_script_id(raw, state_manager)
            if not script_id:
                print("Script not found. Please try again.")

    script_data = state_manager.get_script_state(script_id)
    if not script_data.get("script_text") and not script_data.get("content_metadata", {}).get("script"):
        print(f"Error: Script {script_id} not found or has no script_text.")
        return

    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "english")
    clean_language, _ = resolve_lang_and_type(script_id, script_data)
    if not clean_language or clean_language == "english":
        from video_creation._B_voice_generation.core.script_parser import extract_language_from_label
        extracted = extract_language_from_label(label)
        if extracted != "english":
            clean_language = extracted

    video_type = config.resolve_script_video_type(script_data).upper()
    topic = (
        script_data.get("prompt_params", {}).get("ROLEPLAY_SCENARIO")
        or script_data.get("prompt_params", {}).get("EXPRESSION")
        or script_data.get("content_metadata", {}).get("topic")
        or ""
    )

    script_output_dir = get_script_output_dir(script_id, clean_language, base_dir)
    script_output_dir.mkdir(parents=True, exist_ok=True)

    segments = get_script_segments(script_id, script_text, label)
    if not segments:
        # Fallback to structured content_metadata.script if script_text had formatting quirks
        script_dict = script_data.get("content_metadata", {}).get("script")
        if script_dict and isinstance(script_dict, dict):
            import json
            segments = get_script_segments(script_id, json.dumps(script_dict), label)
            if segments:
                script_data["script_text"] = json.dumps(script_dict, indent=2)
                state_manager.save_script_state(script_id, script_data)

    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return

    unique_speakers = list(set(seg["speaker"] for seg in segments))

    # Display Script Overview
    print("\n" + "=" * 64)
    print(f"🎬 SCRIPT [{script_id}] — {clean_language.upper()} / {video_type}")
    if topic:
        print(f"   Topic:    {topic[:70]}")
    print(f"   Speakers: {', '.join(unique_speakers)}")
    print("=" * 64)

    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)

    # 2. Gender Selection (No manual file selection requested; user chooses genders)
    existing_genders = script_data.get("content_metadata", {}).get("speakers_gender", {})
    if not isinstance(existing_genders, dict):
        existing_genders = {}

    selected_genders = prompt_speaker_genders(
        unique_speakers=unique_speakers,
        current_genders=existing_genders,
        video_type=video_type,
        cli_genders=args.genders
    )

    print("\n-> Confirmed Genders:")
    for spk, g in selected_genders.items():
        print(f"     {spk:12s}: {g.upper()}")

    # 3. Delegate fresh recast + synthesis to the unified Stage B orchestrator (excluding prior voices)
    existing_voices = script_data.get("content_metadata", {}).get("speakers_voice", {}) or {}
    exclude_set = {str(v) for v in existing_voices.values() if v}

    print("\n[Voice Casting] Selecting randomized distinct high-quality voices (excluding previous cast)...")
    ok = synthesize_script_voice(
        script_data=script_data,
        state_manager=state_manager,
        comfy_client=comfy_client,
        voice_manager=voice_manager,
        force=True,
        base_dir=base_dir,
        candidates=args.candidates,
        manual_genders=selected_genders,
        exclude_voices=exclude_set,
        force_fresh_cast=True,
        explicit_accent=args.accent,
        engine_mode=args.engine,
        mark_video_assembly_pending=True,
    )
    if ok:
        print(f"\n[Done] Master voice for {script_id} successfully replaced. Video assembly is set to pending.")
    else:
        print(f"\n[Error] Failed to regenerate voice for {script_id}.")


if __name__ == "__main__":
    main()
