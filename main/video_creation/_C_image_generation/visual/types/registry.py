"""
visual/types/registry.py — Central registry and dispatch factory for video-type visual profiles.
Supports `IMAGE_PROMPT_ENGINE=legacy|typed` environment switch for instant rollback.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional, Type

from .base import VisualProfile

logger = logging.getLogger("visual_profile_registry")


def is_legacy_engine_enabled(video_type: str = "") -> bool:
    """
    Returns True if `IMAGE_PROMPT_ENGINE` is set to 'legacy' (or 'legacy:<type>').
    Defaults to 'typed' in Phase 2+ while keeping 'legacy' available as a safety switch.
    """
    raw = os.getenv("IMAGE_PROMPT_ENGINE", "typed").strip().lower()
    if raw == "legacy":
        return True
    if raw.startswith("legacy:") and video_type:
        disabled = {t.strip().upper() for t in raw.split(":", 1)[1].split(",") if t.strip()}
        return video_type.strip().upper() in disabled
    return False


class VisualProfileRegistry:
    """Thread-safe catalog of video-type visual profiles."""

    _profiles_by_type: Dict[str, VisualProfile] = {}
    _profiles_by_code: Dict[str, VisualProfile] = {}

    @classmethod
    def register(cls, profile_cls: Type[VisualProfile]) -> Type[VisualProfile]:
        instance = profile_cls()
        canon = instance.video_type.lower().strip()
        cls._profiles_by_type[canon] = instance
        for alias in getattr(instance, "aliases", []):
            cls._profiles_by_type[alias.lower().strip()] = instance
        for code in instance.type_codes:
            cls._profiles_by_code[code.upper().strip()] = instance
        return profile_cls

    @classmethod
    def _load_builtins(cls) -> None:
        for mod_name, cls_name in (
            ("game", "GameVisualProfile"),
            ("fun_facts", "FunFactsVisualProfile"),
            ("expression", "ExpressionVisualProfile"),
            ("roleplay", "RoleplayVisualProfile"),
        ):
            try:
                mod = __import__(f"{__package__}.{mod_name}.profile", fromlist=[cls_name])
                cls.register(getattr(mod, cls_name))
            except Exception as exc:
                logger.debug("Could not load %s: %s", cls_name, exc)

    @classmethod
    def get_profile(cls, identifier: str) -> Optional[VisualProfile]:
        """
        Resolves a VisualProfile from:
        1. Exact type name or alias ('game', 'roleplay', 'expression', 'fun_facts', 'funfacts', 'funfact')
        2. Single-letter code ('G', 'R', 'E', 'F')
        3. Canonical Script ID ('SG01', 'ER05', 'FE12', 'EF01')
        """
        if not identifier:
            return None
        if is_legacy_engine_enabled(identifier):
            return None

        if not cls._profiles_by_type:
            cls._load_builtins()

        clean = str(identifier).strip()
        lower = clean.lower()
        if lower in cls._profiles_by_type:
            return cls._profiles_by_type[lower]

        upper = clean.upper()
        if upper in cls._profiles_by_code:
            return cls._profiles_by_code[upper]

        m = re.match(r"^[A-Z]_?([A-Z])\d{2,}$", upper)
        if m and m.group(1) in cls._profiles_by_code:
            return cls._profiles_by_code[m.group(1)]

        return None

    @classmethod
    def list_supported_types(cls) -> List[str]:
        if not cls._profiles_by_type:
            cls._load_builtins()
        return sorted({p.video_type for p in cls._profiles_by_type.values()})

    @classmethod
    def clear(cls) -> None:
        cls._profiles_by_type.clear()
        cls._profiles_by_code.clear()


def get_visual_profile(identifier: str) -> Optional[VisualProfile]:
    return VisualProfileRegistry.get_profile(identifier)
