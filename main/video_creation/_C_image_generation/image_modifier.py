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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# Add project root, video_creation, core, and module directory to path for robust imports
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import (
    BASE_DIR,
    COMFY_API_URL, IMAGE_WORKFLOW_PATH,
    IMAGE_DEFAULT_STEPS, IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT,
    IMAGE_STALL_TIMEOUT,
    LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME, require_services,
    GAME_IMAGES_DIR, get_script_output_dir, resolve_script_language
)
# pyrefly: ignore [missing-import]
from core.cli_prompt import timed_input
# pyrefly: ignore [missing-import]
from core.state_manager import StateManager, resolve_lang_and_type
from _C_image_generation.core.comfy_client import ImageComfyClient
from _C_image_generation.core.prompt_builder import VisualPromptBuilder, resolve_anchor_environment, sanitize_and_style_prompt
from _C_image_generation.core.chalkboard_renderer import render_chalkboard_image
from _B_voice_generation.core.script_parser import parse_sections


logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger("image_modifier")

# Interactive CLI timeout durations (seconds)
GENDER_SELECTION_TIMEOUT = 120.0  # 2 minutes
PROMPT_REVIEW_TIMEOUT = 120.0     # 2 minutes


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


def read_multiline_paste(prompt_msg: str = "") -> str:
    """
    Reads text input from the user cleanly.
    Supports single-line entry and multi-line pastes from external clipboards.
    Prevents lingering unread newlines from poisoning the input buffer.
    """
    if prompt_msg:
        print(prompt_msg)
    try:
        first_line = input("> ").strip()
        if not first_line or first_line.upper() == "END":
            return ""

        lines = [first_line]

        # Check if more characters/lines are queued in the console buffer (Windows paste)
        if sys.platform == "win32":
            import msvcrt
            time.sleep(0.08)  # Let Windows console buffer populate from clipboard
            while msvcrt.kbhit():
                try:
                    line = input().strip()
                except (KeyboardInterrupt, EOFError):
                    break
                if line.upper() == "END":
                    break
                if line:
                    lines.append(line)

        return " ".join(lines).strip()
    except (KeyboardInterrupt, EOFError):
        return ""


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


def modify_group_interactive(
    script_id: str,
    script_data: Dict[str, Any],
    valid_sections: List[str],
    sections: Dict[str, str],
    images_dir: Path,
    state_manager: StateManager,
    comfy_client: ImageComfyClient,
    prompt_builder: VisualPromptBuilder,
    base_dir: Path,
    custom_seed: Optional[int] = None,
) -> bool:
    """
    Regenerates ALL images for a video following a cohesive General Visual Prompt / Story World Anchor.

    Flow:
    1. Confirm/choose principal character gender (with 2 min timeout).
    2. Create the General Prompt using standard prompt options (Auto-generate, Guide LLM, Manual, Reuse).
    3. Review & refine the General Prompt (Enter to accept with 2 min timer, r to regen, g to guide, t to toggle gender, e to edit, s to roll seed).
    4. Image-by-image: LLM creates specific visual prompt for each scene anchored in the general prompt,
       and ComfyUI immediately generates the image (no individual prompt confirmation needed).
    """
    metadata = script_data.get("metadata") or {}
    label = metadata.get("LABEL", "english")
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or metadata.get("VIDEO_TYPE", "EXPRESSION")
    ).upper()

    content_meta = script_data.get("content_metadata", {})
    prompt_params = script_data.get("prompt_params", {})
    character_personalities = content_meta.get("character_personalities", None)

    topic_str = (
        prompt_params.get("EXPRESSION")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("TOPIC")
        or content_meta.get("topic")
        or content_meta.get("target_expression")
        or ""
    )
    scenario_str = (
        content_meta.get("roleplay_scenario")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("CONTEXT")
        or content_meta.get("learning_objective")
        or ""
    )
    lexical_field_str = (
        prompt_params.get("LEXICAL_FIELD")
        or content_meta.get("subcategory")
        or content_meta.get("category")
        or ""
    )
    script_text = script_data.get("script_text", "")

    anchor_environment = resolve_anchor_environment(
        script_text=script_text,
        topic=topic_str,
        scenario=scenario_str,
        lexical_field=lexical_field_str,
        label=label,
        video_type=video_type,
    )

    stored_general_prompt = script_data.get("assets", {}).get("general_prompt", "").strip()

    print("\n" + "=" * 64)
    print(f"🎬 GROUP CHANGE MODE: Script [{script_id}] ({len(valid_sections)} Scenes)")
    if topic_str:
        print(f"Topic / Subject:  {topic_str}")
    if scenario_str:
        print(f"Story Scenario:   {scenario_str}")
    if lexical_field_str:
        print(f"Lexical Field:    {lexical_field_str}")
    if anchor_environment:
        print(f"Base Setting:     >> {anchor_environment} <<")
    print("=" * 64)

    # 1. Character Gender Handling (2 min timeout)
    speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
    if not isinstance(speakers_gender, dict):
        speakers_gender = {}

    current_princ_gender = (
        speakers_gender.get("PERSON_ONE")
        or speakers_gender.get("NARRATOR")
        or "male"
    ).lower()
    current_princ_gender = "female" if "f" in current_princ_gender else "male"

    if video_type == "ROLEPLAY":
        p1_g = (speakers_gender.get("PERSON_ONE") or ("female" if "f" in str(speakers_gender.get("PERSON_ONE", "")).lower() else "male")).lower()
        p2_g = (speakers_gender.get("PERSON_TWO") or ("male" if "m" in str(speakers_gender.get("PERSON_TWO", "")).lower() else "female")).lower()
        p1_g = "female" if "f" in p1_g else "male"
        p2_g = "male" if "m" in p2_g else "female"
        current_princ_gender = p1_g

        print("\n" + "-" * 55)
        print("Roleplay Character Genders:")
        print(f"  [1] PERSON_ONE: {p1_g.upper()} (youthful teen {'boy' if p1_g == 'male' else 'girl'})")
        print(f"  [2] PERSON_TWO: {p2_g.upper()} (youthful teen {'boy' if p2_g == 'male' else 'girl'})")
        print("-" * 55)
        try:
            gender_prompt_msg = (
                f"Choose genders (e.g. 'female, male' or 'f, m' / 'male, female', Enter to keep [{p1_g.upper()}, {p2_g.upper()}]): "
            )
            chosen_gender_input = timed_input(
                gender_prompt_msg,
                timeout=GENDER_SELECTION_TIMEOUT,
                default="",
                default_msg=f"Keeping PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}"
            ).strip().lower()

            if chosen_gender_input:
                parts = [p.strip().lower() for p in chosen_gender_input.replace("/", ",").split(",")]
                if len(parts) >= 2:
                    p1_g = "female" if "f" in parts[0] else "male"
                    p2_g = "female" if "f" in parts[1] else "male"
                elif len(parts) == 1:
                    if parts[0] in ["m", "male", "boy", "1"]:
                        p1_g = "male"
                    elif parts[0] in ["f", "female", "girl", "2"]:
                        p1_g = "female"

            speakers_gender["PERSON_ONE"] = p1_g
            speakers_gender["PERSON_TWO"] = p2_g
            if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                script_data["content_metadata"] = {}
            script_data["content_metadata"]["speakers_gender"] = speakers_gender
            state_manager.save_script_state(script_id, script_data)
            print(f"-> Roleplay Genders confirmed: PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}\n")
        except (KeyboardInterrupt, EOFError):
            print(f"\n-> Keeping PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}\n")
    else:
        current_princ_gender = (
            speakers_gender.get("NARRATOR")
            or speakers_gender.get("PERSON_ONE")
            or "male"
        ).lower()
        current_princ_gender = "female" if "f" in current_princ_gender else "male"

        print(f"\nPrincipal Character: [{current_princ_gender.upper()}] (youthful teen {'boy' if current_princ_gender == 'male' else 'girl'})")
        try:
            gender_prompt_msg = f"Choose principal character gender [m = Male (boy) / f = Female (girl), Enter to keep {current_princ_gender.upper()}]: "
            chosen_gender_input = timed_input(
                gender_prompt_msg,
                timeout=GENDER_SELECTION_TIMEOUT,
                default="",
                default_msg=f"Keeping {current_princ_gender.upper()}"
            ).strip().lower()

            if chosen_gender_input in ["m", "male", "boy", "1"]:
                current_princ_gender = "male"
            elif chosen_gender_input in ["f", "female", "girl", "2"]:
                current_princ_gender = "female"

            speakers_gender["NARRATOR"] = current_princ_gender
            speakers_gender["PERSON_ONE"] = current_princ_gender

            if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                script_data["content_metadata"] = {}
            script_data["content_metadata"]["speakers_gender"] = speakers_gender
            state_manager.save_script_state(script_id, script_data)
            print(f"-> Principal Character Gender confirmed: {current_princ_gender.upper()} ({'young teen boy' if current_princ_gender == 'male' else 'young teen girl'})\n")
        except (KeyboardInterrupt, EOFError):
            print(f"\n-> Keeping {current_princ_gender.upper()}\n")

    # 2. General Prompt Creation Options
    print("General Prompt Generation Options:")
    print("  [1] Auto-generate general prompt with LLM (Anchored in full story & setting)")
    print("  [2] Guide LLM with custom notes (e.g. 'acoustic recording studio with analog audio gear')")
    print("  [3] Enter custom general prompt manually")
    if stored_general_prompt:
        print("  [4] Reuse previously stored story world / general prompt")

    choices_hint = "[1/2/3/4, default: 1]" if stored_general_prompt else "[1/2/3, default: 1]"
    try:
        opt_input = input(f"Select option {choices_hint}: ").strip()
    except (KeyboardInterrupt, EOFError):
        opt_input = "1"

    general_prompt_text = None
    if opt_input == "4" and stored_general_prompt:
        general_prompt_text = stored_general_prompt
        print(f"[OK] Reusing stored general prompt: \"{general_prompt_text[:80]}...\"")
    elif opt_input == "2":
        try:
            guidance = input("Enter your custom visual guidance for the story world: ").strip()
        except (KeyboardInterrupt, EOFError):
            guidance = ""
        print("\n[LLM] Generating refined general prompt with guidance...")
        general_prompt_text = prompt_builder.build_general_prompt(
            script_text=script_text,
            label=label,
            script_id=script_id,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
            topic=topic_str,
            scenario=scenario_str,
            lexical_field=lexical_field_str,
            anchor_environment=anchor_environment,
            guidance=guidance,
            temperature=0.8,
        )
    elif opt_input == "3":
        print("\nEnter custom general prompt text (paste or type; press Enter to submit):")
        raw_custom = read_multiline_paste()
        if raw_custom:
            general_prompt_text = sanitize_and_style_prompt(raw_custom)
            print("[OK] Custom general prompt recorded.")
        else:
            general_prompt_text = None

    if not general_prompt_text:
        print("\n[LLM] Generating fresh general prompt grounded in story world...")
        general_prompt_text = prompt_builder.build_general_prompt(
            script_text=script_text,
            label=label,
            script_id=script_id,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
            topic=topic_str,
            scenario=scenario_str,
            lexical_field=lexical_field_str,
            anchor_environment=anchor_environment,
            temperature=0.75,
        )

    # 3. Interactive Review & Refine Loop (2 min timer)
    confirmed_general_prompt = sanitize_and_style_prompt(general_prompt_text)
    current_seed = custom_seed if custom_seed is not None else random.randint(1, 10**15)

    while True:
        print("\n" + "=" * 64)
        print("PROPOSED GENERAL PROMPT (LEADS ALL SCENE IMAGES):")
        print(f"\"{confirmed_general_prompt}\"")
        print(f"KSampler Base Seed: {current_seed}")
        print("=" * 64)
        print("Options:")
        print("  [Enter] Confirm general prompt & generate ALL images (Auto-confirm in 2 min)")
        print("  [r]     Regenerate fresh general prompt with LLM (new creative variation)")
        print("  [g]     Add guidance notes & regenerate general prompt with LLM")
        if video_type == "ROLEPLAY":
            p1_disp = speakers_gender.get("PERSON_ONE", "female").upper()
            p2_disp = speakers_gender.get("PERSON_TWO", "male").upper()
            print(f"  [t]     Toggle roleplay genders (currently: P1={p1_disp}, P2={p2_disp}) & regenerate")
        else:
            print(f"  [t]     Toggle principal gender (currently: {current_princ_gender.upper()}) & regenerate")
        print("  [e]     Edit general prompt text manually before generating")
        print("  [s]     Roll a new random seed for image generation")
        print("  [b]     Cancel & return to menu")
        try:
            act = timed_input(
                prompt=f"\nChoice [Enter/r/g/t/e/s/b] (2 min timer): ",
                timeout=PROMPT_REVIEW_TIMEOUT,
                default="",
                default_msg="[2 min Timer Expired] Auto-confirming general prompt. Proceeding to generation..."
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n[Info] Group change cancelled.")
            return False

        if act in ["", "y", "yes"]:
            break
        elif act in ["b", "back", "q", "quit"]:
            print("\n[Info] Group change cancelled. Returning to menu.")
            return False
        elif act in ["t", "toggle", "gender"]:
            if video_type == "ROLEPLAY":
                old_p1 = speakers_gender.get("PERSON_ONE", "female").lower()
                old_p2 = speakers_gender.get("PERSON_TWO", "male").lower()
                new_p1 = "male" if old_p1 == "female" else "female"
                new_p2 = "male" if old_p2 == "female" else "female"
                speakers_gender["PERSON_ONE"] = new_p1
                speakers_gender["PERSON_TWO"] = new_p2
                current_princ_gender = new_p1
                if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                    script_data["content_metadata"] = {}
                script_data["content_metadata"]["speakers_gender"] = speakers_gender
                state_manager.save_script_state(script_id, script_data)
                print(f"\n[Genders Toggled] Roleplay characters are now: PERSON_ONE={new_p1.upper()} ({'young teen boy' if new_p1 == 'male' else 'young teen girl'}), PERSON_TWO={new_p2.upper()} ({'young teen boy' if new_p2 == 'male' else 'young teen girl'})")
            else:
                current_princ_gender = "female" if current_princ_gender == "male" else "male"
                speakers_gender["NARRATOR"] = current_princ_gender
                speakers_gender["PERSON_ONE"] = current_princ_gender
                if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                    script_data["content_metadata"] = {}
                script_data["content_metadata"]["speakers_gender"] = speakers_gender
                state_manager.save_script_state(script_id, script_data)
                print(f"\n[Gender Toggled] Principal character is now: {current_princ_gender.upper()} ({'young teen boy' if current_princ_gender == 'male' else 'young teen girl'})")
            print("[LLM] Regenerating general prompt with updated gender...")
            try:
                new_gen = prompt_builder.build_general_prompt(
                    script_text=script_text,
                    label=label,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic_str,
                    scenario=scenario_str,
                    lexical_field=lexical_field_str,
                    anchor_environment=anchor_environment,
                    temperature=0.8,
                )
                if new_gen:
                    confirmed_general_prompt = new_gen
                    print("[OK] General prompt regenerated.")
            except Exception as exc:
                print(f"[ERROR] Failed to regenerate general prompt: {exc}")
        elif act in ["r", "regen", "regenerate"]:
            print("\n[LLM] Generating fresh creative variation of general prompt...")
            try:
                new_gen = prompt_builder.build_general_prompt(
                    script_text=script_text,
                    label=label,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic_str,
                    scenario=scenario_str,
                    lexical_field=lexical_field_str,
                    anchor_environment=anchor_environment,
                    temperature=0.85,
                )
                if new_gen:
                    confirmed_general_prompt = new_gen
                    print("[OK] Fresh general prompt generated.")
            except Exception as exc:
                print(f"[ERROR] Failed to regenerate general prompt: {exc}")
        elif act in ["g", "guide"]:
            try:
                more_notes = input("\nEnter guidance notes for the story world: ").strip()
            except (KeyboardInterrupt, EOFError):
                more_notes = ""
            print("\n[LLM] Refining general prompt with guidance...")
            try:
                new_gen = prompt_builder.build_general_prompt(
                    script_text=script_text,
                    label=label,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic_str,
                    scenario=scenario_str,
                    lexical_field=lexical_field_str,
                    anchor_environment=anchor_environment,
                    guidance=more_notes,
                    temperature=0.8,
                )
                if new_gen:
                    confirmed_general_prompt = new_gen
                    print("[OK] Guided general prompt generated.")
            except Exception as exc:
                print(f"[ERROR] Failed to regenerate general prompt: {exc}")
        elif act in ["e", "edit"]:
            try:
                print("\nEdit general prompt text manually:")
                print("Paste or type modified text below (press Enter immediately to keep unchanged):")
                edited = read_multiline_paste()
                if edited:
                    confirmed_general_prompt = sanitize_and_style_prompt(edited)
                    print("[OK] General prompt updated.")
                else:
                    print("[Info] General prompt kept unchanged.")
            except (KeyboardInterrupt, EOFError):
                pass
        elif act in ["s", "seed"]:
            current_seed = random.randint(1, 10**15)
            print(f"\n-> Rolled new KSampler base seed: {current_seed}")

    # Save confirmed general prompt to state
    confirmed_general_prompt = sanitize_and_style_prompt(confirmed_general_prompt)
    if "assets" not in script_data or not isinstance(script_data["assets"], dict):
        script_data["assets"] = {}
    script_data["assets"]["general_prompt"] = confirmed_general_prompt
    if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
        script_data["content_metadata"] = {}
    script_data["content_metadata"]["anchor_environment"] = confirmed_general_prompt
    state_manager.save_script_state(script_id, script_data)

    # 4. PREPARATION PHASE (Step 1B): Sequential Storyboard Generation
    # Generate all scene prompts at once using Gemma in sequential chronological order,
    # anchored by the confirmed General Prompt, script text, and topic.
    print("\n" + "=" * 64)
    print(f"🎬 PREPARATION PHASE: Generating Sequential Storyboard for {len(valid_sections)} Scenes...")
    print(f"Locked Story World:\n>> {confirmed_general_prompt} <<")
    print("=" * 64)

    sections_for_storyboard = {
        sec: sections.get(sec, f"Illustration for {sec} ({topic_str})")
        for sec in valid_sections
    }
    if video_type == "ROLEPLAY":
        d1 = sections.get("dialogue_part_1") or sections.get("DIALOGUE_PART_1") or ""
        d4 = sections.get("dialogue_part_4") or sections.get("DIALOGUE_PART_4") or ""
        if d1 and "hook" in sections_for_storyboard:
            sections_for_storyboard["hook"] = f"{sections_for_storyboard['hook']}\n{d1}".strip()
        if d4 and "payoff" in sections_for_storyboard:
            sections_for_storyboard["payoff"] = f"{d4}\n{sections_for_storyboard['payoff']}".strip()

    generated_scene_prompts: Dict[str, str] = {}
    try:
        storyboard_map = prompt_builder.build_storyboard_prompts(
            script_text=script_text,
            label=label,
            sections=sections_for_storyboard,
            script_id=script_id,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
            topic=topic_str,
            scenario=scenario_str,
            lexical_field=lexical_field_str,
            anchor_environment=confirmed_general_prompt,
            general_prompt=confirmed_general_prompt,
        )
        for s_key, s_prompt in storyboard_map.items():
            clean_p = sanitize_and_style_prompt(s_prompt)
            generated_scene_prompts[s_key.lower()] = clean_p
            print(f"\n[Scene Prompt - {s_key.upper()}]:\n\"{clean_p}\"")
    except Exception as exc:
        print(f"[WARNING] Storyboard batch generation failed: {exc}. Will fallback per scene.")

    # Cleanup any stale/obsolete scene images not in valid_sections
    for old_img in images_dir.glob(f"script_{script_id}_*.png"):
        sec_name = old_img.stem[len(f"script_{script_id}_"):].lower()
        if sec_name not in valid_sections:
            try:
                old_img.unlink()
                print(f"[Cleanup] Deleted obsolete image: {old_img.name}")
            except Exception as e:
                print(f"[Cleanup] Could not delete {old_img.name}: {e}")

    if "assets" not in script_data or not isinstance(script_data["assets"], dict):
        script_data["assets"] = {}
    if "image_prompts" not in script_data["assets"] or not isinstance(script_data["assets"]["image_prompts"], dict):
        script_data["assets"]["image_prompts"] = {}
    # Prune obsolete scene prompt keys from state
    script_data["assets"]["image_prompts"] = {
        k: v for k, v in script_data["assets"]["image_prompts"].items()
        if k.lower() in valid_sections
    }
    script_data["assets"]["image_prompts"].update(generated_scene_prompts)
    state_manager.save_script_state(script_id, script_data)

    # 5. EXECUTION PHASE (Phase 2): Batch Image Synthesis in ComfyUI
    total_scenes = len(valid_sections)
    print("\n" + "=" * 64)
    print(f"🚀 EXECUTION PHASE: Batch Image Synthesis ({total_scenes} Scenes)")
    print("=" * 64)

    for idx, sec in enumerate(valid_sections, 1):
        dest_image_path = images_dir / f"script_{script_id}_{sec}.png"
        sec_text = sections.get(sec, f"Illustration for {sec} ({topic_str})")
        if video_type == "ROLEPLAY":
            if sec.lower() == "hook":
                d1 = sections.get("dialogue_part_1") or sections.get("DIALOGUE_PART_1") or ""
                if d1:
                    sec_text = f"{sec_text}\n{d1}".strip()
            elif sec.lower() == "payoff":
                d4 = sections.get("dialogue_part_4") or sections.get("DIALOGUE_PART_4") or ""
                if d4:
                    sec_text = f"{d4}\n{sec_text}".strip()

        print(f"\n{'─' * 60}")
        print(f"[{idx}/{total_scenes}] Processing Scene: {sec.upper()}")
        print(f"{'─' * 60}")

        # Specialized handling for GAME: PRESSURE (Static pre-made image)
        if video_type == "GAME" and sec.lower() == "pressure":
            lang_key = resolve_script_language(script_data)
            waiting_img = GAME_IMAGES_DIR / lang_key / f"{lang_key}_waiting.png"
            if not waiting_img.exists():
                waiting_img = GAME_IMAGES_DIR / "english" / "english_waiting.png"
            if waiting_img.exists():
                shutil.copy2(waiting_img, dest_image_path)
                print(f"[OK] Copied static waiting image: {waiting_img.name} -> {dest_image_path.name}")
                continue

        # Specialized handling for GAME: CHALLENGE (High-Res Chalkboard Renderer)
        if video_type == "GAME" and sec.lower() == "challenge":
            chalkboard_model = GAME_IMAGES_DIR / "empty_chalkboard.png"
            if chalkboard_model.exists():
                content_meta = script_data.get("content_metadata", {})
                current_exercise = content_meta.get("chalkboard_exercise", sec_text.strip())
                print(f"[Chalkboard Renderer] Generating high-resolution chalk challenge image...")
                try:
                    render_chalkboard_image(
                        empty_chalkboard_path=chalkboard_model,
                        exercise_text=current_exercise,
                        dest_path=dest_image_path,
                        target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT)
                    )
                    print(f"[OK] Chalkboard image saved: {dest_image_path.name}")
                    continue
                except Exception as exc:
                    print(f"[WARNING] Chalkboard rendering failed: {exc}. Falling back to ComfyUI.")

        # Generative Scene: Retrieve pre-generated prompt or fallback
        specific_prompt = generated_scene_prompts.get(sec.lower()) or generated_scene_prompts.get(sec)
        if not specific_prompt:
            print(f"[LLM] Creating fallback visual prompt for '{sec}' anchored in story world...")
            try:
                specific_prompt = prompt_builder.build_visual_prompt(
                    script_text=script_text,
                    label=label,
                    scene_name=sec,
                    scene_text=sec_text,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic_str,
                    scenario=scenario_str,
                    lexical_field=lexical_field_str,
                    anchor_environment=confirmed_general_prompt,
                    existing_scene_prompts=generated_scene_prompts,
                    general_prompt=confirmed_general_prompt,
                    temperature=0.8,
                )
                specific_prompt = sanitize_and_style_prompt(specific_prompt)
                generated_scene_prompts[sec.lower()] = specific_prompt
                script_data["assets"]["image_prompts"][sec] = specific_prompt
                state_manager.save_script_state(script_id, script_data)
            except Exception as exc:
                print(f"[ERROR] Failed to build visual prompt for '{sec}': {exc}")
                continue

        print(f"\n[Execution Prompt - {sec.upper()}]:\n\"{specific_prompt}\"\n")

        # ComfyUI generation
        scene_seed = (current_seed + idx * 7919) % (10**15) if custom_seed is None else custom_seed
        print(f"[ComfyUI] Generating image for '{sec}' (Seed: {scene_seed})...")
        t0 = time.time()
        try:
            saved_path = comfy_client.generate_image(
                prompt_text=specific_prompt,
                filename_prefix=f"Z-Image/script_{script_id}_{sec}",
                dest_path=dest_image_path,
                seed=scene_seed,
                steps=IMAGE_DEFAULT_STEPS,
                width=IMAGE_DEFAULT_WIDTH,
                height=IMAGE_DEFAULT_HEIGHT,
                stall_timeout=IMAGE_STALL_TIMEOUT,
            )
            elapsed = round(time.time() - t0, 1)
            print(f"[SUCCESS] Scene '{sec}' created in {elapsed}s -> {saved_path.name}")
            if "assets" not in script_data or not isinstance(script_data["assets"], dict):
                script_data["assets"] = {}
            if "image_prompts" not in script_data["assets"] or not isinstance(script_data["assets"]["image_prompts"], dict):
                script_data["assets"]["image_prompts"] = {}
            script_data["assets"]["image_prompts"][sec] = specific_prompt
            state_manager.save_script_state(script_id, script_data)
            time.sleep(0.3)
        except Exception as exc:
            print(f"[ERROR] ComfyUI generation failed for '{sec}': {exc}")

    _update_state_assets(script_data, script_id, images_dir, valid_sections, state_manager)
    print("\n" + "=" * 64)
    print(f"🎉 GROUP GENERATION COMPLETE for Script [{script_id}]!")
    print(f"   All {total_scenes} images updated successfully.")
    print("=" * 64 + "\n")
    return True


def modify_scene_interactive(
    script_id: str,
    script_data: Dict[str, Any],
    state_manager: StateManager,
    comfy_client: ImageComfyClient,
    prompt_builder: VisualPromptBuilder,
    base_dir: Path,
    target_scene: Optional[str] = None,
    custom_seed: Optional[int] = None,
    group_mode: bool = False,
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

    METADATA_IGNORE_KEYS = {
        "title", "difficulty", "emotion", "game_type", "related_content",
        "category", "subcategory", "topic", "learning_objective",
        "chalkboard_exercise", "target_expression", "roleplay_scenario"
    }
    VALID_GAME_SECTIONS = {"hook", "challenge", "pressure", "answer", "explanation"}
    VALID_ROLEPLAY_SECTIONS = {"hook", "dialogue_part_2", "dialogue_part_3", "payoff"}

    sections = parse_sections(script_text)
    valid_sections = []
    for k in sections.keys():
        sec_lower = k.lower().strip()
        if sec_lower in METADATA_IGNORE_KEYS:
            continue
        if video_type == "GAME" and sec_lower not in VALID_GAME_SECTIONS:
            continue
        if video_type == "ROLEPLAY" and sec_lower not in VALID_ROLEPLAY_SECTIONS:
            continue
        if sections[k].strip():
            valid_sections.append(k)

    if not valid_sections:
        print(f"[ERROR] No valid scene sections parsed from script {script_id}.")
        return False

    first_run = True
    while True:
        # Detect any legacy or orphaned images on disk not present in active script
        existing_pngs = sorted(images_dir.glob(f"script_{script_id}_*.png"))
        legacy_sections = []
        valid_lower = [s.lower() for s in valid_sections]
        for p in existing_pngs:
            sec_name = p.stem[len(f"script_{script_id}_"):]
            if sec_name.lower() not in valid_lower:
                legacy_sections.append(sec_name)

        all_selectable = valid_sections + legacy_sections

        print("\n" + "=" * 64)
        print(f"🎬 SCRIPT [{script_id}] — {lang_resolved.upper()} / {video_type}")
        print(f"   Topic: {topic}")
        print(f"   Images Dir: {images_dir}")
        print("=" * 64)
        print("Active Script Scene Images:")
        for i, sec in enumerate(valid_sections, 1):
            img_path = images_dir / f"script_{script_id}_{sec}.png"
            status = "[EXISTS]" if img_path.exists() else "[NOT GENERATED]"
            preview = sections.get(sec, "").replace("\n", " ")[:50]
            print(f"  [{i}] {sec:<18} (script_{script_id}_{sec}.png) {status:<15} | \"{preview}...\"")

        if legacy_sections:
            print("\n  ⚠️  Legacy / Stale Images on Disk (not in active script):")
            for j, lsec in enumerate(legacy_sections, len(valid_sections) + 1):
                img_path = images_dir / f"script_{script_id}_{lsec}.png"
                print(f"  [{j}] {lsec:<18} (script_{script_id}_{lsec}.png) [LEGACY ON DISK]")
            print(f"  [c] Clean up legacy images (deletes {len(legacy_sections)} unused file(s) from disk)")

        chosen_section = None
        if first_run and target_scene:
            chosen_section = normalize_section_input(target_scene, all_selectable)
            first_run = False

        mode_choice = None
        if first_run and not target_scene and not group_mode:
            print("\nRecreation Mode:")
            print("  [1] Individual scene change (select and recreate a specific scene image) [Default]")
            print("  [2] Group change (regenerate ALL scene images with a cohesive general prompt)")
            try:
                mode_input = input("Select mode [1/2, default: 1] (or 'b' for back): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                break
            if mode_input in ["b", "back", "q", "quit"]:
                break
            if mode_input in ["2", "group", "all", "g"]:
                mode_choice = "group"
            else:
                mode_choice = "individual"

        if group_mode or mode_choice == "group":
            group_mode = False
            first_run = False
            modify_group_interactive(
                script_id=script_id,
                script_data=script_data,
                valid_sections=valid_sections,
                sections=sections,
                images_dir=images_dir,
                state_manager=state_manager,
                comfy_client=comfy_client,
                prompt_builder=prompt_builder,
                base_dir=base_dir,
                custom_seed=custom_seed,
            )
            try:
                another = input("\nDo you want to recreate another image or video? [y/N]: ").strip().lower()
                if another in ["y", "yes"]:
                    continue
                else:
                    break
            except (KeyboardInterrupt, EOFError):
                break

        if not chosen_section:
            clean_hint = " or 'c' to clean legacy" if legacy_sections else ""
            try:
                scene_input = input(f"\nWhich image do you want to recreate? (e.g. 'hook', '1', or 'all' for group change{clean_hint}) [or 'b' for back]: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if scene_input.lower() in ["b", "back", "q", "quit"]:
                break

            if scene_input.lower() in ["all", "group"]:
                first_run = False
                modify_group_interactive(
                    script_id=script_id,
                    script_data=script_data,
                    valid_sections=valid_sections,
                    sections=sections,
                    images_dir=images_dir,
                    state_manager=state_manager,
                    comfy_client=comfy_client,
                    prompt_builder=prompt_builder,
                    base_dir=base_dir,
                    custom_seed=custom_seed,
                )
                try:
                    another = input("\nDo you want to recreate another image or video? [y/N]: ").strip().lower()
                    if another in ["y", "yes"]:
                        continue
                    else:
                        break
                except (KeyboardInterrupt, EOFError):
                    break

            if scene_input.lower() in ["c", "clean", "cleanup"] and legacy_sections:
                print(f"\nCleaning up {len(legacy_sections)} legacy image file(s)...")
                for lsec in legacy_sections:
                    lf = images_dir / f"script_{script_id}_{lsec}.png"
                    try:
                        lf.unlink()
                        print(f"  [OK] Deleted: {lf.name}")
                    except Exception as e:
                        print(f"  [ERROR] Could not delete {lf.name}: {e}")
                print("[SUCCESS] Legacy images cleaned up!\n")
                continue

            chosen_section = normalize_section_input(scene_input, all_selectable)
            if not chosen_section:
                print(f"[WARNING] Could not recognize scene '{scene_input}'. Please choose a valid name or number.")
                continue

        first_run = False
        scene_text = sections.get(chosen_section, f"Illustration for {chosen_section} ({topic})")
        if video_type == "ROLEPLAY":
            if chosen_section.lower() == "hook":
                d1 = sections.get("dialogue_part_1") or sections.get("DIALOGUE_PART_1") or ""
                if d1:
                    scene_text = f"{scene_text}\n{d1}".strip()
            elif chosen_section.lower() == "payoff":
                d4 = sections.get("dialogue_part_4") or sections.get("DIALOGUE_PART_4") or ""
                if d4:
                    scene_text = f"{d4}\n{scene_text}".strip()
        dest_image_path = images_dir / f"script_{script_id}_{chosen_section}.png"

        content_meta = script_data.get("content_metadata", {})
        prompt_params = script_data.get("prompt_params", {})
        character_personalities = content_meta.get("character_personalities", None)

        topic_str = (
            prompt_params.get("EXPRESSION")
            or prompt_params.get("ROLEPLAY_SCENARIO")
            or prompt_params.get("TOPIC")
            or content_meta.get("topic")
            or content_meta.get("target_expression")
            or ""
        )
        scenario_str = (
            content_meta.get("roleplay_scenario")
            or prompt_params.get("ROLEPLAY_SCENARIO")
            or prompt_params.get("CONTEXT")
            or content_meta.get("learning_objective")
            or ""
        )
        lexical_field_str = (
            prompt_params.get("LEXICAL_FIELD")
            or content_meta.get("subcategory")
            or content_meta.get("category")
            or ""
        )

        anchor_environment = resolve_anchor_environment(
            script_text=script_text,
            topic=topic_str,
            scenario=scenario_str,
            lexical_field=lexical_field_str,
            label=label,
            video_type=video_type,
        )
        stored_general_prompt = script_data.get("assets", {}).get("general_prompt", "").strip()
        general_prompt_val = stored_general_prompt or anchor_environment

        existing_prompt = (
            script_data.get("assets", {})
            .get("image_prompts", {})
            .get(chosen_section, "")
        )

        print("\n" + "-" * 64)
        print(f"RECREATING IMAGE: Script {script_id} -> {chosen_section.upper()}")
        print(f"Scene Text:       \"{scene_text.strip()}\"")
        if topic_str:
            print(f"Topic / Subject:  {topic_str}")
        if scenario_str:
            print(f"Story Scenario:   {scenario_str}")
        if lexical_field_str:
            print(f"Lexical Field:    {lexical_field_str}")
        if general_prompt_val:
            print(f"Locked Story World:\n>> {general_prompt_val} <<")
        elif anchor_environment:
            print(f"Locked Setting:   >> {anchor_environment} <<")
        if existing_prompt:
            print(f"Stored Prompt:    \"{existing_prompt}\"")
        print("-" * 64)

        # Character Gender Handling (Always confirm for all video types)
        speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
        if not isinstance(speakers_gender, dict):
            speakers_gender = {}

        current_princ_gender = (
            speakers_gender.get("PERSON_ONE")
            or speakers_gender.get("NARRATOR")
            or "male"
        ).lower()
        current_princ_gender = "female" if "f" in current_princ_gender else "male"

        if video_type == "ROLEPLAY":
            p1_g = (speakers_gender.get("PERSON_ONE") or ("female" if "f" in str(speakers_gender.get("PERSON_ONE", "")).lower() else "male")).lower()
            p2_g = (speakers_gender.get("PERSON_TWO") or ("male" if "m" in str(speakers_gender.get("PERSON_TWO", "")).lower() else "female")).lower()
            p1_g = "female" if "f" in p1_g else "male"
            p2_g = "male" if "m" in p2_g else "female"
            current_princ_gender = p1_g

            print("\n" + "-" * 55)
            print("Roleplay Character Genders:")
            print(f"  [1] PERSON_ONE: {p1_g.upper()} (youthful teen {'boy' if p1_g == 'male' else 'girl'})")
            print(f"  [2] PERSON_TWO: {p2_g.upper()} (youthful teen {'boy' if p2_g == 'male' else 'girl'})")
            print("-" * 55)
            try:
                gender_prompt_msg = (
                    f"Choose genders (e.g. 'female, male' or 'f, m' / 'male, female', Enter to keep [{p1_g.upper()}, {p2_g.upper()}]): "
                )
                chosen_gender_input = timed_input(
                    gender_prompt_msg,
                    timeout=GENDER_SELECTION_TIMEOUT,
                    default="",
                    default_msg=f"Keeping PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}"
                ).strip().lower()

                if chosen_gender_input:
                    parts = [p.strip().lower() for p in chosen_gender_input.replace("/", ",").split(",")]
                    if len(parts) >= 2:
                        p1_g = "female" if "f" in parts[0] else "male"
                        p2_g = "female" if "f" in parts[1] else "male"
                    elif len(parts) == 1:
                        if parts[0] in ["m", "male", "boy", "1"]:
                            p1_g = "male"
                        elif parts[0] in ["f", "female", "girl", "2"]:
                            p1_g = "female"

                speakers_gender["PERSON_ONE"] = p1_g
                speakers_gender["PERSON_TWO"] = p2_g
                if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                    script_data["content_metadata"] = {}
                script_data["content_metadata"]["speakers_gender"] = speakers_gender
                state_manager.save_script_state(script_id, script_data)
                print(f"-> Roleplay Genders confirmed: PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}\n")
            except (KeyboardInterrupt, EOFError):
                print(f"\n-> Keeping PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}\n")
        else:
            current_princ_gender = (
                speakers_gender.get("NARRATOR")
                or speakers_gender.get("PERSON_ONE")
                or "male"
            ).lower()
            current_princ_gender = "female" if "f" in current_princ_gender else "male"

            print(f"Principal Character: [{current_princ_gender.upper()}] (youthful teen {'boy' if current_princ_gender == 'male' else 'girl'})")
            try:
                gender_prompt_msg = f"Choose principal character gender [m = Male (boy) / f = Female (girl), Enter to keep {current_princ_gender.upper()}]: "
                chosen_gender_input = timed_input(
                    gender_prompt_msg,
                    timeout=GENDER_SELECTION_TIMEOUT,
                    default="",
                    default_msg=f"Keeping {current_princ_gender.upper()}"
                ).strip().lower()

                if chosen_gender_input in ["m", "male", "boy", "1"]:
                    current_princ_gender = "male"
                elif chosen_gender_input in ["f", "female", "girl", "2"]:
                    current_princ_gender = "female"

                speakers_gender["NARRATOR"] = current_princ_gender
                speakers_gender["PERSON_ONE"] = current_princ_gender

                if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                    script_data["content_metadata"] = {}
                script_data["content_metadata"]["speakers_gender"] = speakers_gender
                state_manager.save_script_state(script_id, script_data)
                print(f"-> Principal Character Gender confirmed: {current_princ_gender.upper()} ({'young teen boy' if current_princ_gender == 'male' else 'young teen girl'})\n")
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
        existing_scene_prompts = script_data.get("assets", {}).get("image_prompts", {})
        if not isinstance(existing_scene_prompts, dict):
            existing_scene_prompts = {}

        print("\nPrompt Generation Options:")
        print("  [1] Auto-generate new prompt with LLM (Anchored in full story)")
        print("  [2] Guide LLM with custom notes (e.g. 'keep student at university library desk')")
        print("  [3] Enter custom positive prompt manually")
        if existing_prompt:
            print("  [4] Reuse previously stored prompt from earlier run")
        print("  [5] Regenerate entire visual storyboard with LLM (all scenes at once)")
        try:
            choices_hint = "[1/2/3/4/5, default: 1]" if existing_prompt else "[1/2/3/5, default: 1]"
            opt_input = input(f"Select option {choices_hint}: ").strip()
        except (KeyboardInterrupt, EOFError):
            opt_input = "1"

        custom_prompt_text = None
        if opt_input == "4" and existing_prompt:
            custom_prompt_text = existing_prompt
        elif opt_input == "5":
            print("\n[LLM] Regenerating cohesive, non-repetitive visual storyboard for all scenes...")
            new_storyboard = prompt_builder.build_storyboard_prompts(
                script_text=script_text,
                label=label,
                sections=sections,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
                topic=topic_str,
                scenario=scenario_str,
                lexical_field=lexical_field_str,
                anchor_environment=anchor_environment,
                general_prompt=general_prompt_val,
            )
            if "assets" not in script_data or not isinstance(script_data["assets"], dict):
                script_data["assets"] = {}
            script_data["assets"]["image_prompts"] = new_storyboard
            state_manager.save_script_state(script_id, script_data)
            custom_prompt_text = new_storyboard.get(chosen_section.lower(), "")
            print(f"[OK] Full storyboard regenerated. {len(new_storyboard)} scene prompt(s) updated in state.")
        elif opt_input == "2":
            try:
                guidance = input("Enter your custom visual guidance for this scene: ").strip()
            except (KeyboardInterrupt, EOFError):
                guidance = ""
            if guidance:
                augmented_scene_text = f"{scene_text}\n[VISUAL DIRECTOR SPECIAL GUIDANCE: {guidance}]"
            else:
                augmented_scene_text = scene_text
            print("\n[LLM] Generating refined visual prompt with custom guidance...")
            custom_prompt_text = prompt_builder.build_visual_prompt(
                script_text=script_text,
                label=label,
                scene_name=chosen_section,
                scene_text=augmented_scene_text,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
                topic=topic_str,
                scenario=scenario_str,
                lexical_field=lexical_field_str,
                anchor_environment=anchor_environment,
                existing_scene_prompts=existing_scene_prompts,
                general_prompt=general_prompt_val,
                temperature=0.8,
            )
        elif opt_input == "3":
            print("\nEnter the complete visual prompt text (paste or type; press Enter to submit):")
            raw_custom = read_multiline_paste()
            if raw_custom:
                custom_prompt_text = sanitize_and_style_prompt(raw_custom)
                print("[OK] Custom prompt recorded and styled with 2D cartoon rules.")
            else:
                custom_prompt_text = None

        if not custom_prompt_text:
            print("\n[LLM] Generating fresh visual prompt grounded in story...")
            custom_prompt_text = prompt_builder.build_visual_prompt(
                script_text=script_text,
                label=label,
                scene_name=chosen_section,
                scene_text=scene_text,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
                topic=topic_str,
                scenario=scenario_str,
                lexical_field=lexical_field_str,
                anchor_environment=anchor_environment,
                existing_scene_prompts=existing_scene_prompts,
                general_prompt=general_prompt_val,
                temperature=0.8,
            )

        # Interactive Prompt Review & Refine Loop (2 min Timed Confirmation)
        confirmed_prompt = sanitize_and_style_prompt(custom_prompt_text)
        current_seed = custom_seed if custom_seed is not None else random.randint(1, 10**15)

        proceed_with_generation = True
        while True:
            print("\n" + "=" * 64)
            print(f"PROPOSED VISUAL PROMPT [{chosen_section.upper()}]:")
            print(f"\"{confirmed_prompt}\"")
            print(f"KSampler Seed: {current_seed}")
            print("=" * 64)
            print("Options:")
            print("  [Enter] Generate image in ComfyUI now (Accept - Auto-accept in 2 min)")
            print("  [r]     Regenerate fresh prompt with LLM (new creative variation)")
            print("  [g]     Add guidance notes & regenerate prompt with LLM")
            if video_type == "ROLEPLAY":
                p1_disp = speakers_gender.get("PERSON_ONE", "female").upper()
                p2_disp = speakers_gender.get("PERSON_TWO", "male").upper()
                print(f"  [t]     Toggle roleplay genders (currently: P1={p1_disp}, P2={p2_disp}) & regenerate")
            else:
                print(f"  [t]     Toggle principal gender (currently: {current_princ_gender.upper()}) & regenerate")
            print("  [e]     Edit prompt text manually before generating")
            print("  [s]     Roll a new random seed (keeps prompt text; changes AI noise seed)")
            print("  [b]     Cancel & return to scene menu")
            try:
                act = timed_input(
                    prompt=f"\nChoice [Enter/r/g/t/e/s/b] (2 min timer): ",
                    timeout=PROMPT_REVIEW_TIMEOUT,
                    default="",
                    default_msg="[2 min Timer Expired] Auto-confirming prompt. Launching generation..."
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                proceed_with_generation = False
                break

            if act in ["", "y", "yes"]:
                # User is happy or auto-confirmed! Proceed to ComfyUI
                break
            elif act in ["t", "toggle", "gender"]:
                if video_type == "ROLEPLAY":
                    old_p1 = speakers_gender.get("PERSON_ONE", "female").lower()
                    old_p2 = speakers_gender.get("PERSON_TWO", "male").lower()
                    new_p1 = "male" if old_p1 == "female" else "female"
                    new_p2 = "male" if old_p2 == "female" else "female"
                    speakers_gender["PERSON_ONE"] = new_p1
                    speakers_gender["PERSON_TWO"] = new_p2
                    current_princ_gender = new_p1
                    if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                        script_data["content_metadata"] = {}
                    script_data["content_metadata"]["speakers_gender"] = speakers_gender
                    state_manager.save_script_state(script_id, script_data)
                    print(f"\n[Genders Toggled] Roleplay characters are now: PERSON_ONE={new_p1.upper()} ({'young teen boy' if new_p1 == 'male' else 'young teen girl'}), PERSON_TWO={new_p2.upper()} ({'young teen boy' if new_p2 == 'male' else 'young teen girl'})")
                else:
                    current_princ_gender = "female" if current_princ_gender == "male" else "male"
                    speakers_gender["NARRATOR"] = current_princ_gender
                    speakers_gender["PERSON_ONE"] = current_princ_gender
                    if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                        script_data["content_metadata"] = {}
                    script_data["content_metadata"]["speakers_gender"] = speakers_gender
                    state_manager.save_script_state(script_id, script_data)
                    print(f"\n[Gender Toggled] Principal character is now: {current_princ_gender.upper()} ({'young teen boy' if current_princ_gender == 'male' else 'young teen girl'})")
                print("[LLM] Regenerating prompt with updated gender...")
                try:
                    new_prompt = prompt_builder.build_visual_prompt(
                        script_text=script_text,
                        label=label,
                        scene_name=chosen_section,
                        scene_text=scene_text,
                        script_id=script_id,
                        speakers_gender=speakers_gender,
                        video_type=video_type,
                        character_personalities=character_personalities,
                        topic=topic_str,
                        scenario=scenario_str,
                        lexical_field=lexical_field_str,
                        anchor_environment=anchor_environment,
                        existing_scene_prompts=existing_scene_prompts,
                        temperature=0.8,
                    )
                    if new_prompt:
                        confirmed_prompt = new_prompt
                        current_seed = random.randint(1, 10**15)
                        print(f"[OK] Prompt regenerated for {current_princ_gender.upper()} with new random seed: {current_seed}")
                except Exception as exc:
                    print(f"[ERROR] Failed to regenerate prompt with LLM: {exc}")
            elif act in ["r", "regen", "regenerate", "redo"]:
                print("\n[LLM] Generating fresh alternative visual prompt with new creative composition...")
                prev_snippet = confirmed_prompt.split(".")[0].strip()[:90]
                if video_type == "ROLEPLAY":
                    p1_g = speakers_gender.get("PERSON_ONE", "female").lower()
                    p2_g = speakers_gender.get("PERSON_TWO", "male").lower()
                    p1_word = "girl" if "f" in p1_g else "boy"
                    p2_word = "girl" if "f" in p2_g else "boy"
                    char_desc = (
                        f"Characters MUST be expressive youthful 2D cartoon teens: "
                        f"PERSON_ONE is a teen {p1_word} ({p1_g.upper()}) and PERSON_TWO is a companion teen {p2_word} ({p2_g.upper()}) (approx. 13-15 years old) "
                        f"wearing authentic thematic scene costumes matching {anchor_environment} (NO generic modern street clothes, NO plain t-shirts/hoodies, NO childish clothes, NO mature adults). "
                    )
                else:
                    gender_word = "boy" if current_princ_gender == "male" else "girl"
                    char_desc = (
                        f"Protagonist MUST be an expressive youthful 2D cartoon teen {gender_word.upper()} (approx. 13-15 years old) "
                        f"wearing authentic thematic scene costume/wardrobe matching {anchor_environment} (NO generic modern street clothes, NO plain t-shirts/hoodies, NO childish clothes, NO mature adults). "
                    )
                aug_scene = (
                    f"{scene_text}\n"
                    f"[VISUAL DIRECTOR REFRESH: Explore a fresh alternative visual composition, distinct character pose/gesture, "
                    f"and alternative focal prop from earlier attempts. {char_desc}"
                    f"Distinct from: '{prev_snippet}']"
                )
                try:
                    new_prompt = prompt_builder.build_visual_prompt(
                        script_text=script_text,
                        label=label,
                        scene_name=chosen_section,
                        scene_text=aug_scene,
                        script_id=script_id,
                        speakers_gender=speakers_gender,
                        video_type=video_type,
                        character_personalities=character_personalities,
                        topic=topic_str,
                        scenario=scenario_str,
                        lexical_field=lexical_field_str,
                        anchor_environment=anchor_environment,
                        existing_scene_prompts=existing_scene_prompts,
                        temperature=0.85,
                    )
                    if new_prompt:
                        confirmed_prompt = new_prompt
                        current_seed = random.randint(1, 10**15)
                        print(f"[OK] Fresh prompt generated with new random seed: {current_seed}")
                except Exception as exc:
                    print(f"[ERROR] Failed to regenerate prompt with LLM: {exc}")
            elif act in ["g", "guide"]:
                try:
                    print("\nEnter guidance notes for the LLM (e.g. 'keep student at university library desk'):")
                    print("(Or press Enter immediately to regenerate with a fresh creative angle):")
                    more_notes = input("> ").strip()
                    if video_type == "ROLEPLAY":
                        p1_g = speakers_gender.get("PERSON_ONE", "female").lower()
                        p2_g = speakers_gender.get("PERSON_TWO", "male").lower()
                        p1_word = "girl" if "f" in p1_g else "boy"
                        p2_word = "girl" if "f" in p2_g else "boy"
                        wardrobe_mandate = (
                            f"(Characters MUST be expressive youthful 2D cartoon teens: PERSON_ONE is a teen {p1_word} ({p1_g.upper()}) and PERSON_TWO is a teen {p2_word} ({p2_g.upper()}) "
                            f"approx. 13-15 years old in authentic thematic costumes matching {anchor_environment}, NO plain street clothes, NO childish clothes, NO mature adults)"
                        )
                    else:
                        gender_word = "boy" if current_princ_gender == "male" else "girl"
                        wardrobe_mandate = f"(Protagonist MUST be a youthful 2D cartoon teen {gender_word.upper()} approx. 13-15 years old in authentic thematic costume matching {anchor_environment}, NO plain street clothes, NO childish clothes, NO mature adults)"
                    if more_notes:
                        aug_text = f"{scene_text}\n[VISUAL DIRECTOR GUIDANCE: {more_notes} {wardrobe_mandate}]"
                    else:
                        prev_snippet = confirmed_prompt.split(".")[0].strip()[:90]
                        aug_text = (
                            f"{scene_text}\n"
                            f"[VISUAL DIRECTOR GUIDANCE: Create a fresh alternative creative angle with {wardrobe_mandate}, "
                            f"distinct from previous attempt: '{prev_snippet}']"
                        )
                    print("\n[LLM] Refining visual prompt with guidance...")
                    new_prompt = prompt_builder.build_visual_prompt(
                        script_text=script_text,
                        label=label,
                        scene_name=chosen_section,
                        scene_text=aug_text,
                        script_id=script_id,
                        speakers_gender=speakers_gender,
                        video_type=video_type,
                        character_personalities=character_personalities,
                        topic=topic_str,
                        scenario=scenario_str,
                        lexical_field=lexical_field_str,
                        anchor_environment=anchor_environment,
                        existing_scene_prompts=existing_scene_prompts,
                        temperature=0.85,
                    )
                    if new_prompt:
                        confirmed_prompt = new_prompt
                        current_seed = random.randint(1, 10**15)
                        print(f"[OK] Guided prompt generated with new random seed: {current_seed}")
                except (KeyboardInterrupt, EOFError):
                    pass
                except Exception as exc:
                    print(f"[ERROR] Failed to regenerate prompt with LLM: {exc}")
            elif act in ["e", "edit"]:
                try:
                    print("\nEdit prompt text manually.")
                    print("Paste or type modified text below (press Enter immediately to keep unchanged):")
                    edited = read_multiline_paste()
                    if edited:
                        confirmed_prompt = sanitize_and_style_prompt(edited)
                        print("[OK] Prompt text updated and styled with 2D cartoon rules.")
                    else:
                        print("[Info] Prompt kept unchanged.")
                except (KeyboardInterrupt, EOFError):
                    pass
            elif act in ["s", "seed"]:
                current_seed = random.randint(1, 10**15)
                print(f"\n-> Rolled new KSampler seed: {current_seed}")
                print("   [NOTE: ComfyUI noise seed updated! Prompt text is kept unchanged.")
                print("    If you want to produce a new prompt text, type [r] to regenerate with LLM or [e] to edit.]")
            elif act in ["b", "back", "q", "quit"]:
                proceed_with_generation = False
                break

        if not proceed_with_generation:
            continue

        confirmed_prompt = sanitize_and_style_prompt(confirmed_prompt)
        print(f"\n[ComfyUI] Generating image for '{chosen_section}'...")
        t0 = time.time()
        try:
            saved_path = comfy_client.generate_image(
                prompt_text=confirmed_prompt,
                filename_prefix=f"Z-Image/script_{script_id}_{chosen_section}",
                dest_path=dest_image_path,
                seed=current_seed,
                steps=IMAGE_DEFAULT_STEPS,
                width=IMAGE_DEFAULT_WIDTH,
                height=IMAGE_DEFAULT_HEIGHT,
                stall_timeout=IMAGE_STALL_TIMEOUT,
            )
            elapsed = round(time.time() - t0, 1)
            print(f"\n[SUCCESS] Image successfully recreated in {elapsed}s!")
            print(f"Saved to: {saved_path}\n")
            if "assets" not in script_data or not isinstance(script_data["assets"], dict):
                script_data["assets"] = {}
            if "image_prompts" not in script_data["assets"] or not isinstance(script_data["assets"]["image_prompts"], dict):
                script_data["assets"]["image_prompts"] = {}
            script_data["assets"]["image_prompts"][chosen_section] = confirmed_prompt
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
    parser.add_argument("--group", "--all", action="store_true", dest="group_mode", help="Regenerate all scene images using cohesive group change mode")
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
            group_mode=args.group_mode,
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
            group_mode=args.group_mode,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
