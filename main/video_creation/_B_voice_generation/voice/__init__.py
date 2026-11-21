"""
voice/ — Modular Stage B Voice Generation engine split by language & video type.
"""
from .common.engine import (
    compute_segment_sampling,
    detect_dialect_hint,
    get_voice_engine_mode,
    is_typed_voice_enabled,
    resolve_voice_context,
)
from .languages import get_language_voice_profile
from .types import get_video_type_voice_profile

__all__ = [
    "compute_segment_sampling",
    "detect_dialect_hint",
    "get_language_voice_profile",
    "get_video_type_voice_profile",
    "get_voice_engine_mode",
    "is_typed_voice_enabled",
    "resolve_voice_context",
]
