"""
assembly/types/roleplay/profile.py — Conversational 6-beat dialogue editing signature for ROLEPLAY shorts.
"""
from __future__ import annotations

from typing import Dict, Tuple

from ...common.audio_mix import AudioMixSpec
from ...common.easing import MotionSpec
from ...common.subtitles import SubtitleStyleSpec
from ...common.transitions import TransitionSpec
from ..base import AssemblyProfile

_PUNCH_IN_MOTION = MotionSpec(1.18, 1.24, 0.50, 0.50, 0.42, 0.40, "cosine")
_MOTION_MAP: Dict[str, MotionSpec] = {
    "hook": MotionSpec(1.00, 1.07, 0.50, 0.50, 0.46, 0.44, "cosine"),
    "dialogue_part_1": MotionSpec(1.03, 1.09, 0.44, 0.36, 0.44, 0.42, "cosine"),
    "dialogue_part_2": MotionSpec(1.03, 1.09, 0.56, 0.64, 0.44, 0.42, "cosine"),
    "dialogue_part_3": MotionSpec(1.08, 1.08, 0.50, 0.50, 0.32, 0.65, "cosine"),
    "dialogue_part_4": MotionSpec(1.10, 1.02, 0.50, 0.50, 0.42, 0.48, "ease_out"),
    "payoff": MotionSpec(1.07, 1.00, 0.50, 0.50, 0.44, 0.46, "ease_out"),
}
_DEFAULT_MOTION = MotionSpec(1.00, 1.06, 0.50, 0.50, 0.46, 0.44, "cosine")

_TRANSITION_MAP: Dict[Tuple[str, str], TransitionSpec] = {
    ("hook", "dialogue_part_1"): TransitionSpec("fade", 0.34),
    ("dialogue_part_1", "dialogue_part_2"): TransitionSpec("smoothleft", 0.34),
    ("dialogue_part_2", "dialogue_part_3"): TransitionSpec("smoothright", 0.34),
    ("dialogue_part_3", "dialogue_part_4"): TransitionSpec("dissolve", 0.34),
    ("dialogue_part_4", "payoff"): TransitionSpec("fade", 0.36),
}
_DEFAULT_TRANSITION = TransitionSpec("fade", 0.36)

_SUBTITLE_STYLE = SubtitleStyleSpec(
    alignment=2,
    margin_v=240,
    default_color="&H0000FFFF",
    named_colors=(
        ("PersonOne", "&H0000FFFF"),
        ("PersonTwo", "&H00FFE680"),
        ("Narrator", "&H00FFFFFF"),
    ),
    pop_in_scale_start=90,
    pop_in_duration_ms=65,
)

_AUDIO_MIX = AudioMixSpec(base_volume=0.04, closure_volume=0.08)


class RoleplayAssemblyProfile(AssemblyProfile):
    """Dialogue shot/reverse-shot choreography, 180-deg counter-pans, and speaker color-coded captions."""

    video_type = "roleplay"
    type_codes = ["R"]
    aliases = ["roleplay", "role_play", "dialogue"]
    companion_fallbacks = {
        "dialogue_part_1": ["hook"],
        "dialogue_part_4": ["payoff"],
        "payoff": ["dialogue_part_4"],
    }

    def get_motion_spec(
        self,
        section: str,
        punch_in: bool = False,
        is_chalkboard: bool = False,
    ) -> MotionSpec:
        if punch_in:
            return _PUNCH_IN_MOTION
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
        spk = speaker.strip().upper()
        if spk == "PERSON_ONE":
            return "PersonOne"
        if spk == "PERSON_TWO":
            return "PersonTwo"
        if spk == "NARRATOR" or section.strip().lower() in ("hook", "payoff"):
            return "Narrator"
        return "Default"

    def get_audio_mix_spec(self) -> AudioMixSpec:
        return _AUDIO_MIX
