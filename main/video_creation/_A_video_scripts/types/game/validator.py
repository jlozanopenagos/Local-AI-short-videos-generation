"""
types/game/validator.py — Schema, structural rules, and word count validator for Game scripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ...common.base_engine import ValidationResult
from ...common.text_utils import count_spoken_words

EXPECTED_GAME_KEYS = ("title", "hook", "challenge", "pressure", "answer", "explanation")
MIN_GAME_WORDS = 95
MAX_GAME_WORDS = 135  # Accommodates 3 to 4 voiced options within 40-55s duration


def validate_game_script(
    script_dict: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """Validates game JSON structure, mandatory keys, audio/chalkboard separation, and word counts."""
    result = ValidationResult()

    if not isinstance(script_dict, dict):
        result.add_error("Script payload is not a JSON object.")
        return result

    # Check root vs nested script
    script_body = script_dict.get("script") if isinstance(script_dict.get("script"), dict) else script_dict

    # 1. Mandatory spoken keys
    for key in EXPECTED_GAME_KEYS:
        val = str(script_body.get(key, "")).strip()
        if not val:
            result.add_error(f"Missing or empty mandatory game key: '{key}'")

    # 2. Spoken challenge validation
    challenge = str(script_body.get("challenge", "")).strip()
    if challenge:
        # Check for banned raw blank in audio
        if re.search(r"_{2,}", challenge):
            result.add_error("Spoken 'challenge' contains raw blank ('___'). Audio must speak the sentence naturally!")

        # Check for voiced options
        has_opt_a = bool(re.search(r"\bA\s*[:\)\.\-]", challenge, re.IGNORECASE))
        has_opt_b = bool(re.search(r"\bB\s*[:\)\.\-]", challenge, re.IGNORECASE))
        if not (has_opt_a and has_opt_b):
            result.add_error("Spoken 'challenge' must explicitly voice both choices ('A: ...  B: ...').")

    # 3. Chalkboard exercise validation
    chalkboard = script_dict.get("chalkboard_exercise") or script_body.get("chalkboard_exercise", "")
    chalkboard_str = str(chalkboard).strip()
    if not chalkboard_str:
        result.add_error("Missing 'chalkboard_exercise' field.")
    else:
        lines = [l.strip() for l in chalkboard_str.splitlines() if l.strip()]
        if len(lines) < 2:
            result.add_error("'chalkboard_exercise' must be multiline (test sentence + options A and B).")
        has_board_a = any(re.match(r"^A\s*[:\)\.\-]", l, re.IGNORECASE) for l in lines)
        has_board_b = any(re.match(r"^B\s*[:\)\.\-]", l, re.IGNORECASE) for l in lines)
        if not (has_board_a and has_board_b):
            result.add_error("'chalkboard_exercise' must include separate lines for options 'A)' and 'B)'.")

    # 4. Spoken word count validation
    spoken_words = count_spoken_words(script_body)
    result.spoken_words = spoken_words

    if spoken_words < MIN_GAME_WORDS:
        result.add_error(
            f"Spoken word count too low: {spoken_words} words (minimum required is {MIN_GAME_WORDS})."
        )
    elif spoken_words > MAX_GAME_WORDS:
        result.add_error(
            f"Spoken word count too high: {spoken_words} words (maximum allowed is {MAX_GAME_WORDS})."
        )

    # 5. Target Expression/Contrast Verification
    target_expr = ""
    if input_data:
        target_expr = str(
            input_data.get("TARGET_EXPRESSION")
            or input_data.get("target_expression")
            or input_data.get("EXPRESSION")
            or input_data.get("expression")
            or ""
        ).strip()

    script_id = str(input_data.get("SCRIPT_ID", "") if input_data else "").strip().upper()
    if target_expr and target_expr.upper() != script_id:
        full_content = (
            " ".join(str(v).lower() for v in script_body.values())
            + " "
            + chalkboard_str.lower()
        )
        expr_clean = target_expr.lower().strip()
        expr_keywords = [w for w in re.findall(r"\b[\w'-]+\b", expr_clean) if len(w) >= 3]

        expr_found = (expr_clean in full_content) or (
            any(w in full_content for w in expr_keywords) if expr_keywords else False
        )
        if not expr_found:
            result.add_error(
                f"Target contrast/expression '{target_expr}' was not found in the game challenge or chalkboard."
            )

    return result

