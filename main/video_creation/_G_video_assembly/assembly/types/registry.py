"""
assembly/types/registry.py — Central registry & dispatch factory for video-type AssemblyProfiles.
Supports `VIDEO_ASSEMBLY_ENGINE=legacy|typed|legacy:<type>` environment switch for instant rollback.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional, Type

from .base import AssemblyProfile

logger = logging.getLogger("assembly_profile_registry")


def is_legacy_assembly_engine_enabled(video_type: str = "") -> bool:
    """Returns True if `VIDEO_ASSEMBLY_ENGINE` is set to 'legacy' or 'legacy:<type>'."""
    raw = os.getenv("VIDEO_ASSEMBLY_ENGINE", "typed").strip().lower()
    if raw == "legacy":
        return True
    if raw.startswith("legacy:") and video_type:
        disabled = {t.strip().upper() for t in raw.split(":", 1)[1].split(",") if t.strip()}
        return video_type.strip().upper() in disabled
    return False


class AssemblyProfileRegistry:
    """Registry of typed video assembly profiles."""

    _profiles_by_type: Dict[str, AssemblyProfile] = {}
    _profiles_by_code: Dict[str, AssemblyProfile] = {}

    @classmethod
    def register(cls, profile_cls: Type[AssemblyProfile]) -> Type[AssemblyProfile]:
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
            ("expression", "ExpressionAssemblyProfile"),
            ("game", "GameAssemblyProfile"),
            ("roleplay", "RoleplayAssemblyProfile"),
            ("fun_facts", "FunFactsAssemblyProfile"),
        ):
            try:
                mod = __import__(f"{__package__}.{mod_name}.profile", fromlist=[cls_name])
                cls.register(getattr(mod, cls_name))
            except Exception as exc:
                logger.debug("Could not load %s: %s", cls_name, exc)

    @classmethod
    def get_profile(cls, identifier: str) -> Optional[AssemblyProfile]:
        """
        Resolves an `AssemblyProfile` from:
        1. Type name or alias ('expression', 'game', 'roleplay', 'fun_facts', 'funfacts', 'quiz')
        2. Single-letter code ('E', 'G', 'R', 'F')
        3. Canonical Script ID ('EE01', 'SG02', 'FR01', 'IF01')
        """
        if not identifier:
            return None
        if is_legacy_assembly_engine_enabled():
            return None

        if not cls._profiles_by_type:
            cls._load_builtins()

        clean = str(identifier).strip()
        lower = clean.lower()
        resolved: Optional[AssemblyProfile] = cls._profiles_by_type.get(lower)

        if resolved is None:
            upper = clean.upper()
            if upper in cls._profiles_by_code:
                resolved = cls._profiles_by_code[upper]
            else:
                m = re.match(r"^[A-Z]_?([A-Z])\d{2,}$", upper)
                if m and m.group(1) in cls._profiles_by_code:
                    resolved = cls._profiles_by_code[m.group(1)]

        if resolved is None:
            return None

        if is_legacy_assembly_engine_enabled(resolved.video_type):
            return None
        return resolved

    @classmethod
    def list_supported_types(cls) -> List[str]:
        if not cls._profiles_by_type:
            cls._load_builtins()
        return sorted({p.video_type for p in cls._profiles_by_type.values()})

    @classmethod
    def clear(cls) -> None:
        cls._profiles_by_type.clear()
        cls._profiles_by_code.clear()


def get_assembly_profile(identifier: str) -> Optional[AssemblyProfile]:
    """Resolves the active `AssemblyProfile`, returning None when legacy mode is enabled."""
    return AssemblyProfileRegistry.get_profile(identifier)
