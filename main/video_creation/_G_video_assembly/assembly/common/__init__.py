"""
assembly/common/__init__.py — Re-exports shared camera easing, transitions, audio mix, and subtitle helpers.
"""
from .audio_mix import AudioEnvelopeSegment, AudioMixSpec, build_bgm_volume_expr
from .easing import MotionSpec, build_zoompan_expressions
from .subtitles import SubtitleStyleSpec, format_ass_dialogue_line, render_ass_header
from .transitions import TransitionSpec, chain_clips_with_xfade, compute_clip_render_durations

__all__ = [
    "MotionSpec",
    "build_zoompan_expressions",
    "TransitionSpec",
    "compute_clip_render_durations",
    "chain_clips_with_xfade",
    "AudioEnvelopeSegment",
    "AudioMixSpec",
    "build_bgm_volume_expr",
    "SubtitleStyleSpec",
    "render_ass_header",
    "format_ass_dialogue_line",
]
