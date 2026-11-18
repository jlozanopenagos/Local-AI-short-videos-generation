"""
visual/types/base.py — Base VisualProfile and SceneSpec contracts for video-type visual engines.
Mirrors the Stage A `BaseScriptEngine` architecture.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class SceneSpec:
    """Explicit contract for a single scene in a video format's visual timeline."""
    name: str
    render_mode: str = "comfy"          # "comfy" | "chalkboard" | "static"
    cast_in_frame: str = "solo"         # "solo" | "p1" | "p2" | "both"
    lens_and_angle: str = ""
    gaze: str = "none"                  # "fourth_wall" | "none" | "upward"
    emotion_arc: str = ""
    prop_rule: str = ""


class VisualProfile(ABC):
    """
    Abstract base class for video-type visual profiles (GAME, FUN_FACTS, EXPRESSION, ROLEPLAY).
    Each profile encapsulates its own scene contracts, shot grammar, storyboard director task,
    single-scene situational goals, and general-prompt staging directive.
    """

    video_type: str = "base"
    type_codes: List[str] = []
    aliases: List[str] = []
    has_two_characters_default: bool = False
    voiceover_isolated: bool = True
    scenes: List[SceneSpec] = []

    def get_scene_map(self) -> Dict[str, SceneSpec]:
        return {s.name.lower(): s for s in self.scenes}

    def get_comfy_scene_names(self) -> List[str]:
        return [s.name.lower() for s in self.scenes if s.render_mode == "comfy"]

    @abstractmethod
    def build_single_scene_goal(self, scene_lower: str, p1_word: str, p2_word: str) -> str:
        """Builds the single-scene situational direction (`text_rule`) for `_build_user_context`."""
        pass

    @abstractmethod
    def build_storyboard_director_task(self, p1_word: str, p2_word: str) -> str:
        """Builds the `director_task` block for `_build_storyboard_context`."""
        pass

    @abstractmethod
    def build_format_staging_directive(self) -> str:
        """Builds the `5. FORMAT STAGING DIRECTIVE (...)` block for `build_general_prompt`."""
        pass
