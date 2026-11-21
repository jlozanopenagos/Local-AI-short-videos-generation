"""voice/types/roleplay/pauses.py — Dramatic theatrical pause choreography for ROLEPLAY."""
from ...common.models import PauseChoreography

ROLEPLAY_PAUSE_CHOREOGRAPHY = PauseChoreography(
    section_gap=0.35,
    dialogue_section_gap=0.18,
    dialogue_gap=0.14,
    dialogue_cliffhanger_gap=0.24,
    paragraph_gap=0.20,
    pressure_gap=2.20,
    hook_to_next_gap=0.38,
    dialogue_to_payoff_gap=0.35,
    option_micro_pause=0.0,
)
