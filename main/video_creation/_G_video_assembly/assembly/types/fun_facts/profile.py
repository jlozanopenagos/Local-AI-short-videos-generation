"""
assembly/types/fun_facts/profile.py — Scale-of-Wonder documentary editing signature for FUN_FACTS shorts.
"""
from __future__ import annotations

import re
from typing import Dict, Tuple

from ...common.audio_mix import AudioEnvelopeSegment, AudioMixSpec
from ...common.easing import MotionSpec
from ...common.subtitles import SubtitleStyleSpec
from ...common.transitions import TransitionSpec
from ..base import AssemblyProfile

_MOTION_MAP: Dict[str, MotionSpec] = {
    "hook": MotionSpec(1.10, 1.10, 0.50, 0.50, 0.78, 0.22, "cosine"),
    "setup": MotionSpec(1.00, 1.11, 0.50, 0.50, 0.46, 0.42, "cosine"),
    "discovery": MotionSpec(1.04, 1.12, 0.35, 0.65, 0.46, 0.42, "cosine"),
    "explanation": MotionSpec(1.10, 1.00, 0.50, 0.50, 0.42, 0.48, "cosine"),
    "payoff": MotionSpec(1.00, 1.08, 0.50, 0.50, 0.45, 0.41, "ease_out"),
}
_DEFAULT_MOTION = MotionSpec(1.00, 1.08, 0.50, 0.50, 0.44, 0.40, "cosine")

_TRANSITION_MAP: Dict[Tuple[str, str], TransitionSpec] = {
    ("hook", "setup"): TransitionSpec("smoothup", 0.36),
    ("setup", "discovery"): TransitionSpec("fade", 0.36),
    ("discovery", "explanation"): TransitionSpec("dissolve", 0.36),
    ("explanation", "payoff"): TransitionSpec("fade", 0.38),
}
_DEFAULT_TRANSITION = TransitionSpec("fade", 0.36)

_SUBTITLE_STYLE = SubtitleStyleSpec(
    alignment=2,
    margin_v=250,
    default_color="&H00FFFFFF",
    named_colors=(("Highlight", "&H0000FFFF"),),
    pop_in_scale_start=88,
    pop_in_duration_ms=65,
)

_AUDIO_MIX = AudioMixSpec(
    base_volume=0.055,
    closure_volume=0.085,
    segments=(
        AudioEnvelopeSegment("discovery", 0.068),
        AudioEnvelopeSegment("payoff", 0.068),
    ),
)


class FunFactsAssemblyProfile(AssemblyProfile):
    """Documentary wonder pacing: vertical crane tilt-up hook, numeric Gold highlights, atmospheric cross-dissolves."""

    video_type = "fun_facts"
    type_codes = ["F"]
    aliases = ["fun_facts", "funfacts", "funfact", "facts", "fun_fact"]

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

    def select_subtitle_style_name(
        self,
        word_text: str,
        section: str = "",
        speaker: str = "",
    ) -> str:
        return "Highlight" if re.search(r"\d", word_text or "") else "Default"

    def get_audio_mix_spec(self) -> AudioMixSpec:
        return _AUDIO_MIX
