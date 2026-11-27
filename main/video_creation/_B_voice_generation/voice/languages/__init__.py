"""voice/languages/__init__.py — Re-exports per-language voice profiles and registry."""
from .english import ENGLISH_VOICE_PROFILE
from .french import FRENCH_VOICE_PROFILE
from .italian import ITALIAN_VOICE_PROFILE
from .registry import get_language_voice_profile
from .spanish import SPANISH_VOICE_PROFILE

__all__ = [
    "ENGLISH_VOICE_PROFILE",
    "FRENCH_VOICE_PROFILE",
    "SPANISH_VOICE_PROFILE",
    "ITALIAN_VOICE_PROFILE",
    "get_language_voice_profile",
]
