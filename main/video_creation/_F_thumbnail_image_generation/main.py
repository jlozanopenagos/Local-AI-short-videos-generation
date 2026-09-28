import argparse
import logging
import sys
from pathlib import Path

# Add project root, video_creation, core, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import COMFY_API_URL, COMFY_INPUT_DIR, BASE_DIR, require_services, THUMBNAIL_WORKFLOW_PATH, THUMBNAIL_MODELS_DIR, get_script_output_dir
# pyrefly: ignore [missing-import]
from state_manager import StateManager
try:
    # pyrefly: ignore [missing-import]
    from _F_thumbnail_image_generation.core.thumbnail_prompt_builder import ThumbnailPromptBuilder
    # pyrefly: ignore [missing-import]
    from _F_thumbnail_image_generation.core.thumbnail_client import ThumbnailComfyClient
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from core.thumbnail_prompt_builder import ThumbnailPromptBuilder
    # pyrefly: ignore [missing-import]
    from core.thumbnail_client import ThumbnailComfyClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thumbnails using Flux dev workflow.")
    parser.add_argument(
        "--script-id",
        type=str,
        default=None,
        help="Target specific script ID (e.g. EE01, FG02)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate thumbnails even if 'thumbnail_generation' is 'done'."
    )
    parser.add_argument("--auto", action="store_true", help="Auto-generate without interactive terminal prompts")
    parser.add_argument(
        "--fun-facts",
        "--fun-facts-only",
        dest="fun_facts_only",
        action="store_true",
        help="Only generate thumbnails for Fun Facts scripts (e.g. EF01, FF01, SF01, IF01)"
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
        "--from-ready-scripts",
        "--ready-scripts",
        "--from-csv",
        dest="ready_scripts_csv",
        nargs="?",
        const="",
        default=None,
        help="Target scripts from <date>_ready_scripts.csv (default checks D:\\AI\\output\\connectivity\\ready_scripts/)"
    )
    args = parser.parse_args()

    base_dir = BASE_DIR
    state_mgr = StateManager(base_dir=base_dir)

    # Find the reference image in the unified input/images/thumbnail_models folder (or local fallback)
    input_images_dir = THUMBNAIL_MODELS_DIR
    if not input_images_dir.exists():
        input_images_dir = Path(__file__).parent / "input_images"

    workflow_path = THUMBNAIL_WORKFLOW_PATH

    # Pre-flight check
    try:
        print("\n" + "=" * 60)
        print("Pre-flight Connection Checks:")
        require_services(comfy=True, llm=True)
        print("=" * 60 + "\n")
    except ConnectionError as exc:
        logger.error("%s", exc)
        return

    # Production Mode Selection: Mass-produce (default in 10s), Specific ID, Group Range, Fun Facts, or Ready Scripts CSV
    # pyrefly: ignore [missing-import]
    try:
        # pyrefly: ignore [missing-import]
        from core.cli_prompt import (
            prompt_production_mode,
            prompt_group_range,
            prompt_fun_facts_mode,
            prompt_ready_scripts_mode,
        )
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from cli_prompt import (
            prompt_production_mode,
            prompt_group_range,
            prompt_fun_facts_mode,
            prompt_ready_scripts_mode,
        )

    is_cli_fun_facts = args.fun_facts_only or (args.video_type and args.video_type.lower() == "fun_facts")

    if is_cli_fun_facts and not args.script_id and args.ready_scripts_csv is None:
        print("\n[CLI Option] Fun Facts mode active: targeting Fun Facts scripts only.")
        target_script_ids = None
        selected_mode = "fun_facts"
    else:
        target_script_ids, selected_mode = prompt_production_mode(
            stage_title="Part F: Thumbnail Generation",
            asset_name="thumbnail images",
            timeout=10.0,
            script_id_arg=args.script_id,
            auto=args.auto,
            require_existing_state=True,
            base_dir=base_dir,
            return_mode=True,
            allow_fun_facts_mode=True,
            allow_ready_scripts_mode=True,
            ready_scripts_path_arg=args.ready_scripts_csv,
        )
        if is_cli_fun_facts:
            selected_mode = "fun_facts"

    # Initialize the client
    client = ThumbnailComfyClient(
        api_url=COMFY_API_URL,
        workflow_path=workflow_path,
        comfy_input_dir=COMFY_INPUT_DIR
    )

    while True:
        target_video_type = None
        if selected_mode == "fun_facts" or args.fun_facts_only:
            target_video_type = "fun_facts"
        elif args.video_type and args.video_type.lower() != "all":
            target_video_type = args.video_type.lower()

        target_language = args.language if args.language and args.language.lower() != "all" else None

        # Query pending scripts via Pipeline Status Tracker
        try:
            try:
                # pyrefly: ignore [missing-import]
                from core.status_tracker import get_status_tracker
            except (ImportError, ModuleNotFoundError):
                # pyrefly: ignore [missing-import]
                from status_tracker import get_status_tracker
            tracker = get_status_tracker(base_dir)
            pending_rows = tracker.get_pending_scripts(
                "thumbnail_generation",
                script_id=target_script_ids,
                language=target_language,
                video_type=target_video_type,
                force=args.force
            )
            pending = [state_mgr.get_script_state(r["ID"]) for r in pending_rows]
            if target_script_ids:
                pending.sort(key=lambda s: target_script_ids.index(s.get("id", "")) if s.get("id", "") in target_script_ids else 9999)
        except Exception:
            all_scripts = state_mgr.get_all_scripts()
            pending = []
            for state in all_scripts:
                script_id = state.get("id")
                if not script_id:
                    continue
                if target_script_ids and script_id not in target_script_ids:
                    continue
                if target_language:
                    slang = (state.get("content_metadata", {}).get("language") or "").lower()
                    if slang != target_language.lower():
                        continue
                if target_video_type:
                    svtype = (state.get("content_metadata", {}).get("video_type") or "").lower()
                    if target_video_type == "fun_facts" and svtype not in ("fun_facts", "funfacts"):
                        continue
                    elif target_video_type != "fun_facts" and svtype != target_video_type:
                        continue

                try:
                    # pyrefly: ignore [missing-import]
                    from core.expression_db import is_expression_done
                except (ImportError, ModuleNotFoundError):
                    # pyrefly: ignore [missing-import]
                    from expression_db import is_expression_done
                if is_expression_done(script_id):
                    continue

                status = state.get("status", {})
                if args.force or status.get("thumbnail_generation") != "done":
                    pending.append(state)

        if not pending:
            scope_label = f" ({target_video_type.upper()})" if target_video_type else ""
            if target_script_ids:
                print(f"None of the target script(s) are pending for thumbnail generation (already generated or missing state). Use --force to regenerate.")
            else:
                print(f"No pending scripts for thumbnail generation{scope_label}.")

            if selected_mode in ("group_range", "fun_facts") and not args.auto:
                try:
                    create_more = input("\nDo you want to select another group or scope of scripts? [y/N]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return
                if create_more in ("y", "yes"):
                    if selected_mode == "fun_facts":
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                    else:
                        target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                    if target_script_ids:
                        continue
            return

        print(f"\nFound {len(pending)} pending script(s) for thumbnail generation:")
        print(f"Target IDs: {', '.join([s['id'] for s in pending[:12]])}{'...' if len(pending) > 12 else ''}\n")

        success_count = 0
        for i, state in enumerate(pending, start=1):
            script_id = state.get("id")
            try:
                print(f"[{i}/{len(pending)}] Generating thumbnail for: {script_id}...")

                # Extract language and expression
                metadata = state.get("metadata", {})
                language_label = metadata.get("LABEL") or state.get("prompt_params", {}).get("TARGET_LANGUAGE", "English")
                lang_key = language_label.split("|")[0].strip().lower()

                output_dir = get_script_output_dir(script_id, lang_key, base_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                dest_path = output_dir / "thumbnail.png"

                content_metadata = state.get("content_metadata", {})
                expression = content_metadata.get("target_expression", "LEARN WITH TITO")

                # Dynamically select the correct reference image based on language
                reference_image_path = input_images_dir / lang_key / f"{lang_key}_thumbnail_model.png"
                if not reference_image_path.exists():
                    logger.error(f"Reference image not found: {reference_image_path}. Falling back to English.")
                    reference_image_path = input_images_dir / "english" / "english_thumbnail_model.png"

                logger.info(f"Using reference image: {reference_image_path.name}")

                # Build the prompt
                prompt = ThumbnailPromptBuilder.build_prompt(
                    chalkboard_text=expression,
                    language_label=language_label
                )

                client.generate_thumbnail(
                    prompt_text=prompt,
                    filename_prefix=f"Thumbnail_{script_id}",
                    dest_path=dest_path,
                    reference_image_path=reference_image_path,
                    width=576,
                    height=1024
                )

                state.setdefault("status", {})["thumbnail_generation"] = "done"
                state_mgr.save_script_state(script_id, state)
                logger.info(f"Thumbnail generation complete for {script_id}.")
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to generate thumbnail for {script_id}: {e}", exc_info=True)
                state.setdefault("status", {})["thumbnail_generation"] = "error"
                state_mgr.save_script_state(script_id, state)

        print(f"\n[Completed] Process complete. Successfully generated {success_count} thumbnail(s).")

        # If in group_range, fun_facts, or ready_scripts mode, prompt whether to process more
        if selected_mode in ("group_range", "fun_facts", "ready_scripts") and not args.auto:
            try:
                create_more = input("\nDo you want to generate thumbnails for more scripts? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nFinished thumbnail generation session.")
                break

            if create_more in ("y", "yes"):
                if selected_mode == "fun_facts":
                    target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                elif selected_mode == "ready_scripts":
                    target_script_ids = prompt_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                else:
                    target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                if target_script_ids:
                    continue
                else:
                    break
            else:
                print("\nFinished thumbnail generation session.")
                break
        else:
            break


if __name__ == "__main__":
    main()
