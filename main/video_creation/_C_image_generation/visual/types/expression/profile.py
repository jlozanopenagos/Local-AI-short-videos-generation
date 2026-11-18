"""
visual/types/expression/profile.py — ExpressionVisualProfile implementation.
"""
from __future__ import annotations

from ..base import VisualProfile
from .rules import EXPRESSION_SCENES, EXPRESSION_ARCHETYPE_DIRECTIVE
from .prompts import (
    EXPRESSION_STORYBOARD_SYSTEM_GRAMMAR,
    EXPRESSION_SINGLE_SCENE_PROGRESSION,
    build_expression_single_scene_goal,
    build_expression_storyboard_task,
    build_expression_format_staging,
)


class ExpressionVisualProfile(VisualProfile):
    video_type = "expression"
    type_codes = ["E"]
    aliases = ["idiom", "expressions"]
    has_two_characters_default = False
    voiceover_isolated = True
    general_prompt_camera_opener = "Medium-wide establishing eye-level shot."
    scenes = EXPRESSION_SCENES

    def build_general_prompt_archetype_directive(self) -> str:
        return EXPRESSION_ARCHETYPE_DIRECTIVE

    def build_single_scene_goal(self, scene_lower: str, p1_word: str, p2_word: str) -> str:
        return build_expression_single_scene_goal(scene_lower, p1_word, p2_word)

    def build_single_scene_progression_summary(self) -> str:
        return EXPRESSION_SINGLE_SCENE_PROGRESSION

    def build_storyboard_system_grammar(self) -> str:
        return EXPRESSION_STORYBOARD_SYSTEM_GRAMMAR

    def build_storyboard_director_task(self, p1_word: str, p2_word: str) -> str:
        return build_expression_storyboard_task(p1_word, p2_word)

    def build_format_staging_directive(self) -> str:
        return build_expression_format_staging()
