"""
visual/types/roleplay/profile.py — RoleplayVisualProfile implementation.
"""
from __future__ import annotations

from ..base import VisualProfile
from .rules import ROLEPLAY_SCENES
from .prompts import (
    ROLEPLAY_STORYBOARD_SYSTEM_GRAMMAR,
    ROLEPLAY_SINGLE_SCENE_PROGRESSION,
    build_roleplay_single_scene_goal,
    build_roleplay_storyboard_task,
    build_roleplay_format_staging,
)


class RoleplayVisualProfile(VisualProfile):
    video_type = "roleplay"
    type_codes = ["R"]
    aliases = ["role_play"]
    has_two_characters_default = True
    voiceover_isolated = False
    scenes = ROLEPLAY_SCENES

    def build_single_scene_goal(self, scene_lower: str, p1_word: str, p2_word: str) -> str:
        return build_roleplay_single_scene_goal(scene_lower, p1_word, p2_word)

    def build_single_scene_progression_summary(self) -> str:
        return ROLEPLAY_SINGLE_SCENE_PROGRESSION

    def build_storyboard_system_grammar(self) -> str:
        return ROLEPLAY_STORYBOARD_SYSTEM_GRAMMAR

    def build_storyboard_director_task(self, p1_word: str, p2_word: str) -> str:
        return build_roleplay_storyboard_task(p1_word, p2_word)

    def build_format_staging_directive(self) -> str:
        return build_roleplay_format_staging()
