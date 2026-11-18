"""
visual/types — Video-type visual profiles and dispatch registry.
"""
from __future__ import annotations

from .base import SceneSpec, VisualProfile
from .registry import VisualProfileRegistry, get_visual_profile, is_legacy_engine_enabled

__all__ = [
    "SceneSpec",
    "VisualProfile",
    "VisualProfileRegistry",
    "get_visual_profile",
    "is_legacy_engine_enabled",
]
