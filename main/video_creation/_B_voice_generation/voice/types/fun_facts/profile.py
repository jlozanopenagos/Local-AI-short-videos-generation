"""voice/types/fun_facts/profile.py — Complete FUN_FACTS documentary vocal profile."""
from ...common.models import VideoTypeVoiceProfile
from .mastering import FUN_FACTS_MASTERING_PRESET
from .pauses import FUN_FACTS_PAUSE_CHOREOGRAPHY

FUN_FACTS_VOICE_PROFILE = VideoTypeVoiceProfile(
    video_type="fun_facts",
    pauses=FUN_FACTS_PAUSE_CHOREOGRAPHY,
    mastering=FUN_FACTS_MASTERING_PRESET,
    beat_sampling_deltas={
        "hook": (0.04, 0.03),
        "discovery": (0.04, 0.04),
        "reveal": (0.04, 0.04),
        "explanation": (-0.02, -0.02),
        "payoff": (0.02, 0.02),
    },
    high_impact_sections=("hook", "discovery", "reveal", "surprise", "payoff", "cta"),
    use_option_micro_pauses=False,
    neutral_challenge_lock=False,
    support_multi_energy_roles=False,
    preferred_narrator_archetypes=("warm_narrator", "energetic_host"),
)
