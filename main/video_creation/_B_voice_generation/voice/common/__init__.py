"""voice/common/__init__.py — Re-exports shared Stage B modular voice utilities."""
from .bank_manifest import VoiceBankManifest, sanitize_ref_transcript
from .casting import VoiceCastingEngine, canonical_speaker_identity, pick_weighted_accent
from .dsp_mastering import apply_vocal_mastering
from .engine import (
    compute_segment_sampling,
    detect_dialect_hint,
    get_voice_engine_mode,
    is_typed_voice_enabled,
    normalize_voice_language,
    normalize_voice_video_type,
    resolve_voice_context,
)
from .models import (
    AcousticGateEnvelope,
    LanguageVoiceProfile,
    MasteringPreset,
    PauseChoreography,
    SamplingProfile,
    VideoTypeVoiceProfile,
    VoiceBankEntry,
)
from .punctuation import (
    ensure_spanish_inverted_punctuation,
    inject_game_option_micro_pauses,
    prepare_tts_prosody_text,
)

__all__ = [
    "AcousticGateEnvelope",
    "LanguageVoiceProfile",
    "MasteringPreset",
    "PauseChoreography",
    "SamplingProfile",
    "VideoTypeVoiceProfile",
    "VoiceBankEntry",
    "VoiceBankManifest",
    "VoiceCastingEngine",
    "apply_vocal_mastering",
    "canonical_speaker_identity",
    "compute_segment_sampling",
    "detect_dialect_hint",
    "ensure_spanish_inverted_punctuation",
    "get_voice_engine_mode",
    "inject_game_option_micro_pauses",
    "is_typed_voice_enabled",
    "normalize_voice_language",
    "normalize_voice_video_type",
    "pick_weighted_accent",
    "prepare_tts_prosody_text",
    "resolve_voice_context",
    "sanitize_ref_transcript",
]
