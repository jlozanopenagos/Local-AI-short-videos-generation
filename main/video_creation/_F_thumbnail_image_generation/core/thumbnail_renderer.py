import json
import os
import re
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


def clean_thumbnail_title(text: str) -> str:
    """Cleans up a script title or expression for chalkboard display.
    Fixes unmatched single/double quotes and normalizes whitespace while
    preserving intentional stress capitalization (e.g. REcord vs reCORD).
    """
    if not text:
        return "LEARN WITH TITO"

    cleaned = re.sub(r"\s+", " ", str(text)).strip()

    # Strip wrapping outer quotes if the entire title is enclosed in quotes
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()

    # Fix trailing unmatched single quote in phrases like: The Secret to Saying 'Piece of Cake
    single_quotes = cleaned.count("'")
    if single_quotes >= 1:
        # Count apostrophes inside words (e.g. Don't, It's, C'est, l'Europe)
        word_apostrophes = len(re.findall(r"\w'\w", cleaned))
        unpaired_quotes = single_quotes - word_apostrophes
        if unpaired_quotes == 1 and not cleaned.endswith("'"):
            # If there is an opening quote like 'Piece of Cake at the end, close it
            if re.search(r"(?:^|\s)'[^']+$", cleaned):
                cleaned = cleaned + "'"

    if cleaned.count('"') == 1 and not cleaned.endswith('"'):
        if re.search(r'(?:^|\s)"[^"]+$', cleaned):
            cleaned = cleaned + '"'

    return cleaned or "LEARN WITH TITO"


def extract_thumbnail_title(state: Dict[str, Any]) -> str:
    """Extracts the chalkboard title for a script from its state dictionary.
    Prioritizes content_metadata.script.title (or title from script_text),
    falling back to content_metadata.target_expression or prompt_params.EXPRESSION.
    """
    if not isinstance(state, dict):
        return "LEARN WITH TITO"

    content_meta = state.get("content_metadata")
    if not isinstance(content_meta, dict):
        content_meta = {}

    script_obj = content_meta.get("script")
    if isinstance(script_obj, dict):
        title = script_obj.get("title") or script_obj.get("TITLE")
        if title and str(title).strip():
            return clean_thumbnail_title(str(title))

    if content_meta.get("title") and str(content_meta.get("title")).strip():
        return clean_thumbnail_title(str(content_meta["title"]))

    # Try parsing script_text JSON if present
    script_text = state.get("script_text")
    if isinstance(script_text, str) and script_text.strip():
        raw = script_text.strip()
        if raw.startswith("{"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    t = parsed.get("title") or parsed.get("TITLE")
                    if t and str(t).strip():
                        return clean_thumbnail_title(str(t))
            except Exception:
                pass

    # Fallback to target_expression / EXPRESSION / TOPIC
    prompt_params = state.get("prompt_params")
    if not isinstance(prompt_params, dict):
        prompt_params = {}

    fallback = (
        content_meta.get("target_expression")
        or prompt_params.get("EXPRESSION")
        or content_meta.get("topic")
        or prompt_params.get("TOPIC")
        or state.get("metadata", {}).get("TITLE")
        or "LEARN WITH TITO"
    )
    return clean_thumbnail_title(str(fallback))


def detect_chalkboard_bounds(img: Image.Image) -> Tuple[int, int, int, int]:
    """Detects the unobstructed inner green chalkboard rectangle (x1, y1, x2, y2)
    on a Tito thumbnail model image (or full chalkboard image) above Tito's ears/beret.
    Uses pure PIL pixel access with safe inner margins.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()

    def is_board_green(r: int, g: int, b: int) -> bool:
        return r < 45 and 38 <= g <= 92 and b < 60 and (g - r) >= 12

    # 1. Sample horizontal row near vertical center of the upper chalkboard (y = 35% of height)
    y_probe = int(h * 0.35)
    x_min_scan = int(w * 0.12)
    x_max_scan = int(w * 0.88)

    green_xs = [
        x for x in range(x_min_scan, x_max_scan)
        if is_board_green(*px[x, y_probe])
    ]

    if len(green_xs) < int(w * 0.25):
        # Fallback bounds if custom/synthetic image without standard green board
        return (int(w * 0.18), int(h * 0.24), int(w * 0.82), int(h * 0.45))

    x_left = min(green_xs)
    x_right = max(green_xs)
    board_w = x_right - x_left

    # 2. Scan rows vertically across the inner 76% of the board width (avoiding rounded corners)
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

    # Apply comfortable inner padding so text never touches the wooden frame or Tito's ears/beret
    pad_x = max(24, int(board_w * 0.065))
    pad_top = max(20, int(board_h * 0.065))
    pad_bottom = max(22, int(board_h * 0.075))

    return (
        x_left + pad_x,
        y_top + pad_top,
        x_right - pad_x,
        y_bottom - pad_bottom,
    )


def _preferred_font_path() -> Optional[Path]:
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    preferred = windir / "Fonts" / "segoeprb.ttf"
    return preferred if preferred.exists() else None


def fit_thumbnail_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    max_h: int,
    font_file: Optional[Path] = None,
) -> Tuple[List[str], ImageFont.FreeTypeFont, int, int]:
    """Finds the largest readable font size and clean word wrapping so that
    `text` fits comfortably inside `(max_w, max_h)`.
    Returns (lines, font, font_size, line_height).
    """
    if font_file is None:
        font_file = _preferred_font_path()

    clean_text = clean_thumbnail_title(text)

    for size in range(62, 23, -2):
        font = _get_font(font_file, size)
        line_h = int(size * 1.26)
        lines, cleanly_wrapped = wrap_words_to_width(clean_text, font, max_w, draw)
        total_h = len(lines) * line_h
        if cleanly_wrapped and total_h <= max_h:
            # Verify every line width is strictly <= max_w
            if all((draw.textbbox((0, 0), ln, font=font)[2] - draw.textbbox((0, 0), ln, font=font)[0]) <= max_w for ln in lines):
                return lines, font, size, line_h

    # Fallback smallest size
    font = _get_font(font_file, 24)
    line_h = int(24 * 1.25)
    lines, _ = wrap_words_to_width(clean_text, font, max_w, draw)
    return lines, font, 24, line_h


def render_thumbnail_chalkboard(
    reference_image_path: Path,
    title_text: str,
    dest_path: Path,
    target_size: Tuple[int, int] = (576, 1024),
) -> Path:
    """Renders high-resolution chalk typography of the expression/script title
    directly onto the chalkboard area of the language thumbnail model image.
    """
    if not reference_image_path.exists():
        raise FileNotFoundError(f"Thumbnail model image not found: {reference_image_path}")

    base = Image.open(str(reference_image_path)).convert("RGBA")
    draw = ImageDraw.Draw(base)

    x1, y1, x2, y2 = detect_chalkboard_bounds(base)
    max_w = max(100, x2 - x1)
    max_h = max(80, y2 - y1)
    center_x = (x1 + x2) // 2

    font_file = _preferred_font_path()
    clean_title = clean_thumbnail_title(title_text)

    chalk_yellow = (255, 238, 140, 255)
    chalk_white = (250, 250, 245, 255)
    chalk_shadow = (8, 28, 14, 170)
    divider_color = (255, 255, 255, 135)

    # Check if title naturally splits into two parts via ':'
    if ":" in clean_title:
        parts = clean_title.split(":", 1)
        top_part = parts[0].strip()
        bottom_part = parts[1].strip()
    else:
        top_part = ""
        bottom_part = clean_title

    if top_part and bottom_part:
        # Fit two-part layout (Header + Divider + Focus Phrase)
        best_layout = None
        for main_size in range(56, 25, -2):
            sub_size = max(24, int(main_size * 0.82))
            font_top = _get_font(font_file, sub_size)
            font_bot = _get_font(font_file, main_size)
            lh_top = int(sub_size * 1.24)
            lh_bot = int(main_size * 1.26)

            top_lines, top_clean = wrap_words_to_width(top_part, font_top, max_w, draw)
            bot_lines, bot_clean = wrap_words_to_width(bottom_part, font_bot, max_w, draw)

            if not (top_clean and bot_clean):
                continue

            gap_above_div = max(18, int(main_size * 0.36))
            gap_below_div = max(16, int(main_size * 0.32))
            divider_gap = gap_above_div + gap_below_div
            total_h = (len(top_lines) * lh_top) + divider_gap + (len(bot_lines) * lh_bot)
            if total_h <= max_h:
                best_layout = (
                    top_lines,
                    font_top,
                    lh_top,
                    bot_lines,
                    font_bot,
                    lh_bot,
                    gap_above_div,
                    gap_below_div,
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
                gap_above_div,
                gap_below_div,
                total_h,
            ) = best_layout
            curr_y = y1 + (max_h - total_h) // 2

            max_line_w = 0
            last_top_bottom = curr_y
            for line in top_lines:
                bbox = draw.textbbox((0, 0), line, font=font_top)
                lw = bbox[2] - bbox[0]
                max_line_w = max(max_line_w, lw)
                lx = center_x - lw // 2
                draw.text((lx + 2, curr_y + 2), line, font=font_top, fill=chalk_shadow)
                draw.text((lx, curr_y), line, font=font_top, fill=chalk_white)
                last_top_bottom = curr_y + bbox[3]
                curr_y += lh_top

            # Chalk divider line centered visually between top text descenders and bottom text ascenders
            div_y = max(curr_y + gap_above_div // 2, last_top_bottom + 12)
            div_w = min(max_w - 20, max(180, int(max_w * 0.68)))
            draw.line(
                [(center_x - div_w // 2, div_y), (center_x + div_w // 2, div_y)],
                fill=divider_color,
                width=3,
            )
            curr_y = div_y + gap_below_div

            for line in bot_lines:
                bbox = draw.textbbox((0, 0), line, font=font_bot)
                lw = bbox[2] - bbox[0]
                max_line_w = max(max_line_w, lw)
                lx = center_x - lw // 2
                draw.text((lx + 2, curr_y + 2), line, font=font_bot, fill=chalk_shadow)
                draw.text((lx, curr_y), line, font=font_bot, fill=chalk_yellow)
                curr_y += lh_bot

            final_img = base.resize(target_size, Image.Resampling.LANCZOS)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            final_img.save(str(dest_path))
            return dest_path

    # Single-block centered layout with decorative chalk underline
    underline_space = 22
    lines, font, size, line_h = fit_thumbnail_text(
        draw, clean_title, max_w, max_h - underline_space, font_file=font_file
    )
    total_text_h = len(lines) * line_h
    total_block_h = total_text_h + underline_space
    curr_y = y1 + (max_h - total_block_h) // 2

    max_line_w = 0
    last_line_bottom = curr_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        max_line_w = max(max_line_w, lw)
        lx = center_x - lw // 2
        draw.text((lx + 2, curr_y + 2), line, font=font, fill=chalk_shadow)
        draw.text((lx, curr_y), line, font=font, fill=chalk_yellow)
        last_line_bottom = curr_y + bbox[3]
        curr_y += line_h

    # Subtle decorative chalk underline beneath the title block
    ul_y = max(curr_y + 10, last_line_bottom + 14)
    ul_w = min(max_w - 20, max(140, int(max_line_w * 0.75)))
    draw.line(
        [(center_x - ul_w // 2, ul_y), (center_x + ul_w // 2, ul_y)],
        fill=divider_color,
        width=3,
    )

    final_img = base.resize(target_size, Image.Resampling.LANCZOS)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(str(dest_path))
    return dest_path
