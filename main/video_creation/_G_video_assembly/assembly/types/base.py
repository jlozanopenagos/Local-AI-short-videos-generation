"""
assembly/types/base.py — Abstract AssemblyProfile contract for video-type editing & subtitle signatures.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Set

from ..common.audio_mix import AudioMixSpec
from ..common.easing import MotionSpec
from ..common.subtitles import SubtitleStyleSpec
from ..common.transitions import TransitionSpec


class AssemblyProfile(ABC):
    """Encapsulates per-type motion choreography, transitions, subtitle styling, and BGM envelope."""

    video_type: str = "base"
    type_codes: List[str] = []
    aliases: List[str] = []
    fps: int = 25
    companion_fallbacks: Dict[str, List[str]] = {}

    @abstractmethod
    def get_motion_spec(
        self,
        section: str,
        punch_in: bool = False,
        is_chalkboard: bool = False,
    ) -> MotionSpec:
        """Returns the camera zoom/pan trajectory for a given timeline section."""
        pass

    @abstractmethod
    def get_transition_spec(self, from_section: str, to_section: str) -> TransitionSpec:
        """Returns the smooth `xfade` transition linking two consecutive timeline sections."""
        pass

    @abstractmethod
    def get_subtitle_style(self) -> SubtitleStyleSpec:
        """Returns ASS styling parameters (safe zone alignment, colors, pop-in animation)."""
        pass

    def select_subtitle_style_name(
        self,
        word_text: str,
        section: str = "",
        speaker: str = "",
    ) -> str:
        """Selects the ASS `Style` name for a word event based on speaker, section, or token."""
        return "Default"

    @abstractmethod
    def get_audio_mix_spec(self) -> AudioMixSpec:
        """Returns the BGM base volume, section envelope rules, and closure swell configuration."""
        pass

    def get_suppress_subtitle_sections(self) -> Set[str]:
        """Returns section names where animated subtitles are suppressed (e.g. `challenge` chalkboard)."""
        return set()
