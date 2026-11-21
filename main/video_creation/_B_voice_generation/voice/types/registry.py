"""voice/types/registry.py & __init__.py — Lookup registry for VideoTypeVoiceProfile instances."""
from __future__ import annotations

from ..common.engine import normalize_voice_video_type
from ..common.models import VideoTypeVoiceProfile
from .expression import EXPRESSION_VOICE_PROFILE
from .fun_facts import FUN_FACTS_VOICE_PROFILE
from .game import GAME_VOICE_PROFILE
from .roleplay import ROLEPLAY_VOICE_PROFILE

_TYPE_PROFILES = {
    "expression": EXPRESSION_VOICE_PROFILE,
    "game": GAME_VOICE_PROFILE,
    "roleplay": ROLEPLAY_VOICE_PROFILE,
    "fun_facts": FUN_FACTS_VOICE_PROFILE,
}


def get_video_type_voice_profile(video_type: str) -> VideoTypeVoiceProfile:
    """Returns the canonical `VideoTypeVoiceProfile` for expression/game/roleplay/fun_facts."""
    norm = normalize_voice_video_type(video_type)
    return _TYPE_PROFILES.get(norm, EXPRESSION_VOICE_PROFILE)
