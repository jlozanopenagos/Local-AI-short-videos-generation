"""
types/fun_facts/validator.py — Schema and word count validator for Fun Facts scripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ...common.base_engine import ValidationResult
from ...common.text_utils import count_spoken_words

MIN_FUN_FACTS_WORDS = 90
MAX_FUN_FACTS_WORDS = 140

AUTHORIZED_FUN_FACTS_KEYS = {
    "title", "hook", "payoff",
    # Format A (Facts list)
    "fact_1", "fact_2", "fact_3", "fact_4", "fact_5", "fact",
    # Format B (Story / Curiosity)
    "setup", "discovery", "story", "context", "details", "explanation",
    # Format C (Challenge)
    "challenge", "thinking_time", "answer", "pressure", "question",
    # Format D (Mystery)
    "mystery", "clues", "reveal", "clue_1", "clue_2", "clue_3",
    # Format E (Comparison)
    "comparison_a", "comparison_b", "surprise",
    # Format F (Ranking/List)
    "item_1", "item_2", "item_3", "item_4", "item_5",
    # Optional helpers
    "cta", "curiosity", "example"
}


def validate_fun_facts_script(
    script_dict: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """Validates fun facts script JSON schema, mandatory keys, and spoken word counts."""
    result = ValidationResult()

    if not isinstance(script_dict, dict):
        result.add_error("Script payload is not a JSON object.")
        return result

    script_body = script_dict.get("script") if isinstance(script_dict.get("script"), dict) else script_dict
    keys_lower = {str(k).lower(): k for k in script_body.keys()}

    # 1. Mandatory keys
    if "title" not in keys_lower:
        result.add_error("Missing mandatory key: 'title'")
    if "hook" not in keys_lower:
        result.add_error("Missing mandatory key: 'hook'")
    if "payoff" not in keys_lower:
        result.add_error("Missing mandatory key: 'payoff'")

    # 2. Check for unauthorized keys
    illegal_keys = [k for k in script_body.keys() if str(k).lower() not in AUTHORIZED_FUN_FACTS_KEYS]
    if illegal_keys:
        result.add_error(f"Unauthorized invented keys in fun facts script: {', '.join(illegal_keys)}")

    # 3. Spoken word count validation
    spoken_words = count_spoken_words(script_body)
    result.spoken_words = spoken_words

    if spoken_words < MIN_FUN_FACTS_WORDS:
        result.add_error(
            f"Spoken word count too low: {spoken_words} words (minimum required is {MIN_FUN_FACTS_WORDS})."
        )
    elif spoken_words > MAX_FUN_FACTS_WORDS:
        result.add_error(
            f"Spoken word count too high: {spoken_words} words (maximum allowed is {MAX_FUN_FACTS_WORDS})."
        )

    return result

