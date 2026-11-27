"""
assembly/types/expression/profile.py — Editorial assembly signature for EXPRESSION shorts.
"""
from __future__ import annotations

from typing import Dict, Tuple

from ...common.audio_mix import AudioMixSpec
from ...common.easing import MotionSpec
from ...common.subtitles import SubtitleStyleSpec
from ...common.transitions import TransitionSpec
from ..base import AssemblyProfile

_MOTION_MAP: Dict[str, MotionSpec] = {
    "hook": MotionSpec(1.00, 1.10, 0.50, 0.50, 0.44, 0.40, "ease_out"),
    "setup": MotionSpec(1.08, 1.08, 0.25, 0.75, 0.45, 0.45, "cosine"),
    "discovery": MotionSpec(1.05, 1.14, 0.50, 0.50, 0.45, 0.40, "cosine"),
    "example": MotionSpec(1.12, 1.00, 0.50, 0.50, 0.42, 0.48, "cosine"),
    "payoff": MotionSpec(1.06, 1.00, 0.50, 0.50, 0.44, 0.46, "ease_out"),
}
_DEFAULT_MOTION = MotionSpec(1.00, 1.08, 0.50, 0.50, 0.45, 0.42, "cosine")

_TRANSITION_MAP: Dict[Tuple[str, str], TransitionSpec] = {
    ("hook", "setup"): TransitionSpec("smoothleft", 0.34),
    ("setup", "discovery"): TransitionSpec("dissolve", 0.36),
    ("discovery", "example"): TransitionSpec("smoothright", 0.34),
    ("example", "payoff"): TransitionSpec("fade", 0.36),
}
_DEFAULT_TRANSITION = TransitionSpec("fade", 0.36)

_SUBTITLE_STYLE = SubtitleStyleSpec(
    alignment=2,
    margin_v=250,
    default_color="&H0000FFFF",
    pop_in_scale_start=85,
    pop_in_duration_ms=65,
)

_AUDIO_MIX = AudioMixSpec(base_volume=0.05, closure_volume=0.08)


class ExpressionAssemblyProfile(AssemblyProfile):
    """Balanced storyteller pacing: ease-out hook push-in, lateral contrast pan, pull-back action reveal."""

    video_type = "expression"
    type_codes = ["E"]
    aliases = ["expression", "idiom"]

    def get_motion_spec(
        self,
        section: str,
        punch_in: bool = False,
        is_chalkboard: bool = False,
    ) -> MotionSpec:
        return _MOTION_MAP.get(section.strip().lower(), _DEFAULT_MOTION)

    def get_transition_spec(self, from_section: str, to_section: str) -> TransitionSpec:
        key = (from_section.strip().lower(), to_section.strip().lower())
        return _TRANSITION_MAP.get(key, _DEFAULT_TRANSITION)

    def get_subtitle_style(self) -> SubtitleStyleSpec:
        return _SUBTITLE_STYLE

    def get_audio_mix_spec(self) -> AudioMixSpec:
        return _AUDIO_MIX
