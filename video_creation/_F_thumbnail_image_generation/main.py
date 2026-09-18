import argparse
import logging
import sys
from pathlib import Path

# Add project root, video_creation, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import COMFY_API_URL, COMFY_INPUT_DIR, BASE_DIR, require_services, THUMBNAIL_WORKFLOW_PATH, THUMBNAIL_MODELS_DIR, get_script_output_dir
# pyrefly: ignore [missing-import]
from state_manager import StateManager
try:
    # pyrefly: ignore [missing-import]
    from core.thumbnail_prompt_builder import ThumbnailPromptBuilder
    # pyrefly: ignore [missing-import]
    from core.thumbnail_client import ThumbnailComfyClient
except ImportError:
    from _F_thumbnail_image_generation.core.thumbnail_prompt_builder import ThumbnailPromptBuilder
    from _F_thumbnail_image_generation.core.thumbnail_client import ThumbnailComfyClient

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
    args = parser.parse_args()

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

    # Production Mode Selection: Mass-produce (default in 10s) or Specific Script ID
    from core.cli_prompt import prompt_production_mode
    target_script_ids = prompt_production_mode(
        stage_title="Part F: Thumbnail Generation",
        asset_name="thumbnail images",
        timeout=10.0,
        script_id_arg=args.script_id,
        require_existing_state=True,
        base_dir=BASE_DIR,
    )

    # Initialize the client
    client = ThumbnailComfyClient(
        api_url=COMFY_API_URL,
        workflow_path=workflow_path,
        comfy_input_dir=COMFY_INPUT_DIR
    )

    state_mgr = StateManager(base_dir=BASE_DIR)
    
    # Query pending scripts via Pipeline Status Tracker
    scripts_to_process = {}
    try:
        from core.status_tracker import get_status_tracker
        tracker = get_status_tracker(BASE_DIR)
        pending_rows = tracker.get_pending_scripts("thumbnail_generation", script_id=target_script_ids, force=args.force)
        if target_script_ids:
            pending_rows.sort(key=lambda r: target_script_ids.index(r["ID"]) if r["ID"] in target_script_ids else 9999)
        for r in pending_rows:
            st = state_mgr.get_script_state(r["ID"])
            scripts_to_process[r["ID"]] = st
    except Exception:
        all_scripts = state_mgr.get_all_scripts()
        for state in all_scripts:
            script_id = state.get("id")
            if not script_id:
                continue
            if target_script_ids and script_id not in target_script_ids:
                continue
            from core.expression_db import is_expression_done
            if is_expression_done(script_id):
                continue
            status = state.get("status", {})
            if args.force or status.get("thumbnail_generation") != "done":
                scripts_to_process[script_id] = state

    if not scripts_to_process:
        logger.info("No scripts pending thumbnail generation.")
        return

    for script_id, state in scripts_to_process.items():
        if args.force or state.get("status", {}).get("thumbnail_generation") != "done":
            logger.info("========================================")
            logger.info(f"Generating thumbnail for: {script_id}")

            # Extract language and expression
            metadata = state.get("metadata", {})
            language_label = metadata.get("LABEL") or state.get("prompt_params", {}).get("TARGET_LANGUAGE", "English")
            lang_key = language_label.split("|")[0].strip().lower()

            output_dir = get_script_output_dir(script_id, lang_key, BASE_DIR)
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

            try:
                # ComfyUI requires dimensions in multiples of 64 or 16 depending on the model
                # Let's use 576x1024 for 9:16 (vertical shorts)
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

            except Exception as e:
                logger.error(f"Failed to generate thumbnail for {script_id}: {e}", exc_info=True)
                state.setdefault("status", {})["thumbnail_generation"] = "error"
                state_mgr.save_script_state(script_id, state)

if __name__ == "__main__":
    main()
