"""
visual/types/fun_facts/profile.py — FunFactsVisualProfile implementation.
"""
from __future__ import annotations

from ..base import VisualProfile
from .rules import FUN_FACTS_SCENES
from .prompts import (
    FUN_FACTS_STORYBOARD_SYSTEM_GRAMMAR,
    FUN_FACTS_SINGLE_SCENE_PROGRESSION,
    build_fun_facts_single_scene_goal,
    build_fun_facts_storyboard_task,
    build_fun_facts_format_staging,
)


class FunFactsVisualProfile(VisualProfile):
    video_type = "fun_facts"
    type_codes = ["F"]
    aliases = ["funfacts", "funfact", "fun_fact", "facts"]
    has_two_characters_default = False
    voiceover_isolated = True
    scenes = FUN_FACTS_SCENES

    def build_single_scene_goal(self, scene_lower: str, p1_word: str, p2_word: str) -> str:
        return build_fun_facts_single_scene_goal(scene_lower, p1_word, p2_word)

    def build_single_scene_progression_summary(self) -> str:
        return FUN_FACTS_SINGLE_SCENE_PROGRESSION

    def build_storyboard_system_grammar(self) -> str:
        return FUN_FACTS_STORYBOARD_SYSTEM_GRAMMAR

    def build_storyboard_director_task(self, p1_word: str, p2_word: str) -> str:
        return build_fun_facts_storyboard_task(p1_word, p2_word)

    def build_format_staging_directive(self) -> str:
        return build_fun_facts_format_staging()
