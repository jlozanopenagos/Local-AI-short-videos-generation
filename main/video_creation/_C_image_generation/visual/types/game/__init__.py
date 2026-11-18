"""Visual profile package for GAME shorts."""
from __future__ import annotations

from .profile import GameVisualProfile
from .rules import GAME_SCENES, GAME_FORMAT_STAGING_DIRECTIVE
from .prompts import (
    build_game_single_scene_goal,
    build_game_storyboard_task,
    build_game_format_staging,
)

__all__ = [
    "GameVisualProfile",
    "GAME_SCENES",
    "GAME_FORMAT_STAGING_DIRECTIVE",
    "build_game_single_scene_goal",
    "build_game_storyboard_task",
    "build_game_format_staging",
]
