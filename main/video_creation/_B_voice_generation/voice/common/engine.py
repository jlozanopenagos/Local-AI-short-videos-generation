"""
voice/common/engine.py — Engine toggle (`VOICE_ENGINE`), dialect hint resolution, and sampling resolver.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import config

from .models import LanguageVoiceProfile, VideoTypeVoiceProfile

_LANG_SHORTHANDS = {
    "en": "english",
    "eng": "english",
    "fr": "french",
    "fra": "french",
    "français": "french",
    "es": "spanish",
    "sp": "spanish",
    "esp": "spanish",
    "español": "spanish",
    "it": "italian",
    "ita": "italian",
    "italiano": "italian",
}

_TYPE_SHORTHANDS = {
    "funfacts": "fun_facts",
    "facts": "fun_facts",
    "quiz": "game",
    "explanation": "expression",
}


def normalize_voice_language(raw: str) -> str:
    clean = str(raw or "english").split("|")[0].strip().lower()
    if clean in _LANG_SHORTHANDS:
        return _LANG_SHORTHANDS[clean]
    if "french" in clean or "français" in clean or "francais" in clean:
        return "french"
    if "spanish" in clean or "español" in clean or "espanol" in clean:
        return "spanish"
    if "italian" in clean or "italiano" in clean:
        return "italian"
    if "english" in clean:
        return "english"
    return clean or "english"


def normalize_voice_video_type(raw: str) -> str:
    clean = str(raw or "expression").strip().lower()
    if clean in _TYPE_SHORTHANDS:
        return _TYPE_SHORTHANDS[clean]
    if "game" in clean:
        return "game"
    if "roleplay" in clean:
        return "roleplay"
    if "fun_facts" in clean or "funfacts" in clean or "facts" in clean:
        return "fun_facts"
    return "expression"


def get_voice_engine_mode() -> str:
    """Reads `VOICE_ENGINE` dynamically from environment (or config default `typed`)."""
    raw = os.getenv("VOICE_ENGINE")
    if raw is None or not raw.strip():
        raw = getattr(config, "VOICE_ENGINE", "typed")
    return str(raw or "typed").strip().lower()


def is_typed_voice_enabled(video_type: str = "", language: str = "") -> bool:
    """Returns True when modular typed voice rules apply to `(video_type, language)`.

    Supports:
    - `VOICE_ENGINE=typed` (default): enabled everywhere
    - `VOICE_ENGINE=legacy`: disabled everywhere (exact Phase 0 legacy behavior)
    - `VOICE_ENGINE=legacy:game,italian`: selectively disabled for listed types/languages
    """
    mode = get_voice_engine_mode()
    if mode == "legacy":
        return False
    if mode.startswith("legacy:"):
        tokens = {t.strip().lower() for t in mode.split(":", 1)[1].split(",") if t.strip()}
        norm_tokens = set()
        for tok in tokens:
            norm_tokens.add(tok)
            if tok in _LANG_SHORTHANDS:
                norm_tokens.add(_LANG_SHORTHANDS[tok])
            if tok in _TYPE_SHORTHANDS:
                norm_tokens.add(_TYPE_SHORTHANDS[tok])
        vtype_norm = normalize_voice_video_type(video_type) if video_type else ""
        lang_norm = normalize_voice_language(language) if language else ""
        if (vtype_norm and vtype_norm in norm_tokens) or (lang_norm and lang_norm in norm_tokens):
            return False
    return True


def detect_dialect_hint(
    language: str,
    script_data: Optional[dict] = None,
    explicit_accent: Optional[str] = None,
) -> Optional[str]:
    """Resolves a neutral dialect lock when explicit override or script content calls for one."""
    lang = normalize_voice_language(language)

    if explicit_accent:
        cleaned = explicit_accent.strip().lower()
        if lang == "spanish":
            if any(k in cleaned for k in ("spain", "castil", "españ", "penin", "es_es")):
                return "es_spain_castilian"
            if any(k in cleaned for k in ("latam", "latin", "amer", "neutral", "mex", "col")):
                return "es_latam_neutral"
        elif lang == "english":
            if any(k in cleaned for k in ("brit", "uk", "england", "london", "en_uk")):
                return "en_uk_neutral"
            if any(k in cleaned for k in ("amer", "us", "usa", "en_us")):
                return "en_us_neutral"
        return cleaned

    if not isinstance(script_data, dict):
        return None

    corpus = []
    for key in ("prompt_params", "content_metadata", "metadata"):
        block = script_data.get(key)
        if isinstance(block, dict):
            for val in block.values():
                if isinstance(val, str):
                    corpus.append(val.lower())
                elif isinstance(val, (list, tuple)):
                    corpus.extend(str(v).lower() for v in val)
    if isinstance(script_data.get("script_text"), str):
        corpus.append(script_data["script_text"].lower())
    combined = " ".join(corpus)

    if lang == "spanish":
        if any(k in combined for k in ("spain", "españa", "castellano", "castilian", "rae", "real academia", "peninsular", "madrid")):
            return "es_spain_castilian"
        if any(k in combined for k in ("latin america", "latinoamérica", "latam", "latin_american")):
            return "es_latam_neutral"
    elif lang == "english":
        if any(k in combined for k in ("british", "uk accent", "united kingdom", "england", "queen's english", "in the uk", "london")):
            return "en_uk_neutral"
        if any(k in combined for k in ("american english", "us accent", "united states", "in the us")):
            return "en_us_neutral"
    elif lang == "french":
        return "fr_standard"
    elif lang == "italian":
        return "it_standard"

    return None


def resolve_voice_context(
    language: str,
    video_type: str,
    script_data: Optional[dict] = None,
    explicit_accent: Optional[str] = None,
) -> Tuple[LanguageVoiceProfile, VideoTypeVoiceProfile, Optional[str]]:
    """Loads the language profile, video-type profile, and optional dialect hint."""
    from ..languages import get_language_voice_profile
    from ..types import get_video_type_voice_profile

    lang_profile = get_language_voice_profile(language)
    type_profile = get_video_type_voice_profile(video_type)
    dialect_hint = detect_dialect_hint(language, script_data=script_data, explicit_accent=explicit_accent)
    return lang_profile, type_profile, dialect_hint


def _normalize_section_bucket(section: str) -> str:
    sec = str(section or "").strip().lower()
    for key in ("hook", "challenge", "pressure", "answer", "explanation", "discovery", "reveal", "example", "payoff", "cta"):
        if key in sec:
            return key
    if "dialogue" in sec:
        return "dialogue"
    return sec


def compute_segment_sampling(
    lang_profile: LanguageVoiceProfile,
    type_profile: VideoTypeVoiceProfile,
    section: str,
    is_dialogue_speaker: bool,
    prosody_flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Computes Qwen3-TTS sampling overrides from language, video type, beat, and punctuation."""
    base = lang_profile.dialogue_sampling if is_dialogue_speaker else lang_profile.narrator_sampling
    temp = base.temperature
    sub_temp = base.subtalker_temperature

    bucket = _normalize_section_bucket(section)
    delta_temp, delta_sub = type_profile.beat_sampling_deltas.get(bucket, (0.0, 0.0))
    temp += delta_temp
    sub_temp += delta_sub

    flags = prosody_flags or {}
    # Protect GAME quiz challenge neutrality (no stress/enthusiasm giveaway on the right option)
    if not (type_profile.neutral_challenge_lock and bucket == "challenge"):
        if flags.get("has_question"):
            temp += lang_profile.question_temp_delta
            sub_temp += lang_profile.question_temp_delta * 0.4
        if flags.get("has_exclamation"):
            temp += lang_profile.exclamation_temp_delta
            sub_temp += lang_profile.exclamation_temp_delta * 0.4

    temp = round(max(0.65, min(0.90, temp)), 3)
    sub_temp = round(max(0.68, min(0.86, sub_temp)), 3)

    return {
        "temperature": temp,
        "top_p": base.top_p,
        "top_k": base.top_k,
        "subtalker_temperature": sub_temp,
        "repetition_penalty": base.repetition_penalty,
    }
