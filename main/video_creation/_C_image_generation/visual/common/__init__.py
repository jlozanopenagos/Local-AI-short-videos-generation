"""
visual/common — Shared visual rules, sanitizers, environment resolvers, and character cast utilities.
"""
from __future__ import annotations

from .style import (
    _VISUAL_DIRECTOR_SYSTEM_PROMPT,
    _STORYBOARD_DIRECTOR_SYSTEM_PROMPT,
    build_storyboard_system_prompt,
    _get_language_palette,
    _parse_label,
)
from .environment import (
    HETERONYM_DOMAINS,
    EXPLICIT_SCENARIO_DOMAINS,
    is_figurative_idiom,
    resolve_anchor_environment,
)
from .cast import (
    FEMALE_HAIRSTYLE_TERMS,
    MALE_HAIRSTYLE_TERMS,
    get_speaker_gender_safe,
    sanitize_character_hair,
    _split_sentences_safe,
    _clean_character_clause,
    extract_or_build_character_anchors,
)
from .sanitizer import sanitize_and_style_prompt, is_present_heteronym_topic
from .llm_stream import _extract_json_payload

__all__ = [
    "_VISUAL_DIRECTOR_SYSTEM_PROMPT",
    "_STORYBOARD_DIRECTOR_SYSTEM_PROMPT",
    "build_storyboard_system_prompt",
    "_get_language_palette",
    "_parse_label",
    "HETERONYM_DOMAINS",
    "EXPLICIT_SCENARIO_DOMAINS",
    "is_figurative_idiom",
    "resolve_anchor_environment",
    "FEMALE_HAIRSTYLE_TERMS",
    "MALE_HAIRSTYLE_TERMS",
    "get_speaker_gender_safe",
    "sanitize_character_hair",
    "_split_sentences_safe",
    "_clean_character_clause",
    "extract_or_build_character_anchors",
    "sanitize_and_style_prompt",
    "is_present_heteronym_topic",
    "_extract_json_payload",
]
