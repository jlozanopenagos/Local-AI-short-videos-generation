import os
import re
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple
# pyrefly: ignore [missing-import]
from PIL import Image, ImageDraw, ImageFont


def parse_quiz_exercise(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Extracts question text and list of (option_letter, option_text) pairs.
    Handles both multi-line formatting and single-line inline formatting (A) ... B) ...).
    """
    clean_text = text.strip()
    # Split by option markers like 'A)', 'A.', 'A:', 'A -'
    parts = re.split(r"(?=(?:^|\s)[A-D][\)\.:\-]\s+)", clean_text)
    
    question = parts[0].strip()
    options: List[Tuple[str, str]] = []
    
    for p in parts[1:]:
        p_clean = p.strip()
        m = re.match(r"^([A-D])[\)\.:\-]\s*(.*)$", p_clean, flags=re.DOTALL)
        if m:
            letter = m.group(1).upper()
            opt_text = m.group(2).strip().rstrip("?").strip()
            options.append((letter, opt_text))
            
    # Fallback if no structured options were detected
    if not options:
        options = [
            ("A", "Option A"),
            ("B", "Option B"),
            ("C", "Option C"),
            ("D", "Option D")
        ]
        
    return question, options


def _get_font_candidates() -> List[Path]:
    """Returns candidate chalkboard handwriting font paths based on OS."""
    candidates = []
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates.extend([
        windir / "Fonts" / "segoeprb.ttf",
        windir / "Fonts" / "segoepr.ttf",
        windir / "Fonts" / "Inkfree.ttf",
        windir / "Fonts" / "comicbd.ttf",
        windir / "Fonts" / "comic.ttf",
        windir / "Fonts" / "arialbd.ttf"
    ])
    # Linux / macOS font paths
    candidates.extend([
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/Library/Fonts/Comic Sans MS.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc")
    ])
    return candidates


def _get_font(font_path: Optional[Path], size: int) -> ImageFont.FreeTypeFont:
    """Safely loads a FreeType font with fallbacks."""
    if font_path and font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass
            
    # System font fallbacks
    for fallback in _get_font_candidates():
        if fallback.exists():
            try:
                return ImageFont.truetype(str(fallback), size)
            except Exception:
                continue
                
    return ImageFont.load_default()


def render_chalkboard_image(
    empty_chalkboard_path: Path,
    exercise_text: str,
    dest_path: Path,
    target_size: Tuple[int, int] = (576, 1024)
) -> Path:
    """Renders high-resolution chalk typography directly onto empty_chalkboard.png.
    Produces zero spelling errors, crystal-clear readability, and authentic chalkboard styling.
    """
    if not empty_chalkboard_path.exists():
        raise FileNotFoundError(f"Chalkboard template not found: {empty_chalkboard_path}")
        
    base = Image.open(str(empty_chalkboard_path)).convert("RGBA")
    draw = ImageDraw.Draw(base)
    w, h = base.size

    question, options = parse_quiz_exercise(exercise_text)

    # Primary font: Segoe Print Bold or best available handwritten font
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    preferred_font = windir / "Fonts" / "segoeprb.ttf"
    font_file = preferred_font if preferred_font.exists() else None
    font_q = _get_font(font_file, 48)
    font_badge = _get_font(font_file, 44)
    font_opt = _get_font(font_file, 40)

    # Line wrap question (22-26 chars depending on length)
    wrap_width = 24 if len(question) < 75 else 28
    lines = textwrap.wrap(question, width=wrap_width)
    q_line_h = 66
    total_q_h = len(lines) * q_line_h

    # Option boxes layout
    box_w = 750
    box_h = 96
    box_spacing = 28
    total_opts_h = len(options) * box_h + (len(options) - 1) * box_spacing
    divider_gap = 40

    total_content_h = total_q_h + divider_gap + total_opts_h
    # Optical center on the board, accounting for the lower chalk tray
    start_y = max(180, (h - total_content_h) // 2 - 35)

    y = start_y

    # Chalk colors
    chalk_yellow = (255, 238, 140, 255)
    chalk_white = (250, 250, 245, 255)

    # 1. Render Question
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_q)
        lw = bbox[2] - bbox[0]
        draw.text(((w - lw) // 2, y), line, font=font_q, fill=chalk_yellow)
        y += q_line_h

    y += 10
    # 2. Render Decorative Chalk Divider Line
    div_w = 680
    draw.line([((w - div_w) // 2, y), ((w + div_w) // 2, y)], fill=(255, 255, 255, 120), width=3)
    y += 35

    # 3. Render Option Boxes
    box_x1 = (w - box_w) // 2
    box_x2 = box_x1 + box_w
    badge_w = 70

    for letter, opt_text in options:
        # Translucent dark-green chalk box with rounded corners
        draw.rounded_rectangle(
            [box_x1, y, box_x2, y + box_h],
            radius=18,
            outline=(255, 255, 255, 150),
            width=2,
            fill=(0, 32, 16, 120)
        )
        
        # Chalk-yellow letter badge
        draw.rounded_rectangle(
            [box_x1 + 10, y + 10, box_x1 + 10 + badge_w, y + box_h - 10],
            radius=12,
            fill=(255, 235, 120, 230)
        )
        
        # Letter text inside badge
        l_bbox = draw.textbbox((0, 0), letter, font=font_badge)
        lw = l_bbox[2] - l_bbox[0]
        lh = l_bbox[3] - l_bbox[1]
        draw.text(
            (box_x1 + 10 + (badge_w - lw) // 2, y + 10 + (box_h - 20 - lh) // 2 - 4),
            letter,
            font=font_badge,
            fill=(15, 35, 15, 255)
        )
        
        # Option text (dynamically truncate or scale if extraordinarily long)
        if len(opt_text) > 34:
            font_opt_dynamic = _get_font(font_file, 34)
        else:
            font_opt_dynamic = font_opt
            
        t_bbox = draw.textbbox((0, 0), opt_text, font=font_opt_dynamic)
        th = t_bbox[3] - t_bbox[1]
        draw.text(
            (box_x1 + badge_w + 28, y + (box_h - th) // 2 - 6),
            opt_text,
            font=font_opt_dynamic,
            fill=chalk_white
        )
        
        y += box_h + box_spacing

    # Resize to video resolution using high-quality Lanczos resampling
    final_img = base.resize(target_size, Image.Resampling.LANCZOS)
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(str(dest_path))
    return dest_path
