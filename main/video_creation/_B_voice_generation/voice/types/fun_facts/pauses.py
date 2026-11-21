"""voice/types/fun_facts/pauses.py — Curiosity-reveal pause choreography for FUN_FACTS."""
from ...common.models import PauseChoreography

FUN_FACTS_PAUSE_CHOREOGRAPHY = PauseChoreography(
    section_gap=0.34,
    dialogue_section_gap=0.20,
    dialogue_gap=0.15,
    dialogue_cliffhanger_gap=0.24,
    paragraph_gap=0.22,
    pressure_gap=2.20,
    hook_to_next_gap=0.32,
    pre_discovery_gap=0.45,
    option_micro_pause=0.0,
)
