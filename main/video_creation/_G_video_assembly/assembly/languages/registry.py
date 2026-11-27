"""
assembly/languages/registry.py — Language assembly profile resolution by name, code, or Script ID.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

from .base import AssemblyLanguageProfile
from .english import ENGLISH_ASSEMBLY_PROFILE
from .french import FRENCH_ASSEMBLY_PROFILE
from .italian import ITALIAN_ASSEMBLY_PROFILE
from .spanish import SPANISH_ASSEMBLY_PROFILE

_PROFILES_BY_KEY: Dict[str, AssemblyLanguageProfile] = {
    "en": ENGLISH_ASSEMBLY_PROFILE,
    "eng": ENGLISH_ASSEMBLY_PROFILE,
    "english": ENGLISH_ASSEMBLY_PROFILE,
    "fr": FRENCH_ASSEMBLY_PROFILE,
    "fra": FRENCH_ASSEMBLY_PROFILE,
    "french": FRENCH_ASSEMBLY_PROFILE,
    "français": FRENCH_ASSEMBLY_PROFILE,
    "francais": FRENCH_ASSEMBLY_PROFILE,
    "es": SPANISH_ASSEMBLY_PROFILE,
    "spa": SPANISH_ASSEMBLY_PROFILE,
    "spanish": SPANISH_ASSEMBLY_PROFILE,
    "español": SPANISH_ASSEMBLY_PROFILE,
    "espanol": SPANISH_ASSEMBLY_PROFILE,
    "it": ITALIAN_ASSEMBLY_PROFILE,
    "ita": ITALIAN_ASSEMBLY_PROFILE,
    "italian": ITALIAN_ASSEMBLY_PROFILE,
    "italiano": ITALIAN_ASSEMBLY_PROFILE,
}

_PREFIX_MAP: Dict[str, AssemblyLanguageProfile] = {
    "E": ENGLISH_ASSEMBLY_PROFILE,
    "F": FRENCH_ASSEMBLY_PROFILE,
    "S": SPANISH_ASSEMBLY_PROFILE,
    "I": ITALIAN_ASSEMBLY_PROFILE,
}


def get_assembly_language_profile(language: Optional[str]) -> AssemblyLanguageProfile:
    """Resolves an `AssemblyLanguageProfile` from a language string or canonical Script ID, defaulting to English."""
    if not language:
        return ENGLISH_ASSEMBLY_PROFILE

    clean = str(language).split("|")[0].strip()
    lower = clean.lower()
    if lower in _PROFILES_BY_KEY:
        return _PROFILES_BY_KEY[lower]

    for key, prof in _PROFILES_BY_KEY.items():
        if len(key) >= 4 and key in lower:
            return prof

    upper = clean.upper()
    if re.match(r"^[EFSI]_?[EGRF]\d{2,}$", upper) and upper[0] in _PREFIX_MAP:
        return _PREFIX_MAP[upper[0]]

    return ENGLISH_ASSEMBLY_PROFILE
