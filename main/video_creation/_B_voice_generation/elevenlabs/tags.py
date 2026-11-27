"""
elevenlabs/tags.py — Provider routing, Eleven v3 audio-tag mapping, and pre-flight credit estimation.
Isolated from ComfyUI / Qwen3-TTS core modules.
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

SUPPORTED_ELEVENLABS_MODELS: Dict[str, Dict[str, Any]] = {
    "eleven_v3": {
        "id": "eleven_v3",
        "label": "Eleven v3 (Most Expressive — 1 cr/char)",
        "credits_per_char": 1.0,
        "supports_audio_tags": True,
    },
    "eleven_multilingual_v2": {
        "id": "eleven_multilingual_v2",
        "label": "Multilingual v2 (Classic Stable — 1 cr/char)",
        "credits_per_char": 1.0,
        "supports_audio_tags": False,
    },
    "eleven_flash_v2_5": {
        "id": "eleven_flash_v2_5",
        "label": "Flash v2.5 (Budget 2x — 0.5 cr/char)",
        "credits_per_char": 0.5,
        "supports_audio_tags": False,
    },
}

DEFAULT_ELEVENLABS_MODEL_ID = "eleven_v3"
DEFAULT_HYBRID_ELEVENLABS_TYPES = frozenset({"roleplay", "expression", "fun_facts"})

_LANGUAGE_CODE_MAP = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "italian": "it",
    "german": "de",
    "portuguese": "pt",
}

# Ordered emotion cue -> Eleven v3 inline Audio Tag mapping
_EMOTION_TO_V3_TAG: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("shock", "choqu", "scioccat", "stunn", "atónit", "atonit", "gasping"), "[gasps]"),
    (("baffl", "incredul", "surpris", "sorpren", "asombr", "stupit", "disbelief"), "[surprised]"),
    (("anxi", "ansia", "ansios", "panic", "nerv", "angoiss", "worri", "preocup", "agobiad", "urgent"), "[nervous]"),
    (("scared", "terrif", "afraid", "fear", "peur", "miedo", "paura", "spavent", "fright", "asustad"), "[fearful]"),
    (("chuckl", "laugh", "riend", "ridend", "hilarious", "giggle"), "[chuckles]"),
    (("teas", "smirk", "playful", "scherz", "brom", "amused", "divertid", "grin", "sonrien", "smil", "souri"), "[playfully]"),
    (("sarcas", "ironi", "moqu", "burl"), "[sarcastically]"),
    (("reliev", "soulag", "sollev", "alivi"), "[sighs] [relieved]"),
    (("embarrass", "fluster", "gêné", "gene", "avergonz", "imbarazz"), "[nervously]"),
    (("angry", "furious", "mad", "heated", "enoj", "enfad", "arrabbi", "colère", "colere", "indign", "confrontativ"), "[angry]"),
    (("frustr", "exasp", "agacé", "agace", "molest", "infastid", "annoy", "impatien", "énerv", "enerv"), "[frustrated]"),
    (("skept", "escéptic", "esceptic", "scettic", "confus", "perplex", "desconcert", "confund"), "[skeptical]"),
    (("whisper", "chuchot", "susurr", "sussurr"), "[whispers]"),
    (("deadpan", "serio", "serious", "dry", "impassib"), "[deadpan]"),
    (("excit", "happy", "joy", "enthousias", "entusias", "feliz", "alegr", "emozion", "emocion", "hyped", "celebrat", "delight"), "[excited]"),
    (("proud", "fier", "fiero", "orgull", "triumph", "boast"), "[proudly]"),
    (("calm", "tranquil", "rassur", "reassur", "rilassat", "relax", "pazient", "encourag", "warm"), "[warmly]"),
    (("curious", "curios", "intrig", "myster"), "[curious]"),
)

_NARRATOR_SECTION_TAGS: Dict[str, str] = {
    "hook": "[excited]",
    "title": "[excited]",
    "setup": "[curious]",
    "mystery": "[curious]",
    "discovery": "[excited]",
    "reveal": "[excited]",
    "answer": "[excited]",
    "payoff": "[warmly]",
    "cta": "[warmly]",
    "explanation": "[warmly]",
    "example": "[playfully]",
}


def normalize_elevenlabs_model(model_id: Optional[str]) -> str:
    clean = (model_id or "").strip().lower()
    if clean in SUPPORTED_ELEVENLABS_MODELS:
        return clean
    return DEFAULT_ELEVENLABS_MODEL_ID


def get_language_iso_code(language: str) -> str:
    clean = str(language or "english").split("|")[0].strip().lower()
    for key, code in _LANGUAGE_CODE_MAP.items():
        if key in clean or clean == code:
            return code
    return "en"


def resolve_voice_provider(
    video_type: str,
    requested_provider: Optional[str] = None,
    hybrid_types: Optional[Tuple[str, ...]] = None,
) -> str:
    """Resolves whether a script should synthesize via `'elevenlabs'` or `'local'` (Qwen3-TTS).

    - `'elevenlabs'` -> always ElevenLabs
    - `'local'` / `'qwen3'` / `'comfyui'` -> always Local Qwen3-TTS
    - `'auto'` (default) -> ElevenLabs for `ROLEPLAY`, `EXPRESSION`, & `FUN_FACTS`, Local Qwen3-TTS for `GAME`
    """
    req = (requested_provider or os.getenv("VOICE_PROVIDER", "") or "").strip().lower()
    if not req:
        try:
            import config
            req = str(getattr(config, "VOICE_PROVIDER", "auto") or "auto").strip().lower()
        except Exception:
            req = "auto"

    if req in ("elevenlabs", "eleven", "11labs"):
        return "elevenlabs"
    if req in ("local", "qwen3", "qwen", "comfyui", "comfy"):
        return "local"

    vtype_norm = (video_type or "expression").strip().lower().replace("-", "_").replace(" ", "_")
    if vtype_norm in ("role_play", "dialogue"):
        vtype_norm = "roleplay"
    elif vtype_norm in ("expressions", "idiom"):
        vtype_norm = "expression"
    elif vtype_norm in ("games", "quiz"):
        vtype_norm = "game"
    elif vtype_norm in ("fun_fact", "funfacts", "funfact", "facts"):
        vtype_norm = "fun_facts"

    if hybrid_types is None:
        try:
            import config
            hybrid_set = {str(t).strip().lower() for t in getattr(config, "ELEVENLABS_HYBRID_TYPES", DEFAULT_HYBRID_ELEVENLABS_TYPES)}
        except Exception:
            hybrid_set = set(DEFAULT_HYBRID_ELEVENLABS_TYPES)
    else:
        hybrid_set = {str(t).strip().lower() for t in hybrid_types}

    return "elevenlabs" if vtype_norm in hybrid_set else "local"


def map_emotion_to_v3_tag(
    emotion: str = "",
    text: str = "",
    section: str = "",
    is_narrator: bool = False,
) -> str:
    """Maps a script's parenthetical emotion or section role to an Eleven v3 inline Audio Tag."""
    emo_low = (emotion or "").strip().lower()
    if emo_low and emo_low not in ("neutral", "none", "normal"):
        for cues, tag in _EMOTION_TO_V3_TAG:
            if any(c in emo_low for c in cues):
                return tag

    sec_low = (section or "").strip().lower()
    if is_narrator and sec_low in _NARRATOR_SECTION_TAGS:
        return _NARRATOR_SECTION_TAGS[sec_low]

    if not is_narrator:
        if "?!" in text or "!?" in text:
            return "[surprised]"
        if "!" in text:
            return "[excited]"
        if "?" in text:
            return "[curious]"

    return ""


def prepare_elevenlabs_text(
    text: str,
    *,
    emotion: str = "",
    section: str = "",
    model_id: str = DEFAULT_ELEVENLABS_MODEL_ID,
    is_narrator: bool = False,
) -> str:
    """Prepares spoken text for ElevenLabs, removing ComfyUI pause tags and injecting Eleven v3 Audio Tags."""
    cleaned = re.sub(r"\[(?:pause|p):\d+(?:\.\d+)?\]", " ", str(text or ""), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""

    norm_model = normalize_elevenlabs_model(model_id)
    if not SUPPORTED_ELEVENLABS_MODELS[norm_model]["supports_audio_tags"]:
        return cleaned

    tag = map_emotion_to_v3_tag(emotion=emotion, text=cleaned, section=section, is_narrator=is_narrator)
    if tag and not cleaned.startswith("["):
        return f"{tag} {cleaned}"
    return cleaned


def estimate_script_credits(
    script_data: Dict[str, Any],
    model_id: str = DEFAULT_ELEVENLABS_MODEL_ID,
) -> int:
    """Estimates ElevenLabs credit cost for one script based on its spoken text and model multiplier."""
    norm_model = normalize_elevenlabs_model(model_id)
    mult = float(SUPPORTED_ELEVENLABS_MODELS[norm_model]["credits_per_char"])
    supports_tags = bool(SUPPORTED_ELEVENLABS_MODELS[norm_model]["supports_audio_tags"])

    meta = script_data.get("content_metadata") or {}
    script_obj = meta.get("script")
    if not isinstance(script_obj, dict) or not script_obj:
        raw_txt = str(script_data.get("script_text") or "").strip()
        if raw_txt.startswith("{"):
            try:
                parsed = json.loads(raw_txt)
                if isinstance(parsed, dict):
                    script_obj = parsed
            except Exception:
                script_obj = None

    total_chars = 0
    if isinstance(script_obj, dict) and script_obj:
        for key, val in script_obj.items():
            if str(key).lower() in ("title", "game_archetype", "category", "subcategory", "topic", "learning_objective", "chalkboard_exercise"):
                continue
            raw_line = str(val or "")
            # Strip speaker labels like "PERSON_ONE (Anxious):" so estimate reflects actual spoken text
            for subline in raw_line.splitlines():
                sub = subline.strip()
                if not sub:
                    continue
                m = re.match(r"^(?:PERSON_(?:ONE|TWO)|NARRATOR)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$", sub, flags=re.IGNORECASE)
                if m:
                    emo = (m.group(1) or "").strip()
                    spoken = m.group(2).strip()
                    prepared = prepare_elevenlabs_text(spoken, emotion=emo, section=str(key), model_id=norm_model, is_narrator="narrator" in sub.lower())
                    total_chars += len(prepared)
                else:
                    prepared = prepare_elevenlabs_text(sub, section=str(key), model_id=norm_model, is_narrator=True)
                    total_chars += len(prepared)
    else:
        raw_txt = re.sub(r"\[(?:pause|p):\d+(?:\.\d+)?\]", " ", str(script_data.get("script_text") or ""), flags=re.IGNORECASE)
        total_chars = len(re.sub(r"\s+", " ", raw_txt).strip())
        if supports_tags and total_chars > 0:
            total_chars += 40

    return int(math.ceil(total_chars * mult))
