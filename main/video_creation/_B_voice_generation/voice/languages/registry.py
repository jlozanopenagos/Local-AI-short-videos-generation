"""voice/languages/registry.py — Lookup registry for LanguageVoiceProfile instances."""
from __future__ import annotations

from ..common.engine import normalize_voice_language
from ..common.models import LanguageVoiceProfile
from .english import ENGLISH_VOICE_PROFILE
from .french import FRENCH_VOICE_PROFILE
from .italian import ITALIAN_VOICE_PROFILE
from .spanish import SPANISH_VOICE_PROFILE

_PROFILES = {
    "english": ENGLISH_VOICE_PROFILE,
    "french": FRENCH_VOICE_PROFILE,
    "spanish": SPANISH_VOICE_PROFILE,
    "italian": ITALIAN_VOICE_PROFILE,
}


def get_language_voice_profile(language: str) -> LanguageVoiceProfile:
    """Returns the canonical `LanguageVoiceProfile` for any language string or compound label."""
    norm = normalize_voice_language(language)
    return _PROFILES.get(norm, ENGLISH_VOICE_PROFILE)
