from pathlib import Path

from config import (
    BASE_DIR,
    IMAGE_DEFAULT_HEIGHT,
    IMAGE_DEFAULT_WIDTH,
    THUMBNAIL_MODELS_DIR,
    get_script_output_dir,
    resolve_script_language,
    resolve_script_video_type,
)
from core.state_manager import StateManager
from video_creation._F_thumbnail_image_generation.core.thumbnail_renderer import (
    extract_thumbnail_title,
    render_thumbnail_chalkboard,
)


def generate_thumbnail_for_script(
    script_data: dict,
    state_mgr: StateManager | None = None,
    base_dir: Path | None = None,
    input_images_dir: Path | None = None,
) -> bool:
    """Renders a chalkboard thumbnail for a single script and updates state."""
    b_dir = base_dir or BASE_DIR
    sm = state_mgr or StateManager(base_dir=b_dir)
    in_dir = input_images_dir or (
        THUMBNAIL_MODELS_DIR if b_dir == BASE_DIR else b_dir / "input" / "images" / "thumbnail_models"
    )
    if not in_dir.exists():
        in_dir = Path(__file__).parent / "input_images"

    script_id = script_data.get("id")
    if not script_id:
        return False

    lang_key = resolve_script_language(script_data)
    video_type = resolve_script_video_type(script_data)

    output_dir = get_script_output_dir(script_id, lang_key, b_dir, video_type=video_type)
    output_dir.mkdir(parents=True, exist_ok=True)
    dest_path = output_dir / "thumbnail.png"

    title_text = extract_thumbnail_title(script_data)
    reference_image_path = in_dir / lang_key / f"{lang_key}_thumbnail_model.png"
    if not reference_image_path.exists():
        reference_image_path = in_dir / "english" / "english_thumbnail_model.png"

    render_thumbnail_chalkboard(
        reference_image_path=reference_image_path,
        title_text=title_text,
        dest_path=dest_path,
        target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT),
    )

    script_data.setdefault("assets", {})["thumbnail_path"] = str(dest_path)
    script_data.setdefault("status", {})["thumbnail_generation"] = "done"
    sm.save_script_state(script_id, script_data)
    return True
