"""
types/expression/validator.py — Schema and word count validator for Expression scripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ...common.base_engine import ValidationResult
from ...common.text_utils import count_spoken_words

EXPECTED_EXPRESSION_KEYS = ("title", "hook", "setup", "discovery", "example", "payoff")
MIN_EXPRESSION_WORDS = 80
MAX_EXPRESSION_WORDS = 120

BANNED_EXPRESSION_PATTERNS = [
    r"\bstop\s+saying\b",
    r"\barr[êe]te\s+de\s+dire\b",
    r"\bdeja\s+de\s+decir\b",
    r"\bsmetti\s+di\s+dire\b",
    r"\bchanges\s+everything\b",
    r"\bgame\s*changer\b",
    r"\bstop\s+making\s+this\s+mistake\b",
    r"\barr[êe]te\s+de\s+faire\s+cette\s+erreur\b",
    r"\bdeja\s+de\s+cometer\s+este\s+error\b",
    r"\bsmetti\s+di\s+fare\s+questo\s+errore\b",
]


def validate_expression_script(
    script_dict: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """Validates expression script JSON schema, mandatory keys, and spoken word counts."""
    result = ValidationResult()

    if not isinstance(script_dict, dict):
        result.add_error("Script payload is not a JSON object.")
        return result

    script_body = script_dict.get("script") if isinstance(script_dict.get("script"), dict) else script_dict

    # 1. Mandatory keys
    for key in EXPECTED_EXPRESSION_KEYS:
        val = str(script_body.get(key, "")).strip()
        if not val:
            result.add_error(f"Missing mandatory expression key: '{key}'")

    # 2. Cliché checks
    full_text = " ".join(str(v) for v in script_body.values())
    for pat in BANNED_EXPRESSION_PATTERNS:
        if re.search(pat, full_text, re.IGNORECASE):
            result.add_error(f"Script contains forbidden formulaic phrase matching '{pat}'")

    # 3. Spoken word count validation
    spoken_words = count_spoken_words(script_body)
    result.spoken_words = spoken_words

    if spoken_words < MIN_EXPRESSION_WORDS:
        result.add_error(
            f"Spoken word count too low: {spoken_words} words (minimum required is {MIN_EXPRESSION_WORDS})."
        )
    elif spoken_words > MAX_EXPRESSION_WORDS:
        result.add_error(
            f"Spoken word count too high: {spoken_words} words (maximum allowed is {MAX_EXPRESSION_WORDS})."
        )

    # 4. Language Check (prevent English leakage in French, Spanish, Italian scripts)
    target_lang = str(
        (input_data.get("LANGUAGE") or input_data.get("language") or "") if input_data else ""
    ).strip().lower()

    if target_lang and target_lang != "english":
        english_indicators = {
            "the", "this", "that", "with", "your", "about", "imagine", "trying",
            "saying", "sounds", "like", "common", "idiom", "leaving", "someone",
            "means", "when", "after", "before", "people", "would", "could", "should",
            "because", "friend", "making", "mistake"
        }
        text_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{2,}\b", full_text)]
        eng_count = sum(1 for w in text_words if w in english_indicators)
        if len(text_words) > 0 and (eng_count / len(text_words)) > 0.12:
            result.add_error(
                f"Language mismatch: Script was generated in English, but target language is {target_lang.upper()}! "
                f"The entire script must be written 100% in {target_lang.upper()}."
            )

    # 5. Target Expression Presence Verification
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
        disc_text = str(script_body.get("discovery", "")).lower()
        ex_text = str(script_body.get("example", "")).lower()
        full_text_lower = " ".join(str(v).lower() for v in script_body.values())

        expr_clean = target_expr.lower().strip()
        expr_keywords = [w for w in re.findall(r"\b[\w'-]+\b", expr_clean) if len(w) >= 3]

        expr_in_full = expr_clean in full_text_lower
        keywords_in_disc_or_ex = (
            all(w in (disc_text + " " + ex_text) for w in expr_keywords)
            if expr_keywords
            else (expr_clean in disc_text or expr_clean in ex_text)
        )

        if not (expr_in_full or keywords_in_disc_or_ex):
            result.add_error(
                f"Target expression '{target_expr}' was not found in the script (must be taught in 'discovery' or used in 'example')."
            )

    return result

