import os
import re
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple
# pyrefly: ignore [missing-import]
from PIL import Image, ImageDraw, ImageFont


def clean_option_text(text: str) -> str:
    """Isolates and cleans option text by stripping trailing/leading commas, semicolons,
    and coordinating conjunctions (e.g. ', or', 'or', ', and', ', o', ', ou', ', e').
    Preserves meaningful ending punctuation like '?' and '!'.
    """
    opt = text.strip()
    
    # 1. Remove leading conjunctions if accidentally captured: e.g. "or Break a leg!" -> "Break a leg!"
    opt = re.sub(r"^(?:or|and|o|ou|y|e|u|ed|et)\s+", "", opt, flags=re.IGNORECASE)
    
    # 2. Remove trailing conjunctions (with optional preceding punctuation/whitespace):
    # e.g. "Are you ready to win.?, or" -> "Are you ready to win.?"
    # e.g. "You have a great show, or" -> "You have a great show"
    opt = re.sub(r"(?:[,;]\s*|\s+)\b(?:or|and|o|ou|y|e|u|ed|et)\b[\s\.,;]*$", "", opt, flags=re.IGNORECASE)
    
    # 3. Clean up awkward punctuation combinations at the end of the option
    opt = re.sub(r",\s*\.$", ".", opt)  # ",." -> "."
    opt = re.sub(r"\.\s*,$", ".", opt)  # ".," -> "."
    opt = re.sub(r"\?\s*,$", "?", opt)  # "?," -> "?"
    opt = re.sub(r"!\s*,$", "!", opt)   # "!," -> "!"
    
    # 4. Remove lingering trailing commas or semicolons
    opt = re.sub(r"[\s,;]+$", "", opt)
    
    # 5. Clean up extra whitespace
    return re.sub(r"\s+", " ", opt).strip()


def mask_revealed_answer_in_question(question: str, options: List[Tuple[str, str]]) -> str:
    """If the question is a listening/identification challenge and reveals the answer
    in the test sentence without a blank, replaces the revealed phrase with '_________'.
    """
    # 1. If question already has a blank (e.g. '___', '_________'), do not modify
    if re.search(r"_{2,}", question):
        return question

    # 2. Check if this is a listening/identification game
    listening_pattern = re.compile(
        r"\b(which\s+(?:rhythm|word|phrase|version|option|stress|pronunciation|sound)|"
        r"what\s+did\s+you\s+hear|"
        r"did\s+you\s+(?:hear|get)|"
        r"listen(?:\s+closely|\s+carefully)?|"
        r"which\s+did\s+you\s+hear|"
        r"escucha\s+bien|"
        r"cu[aá]l\s+(?:palabra|opci[oó]n|ritmo)?\s*(?:has\s+)?(?:escuchaste|o[ií]ste|se\s+escucha)|"
        r"qu[\x27\’]?avez-vous\s+entendu|"
        r"avez-vous\s+entendu|"
        r"hai\s+sentito|"
        r"ascolta\s+bene)\b",
        re.IGNORECASE
    )
    
    m_listen = listening_pattern.search(question)
    if not m_listen:
        return question

    # Split question into test sentence (before the prompt) and listening prompt (from the match)
    test_sentence = question[:m_listen.start()]
    prompt_suffix = question[m_listen.start():]

    if not test_sentence.strip():
        return question

    # Look for any option (or option with leading dummy pronouns/verbs) in test_sentence
    sorted_opts = sorted([opt_text for _, opt_text in options], key=len, reverse=True)

    for opt in sorted_opts:
        clean_opt = re.sub(r"^[\s'\"\(]+|[\s'\"\)\.,!\?]+$", "", opt).strip()
        if not clean_opt or len(clean_opt) < 2:
            continue

        opt_escaped = re.escape(clean_opt)
        core_opt = re.sub(r"^(?:a|an|the|to|un|una|el|la|los|las|le|les|des|du|il|lo|gli)\s+", "", clean_opt, flags=re.IGNORECASE).strip()
        core_escaped = re.escape(core_opt) if core_opt and len(core_opt) >= 3 else opt_escaped

        pattern = re.compile(
            rf"(?:(?:it\s+(?:was|is)|c[\x27\’]est|es|è)\s+)?\b(?:{opt_escaped}|{core_escaped})\b",
            re.IGNORECASE
        )

        m_found = pattern.search(test_sentence)
        if m_found:
            test_sentence_masked = test_sentence[:m_found.start()] + "_________" + test_sentence[m_found.end():]
            test_sentence_masked = re.sub(r"\s+([.,!?;:])", r"\1", test_sentence_masked)
            test_sentence_masked = re.sub(r"\s+", " ", test_sentence_masked).strip()
            return f"{test_sentence_masked} {prompt_suffix.strip()}"

    return question


def parse_quiz_exercise(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Extracts question text and list of (option_letter, option_text) pairs.
    Handles both multi-line formatting and single-line inline formatting (A) ... B) ...).
    Isolates options cleanly without trailing commas or conjunctions ('or', 'and', etc.).
    Automatically masks revealed answers in listening games with '_________'.
    """
    clean_text = text.strip()
    # Split by option markers, optionally preceded by coordinating conjunctions (or, and, o, ou, etc.)
    parts = re.split(
        r"(?=(?:^|\s)(?:(?:or|and|o|ou|y|e|u|ed|et)\s+)?[A-D][\)\.:\-]\s+)",
        clean_text,
        flags=re.IGNORECASE
    )
    
    question = parts[0].strip()
    # Clean question trailing conjunctions and messy punctuation like '?.'
    question = re.sub(r"(?:[,;]\s*|\s+)\b(?:or|and|o|ou|y|e|u|ed|et)\b[\s\.,;]*$", "", question, flags=re.IGNORECASE)
    question = re.sub(r"[\?,!]\s*\.", lambda m: m.group(0)[0], question)
    question = re.sub(r"[\s,;]+$", "", question)
    
    options: List[Tuple[str, str]] = []
    
    for p in parts[1:]:
        p_clean = p.strip()
        m = re.match(
            r"^(?:(?:or|and|o|ou|y|e|u|ed|et)\s+)?([A-D])[\)\.:\-]\s*(.*)$",
            p_clean,
            flags=re.IGNORECASE | re.DOTALL
        )
        if m:
            letter = m.group(1).upper()
            opt_text = clean_option_text(m.group(2))
            if opt_text:
                options.append((letter, opt_text))
            
    # Fallback if no structured options were detected
    if not options:
        options = [
            ("A", "Option A"),
            ("B", "Option B"),
            ("C", "Option C"),
            ("D", "Option D")
        ]

    # Automatically mask revealed answer if this is a listening/identification game
    question = mask_revealed_answer_in_question(question, options)
        
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


def wrap_words_to_width(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int,
    draw: ImageDraw.ImageDraw
) -> Tuple[List[str], bool]:
    """Wraps text into lines that each fit within max_w pixels using font metrics.
    Preserves explicit line breaks. Handles overly long individual words safely.
    Returns (lines, cleanly_wrapped).
    """
    clean = text.strip()
    if not clean:
        return [""], True

    result_lines: List[str] = []
    cleanly_wrapped = True

    paragraphs = clean.splitlines() or [clean]
    for para in paragraphs:
        words = para.split()
        if not words:
            continue
        cur_line: List[str] = []
        for word in words:
            test_line = " ".join(cur_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_w = bbox[2] - bbox[0]
            if line_w <= max_w:
                cur_line.append(word)
            else:
                if cur_line:
                    result_lines.append(" ".join(cur_line))
                    cur_line = []
                w_bbox = draw.textbbox((0, 0), word, font=font)
                if (w_bbox[2] - w_bbox[0]) <= max_w:
                    cur_line = [word]
                else:
                    # Single word is wider than max_w; split word by characters
                    cleanly_wrapped = False
                    partial = ""
                    for ch in word:
                        test_partial = partial + ch
                        p_bbox = draw.textbbox((0, 0), test_partial, font=font)
                        if (p_bbox[2] - p_bbox[0]) <= max_w:
                            partial = test_partial
                        else:
                            if partial:
                                result_lines.append(partial)
                            partial = ch
                    if partial:
                        cur_line = [partial]
        if cur_line:
            result_lines.append(" ".join(cur_line))

    return result_lines or [clean], cleanly_wrapped


def fit_option_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    font_file: Optional[Path]
) -> Tuple[List[str], ImageFont.FreeTypeFont, int, int]:
    """Finds the optimal font size and line wrapping so that option text fits cleanly within max_w.
    Prefers 1 line with font size 40 -> 30, then 2 lines with size 32 -> 24, then 3 lines 24 -> 18.
    Returns (wrapped_lines, font, font_size, line_height).
    """
    # 1. Try single line: font size 40 down to 30
    for size in range(40, 29, -2):
        font = _get_font(font_file, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return [text], font, size, int(size * 1.25)

    # 2. Try 2 lines: font size 32 down to 24
    for size in range(32, 23, -2):
        font = _get_font(font_file, size)
        lines, clean = wrap_words_to_width(text, font, max_w, draw)
        if clean and len(lines) <= 2:
            return lines, font, size, int(size * 1.22)

    # 3. Try 3 lines: font size 24 down to 18
    for size in range(24, 17, -2):
        font = _get_font(font_file, size)
        lines, clean = wrap_words_to_width(text, font, max_w, draw)
        if clean and len(lines) <= 3:
            return lines, font, size, int(size * 1.2)

    # 4. Fallback: size 18, as many lines as necessary
    font = _get_font(font_file, 18)
    lines, _ = wrap_words_to_width(text, font, max_w, draw)
    return lines, font, 18, 22


def render_chalkboard_image(
    empty_chalkboard_path: Path,
    exercise_text: str,
    dest_path: Path,
    target_size: Tuple[int, int] = (576, 1024)
) -> Path:
    """Renders high-resolution chalk typography directly onto empty_chalkboard.png.
    Produces zero spelling errors, crystal-clear readability, and authentic chalkboard styling.
    Dynamically scales and wraps options to ensure they always fit inside their text boxes.
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

    # Line wrap question preserving manual linebreaks and using dynamic sizing for long questions
    wrap_width = 24 if len(question) < 75 else 28
    lines = []
    for raw_l in question.splitlines():
        raw_clean = raw_l.strip()
        if raw_clean:
            lines.extend(textwrap.wrap(raw_clean, width=wrap_width))
    if not lines:
        lines = [question]

    q_font_size = 42 if len(lines) >= 5 else 48
    q_line_h = 58 if len(lines) >= 5 else 66
    font_q = _get_font(font_file, q_font_size)
    font_badge = _get_font(font_file, 44)
    total_q_h = len(lines) * q_line_h

    # Option boxes layout
    box_w = 750
    box_x1 = (w - box_w) // 2
    box_x2 = box_x1 + box_w
    badge_w = 70
    text_start_x = box_x1 + badge_w + 24
    max_text_w = box_x2 - text_start_x - 20

    # Fit all options within the box boundaries
    fitted_opts = []
    max_lines_needed = 1
    min_font_size = 40
    for letter, opt_text in options:
        opt_lines, opt_font, opt_size, opt_line_h = fit_option_text(draw, opt_text, max_text_w, font_file)
        fitted_opts.append((letter, opt_text, opt_lines, opt_font, opt_size, opt_line_h))
        if len(opt_lines) > max_lines_needed:
            max_lines_needed = len(opt_lines)
        if opt_size < min_font_size:
            min_font_size = opt_size

    # Harmonize font sizes: if any option needed multi-line, cap single-line options
    # so they don't look excessively large compared to multi-line siblings
    harmonized_opts = []
    for letter, opt_text, opt_lines, opt_font, opt_size, opt_line_h in fitted_opts:
        if len(opt_lines) == 1 and max_lines_needed >= 2 and opt_size > min_font_size + 6:
            harmonized_size = min_font_size + 6
            h_font = _get_font(font_file, harmonized_size)
            harmonized_opts.append((letter, opt_lines, h_font, harmonized_size, int(harmonized_size * 1.25)))
        else:
            harmonized_opts.append((letter, opt_lines, opt_font, opt_size, opt_line_h))

    # Box height adapts to maximum lines needed across options
    if max_lines_needed >= 3:
        box_h = 126
    elif max_lines_needed == 2:
        box_h = 112
    else:
        box_h = 96

    box_spacing = 24 if (len(options) >= 4 or max_lines_needed >= 3) else 28
    total_opts_h = len(options) * box_h + (len(options) - 1) * box_spacing
    divider_gap = 36 if max_lines_needed > 1 else 40

    total_content_h = total_q_h + divider_gap + total_opts_h
    # Optical center on the board, accounting for the lower chalk tray
    start_y = max(160, (h - total_content_h) // 2 - 30)

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
    y += divider_gap - 10

    # 3. Render Option Boxes
    for letter, opt_lines, opt_font, opt_size, opt_line_h in harmonized_opts:
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
        
        # Letter text inside badge (centered vertically and horizontally)
        l_bbox = draw.textbbox((0, 0), letter, font=font_badge)
        lw = l_bbox[2] - l_bbox[0]
        lh = l_bbox[3] - l_bbox[1]
        draw.text(
            (box_x1 + 10 + (badge_w - lw) // 2, y + 10 + (box_h - 20 - lh) // 2 - 4),
            letter,
            font=font_badge,
            fill=(15, 35, 15, 255)
        )
        
        # Render option text lines (vertically centered inside box)
        text_block_h = len(opt_lines) * opt_line_h
        start_opt_y = y + (box_h - text_block_h) // 2 - 2
        for i, o_line in enumerate(opt_lines):
            line_y = start_opt_y + i * opt_line_h
            draw.text(
                (text_start_x, line_y),
                o_line,
                font=opt_font,
                fill=chalk_white
            )
        
        y += box_h + box_spacing

    # Resize to video resolution using high-quality Lanczos resampling
    final_img = base.resize(target_size, Image.Resampling.LANCZOS)
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(str(dest_path))
    return dest_path
