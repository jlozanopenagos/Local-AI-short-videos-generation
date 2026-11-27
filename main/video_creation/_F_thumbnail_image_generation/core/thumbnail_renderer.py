import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
from PIL import Image, ImageDraw, ImageFont

try:
    # pyrefly: ignore [missing-import]
    from _C_image_generation.core.chalkboard_renderer import (
        _get_font,
        wrap_words_to_width,
    )
except (ImportError, ModuleNotFoundError):
    from video_creation._C_image_generation.core.chalkboard_renderer import (
        _get_font,
        wrap_words_to_width,
    )


@dataclass(frozen=True)
class CategoryThumbnailStyle:
    """Visual styling and static panel safe region for a Tito's LingoVerse thumbnail category."""

    category: str
    safe_box: Tuple[float, float, float, float]
    main_color: Tuple[int, int, int, int]
    header_color: Tuple[int, int, int, int]
    shadow_color: Tuple[int, int, int, int]
    divider_color: Tuple[int, int, int, int]
    font_filename: str = "segoeprb.ttf"


CATEGORY_THUMBNAIL_STYLES: Dict[str, CategoryThumbnailStyle] = {
    "expression": CategoryThumbnailStyle(
        category="expression",
        safe_box=(0.115, 0.242, 0.850, 0.452),
        main_color=(255, 238, 140, 255),
        header_color=(250, 250, 245, 255),
        shadow_color=(8, 28, 14, 185),
        divider_color=(255, 255, 255, 140),
        font_filename="segoeprb.ttf",
    ),
    "game": CategoryThumbnailStyle(
        category="game",
        safe_box=(0.125, 0.248, 0.875, 0.470),
        main_color=(255, 226, 74, 255),
        header_color=(255, 255, 255, 255),
        shadow_color=(4, 12, 48, 210),
        divider_color=(140, 225, 255, 175),
        font_filename="segoeuib.ttf",
    ),
    "roleplay": CategoryThumbnailStyle(
        category="roleplay",
        safe_box=(0.115, 0.242, 0.885, 0.482),
        main_color=(255, 224, 118, 255),
        header_color=(255, 246, 228, 255),
        shadow_color=(36, 4, 14, 210),
        divider_color=(255, 214, 120, 165),
        font_filename="segoeuib.ttf",
    ),
    "fun_facts": CategoryThumbnailStyle(
        category="fun_facts",
        safe_box=(0.115, 0.250, 0.850, 0.482),
        main_color=(255, 236, 102, 255),
        header_color=(248, 246, 255, 255),
        shadow_color=(22, 4, 42, 210),
        divider_color=(255, 220, 140, 170),
        font_filename="segoeuib.ttf",
    ),
}

_CATEGORY_ALIASES: Dict[str, str] = {
    "expression": "expression",
    "expressions": "expression",
    "game": "game",
    "games": "game",
    "roleplay": "roleplay",
    "fun_fact": "fun_facts",
    "fun_facts": "fun_facts",
    "funfact": "fun_facts",
    "funfacts": "fun_facts",
}


def get_category_thumbnail_style(category: Optional[str]) -> Optional[CategoryThumbnailStyle]:
    """Resolves a CategoryThumbnailStyle from a video type/category string."""
    if not category:
        return None
    canonical = _CATEGORY_ALIASES.get(str(category).strip().lower().replace("-", "_").replace(" ", "_"))
    return CATEGORY_THUMBNAIL_STYLES.get(canonical) if canonical else None


_CATEGORY_PREFIX_RE = re.compile(
    r"^(?:[\[\(]\s*)?"
    r"(?:"
    r"quiz|game|juego|jeu|gioco|trivia|"
    r"expression|expresi[óo]n|espressione|idiom|modismo|"
    r"fun\s*facts?|dato\s*curioso|datos\s*curiosos|curiosidad|curiosit[éeàa]|"
    r"role[\s-]*play|dialogue|di[áa]logo|dialogo|"
    r"in\s+action|en\s+acci[óo]n|en\s+action|in\s+azione|"
    r"origin|origen|origine"
    r")"
    r"(?:\s*[\]\)]\s*[:：\|\-–—]?\s*|\s*(?:[:：\|]|\s[-–—]\s)\s*)",
    re.IGNORECASE,
)


def _strip_category_prefix(text: str) -> str:
    current = str(text).strip()
    while current:
        stripped = _CATEGORY_PREFIX_RE.sub("", current, count=1).strip()
        if not stripped or stripped == current:
            break
        current = stripped
    return current


def clean_thumbnail_title(text: str, *, strip_prefix: bool = True) -> str:
    """Cleans up a script title or expression for thumbnail panel display.
    Strips leading category/format labels when `strip_prefix=True`, fixes unmatched single/double quotes,
    and normalizes whitespace while preserving intentional stress capitalization (e.g. REcord vs reCORD).
    """
    if not text:
        return "LEARN WITH TITO"

    text_no_emoji = re.sub(
        r"[\U0001F1E0-\U0001F1FF\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251\U00002600-\U000026FF\U00002300-\U000023FF]+",
        "",
        str(text),
        flags=re.UNICODE,
    )
    cleaned = re.sub(r"\s+", " ", text_no_emoji).strip()

    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()

    if strip_prefix:
        cleaned = _strip_category_prefix(cleaned) or cleaned

    single_quotes = cleaned.count("'")
    if single_quotes >= 1:
        word_apostrophes = len(re.findall(r"\w'\w", cleaned))
        unpaired_quotes = single_quotes - word_apostrophes
        if unpaired_quotes == 1 and not cleaned.endswith("'"):
            if re.search(r"(?:^|\s)'[^']+$", cleaned):
                cleaned = cleaned + "'"

    if cleaned.count('"') == 1 and not cleaned.endswith('"'):
        if re.search(r'(?:^|\s)"[^"]+$', cleaned):
            cleaned = cleaned + '"'

    return cleaned or "LEARN WITH TITO"


def sanitize_thumbnail_title(title: str, lang: str, expression: str = "") -> str:
    """Sanitizes and localizes thumbnail titles for non-English languages,
    stripping formulaic clichés and English leakage from Latin language panels.
    """
    lang = (lang or "").lower().strip()
    if not title:
        return expression or "LEARN WITH TITO"

    cleaned = title.strip()

    if lang in ("italian", "spanish", "french"):
        banned_patterns = [
            r":\s*(?:the\s+)?native\s+(?:secret|trick|way)\b.*$",
            r":\s*(?:le\s+)?secret\s+des\s+natifs\b.*$",
            r":\s*(?:el\s+)?secreto\s+de\s+los\s+nativos\b.*$",
            r":\s*(?:il\s+)?segreto\s+dei\s+nativi\b.*$",
            r":\s*(?:the\s+)?secret\s*$",
        ]
        for pat in banned_patterns:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

        english_markers = {
            "the", "secret", "phrase", "luck", "stop", "saying", "instead", "wrong",
            "tense", "truth", "about", "spelling", "word", "words", "how", "to",
            "why", "never", "use", "ultimate", "trap", "chaos", "family",
        }
        words = re.findall(r"[a-zA-Z]+", cleaned.lower())
        if words:
            english_word_count = sum(1 for w in words if w in english_markers)
            is_english = False
            if cleaned.lower().startswith(("the secret ", "stop saying ", "stop using ", "how to ")):
                is_english = True
            elif len(words) >= 3 and (english_word_count / len(words)) >= 0.4:
                is_english = True

            if is_english and expression:
                return expression

    return cleaned


def extract_thumbnail_title(state: Dict[str, Any]) -> str:
    """Extracts the title for a script from its state dictionary.
    Prioritizes content_metadata.script.title (or title from script_text),
    falling back to content_metadata.target_expression or prompt_params.EXPRESSION.
    Sanitizes against English leakage for Latin languages.
    """
    if not isinstance(state, dict):
        return "LEARN WITH TITO"

    content_meta = state.get("content_metadata")
    if not isinstance(content_meta, dict):
        content_meta = {}

    explicit_thumb_title = content_meta.get("thumbnail_title")
    if explicit_thumb_title and str(explicit_thumb_title).strip():
        return clean_thumbnail_title(str(explicit_thumb_title).strip(), strip_prefix=False)

    title = None
    script_obj = content_meta.get("script")
    if isinstance(script_obj, dict):
        t = script_obj.get("title") or script_obj.get("TITLE")
        if t and str(t).strip():
            title = str(t).strip()

    if not title and content_meta.get("title") and str(content_meta.get("title")).strip():
        title = str(content_meta["title"]).strip()

    if not title:
        script_text = state.get("script_text")
        if isinstance(script_text, str) and script_text.strip():
            raw = script_text.strip()
            if raw.startswith("{"):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        t = parsed.get("title") or parsed.get("TITLE")
                        if t and str(t).strip():
                            title = str(t).strip()
                except Exception:
                    pass

    prompt_params = state.get("prompt_params")
    if not isinstance(prompt_params, dict):
        prompt_params = {}

    expression = (
        content_meta.get("target_expression")
        or prompt_params.get("EXPRESSION")
        or content_meta.get("topic")
        or prompt_params.get("TOPIC")
        or ""
    )

    lang = ""
    try:
        from config import resolve_script_language
        lang = resolve_script_language(state)
    except Exception:
        lang = str(
            content_meta.get("language")
            or prompt_params.get("TARGET_LANGUAGE")
            or ""
        ).lower()

    if not title:
        title = (
            expression
            or state.get("metadata", {}).get("TITLE")
            or "LEARN WITH TITO"
        )

    sanitized = sanitize_thumbnail_title(str(title), lang=lang, expression=str(expression))
    return clean_thumbnail_title(sanitized)


def detect_chalkboard_bounds(img: Image.Image) -> Tuple[int, int, int, int]:
    """Detects the unobstructed inner green chalkboard rectangle (x1, y1, x2, y2)
    on legacy classroom templates or synthetic green canvases.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()

    def is_board_green(r: int, g: int, b: int) -> bool:
        return r < 45 and 38 <= g <= 92 and b < 60 and (g - r) >= 12

    y_probe = int(h * 0.35)
    x_min_scan = int(w * 0.12)
    x_max_scan = int(w * 0.88)

    green_xs = [
        x for x in range(x_min_scan, x_max_scan)
        if is_board_green(*px[x, y_probe])
    ]

    if len(green_xs) < int(w * 0.25):
        return (int(w * 0.18), int(h * 0.24), int(w * 0.82), int(h * 0.45))

    x_left = min(green_xs)
    x_right = max(green_xs)
    board_w = x_right - x_left

    inner_x1 = x_left + int(board_w * 0.12)
    inner_x2 = x_right - int(board_w * 0.12)
    sample_xs = list(range(inner_x1, inner_x2, max(1, (inner_x2 - inner_x1) // 40)))

    y_min_scan = int(h * 0.12)
    y_max_scan = int(h * 0.56)

    clean_ys: List[int] = []
    for y in range(y_min_scan, y_max_scan):
        green_count = sum(1 for x in sample_xs if is_board_green(*px[x, y]))
        if green_count >= len(sample_xs) * 0.96:
            clean_ys.append(y)

    if not clean_ys:
        return (
            x_left + int(board_w * 0.08),
            int(h * 0.24),
            x_right - int(board_w * 0.08),
            int(h * 0.45),
        )

    y_top = min(clean_ys)
    y_bottom = max(clean_ys)
    board_h = y_bottom - y_top

    pad_x = max(24, int(board_w * 0.065))
    pad_top = max(20, int(board_h * 0.065))
    pad_bottom = max(22, int(board_h * 0.075))

    return (
        x_left + pad_x,
        y_top + pad_top,
        x_right - pad_x,
        y_bottom - pad_bottom,
    )


def resolve_panel_bounds(img: Image.Image, category: Optional[str] = None) -> Tuple[int, int, int, int]:
    """Resolves the safe interior text box `(x1, y1, x2, y2)` in image pixel coordinates.

    Uses category-calibrated coordinates for all 4 Tito's LingoVerse master templates so colored
    gradients, bulbs, and frames never distort text placement; falls back to pixel detection when
    `category` is omitted (e.g. legacy single-template or synthetic unit tests).
    """
    style = get_category_thumbnail_style(category)
    if style is not None:
        w, h = img.size
        nx1, ny1, nx2, ny2 = style.safe_box
        return (
            int(round(w * nx1)),
            int(round(h * ny1)),
            int(round(w * nx2)),
            int(round(h * ny2)),
        )
    return detect_chalkboard_bounds(img)


def _resolve_font_path(font_filename: str = "segoeprb.ttf") -> Optional[Path]:
    windir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for candidate_name in (font_filename, "segoeprb.ttf", "arialbd.ttf"):
        candidate = windir / candidate_name
        if candidate.exists():
            return candidate
    return None


def _preferred_font_path() -> Optional[Path]:
    return _resolve_font_path("segoeprb.ttf")


def fit_thumbnail_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    max_h: int,
    font_file: Optional[Path] = None,
    *,
    strip_prefix: bool = True,
) -> Tuple[List[str], ImageFont.FreeTypeFont, int, int]:
    """Finds the largest readable font size and clean word wrapping so that
    `text` fits comfortably inside `(max_w, max_h)`.
    Returns (lines, font, font_size, line_height).
    """
    if font_file is None:
        font_file = _preferred_font_path()

    clean_text = clean_thumbnail_title(text, strip_prefix=strip_prefix)
    max_sz = max(62, min(116, int(max_h * 0.27)))
    min_sz = max(24, int(max_h * 0.08))

    for size in range(max_sz, min_sz - 1, -2):
        font = _get_font(font_file, size)
        line_h = int(size * 1.24)
        lines, cleanly_wrapped = wrap_words_to_width(clean_text, font, max_w, draw)
        if not lines or not cleanly_wrapped:
            continue
        last_bottom = draw.textbbox((0, 0), lines[-1], font=font)[3]
        shadow_off = max(2, min(5, size // 22))
        total_h = (len(lines) - 1) * line_h + max(line_h, last_bottom + shadow_off)
        if total_h <= max_h:
            if all((draw.textbbox((0, 0), ln, font=font)[2] - draw.textbbox((0, 0), ln, font=font)[0]) <= max_w for ln in lines):
                return lines, font, size, line_h

    font = _get_font(font_file, min_sz)
    line_h = int(min_sz * 1.24)
    lines, _ = wrap_words_to_width(clean_text, font, max_w, draw)
    return lines, font, min_sz, line_h


def _draw_centered_line(
    draw: ImageDraw.ImageDraw,
    line: str,
    center_x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    shadow_fill: Tuple[int, int, int, int],
    shadow_offset: int,
    bounds: Tuple[int, int, int, int],
) -> int:
    """Draws a centered line with drop shadow, strictly clamped inside horizontal bounds."""
    x1, _y1, x2, _y2 = bounds
    bbox = draw.textbbox((0, 0), line, font=font)
    lw = bbox[2] - bbox[0]
    lx = center_x - (bbox[0] + bbox[2]) // 2
    lx = max(x1 - bbox[0], min(x2 - bbox[2] - shadow_offset, lx))
    draw.text((lx + shadow_offset, y + shadow_offset), line, font=font, fill=shadow_fill)
    draw.text((lx, y), line, font=font, fill=fill)
    return lw


def render_thumbnail_chalkboard(
    reference_image_path: Path,
    title_text: str,
    dest_path: Path,
    target_size: Tuple[int, int] = (576, 1024),
    category: Optional[str] = None,
    *,
    strip_prefix: bool = True,
) -> Path:
    """Renders high-resolution typography of the expression/script title strictly within
    the template's designated empty central panel, preserving all artwork intact.
    """
    if not reference_image_path.exists():
        raise FileNotFoundError(f"Thumbnail model image not found: {reference_image_path}")

    base = Image.open(str(reference_image_path)).convert("RGBA")
    draw = ImageDraw.Draw(base)
    w, h = base.size

    style = get_category_thumbnail_style(category)
    x1, y1, x2, y2 = resolve_panel_bounds(base, category=category)
    bounds = (x1, y1, x2, y2)
    max_w = max(100, x2 - x1)
    max_h = max(80, y2 - y1)
    center_x = (x1 + x2) // 2

    if style is not None:
        font_file = _resolve_font_path(style.font_filename)
        main_color = style.main_color
        header_color = style.header_color
        shadow_color = style.shadow_color
        divider_color = style.divider_color
    else:
        font_file = _preferred_font_path()
        main_color = (255, 238, 140, 255)
        header_color = (250, 250, 245, 255)
        shadow_color = (8, 28, 14, 170)
        divider_color = (255, 255, 255, 135)

    div_line_w = max(3, int(h * 0.0028))
    clean_title = clean_thumbnail_title(title_text, strip_prefix=strip_prefix)

    if ":" in clean_title:
        parts = clean_title.split(":", 1)
        top_part = parts[0].strip()
        bottom_part = parts[1].strip()
    else:
        top_part = ""
        bottom_part = clean_title

    if top_part and bottom_part:
        best_layout = None
        max_main = max(56, min(104, int(max_h * 0.25)))
        min_main = max(22, int(max_h * 0.08))
        for main_size in range(max_main, min_main - 1, -2):
            sub_size = max(20, int(main_size * 0.80))
            font_top = _get_font(font_file, sub_size)
            font_bot = _get_font(font_file, main_size)
            lh_top = int(sub_size * 1.22)
            lh_bot = int(main_size * 1.24)

            top_lines, top_clean = wrap_words_to_width(top_part, font_top, max_w, draw)
            bot_lines, bot_clean = wrap_words_to_width(bottom_part, font_bot, max_w, draw)

            if not (top_clean and bot_clean and top_lines and bot_lines):
                continue

            gap_above_div = max(12, int(main_size * 0.30))
            gap_below_div = max(12, int(main_size * 0.28))
            last_top_bottom_rel = (len(top_lines) - 1) * lh_top + draw.textbbox((0, 0), top_lines[-1], font=font_top)[3]
            div_rel_y = max(
                len(top_lines) * lh_top + gap_above_div // 2,
                last_top_bottom_rel + max(10, gap_above_div // 2),
            )
            bot_start_rel = div_rel_y + gap_below_div
            bot_shadow = max(2, min(5, main_size // 22))
            last_bot_bottom = draw.textbbox((0, 0), bot_lines[-1], font=font_bot)[3]
            total_h = bot_start_rel + (len(bot_lines) - 1) * lh_bot + last_bot_bottom + bot_shadow

            if total_h <= max_h:
                best_layout = (
                    top_lines,
                    font_top,
                    lh_top,
                    bot_lines,
                    font_bot,
                    lh_bot,
                    sub_size,
                    main_size,
                    div_rel_y,
                    bot_start_rel,
                    total_h,
                )
                break

        if best_layout is not None:
            (
                top_lines,
                font_top,
                lh_top,
                bot_lines,
                font_bot,
                lh_bot,
                sub_size,
                main_size,
                div_rel_y,
                bot_start_rel,
                total_h,
            ) = best_layout
            start_y = max(y1, y1 + (max_h - total_h) // 2)
            top_shadow = max(2, min(4, sub_size // 24))
            bot_shadow = max(2, min(5, main_size // 22))

            curr_y = start_y
            for line in top_lines:
                _draw_centered_line(
                    draw, line, center_x, curr_y, font_top,
                    header_color, shadow_color, top_shadow, bounds,
                )
                curr_y += lh_top

            div_y = start_y + div_rel_y
            div_w = min(max_w - 20, max(180, int(max_w * 0.68)))
            draw.line(
                [(center_x - div_w // 2, div_y), (center_x + div_w // 2, div_y)],
                fill=divider_color,
                width=div_line_w,
            )

            curr_y = start_y + bot_start_rel
            for line in bot_lines:
                _draw_centered_line(
                    draw, line, center_x, curr_y, font_bot,
                    main_color, shadow_color, bot_shadow, bounds,
                )
                curr_y += lh_bot

            final_img = base.resize(target_size, Image.Resampling.LANCZOS)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            final_img.save(str(dest_path))
            return dest_path

    # Single-block centered layout with subtle decorative accent underline
    underline_space = max(22, int(max_h * 0.11))
    lines, font, size, line_h = fit_thumbnail_text(
        draw, clean_title, max_w, max(60, max_h - underline_space), font_file=font_file, strip_prefix=strip_prefix
    )
    shadow_off = max(2, min(5, size // 22))
    last_bottom_rel = (len(lines) - 1) * line_h + draw.textbbox((0, 0), lines[-1], font=font)[3] + shadow_off
    total_block_h = min(max_h, max(len(lines) * line_h, last_bottom_rel) + underline_space)
    start_y = max(y1, y1 + (max_h - total_block_h) // 2)
    curr_y = start_y

    max_line_w = 0
    for line in lines:
        lw = _draw_centered_line(
            draw, line, center_x, curr_y, font,
            main_color, shadow_color, shadow_off, bounds,
        )
        max_line_w = max(max_line_w, lw)
        curr_y += line_h

    ul_y = min(y2 - div_line_w - 2, max(curr_y + 10, start_y + last_bottom_rel + 10))
    ul_w = min(max_w - 20, max(140, int(max_line_w * 0.75)))
    draw.line(
        [(center_x - ul_w // 2, ul_y), (center_x + ul_w // 2, ul_y)],
        fill=divider_color,
        width=div_line_w,
    )

    final_img = base.resize(target_size, Image.Resampling.LANCZOS)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(str(dest_path))
    return dest_path


render_thumbnail = render_thumbnail_chalkboard
