"""voice/types/__init__.py — Re-exports per-video-type voice profiles and registry."""
from .expression import EXPRESSION_VOICE_PROFILE
from .fun_facts import FUN_FACTS_VOICE_PROFILE
from .game import GAME_VOICE_PROFILE
from .registry import get_video_type_voice_profile
from .roleplay import ROLEPLAY_VOICE_PROFILE

__all__ = [
    "EXPRESSION_VOICE_PROFILE",
    "FUN_FACTS_VOICE_PROFILE",
    "GAME_VOICE_PROFILE",
    "ROLEPLAY_VOICE_PROFILE",
    "get_video_type_voice_profile",
]
