"""
elevenlabs — Isolated ElevenLabs voice synthesis package for Stage B.
"""
from .catalog import ELEVENLABS_ACCENT_WEIGHTS, ElevenLabsVoiceCatalog, ElevenLabsVoiceEntry, pick_elevenlabs_accent
from .client import ElevenLabsClient, resolve_elevenlabs_api_key
from .orchestrator import synthesize_script_voice_elevenlabs
from .tags import (
    DEFAULT_ELEVENLABS_MODEL_ID,
    SUPPORTED_ELEVENLABS_MODELS,
    estimate_script_credits,
    map_emotion_to_v3_tag,
    normalize_elevenlabs_model,
    prepare_elevenlabs_text,
    resolve_voice_provider,
)

__all__ = [
    "DEFAULT_ELEVENLABS_MODEL_ID",
    "ELEVENLABS_ACCENT_WEIGHTS",
    "SUPPORTED_ELEVENLABS_MODELS",
    "ElevenLabsClient",
    "ElevenLabsVoiceCatalog",
    "ElevenLabsVoiceEntry",
    "estimate_script_credits",
    "map_emotion_to_v3_tag",
    "normalize_elevenlabs_model",
    "pick_elevenlabs_accent",
    "prepare_elevenlabs_text",
    "resolve_elevenlabs_api_key",
    "resolve_voice_provider",
    "synthesize_script_voice_elevenlabs",
]
