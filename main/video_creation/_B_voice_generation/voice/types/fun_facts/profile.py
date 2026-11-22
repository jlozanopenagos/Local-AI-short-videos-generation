"""voice/types/fun_facts/profile.py — Complete FUN_FACTS documentary vocal profile."""
from ...common.models import VideoTypeVoiceProfile
from .mastering import FUN_FACTS_MASTERING_PRESET
from .pauses import FUN_FACTS_PAUSE_CHOREOGRAPHY

FUN_FACTS_VOICE_PROFILE = VideoTypeVoiceProfile(
    video_type="fun_facts",
    pauses=FUN_FACTS_PAUSE_CHOREOGRAPHY,
    mastering=FUN_FACTS_MASTERING_PRESET,
    beat_sampling_deltas={
        "hook": (0.01, 0.01),
        "discovery": (0.02, 0.02),
        "reveal": (0.01, 0.01),
        "explanation": (-0.03, -0.02),
        "payoff": (0.0, 0.0),
    },
    high_impact_sections=("hook", "discovery", "reveal", "surprise", "payoff", "cta"),
    use_option_micro_pauses=False,
    neutral_challenge_lock=False,
    support_multi_energy_roles=False,
    preferred_narrator_archetypes=("warm_narrator", "energetic_host"),
    target_cps_override=11.8,
    max_cps_override=15.2,
    target_wpm_range=(130.0, 140.0),
    max_wpm=148.0,
    apply_pace_safety_net=True,
)
