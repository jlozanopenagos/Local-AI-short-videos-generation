from pathlib import Path
from typing import List, Optional, Tuple

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

_SPANISH_VARIANTS = ("latam", "spain")


def _category_dir_candidates(video_type: str) -> List[str]:
    norm = (video_type or "expression").strip().lower().replace("-", "_").replace(" ", "_")
    if norm in ("fun_facts", "fun_fact", "funfacts", "funfact"):
        return ["fun_facts", "fun_fact"]
    if norm in ("expressions", "idiom"):
        return ["expression"]
    if norm in ("games", "quiz"):
        return ["game"]
    if norm in ("role_play", "dialogue"):
        return ["roleplay"]
    return [norm or "expression"]


def resolve_thumbnail_templates(
    lang_key: str,
    video_type: str,
    models_dir: Path,
) -> List[Tuple[Optional[str], Path]]:
    """Resolves matching master thumbnail templates for `(lang_key, video_type)`.

    - For `spanish`: returns `[("latam", ...), ("spain", ...)]` (all existing region variants).
    - For `english`, `french`, `italian`: returns `[(None, <category>/template.png)]`.
    - Falls back to legacy `<lang>/<lang>_thumbnail_model.png` (then `english/english_thumbnail_model.png`)
      when category subfolders are absent in isolated fixture workspaces.
    """
    lang = (lang_key or "english").strip().lower()
    cat_candidates = _category_dir_candidates(video_type)
    lang_dir = models_dir / lang

    for cat_name in cat_candidates:
        cat_dir = lang_dir / cat_name
        if not cat_dir.is_dir():
            continue

        if lang == "spanish":
            variants: List[Tuple[Optional[str], Path]] = []
            for variant in _SPANISH_VARIANTS:
                cand = cat_dir / f"{variant}.png"
                if cand.is_file():
                    variants.append((variant, cand))
            if variants:
                return variants

        tpl = cat_dir / "template.png"
        if tpl.is_file():
            return [(None, tpl)]

        pngs = sorted(cat_dir.glob("*.png"))
        if pngs:
            return [(None, pngs[0])]

    # Legacy single-template fallback (e.g. minimal test workspaces)
    legacy_lang = lang_dir / f"{lang}_thumbnail_model.png"
    if legacy_lang.is_file():
        return [(None, legacy_lang)]

    legacy_en = models_dir / "english" / "english_thumbnail_model.png"
    if legacy_en.is_file():
        return [(None, legacy_en)]

    raise FileNotFoundError(
        f"No thumbnail template found for language='{lang}', category='{cat_candidates[0]}' under {models_dir}"
    )


def generate_thumbnail_for_script(
    script_data: dict,
    state_mgr: StateManager | None = None,
    base_dir: Path | None = None,
    input_images_dir: Path | None = None,
) -> bool:
    """Renders category-specific thumbnail(s) for a single script and updates state.

    Spanish scripts produce both `thumbnail_latam.png` and `thumbnail_spain.png`, recorded in
    `assets.thumbnail_variants` (with `assets.thumbnail_path` pointing to the LatAm primary image).
    English, French, and Italian scripts produce `<output_dir>/thumbnail.png`.
    """
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

    has_explicit_thumb_title = bool(str((script_data.get("content_metadata") or {}).get("thumbnail_title") or "").strip())
    title_text = extract_thumbnail_title(script_data)
    templates = resolve_thumbnail_templates(lang_key, video_type, in_dir)
    target_size = (IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT)

    assets = script_data.setdefault("assets", {})
    if len(templates) == 1 and templates[0][0] is None:
        _variant, template_path = templates[0]
        dest_path = output_dir / "thumbnail.png"
        render_thumbnail_chalkboard(
            reference_image_path=template_path,
            title_text=title_text,
            dest_path=dest_path,
            target_size=target_size,
            category=video_type,
            strip_prefix=not has_explicit_thumb_title,
        )
        assets["thumbnail_path"] = str(dest_path)
        assets.pop("thumbnail_variants", None)
    else:
        variant_paths = {}
        for variant, template_path in templates:
            v_key = variant or "default"
            dest_path = output_dir / f"thumbnail_{v_key}.png"
            render_thumbnail_chalkboard(
                reference_image_path=template_path,
                title_text=title_text,
                dest_path=dest_path,
                target_size=target_size,
                category=video_type,
                strip_prefix=not has_explicit_thumb_title,
            )
            variant_paths[v_key] = str(dest_path)

        assets["thumbnail_variants"] = variant_paths
        assets["thumbnail_path"] = variant_paths.get("latam") or next(iter(variant_paths.values()))

    script_data.setdefault("status", {})["thumbnail_generation"] = "done"
    sm.save_script_state(script_id, script_data)
    return True
