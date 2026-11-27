"""
visual/types/game/profile.py — GameVisualProfile implementation.
"""
from __future__ import annotations

from ..base import VisualProfile
from .rules import GAME_SCENES, GAME_ARCHETYPE_DIRECTIVE
from .prompts import (
    GAME_STORYBOARD_SYSTEM_GRAMMAR,
    GAME_SINGLE_SCENE_PROGRESSION,
    build_game_single_scene_goal,
    build_game_storyboard_task,
    build_game_format_staging,
)


class GameVisualProfile(VisualProfile):
    video_type = "game"
    type_codes = ["G"]
    aliases = ["quiz"]
    has_two_characters_default = False
    voiceover_isolated = True
    general_prompt_camera_opener = "Medium-wide establishing eye-level shot."
    scenes = GAME_SCENES

    def build_general_prompt_archetype_directive(self) -> str:
        return GAME_ARCHETYPE_DIRECTIVE

    def build_single_scene_goal(self, scene_lower: str, p1_word: str, p2_word: str) -> str:
        return build_game_single_scene_goal(scene_lower, p1_word, p2_word)

    def build_single_scene_progression_summary(self) -> str:
        return GAME_SINGLE_SCENE_PROGRESSION

    def build_storyboard_system_grammar(self) -> str:
        return GAME_STORYBOARD_SYSTEM_GRAMMAR

    def build_storyboard_director_task(self, p1_word: str, p2_word: str) -> str:
        return build_game_storyboard_task(p1_word, p2_word)

    def build_format_staging_directive(self) -> str:
        return build_game_format_staging()
