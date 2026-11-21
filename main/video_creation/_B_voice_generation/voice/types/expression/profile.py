"""voice/types/expression/profile.py — Complete EXPRESSION charismatic mentor vocal profile."""
from ...common.models import VideoTypeVoiceProfile
from .mastering import EXPRESSION_MASTERING_PRESET
from .pauses import EXPRESSION_PAUSE_CHOREOGRAPHY

EXPRESSION_VOICE_PROFILE = VideoTypeVoiceProfile(
    video_type="expression",
    pauses=EXPRESSION_PAUSE_CHOREOGRAPHY,
    mastering=EXPRESSION_MASTERING_PRESET,
    beat_sampling_deltas={
        "hook": (0.04, 0.03),
        "discovery": (0.05, 0.04),
        "reveal": (0.04, 0.04),
        "example": (0.02, 0.02),
        "payoff": (0.02, 0.02),
    },
    high_impact_sections=("hook", "discovery", "reveal", "payoff", "cta"),
    use_option_micro_pauses=False,
    neutral_challenge_lock=False,
    support_multi_energy_roles=False,
    preferred_narrator_archetypes=("warm_narrator", "energetic_host"),
)
