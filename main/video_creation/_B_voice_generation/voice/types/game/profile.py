"""voice/types/game/profile.py & __init__.py — Complete GAME vocal profile."""
from ...common.models import VideoTypeVoiceProfile
from .mastering import GAME_MASTERING_PRESET
from .pauses import GAME_PAUSE_CHOREOGRAPHY

GAME_VOICE_PROFILE = VideoTypeVoiceProfile(
    video_type="game",
    pauses=GAME_PAUSE_CHOREOGRAPHY,
    mastering=GAME_MASTERING_PRESET,
    beat_sampling_deltas={
        "hook": (0.05, 0.04),
        "challenge": (-0.06, -0.05),
        "pressure": (0.04, 0.04),
        "answer": (0.06, 0.05),
        "explanation": (0.0, 0.0),
    },
    high_impact_sections=("hook", "pressure", "answer", "payoff", "cta"),
    use_option_micro_pauses=True,
    neutral_challenge_lock=True,
    support_multi_energy_roles=False,
    preferred_narrator_archetypes=("energetic_host", "warm_narrator"),
)
