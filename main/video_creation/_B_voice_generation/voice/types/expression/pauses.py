"""voice/types/expression/pauses.py — Idiom spotlight pause choreography for EXPRESSION."""
from ...common.models import PauseChoreography

EXPRESSION_PAUSE_CHOREOGRAPHY = PauseChoreography(
    section_gap=0.58,
    dialogue_section_gap=0.25,
    dialogue_gap=0.20,
    dialogue_cliffhanger_gap=0.30,
    paragraph_gap=0.38,
    pressure_gap=2.20,
    hook_to_next_gap=0.55,
    pre_discovery_gap=0.65,
    pre_example_gap=0.70,
    example_to_payoff_gap=0.60,
    option_micro_pause=0.0,
)
