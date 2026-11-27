"""
visual/languages/base.py — Base contract for language-specific visual data.

Rule of separation:
    A LanguageVisualProfile ONLY supplies language data (brand palette, idiom markers,
    idiom metaphor environments, heteronyms, domain keywords, cultural cues, and
    the language's CulturalWorld atlas).
    It MUST NEVER mention camera angles, shot framing, cast size, or video types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class CulturalWorld:
    """
    A curated, 100% text-free cultural venue or landmark tailored to a target language.

    Uses spatial architecture `staging_tags` ("layered_depth", "threshold", "tactile_props",
    "monumental") rather than camera-lens or video-type terms to keep language data separated
    from shot grammar.
    """

    id: str
    title: str
    region: str
    category: str  # "shop" | "food_market" | "street_plaza" | "coastal_nature" | "transit_civic" | "landmark"
    indoor_outdoor: str  # "interior" | "exterior" | "semi_open"
    staging_tags: Tuple[str, ...]
    vibe_tags: Tuple[str, ...]
    setting_prompt: str
    focal_props: Tuple[str, ...]
    wardrobe_cue: str
    explicit_keywords: Tuple[str, ...] = ()


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
    cultural_worlds: Tuple[CulturalWorld, ...] = ()
