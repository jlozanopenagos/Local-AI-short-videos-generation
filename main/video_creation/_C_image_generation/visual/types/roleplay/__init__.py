"""Visual profile package for ROLEPLAY shorts."""
from __future__ import annotations

from .profile import RoleplayVisualProfile
from .rules import ROLEPLAY_SCENES, ROLEPLAY_FORMAT_STAGING_DIRECTIVE
from .prompts import (
    build_roleplay_single_scene_goal,
    build_roleplay_storyboard_task,
    build_roleplay_format_staging,
)

__all__ = [
    "RoleplayVisualProfile",
    "ROLEPLAY_SCENES",
    "ROLEPLAY_FORMAT_STAGING_DIRECTIVE",
    "build_roleplay_single_scene_goal",
    "build_roleplay_storyboard_task",
    "build_roleplay_format_staging",
]
