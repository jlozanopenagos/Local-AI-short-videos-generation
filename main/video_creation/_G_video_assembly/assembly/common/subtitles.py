"""
assembly/common/subtitles.py — Safe-zone ASS header rendering and kinetic pop-in dialogue helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class SubtitleStyleSpec:
    """ASS subtitle styling parameters for a video archetype."""

    font_name: str = "Arial"
    font_size: int = 60
    alignment: int = 2
    margin_v: int = 250
    margin_l: int = 20
    margin_r: int = 20
    outline: int = 3
    shadow: int = 2
    default_color: str = "&H0000FFFF"
    named_colors: Tuple[Tuple[str, str], ...] = ()
    pop_in_scale_start: int = 85
    pop_in_duration_ms: int = 65
    enable_pop_in: bool = True


def _style_line(
    name: str,
    primary_color: str,
    spec: SubtitleStyleSpec,
    margin_v: int,
    font_name: str,
) -> str:
    return (
        f"Style: {name},{font_name},{spec.font_size},{primary_color},&H000000FF,"
        f"&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{spec.outline},{spec.shadow},"
        f"{spec.alignment},{spec.margin_l},{spec.margin_r},{margin_v},1"
    )


def render_ass_header(
    spec: SubtitleStyleSpec,
    video_width: int = 576,
    video_height: int = 1024,
    margin_v_offset: int = 0,
    font_override: Optional[str] = None,
) -> str:
    """Renders `[Script Info]`, `[V4+ Styles]`, and `[Events]` header for an ASS file."""
    margin_v = max(20, int(spec.margin_v) + int(margin_v_offset))
    font_name = font_override or spec.font_name

    style_lines = [_style_line("Default", spec.default_color, spec, margin_v, font_name)]
    for style_name, color_bgr in spec.named_colors:
        style_lines.append(_style_line(style_name, color_bgr, spec, margin_v, font_name))

    styles_block = "\n".join(style_lines)
    return (
        f"[Script Info]\n"
        f"ScriptType: v4.00+\n"
        f"PlayResX: {video_width}\n"
        f"PlayResY: {video_height}\n\n"
        f"[V4+ Styles]\n"
        f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        f"Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        f"Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{styles_block}\n\n"
        f"[Events]\n"
        f"Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def format_ass_dialogue_line(
    start_str: str,
    end_str: str,
    text: str,
    style_name: str,
    spec: SubtitleStyleSpec,
) -> str:
    """Formats a single ASS `Dialogue:` event, optionally prepending kinetic pop-in scale tags."""
    if spec.enable_pop_in:
        tag = f"{{\\fscx{spec.pop_in_scale_start}\\fscy{spec.pop_in_scale_start}\\t(0,{spec.pop_in_duration_ms},\\fscx100\\fscy100)}}"
        styled_text = f"{tag}{text}"
    else:
        styled_text = text
    return f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{styled_text}\n"
