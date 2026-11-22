"""voice/types/roleplay/pauses.py — Dramatic theatrical pause choreography for ROLEPLAY."""
from ...common.models import PauseChoreography

ROLEPLAY_PAUSE_CHOREOGRAPHY = PauseChoreography(
    section_gap=0.55,
    dialogue_section_gap=0.42,
    dialogue_gap=0.30,
    dialogue_cliffhanger_gap=0.48,
    paragraph_gap=0.35,
    pressure_gap=2.20,
    hook_to_next_gap=0.65,
    dialogue_to_payoff_gap=0.65,
    option_micro_pause=0.0,
)
