"""voice/types/expression/profile.py — Complete EXPRESSION charismatic mentor vocal profile."""
from ...common.models import VideoTypeVoiceProfile
from .mastering import EXPRESSION_MASTERING_PRESET
from .pauses import EXPRESSION_PAUSE_CHOREOGRAPHY

EXPRESSION_VOICE_PROFILE = VideoTypeVoiceProfile(
    video_type="expression",
    pauses=EXPRESSION_PAUSE_CHOREOGRAPHY,
    mastering=EXPRESSION_MASTERING_PRESET,
    beat_sampling_deltas={
        "hook": (0.01, 0.01),
        "discovery": (0.02, 0.02),
        "reveal": (0.01, 0.01),
        "example": (-0.02, -0.02),
        "payoff": (0.0, 0.0),
    },
    high_impact_sections=("hook", "discovery", "reveal", "payoff", "cta"),
    use_option_micro_pauses=False,
    neutral_challenge_lock=False,
    support_multi_energy_roles=False,
    preferred_narrator_archetypes=("warm_narrator", "energetic_host"),
    target_cps_override=11.2,
    max_cps_override=14.5,
    target_wpm_range=(130.0, 140.0),
    max_wpm=145.0,
    apply_pace_safety_net=True,
)
