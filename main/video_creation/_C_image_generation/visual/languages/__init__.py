"""
visual/languages — Language-specific visual profiles, palettes, idioms, and semantic domains.
"""
from __future__ import annotations

from .base import CulturalWorld, LanguageVisualProfile
from .english import ENGLISH_PROFILE, ENGLISH_HETERONYM_DOMAINS
from .french import FRENCH_PROFILE
from .spanish import SPANISH_PROFILE
from .italian import ITALIAN_PROFILE
from .registry import (
    ALL_LANGUAGE_PROFILES,
    MULTILINGUAL_SEMANTIC_DOMAINS,
    get_language_profile,
    get_all_idiom_markers,
    get_all_idiom_environments,
    get_all_heteronym_domains,
)

__all__ = [
    "CulturalWorld",
    "LanguageVisualProfile",
    "ENGLISH_PROFILE",
    "ENGLISH_HETERONYM_DOMAINS",
    "FRENCH_PROFILE",
    "SPANISH_PROFILE",
    "ITALIAN_PROFILE",
    "ALL_LANGUAGE_PROFILES",
    "MULTILINGUAL_SEMANTIC_DOMAINS",
    "get_language_profile",
    "get_all_idiom_markers",
    "get_all_idiom_environments",
    "get_all_heteronym_domains",
]
