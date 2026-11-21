"""voice/types/roleplay/profile.py — Complete ROLEPLAY vocal profile."""
from ...common.models import VideoTypeVoiceProfile
from .mastering import ROLEPLAY_MASTERING_PRESET
from .pauses import ROLEPLAY_PAUSE_CHOREOGRAPHY

ROLEPLAY_VOICE_PROFILE = VideoTypeVoiceProfile(
    video_type="roleplay",
    pauses=ROLEPLAY_PAUSE_CHOREOGRAPHY,
    mastering=ROLEPLAY_MASTERING_PRESET,
    beat_sampling_deltas={
        "hook": (0.04, 0.03),
        "dialogue": (0.02, 0.02),
        "payoff": (0.03, 0.02),
        "cta": (0.02, 0.02),
    },
    high_impact_sections=("hook", "payoff", "cta"),
    use_option_micro_pauses=False,
    neutral_challenge_lock=False,
    support_multi_energy_roles=True,
    preferred_narrator_archetypes=("warm_narrator", "energetic_host"),
)
