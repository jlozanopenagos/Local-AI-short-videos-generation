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
    DEFAULT_P1_GENDER,
    DEFAULT_P2_GENDER,
    FEMALE_HAIRSTYLE_TERMS,
    MALE_HAIRSTYLE_TERMS,
    CharacterCast,
    get_speaker_gender_safe,
    resolve_default_speakers_gender,
    sanitize_character_hair,
    _split_sentences_safe,
    _clean_character_clause,
    build_character_cast,
    extract_or_build_character_anchors,
    persist_character_anchors_in_state,
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
    "DEFAULT_P1_GENDER",
    "DEFAULT_P2_GENDER",
    "FEMALE_HAIRSTYLE_TERMS",
    "MALE_HAIRSTYLE_TERMS",
    "CharacterCast",
    "get_speaker_gender_safe",
    "resolve_default_speakers_gender",
    "sanitize_character_hair",
    "_split_sentences_safe",
    "_clean_character_clause",
    "build_character_cast",
    "extract_or_build_character_anchors",
    "persist_character_anchors_in_state",
    "sanitize_and_style_prompt",
    "is_present_heteronym_topic",
    "_extract_json_payload",
]
