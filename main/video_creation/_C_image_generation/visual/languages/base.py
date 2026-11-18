"""
visual/languages/base.py — Base contract for language-specific visual data.

Rule of separation:
    A LanguageVisualProfile ONLY supplies language data (brand palette, idiom markers,
    idiom metaphor environments, heteronyms, domain keywords, cultural cues).
    It MUST NEVER mention camera angles, shot framing, cast size, or video types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class LanguageVisualProfile:
    language: str
    lang_code: str
    aliases: Tuple[str, ...] = ()
    palette_mood: str = ""
    idiom_markers: Tuple[str, ...] = ()
    idiom_environments: Tuple[Tuple[Tuple[str, ...], str], ...] = ()
    heteronym_domains: Dict[str, str] = field(default_factory=dict)
    cultural_cue: str = ""
