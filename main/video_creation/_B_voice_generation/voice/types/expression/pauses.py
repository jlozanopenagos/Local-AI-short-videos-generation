"""voice/types/expression/pauses.py — Idiom spotlight pause choreography for EXPRESSION."""
from ...common.models import PauseChoreography

EXPRESSION_PAUSE_CHOREOGRAPHY = PauseChoreography(
    section_gap=0.32,
    dialogue_section_gap=0.18,
    dialogue_gap=0.15,
    dialogue_cliffhanger_gap=0.22,
    paragraph_gap=0.20,
    pressure_gap=2.20,
    hook_to_next_gap=0.28,
    pre_discovery_gap=0.38,
    option_micro_pause=0.0,
)
