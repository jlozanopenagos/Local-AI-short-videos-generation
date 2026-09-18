#!/usr/bin/env python3
"""
video_creation/_C_image_generation/image_modifier.py

CLI entrypoint for interactive scene recreation, prompt steering, and live editing of images.
Supports structured canonical IDs (<Lang><Type><02d>, e.g. EE01, FG02, SR03, IF04).
"""

import os
import sys
import time
import random
import shutil
import logging
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add project root, video_creation, and module directory to path for robust imports
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from config import (
        BASE_DIR,
        COMFY_API_URL, IMAGE_WORKFLOW_PATH,
        IMAGE_DEFAULT_STEPS, IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT,
        LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME, require_services,
        GAME_IMAGES_DIR, get_script_output_dir, resolve_script_language
    )
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from shorts_automation.config import (
        BASE_DIR,
        COMFY_API_URL, IMAGE_WORKFLOW_PATH,
        IMAGE_DEFAULT_STEPS, IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT,
        LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME, require_services,
        GAME_IMAGES_DIR, get_script_output_dir, resolve_script_language
    )

try:
    # pyrefly: ignore [missing-import]
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    try:
        # pyrefly: ignore [missing-import]
        from state_manager import StateManager, resolve_lang_and_type
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from shorts_automation.core.state_manager import StateManager, resolve_lang_and_type

try:
    from video_creation._C_image_generation.core.comfy_client import ImageComfyClient
    from video_creation._C_image_generation.core.prompt_builder import VisualPromptBuilder
    from video_creation._C_image_generation.core.chalkboard_renderer import render_chalkboard_image
    from video_creation._B_voice_generation.core.script_parser import parse_sections
except (ImportError, ModuleNotFoundError):
    try:
        from core.comfy_client import ImageComfyClient
        from core.prompt_builder import VisualPromptBuilder
        from core.chalkboard_renderer import render_chalkboard_image
        from _B_voice_generation.core.script_parser import parse_sections
    except (ImportError, ModuleNotFoundError):
        try:
            from _C_image_generation.core.comfy_client import ImageComfyClient
            from _C_image_generation.core.prompt_builder import VisualPromptBuilder
            from _C_image_generation.core.chalkboard_renderer import render_chalkboard_image
            from _B_voice_generation.core.script_parser import parse_sections
        except (ImportError, ModuleNotFoundError):
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._C_image_generation.core.comfy_client import ImageComfyClient
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._C_image_generation.core.prompt_builder import VisualPromptBuilder
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._C_image_generation.core.chalkboard_renderer import render_chalkboard_image
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._B_voice_generation.core.script_parser import parse_sections


logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger("image_modifier")


def normalize_section_input(user_input: str, valid_sections: List[str]) -> Optional[str]:
    """
    Normalizes user input to a valid section name.
    Accepts:
      - Section index (e.g. '1', '2')
      - Clean section name (e.g. 'hook', 'dialogue_part_1')
      - Full filename (e.g. 'script_EE01_hook.png', 'hook.png')
    """
    raw = user_input.strip().lower()
    if not raw:
        return None

    # Check by 1-based index
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(valid_sections):
            return valid_sections[idx]

    # Clean potential prefixes/extensions
    cleaned = raw.replace(".png", "").replace(".jpg", "")
    if cleaned.startswith("script_"):
        parts = cleaned.split("_", 2)
        if len(parts) >= 3:
            cleaned = parts[2]

    # Direct match or fuzzy match against valid sections
    for sec in valid_sections:
        if cleaned == sec.lower():
            return sec

    # Substring match (e.g. 'part 1' -> 'dialogue_part_1')
    cleaned_norm = cleaned.replace(" ", "_").replace("-", "_")
    for sec in valid_sections:
        if cleaned_norm in sec.lower() or sec.lower() in cleaned_norm:
            return sec

    return None


def resolve_user_script_id(raw_input: str, state_manager: StateManager) -> Optional[str]:
    """
    Resolves raw user input into a valid canonical Script ID.
    Handles:
      - Canonical IDs: 'EE01', 'fg02', 'sr03', 'IF04'
      - Prefixed IDs: 'script_EE01', 'script_EE01.json'
      - Plain index numbers: e.g. '1' -> checks if EE01, FG01 etc. and helps disambiguate
    """
    cleaned = raw_input.strip().upper().replace("SCRIPT_", "").replace(".JSON", "")
    if not cleaned:
        return None

    if state_manager.script_exists(cleaned):
        return cleaned

    # If user entered a plain number (e.g. '1' or '01')
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
            print("Please enter the full canonical ID (e.g. EE01, FG01, ER01).")
            return None

    return None


def modify_scene_interactive(
    script_id: str,
    script_data: Dict[str, Any],
    state_manager: StateManager,
    comfy_client: ImageComfyClient,
    prompt_builder: VisualPromptBuilder,
    base_dir: Path,
    target_scene: Optional[str] = None,
    custom_seed: Optional[int] = None,
) -> bool:
    """Interactively modifies/recreates scenes for a specific script."""
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata") or {}
    label = metadata.get("LABEL", "english")
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or metadata.get("VIDEO_TYPE", "EXPRESSION")
    ).upper()

    topic = (
        script_data.get("prompt_params", {}).get("EXPRESSION")
        or script_data.get("prompt_params", {}).get("ROLEPLAY_SCENARIO")
        or script_data.get("prompt_params", {}).get("TOPIC")
        or script_data.get("content_metadata", {}).get("topic")
        or script_id
    )

    lang_resolved, type_resolved = resolve_lang_and_type(script_id, script_data)
    images_dir = get_script_output_dir(script_id, lang_resolved, base_dir, video_type=type_resolved) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    sections = parse_sections(script_text)
    valid_sections = [k for k in sections.keys() if k.lower() != "title" and sections[k].strip()]

    if not valid_sections:
        print(f"[ERROR] No valid scene sections parsed from script {script_id}.")
        return False

    first_run = True
    while True:
        print("\n" + "=" * 64)
        print(f"🎬 SCRIPT [{script_id}] — {lang_resolved.upper()} / {video_type}")
        print(f"   Topic: {topic}")
        print(f"   Images Dir: {images_dir}")
        print("=" * 64)
        print("Scene Images Status:")
        for i, sec in enumerate(valid_sections, 1):
            img_path = images_dir / f"script_{script_id}_{sec}.png"
            status = "[EXISTS]" if img_path.exists() else "[NOT GENERATED]"
            preview = sections[sec].replace("\n", " ")[:50]
            print(f"  [{i}] {sec:<18} (script_{script_id}_{sec}.png) {status:<15} | \"{preview}...\"")

        chosen_section = None
        if first_run and target_scene:
            chosen_section = normalize_section_input(target_scene, valid_sections)
            first_run = False

        if not chosen_section:
            try:
                scene_input = input(f"\nWhich image do you want to recreate? (e.g. 'hook', '1', 'payoff') [or 'b' for back]: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if scene_input.lower() in ["b", "back", "q", "quit"]:
                break

            chosen_section = normalize_section_input(scene_input, valid_sections)
            if not chosen_section:
                print(f"[WARNING] Could not recognize scene '{scene_input}'. Please choose a valid name or number.")
                continue

        first_run = False
        scene_text = sections[chosen_section]
        dest_image_path = images_dir / f"script_{script_id}_{chosen_section}.png"

        print("\n" + "-" * 64)
        print(f"RECREATING IMAGE: Script {script_id} -> {chosen_section.upper()}")
        print(f"Scene Text: {scene_text.strip()}")
        print("-" * 64)

        # Character Genders Handling
        speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
        if not isinstance(speakers_gender, dict):
            speakers_gender = {}

        if video_type == "ROLEPLAY":
            p1_g = speakers_gender.get("PERSON_ONE", "male")
            p2_g = speakers_gender.get("PERSON_TWO", "female")
            print(f"Current character genders: PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}")
            try:
                override_gender = input("Press Enter to keep these genders, or enter new (e.g. 'male, female'): ").strip()
                if override_gender:
                    parts = [p.strip().lower() for p in override_gender.replace("/", ",").split(",")]
                    if len(parts) >= 2:
                        p1_g = "female" if "f" in parts[0] else "male"
                        p2_g = "female" if "f" in parts[1] else "male"
                    elif len(parts) == 1:
                        p1_g = "female" if "f" in parts[0] else "male"
                    speakers_gender["PERSON_ONE"] = p1_g
                    speakers_gender["PERSON_TWO"] = p2_g
                    if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                        script_data["content_metadata"] = {}
                    script_data["content_metadata"]["speakers_gender"] = speakers_gender
                    state_manager.save_script_state(script_id, script_data)
                    print(f"-> Genders updated: PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}")
            except (KeyboardInterrupt, EOFError):
                pass

        # Specialized handling for GAME: PRESSURE (Static pre-made image)
        if video_type == "GAME" and chosen_section.lower() == "pressure":
            print("\n[GAME] 'pressure' uses a static pre-made waiting image.")
            lang_key = resolve_script_language(script_data)
            waiting_img = GAME_IMAGES_DIR / lang_key / f"{lang_key}_waiting.png"
            if not waiting_img.exists():
                waiting_img = GAME_IMAGES_DIR / "english" / "english_waiting.png"
            shutil.copy2(waiting_img, dest_image_path)
            print(f"[SUCCESS] Copied static waiting image: {waiting_img.name} -> {dest_image_path.name}\n")
            _update_state_assets(script_data, script_id, images_dir, valid_sections, state_manager)
            try:
                another = input("Do you want to recreate another image in this script? [y/N]: ").strip().lower()
                if another not in ["y", "yes"]:
                    break
                continue
            except (KeyboardInterrupt, EOFError):
                break

        # Specialized handling for GAME: CHALLENGE (High-Res Chalkboard Renderer)
        if video_type == "GAME" and chosen_section.lower() == "challenge":
            print("\n" + "-" * 60)
            print("           CHALKBOARD EXERCISE RECREATION")
            print("-" * 60)
            chalkboard_model = GAME_IMAGES_DIR / "empty_chalkboard.png"
            content_meta = script_data.get("content_metadata", {})
            current_exercise = content_meta.get("chalkboard_exercise", scene_text.strip())
            print(f"Current chalkboard exercise text:\n{current_exercise}\n")
            try:
                edit_opt = input("Press Enter to keep this text, or type 'edit' to update: ").strip().lower()
                if edit_opt in ["e", "edit"]:
                    print("Enter new chalkboard text (type 'END' on a new line when done):")
                    lines = []
                    while True:
                        l = input()
                        if l.strip() == "END":
                            break
                        lines.append(l)
                    if lines:
                        current_exercise = "\n".join(lines).strip()
                        content_meta["chalkboard_exercise"] = current_exercise
                        script_data["content_metadata"] = content_meta
                        state_manager.save_script_state(script_id, script_data)
            except (KeyboardInterrupt, EOFError):
                pass

            print(f"\n[Chalkboard Renderer] Generating high-resolution chalk typography...")
            t0 = time.time()
            try:
                render_chalkboard_image(
                    empty_chalkboard_path=chalkboard_model,
                    exercise_text=current_exercise,
                    dest_path=dest_image_path,
                    target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT)
                )
                elapsed = round(time.time() - t0, 2)
                print(f"\n[SUCCESS] Chalkboard image recreated in {elapsed}s: {dest_image_path.name}\n")
                _update_state_assets(script_data, script_id, images_dir, valid_sections, state_manager)
            except Exception as exc:
                print(f"\n[ERROR] Chalkboard rendering failed: {exc}\n")

            try:
                another = input("Do you want to recreate another image in this script? [y/N]: ").strip().lower()
                if another not in ["y", "yes"]:
                    break
                continue
            except (KeyboardInterrupt, EOFError):
                break

        # Standard Scene: Prompt Mode Selection
        print("\nPrompt Generation Options:")
        print("  [1] Auto-generate new prompt with LLM + fresh random seed (Recommended)")
        print("  [2] Guide LLM with custom notes (e.g. 'make lighting more dramatic, add theater curtain')")
        print("  [3] Enter custom positive prompt manually")
        try:
            opt_input = input("Select option [1/2/3, default: 1]: ").strip()
        except (KeyboardInterrupt, EOFError):
            opt_input = "1"

        custom_prompt_text = None
        if opt_input == "2":
            try:
                guidance = input("Enter your custom visual guidance for this scene: ").strip()
            except (KeyboardInterrupt, EOFError):
                guidance = ""
            augmented_scene_text = f"{scene_text}\n[VISUAL DIRECTOR SPECIAL GUIDANCE: {guidance}]"
            print("\n[LLM] Generating refined visual prompt with custom guidance...")
            character_personalities = script_data.get("content_metadata", {}).get("character_personalities", None)
            custom_prompt_text = prompt_builder.build_visual_prompt(
                script_text=script_text,
                label=label,
                scene_name=chosen_section,
                scene_text=augmented_scene_text,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
            )
        elif opt_input == "3":
            try:
                custom_prompt_text = input("Enter the complete visual prompt text:\n> ").strip()
            except (KeyboardInterrupt, EOFError):
                custom_prompt_text = None

        if not custom_prompt_text:
            print("\n[LLM] Generating fresh visual prompt...")
            character_personalities = script_data.get("content_metadata", {}).get("character_personalities", None)
            custom_prompt_text = prompt_builder.build_visual_prompt(
                script_text=script_text,
                label=label,
                scene_name=chosen_section,
                scene_text=scene_text,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
            )

        # Generate seed
        new_seed = custom_seed if custom_seed is not None else random.randint(1, 10**15)
        print("\n" + "-" * 60)
        print("Final Visual Prompt:")
        print(f"\"{custom_prompt_text}\"")
        print(f"KSampler Seed: {new_seed}")
        print("-" * 60)

        # ComfyUI Image Generation
        print(f"\n[ComfyUI] Generating image for '{chosen_section}'...")
        t0 = time.time()
        try:
            saved_path = comfy_client.generate_image(
                prompt_text=custom_prompt_text,
                filename_prefix=f"Z-Image/script_{script_id}_{chosen_section}",
                dest_path=dest_image_path,
                seed=new_seed,
                steps=IMAGE_DEFAULT_STEPS,
                width=IMAGE_DEFAULT_WIDTH,
                height=IMAGE_DEFAULT_HEIGHT,
            )
            elapsed = round(time.time() - t0, 1)
            print(f"\n[SUCCESS] Image successfully recreated in {elapsed}s!")
            print(f"Saved to: {saved_path}\n")
            _update_state_assets(script_data, script_id, images_dir, valid_sections, state_manager)
        except Exception as exc:
            print(f"\n[ERROR] ComfyUI generation failed: {exc}\n")

        try:
            another = input("Do you want to recreate another image in this script? [y/N]: ").strip().lower()
            if another not in ["y", "yes"]:
                break
        except (KeyboardInterrupt, EOFError):
            break

    return True


def _update_state_assets(
    script_data: Dict[str, Any],
    script_id: str,
    images_dir: Path,
    valid_sections: List[str],
    state_manager: StateManager,
) -> None:
    """Updates image directory in state and sets image_generation to done if all scenes exist."""
    if "assets" not in script_data or not isinstance(script_data["assets"], dict):
        script_data["assets"] = {}
    script_data["assets"]["image_dir"] = str(images_dir)

    all_exist = all((images_dir / f"script_{script_id}_{s}.png").exists() for s in valid_sections)
    if all_exist:
        script_data["status"]["image_generation"] = "done"
    state_manager.save_script_state(script_id, script_data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LingoVerse Image Modifier — Interactive scene recreation, prompt steering, and chalkboard editing."
    )
    parser.add_argument("--script-id", help="Canonical Video ID to modify (e.g. EE01, FG02, SR03, IF04)")
    parser.add_argument("--scene", help="Scene section name or 1-based index (e.g. 'hook', '1', 'challenge')")
    parser.add_argument("--seed", type=int, default=None, help="Custom random seed for image generation")
    args = parser.parse_args()

    print("\n" + "=" * 64)
    print("           Z-IMAGE TURBO — SCENE IMAGE MODIFIER")
    print("=" * 64)

    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)

    # Pre-flight connection checks
    print("\nChecking server connections (ComfyUI & LLM)...")
    try:
        require_services(comfy=True, llm=True)
    except ConnectionError as exc:
        print(f"\n{exc}\n")
        return 1

    comfy_client = ImageComfyClient(
        api_url=COMFY_API_URL,
        workflow_path=IMAGE_WORKFLOW_PATH,
        poll_timeout=3600,
        poll_interval=2,
    )

    llm_timeout = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "180"))
    prompt_builder = VisualPromptBuilder(
        api_base_url=LLM_API_BASE_URL,
        api_key=LLM_API_KEY,
        model_name=LLM_MODEL_NAME,
        request_timeout=llm_timeout,
    )

    # If --script-id is provided via CLI
    if args.script_id:
        resolved_id = resolve_user_script_id(args.script_id, state_manager)
        if not resolved_id:
            print(f"[ERROR] Script ID '{args.script_id}' does not exist in state/.", file=sys.stderr)
            return 1
        script_data = state_manager.get_script_state(resolved_id)
        if not script_data.get("script_text"):
            print(f"[ERROR] Script '{resolved_id}' has no generated script_text.", file=sys.stderr)
            return 1

        modify_scene_interactive(
            script_id=resolved_id,
            script_data=script_data,
            state_manager=state_manager,
            comfy_client=comfy_client,
            prompt_builder=prompt_builder,
            base_dir=base_dir,
            target_scene=args.scene,
            custom_seed=args.seed,
        )
        return 0

    # Interactive script selection loop
    while True:
        print("\n" + "-" * 64)
        try:
            prompt_text = "Enter Video ID to modify (e.g. EE01, FG02, SR03, IF04) [or 'q' to quit]: "
            script_input = input(prompt_text).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if script_input.lower() in ["q", "quit", "exit"]:
            print("Goodbye!")
            break

        resolved_id = resolve_user_script_id(script_input, state_manager)
        if not resolved_id:
            print(f"[ERROR] Could not find script matching '{script_input}'. Example valid IDs: EE01, EG01, ER01, FE01.")
            continue

        script_data = state_manager.get_script_state(resolved_id)
        script_text = script_data.get("script_text", "")
        if not script_text:
            print(f"[ERROR] Script '{resolved_id}' found, but has no script_text.")
            continue

        modify_scene_interactive(
            script_id=resolved_id,
            script_data=script_data,
            state_manager=state_manager,
            comfy_client=comfy_client,
            prompt_builder=prompt_builder,
            base_dir=base_dir,
            target_scene=args.scene,
            custom_seed=args.seed,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
