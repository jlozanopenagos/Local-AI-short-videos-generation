"""Visual profile package for FUN_FACTS shorts."""
from __future__ import annotations

from .profile import FunFactsVisualProfile
from .rules import FUN_FACTS_SCENES, FUN_FACTS_FORMAT_STAGING_DIRECTIVE
from .prompts import (
    build_fun_facts_single_scene_goal,
    build_fun_facts_storyboard_task,
    build_fun_facts_format_staging,
)

__all__ = [
    "FunFactsVisualProfile",
    "FUN_FACTS_SCENES",
    "FUN_FACTS_FORMAT_STAGING_DIRECTIVE",
    "build_fun_facts_single_scene_goal",
    "build_fun_facts_storyboard_task",
    "build_fun_facts_format_staging",
]
