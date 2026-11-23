"""
assembly/types/game/profile.py — High-stakes quiz editing signature for GAME shorts.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Set, Tuple

from ...common.audio_mix import AudioEnvelopeSegment, AudioMixSpec
from ...common.easing import MotionSpec
from ...common.subtitles import SubtitleStyleSpec
from ...common.transitions import TransitionSpec
from ..base import AssemblyProfile

_CHALKBOARD_MOTION = MotionSpec(1.00, 1.015, 0.50, 0.50, 0.50, 0.50, "linear")
_MOTION_MAP: Dict[str, MotionSpec] = {
    "hook": MotionSpec(1.00, 1.12, 0.50, 0.50, 0.44, 0.40, "ease_in"),
    "challenge": _CHALKBOARD_MOTION,
    "pressure": MotionSpec(1.02, 1.15, 0.50, 0.50, 0.46, 0.42, "ease_in"),
    "answer": MotionSpec(1.14, 1.02, 0.50, 0.50, 0.42, 0.46, "ease_out"),
    "explanation": MotionSpec(1.06, 1.06, 0.72, 0.28, 0.46, 0.46, "cosine"),
}
_DEFAULT_MOTION = MotionSpec(1.00, 1.08, 0.50, 0.50, 0.46, 0.42, "cosine")

_TRANSITION_MAP: Dict[Tuple[str, str], TransitionSpec] = {
    ("hook", "challenge"): TransitionSpec("smoothup", 0.18),
    ("challenge", "pressure"): TransitionSpec("fade", 0.18),
    ("pressure", "answer"): TransitionSpec("circleopen", 0.26),
    ("answer", "explanation"): TransitionSpec("smoothleft", 0.34),
}
_DEFAULT_TRANSITION = TransitionSpec("smoothleft", 0.34)

_SUBTITLE_STYLE = SubtitleStyleSpec(
    alignment=2,
    margin_v=260,
    default_color="&H0000FFFF",
    named_colors=(("Explanation", "&H00FFFFFF"),),
    pop_in_scale_start=80,
    pop_in_duration_ms=50,
)

_AUDIO_MIX = AudioMixSpec(
    base_volume=0.05,
    closure_volume=0.08,
    segments=(
        AudioEnvelopeSegment("pressure", 0.075),
        AudioEnvelopeSegment("answer", 0.025, head_seconds=0.6),
    ),
)


class GameAssemblyProfile(AssemblyProfile):
    """High-energy quiz pacing: accelerating pressure zoom, steady chalkboard, snap reveal, audio pressure tension."""

    video_type = "game"
    type_codes = ["G"]
    aliases = ["game", "quiz"]
    locked_visual_sections = frozenset({"challenge", "pressure"})

    def get_motion_spec(
        self,
        section: str,
        punch_in: bool = False,
        is_chalkboard: bool = False,
    ) -> MotionSpec:
        if is_chalkboard:
            return _CHALKBOARD_MOTION
        return _MOTION_MAP.get(section.strip().lower(), _DEFAULT_MOTION)

    def get_transition_spec(self, from_section: str, to_section: str) -> TransitionSpec:
        key = (from_section.strip().lower(), to_section.strip().lower())
        return _TRANSITION_MAP.get(key, _DEFAULT_TRANSITION)

    def get_subtitle_style(self) -> SubtitleStyleSpec:
        return _SUBTITLE_STYLE

    def select_subtitle_style_name(
        self,
        word_text: str,
        section: str = "",
        speaker: str = "",
    ) -> str:
        return "Explanation" if section.strip().lower() == "explanation" else "Default"

    def get_audio_mix_spec(self) -> AudioMixSpec:
        return _AUDIO_MIX

    def get_suppress_subtitle_sections(self) -> Set[str]:
        return {"challenge"}
