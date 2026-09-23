import argparse
import os
import sys
import shutil
import traceback
from pathlib import Path
import logging

# Add project root, video_creation, and module directory to path for robust imports
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import (
    COMFY_API_URL, COMFY_INPUT_DIR, BASE_DIR, GAME_IMAGES_DIR,
    IMAGE_WORKFLOW_PATH, IMAGE_DEFAULT_STEPS, IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT,
    LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME, require_services,
    get_script_output_dir
)
# pyrefly: ignore [missing-import]
from state_manager import StateManager

try:
    from core.comfy_client import ImageComfyClient, ChalkboardComfyClient
    from core.prompt_builder import VisualPromptBuilder
    from core.chalkboard_renderer import render_chalkboard_image
except ImportError:
    from _C_image_generation.core.comfy_client import ImageComfyClient, ChalkboardComfyClient
    from _C_image_generation.core.prompt_builder import VisualPromptBuilder
    from _C_image_generation.core.chalkboard_renderer import render_chalkboard_image

from _B_voice_generation.core.script_parser import parse_sections


logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)


def process_script(
    script_data: dict,
    state_manager: StateManager,
    comfy_client: ImageComfyClient,
    prompt_builder: VisualPromptBuilder,
    force: bool,
    seed: int,
    base_dir: Path
) -> bool:
    script_id = script_data["id"]
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "english")
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or metadata.get("VIDEO_TYPE", "EXPRESSION")
    ).upper()

    print("=" * 60)
    print(f"Processing Script ID: {script_id} for Images [{video_type}]")
    print(f"Label: {label}")
    print("=" * 60)

    # Establish character genders: read from voice generation metadata or prompt user in terminal
    speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
    if not isinstance(speakers_gender, dict):
        speakers_gender = {}

    if video_type == "ROLEPLAY":
        p1_g = speakers_gender.get("PERSON_ONE", "male")
        p2_g = speakers_gender.get("PERSON_TWO", "female")

        print("\n" + "-" * 55)
        print("Roleplay Character Genders (matched to voices):")
        print(f"  [1] PERSON_ONE: {p1_g.upper()}")
        print(f"  [2] PERSON_TWO: {p2_g.upper()}")
        print("-" * 55)
        try:
            prompt_msg = (
                f"Press Enter to use these genders, or type new ones "
                f"(e.g. 'male, female' or 'female, male'): "
            )
            user_input = input(prompt_msg).strip()
            if user_input:
                parts = [p.strip().lower() for p in user_input.replace("/", ",").split(",")]
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
                print(f"-> Genders established: PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}\n")
            else:
                print(f"-> Using confirmed voice genders: PERSON_ONE={p1_g.upper()}, PERSON_TWO={p2_g.upper()}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nUsing default voice genders.\n")

    script_output_dir = get_script_output_dir(script_id, label, base_dir) / "images"
    script_output_dir.mkdir(parents=True, exist_ok=True)
    
    sections = parse_sections(script_text)
    if not sections:
        logger.warning("[%s] No sections found in script.", script_id)
        return False

    VALID_GAME_SECTIONS = {"hook", "challenge", "pressure", "answer", "explanation"}
    METADATA_IGNORE_KEYS = {
        "title", "difficulty", "emotion", "game_type", "related_content",
        "category", "subcategory", "topic", "learning_objective",
        "chalkboard_exercise", "target_expression", "roleplay_scenario"
    }

    success = True
    for section_name, section_text in sections.items():
        sec_lower = section_name.strip().lower()
        if sec_lower in METADATA_IGNORE_KEYS:
            continue
        if video_type == "GAME" and sec_lower not in VALID_GAME_SECTIONS:
            continue
        if not section_text.strip():
            continue
            
        print(f"\n--- Generating Image for Scene: {section_name.upper()} ---")
        
        scene_filename = f"script_{script_id}_{section_name}.png"
        dest_path = script_output_dir / scene_filename

        if dest_path.exists() and not force:
            logger.info("[%s] Image for %s already exists: %s — skipping.", script_id, section_name, dest_path.name)
            continue

        # Specialized handling for GAME: PRESSURE (Static pre-made image)
        if video_type == "GAME" and section_name.lower() == "pressure":
            lang_lower = label.split("|")[0].strip().lower()
            if "french" in lang_lower or "français" in lang_lower:
                lang_key = "french"
            elif "spanish" in lang_lower or "español" in lang_lower:
                lang_key = "spanish"
            elif "italian" in lang_lower or "italiano" in lang_lower:
                lang_key = "italian"
            else:
                lang_key = "english"

            waiting_img = GAME_IMAGES_DIR / lang_key / f"{lang_key}_waiting.png"
            if not waiting_img.exists():
                waiting_img = GAME_IMAGES_DIR / "english" / "english_waiting.png"

            if waiting_img.exists():
                shutil.copy2(waiting_img, dest_path)
                print(f"✓ Copied static waiting image: {waiting_img.name} -> {dest_path.name}")
                continue
            else:
                logger.warning(f"Could not find waiting image at {waiting_img}, falling back to generation.")

        # Specialized handling for GAME: CHALLENGE (Native high-resolution chalk typography on empty_chalkboard.png)
        if video_type == "GAME" and section_name.lower() == "challenge":
            chalkboard_model = GAME_IMAGES_DIR / "empty_chalkboard.png"
            if chalkboard_model.exists():
                content_meta = script_data.get("content_metadata", {})
                exercise_text = content_meta.get("chalkboard_exercise", "")
                if not exercise_text:
                    exercise_text = section_text.strip()

                print(f"[Chalkboard Renderer] Generating high-resolution chalk challenge image...")
                print(f"Chalkboard Exercise Text:\n{exercise_text}")
                try:
                    render_chalkboard_image(
                        empty_chalkboard_path=chalkboard_model,
                        exercise_text=exercise_text,
                        dest_path=dest_path,
                        target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT)
                    )
                    print(f"✓ Chalkboard challenge image saved: {dest_path.name}")
                    continue
                except Exception as exc:
                    logger.error("[%s] Native chalkboard rendering failed: %s. Falling back to Z-Image.", script_id, exc)

        try:
            character_personalities = script_data.get("content_metadata", {}).get("character_personalities", None)

            visual_prompt = prompt_builder.build_visual_prompt(
                script_text=script_text,
                label=label,
                scene_name=section_name,
                scene_text=section_text,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
            )
        except Exception as exc:
            logger.error("[%s] Failed to generate visual prompt for %s: %s", script_id, section_name, exc)
            success = False
            continue

        filename_prefix = f"Z-Image/script_{script_id}_{section_name}"
        try:
            result_path = comfy_client.generate_image(
                prompt_text=visual_prompt,
                filename_prefix=filename_prefix,
                dest_path=dest_path,
                seed=seed,
                steps=IMAGE_DEFAULT_STEPS,
                width=IMAGE_DEFAULT_WIDTH,
                height=IMAGE_DEFAULT_HEIGHT,
            )
            print(f"✓ Image saved: {result_path}")
        except Exception as exc:
            logger.error("[%s] Unexpected generation error on %s: %s", script_id, section_name, exc)
            success = False
            break

    if success:
        script_data["assets"]["image_dir"] = str(script_output_dir)
        script_data["status"]["image_generation"] = "done"
        state_manager.save_script_state(script_id, script_data)
        
    return success

def main() -> int:
    parser = argparse.ArgumentParser(description="LingoVerse Shorts Image Generator (Flux / Z-Image)")
    parser.add_argument("--script-id", type=str, default=None, help="Target specific script ID(s) (e.g. EE01, FG02 or comma-separated)")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if images are already generated")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for generation reproducibility")
    parser.add_argument("--auto", action="store_true", help="Auto-generate without interactive terminal prompts")
    parser.add_argument(
        "--fun-facts",
        "--fun-facts-only",
        dest="fun_facts_only",
        action="store_true",
        help="Only generate images for Fun Facts scripts (e.g. EF01, FF01, SF01, IF01)"
    )
    parser.add_argument(
        "--video-type",
        type=str,
        default=None,
        choices=["expression", "game", "roleplay", "fun_facts", "all"],
        help="Filter generation to specific video type"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=["all", "english", "french", "spanish", "italian"],
        help="Filter generation to specific language"
    )
    parser.add_argument(
        "--from-csv",
        "--csv-list",
        dest="csv_list",
        nargs="?",
        const="",
        default=None,
        help="Target scripts listed in CSV (default checks input/csv/image_to_change/)"
    )
    args = parser.parse_args()

    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)

    workflow_path = IMAGE_WORKFLOW_PATH
    if not workflow_path.exists():
        logger.error(f"Workflow file not found: {workflow_path}")
        return 1

    try:
        comfy_client = ImageComfyClient(
            api_url=COMFY_API_URL,
            workflow_path=workflow_path,
            poll_timeout=3600,
            poll_interval=2,
        )
    except FileNotFoundError as exc:
        logger.error("Workflow load failed: %s", exc)
        return 1

    llm_timeout = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "180"))
    prompt_builder = VisualPromptBuilder(
        api_base_url=LLM_API_BASE_URL,
        api_key=LLM_API_KEY,
        model_name=LLM_MODEL_NAME,
        request_timeout=llm_timeout,
    )

    # Pre-flight connection checks: verify ComfyUI and LLM server before processing
    print("\n" + "=" * 60)
    print("Pre-flight Connection Checks:")
    try:
        require_services(comfy=True, llm=True)
    except ConnectionError as exc:
        print(f"\n{exc}\n")
        return 1
    print("=" * 60 + "\n")

    # Production Mode Selection: Mass-produce (default in 10s), Specific ID, Group Range, Fun Facts, or CSV List
    # pyrefly: ignore [missing-import]
    from core.cli_prompt import prompt_production_mode, prompt_group_range, prompt_fun_facts_mode

    is_cli_fun_facts = args.fun_facts_only or (args.video_type and args.video_type.lower() == "fun_facts")

    if is_cli_fun_facts and not args.script_id and args.csv_list is None:
        print("\n[CLI Option] Fun Facts mode active: targeting Fun Facts scripts only.")
        target_script_ids = None
        selected_mode = "fun_facts"
    else:
        target_script_ids, selected_mode = prompt_production_mode(
            stage_title="Part C: Image Generation",
            asset_name="scene illustrations",
            timeout=10.0,
            script_id_arg=args.script_id,
            auto=args.auto,
            require_existing_state=True,
            base_dir=base_dir,
            return_mode=True,
            allow_fun_facts_mode=True,
            allow_csv_list_mode=True,
            csv_folder_name="image_to_change",
            csv_path_arg=args.csv_list,
        )
        if is_cli_fun_facts:
            selected_mode = "fun_facts"

    while True:
        # Determine target video type filter
        target_video_type = None
        if selected_mode == "fun_facts" or args.fun_facts_only:
            target_video_type = "fun_facts"
        elif args.video_type and args.video_type.lower() != "all":
            target_video_type = args.video_type.lower()

        target_language = args.language if args.language and args.language.lower() != "all" else None

        # Query pending scripts via Pipeline Status Tracker
        try:
            # pyrefly: ignore [missing-import]
            from core.status_tracker import get_status_tracker
            tracker = get_status_tracker(base_dir)
            pending_rows = tracker.get_pending_scripts(
                "image_generation",
                script_id=target_script_ids,
                language=target_language,
                video_type=target_video_type,
                force=args.force
            )
            pending = [state_manager.get_script_state(r["ID"]) for r in pending_rows]
            if target_script_ids:
                pending.sort(key=lambda s: target_script_ids.index(s.get("id", "")) if s.get("id", "") in target_script_ids else 9999)
        except Exception:
            all_scripts = state_manager.get_all_scripts()
            pending = []
            for script in all_scripts:
                script_id = script.get("id")
                if target_script_ids and script_id not in target_script_ids:
                    continue
                if target_language:
                    slang = (script.get("content_metadata", {}).get("language") or "").lower()
                    if slang != target_language.lower():
                        continue
                if target_video_type:
                    svtype = (script.get("content_metadata", {}).get("video_type") or "").lower()
                    if target_video_type == "fun_facts" and svtype not in ("fun_facts", "funfacts"):
                        continue
                    elif target_video_type != "fun_facts" and svtype != target_video_type:
                        continue

                # pyrefly: ignore [missing-import]
                from core.expression_db import is_expression_done
                if is_expression_done(script_id):
                    continue

                status = script.get("status", {})
                if status.get("script_generation") == "done":
                    if args.force or status.get("image_generation") != "done":
                        pending.append(script)

        if not pending:
            scope_label = f" ({target_video_type.upper()})" if target_video_type else ""
            if target_script_ids:
                print(f"None of the target script(s) are pending for image generation (already illustrated or missing state). Use --force to regenerate.")
            else:
                print(f"No pending video scripts for image generation{scope_label}.")

            if selected_mode in ("group_range", "fun_facts") and not args.auto:
                try:
                    create_more = input("\nDo you want to select another group or scope of scripts? [y/N]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return 0
                if create_more in ("y", "yes"):
                    if selected_mode == "fun_facts":
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                    else:
                        target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                    if target_script_ids:
                        continue
            return 0

        print(f"\nFound {len(pending)} pending script(s) for image generation:")
        print(f"Target IDs: {', '.join([s['id'] for s in pending[:12]])}{'...' if len(pending) > 12 else ''}\n")
        
        success_count = 0
        for i, script in enumerate(pending, start=1):
            try:
                print(f"[{i}/{len(pending)}] Processing Script ID: {script.get('id', '')} for Images...")
                if process_script(script, state_manager, comfy_client, prompt_builder, args.force, args.seed, base_dir):
                    success_count += 1
                else:
                    print(f"Failed to generate images for script ID {script.get('id', '')}.", file=sys.stderr)
                    return 1
            except Exception as exc:
                print(f"Unexpected error processing script ID {script.get('id', '')}: {exc}", file=sys.stderr)
                traceback.print_exc()
                return 1

        print(f"\n[Completed] Process complete. Successfully generated {success_count} image set(s).")

        # If in group_range or fun_facts mode, prompt whether to process more
        if selected_mode in ("group_range", "fun_facts") and not args.auto:
            try:
                create_more = input("\nDo you want to generate images for more scripts? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nFinished image generation session.")
                break

            if create_more in ("y", "yes"):
                if selected_mode == "fun_facts":
                    target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                else:
                    target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                if target_script_ids:
                    continue
                else:
                    break
            else:
                print("\nFinished image generation session.")
                break
        else:
            break

    return 0

if __name__ == "__main__":
    sys.exit(main())

