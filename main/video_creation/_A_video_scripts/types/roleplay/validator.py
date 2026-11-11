"""
types/roleplay/validator.py — Schema, character alternation, and word count validator for Roleplay.
Enforces the strict 2-speaker rule in every dialogue part and eliminates single-character monologues.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ...common.base_engine import ValidationResult
from ...common.text_utils import count_spoken_words

EXPECTED_ROLEPLAY_PARTS = ("DIALOGUE_PART_1", "DIALOGUE_PART_2", "DIALOGUE_PART_3", "DIALOGUE_PART_4")
MIN_ROLEPLAY_WORDS = 135
MAX_ROLEPLAY_WORDS = 195

BANNED_TUTOR_PATTERNS = [
    r"\bremember\s*:\s*[a-z]+\s+is\s+the\s+noun\b",
    r"\brecuerda\s*:\s*[a-z]+\s+es\s+el\s+sustantivo\b",
    r"\bstop\s+saying\b",
    r"\bstop\s+messing\s+up\b",
    r"\bfree\s+(?:coffee|pizza|latte)\s+on\s+the\s+line\b",
    r"\b(?:speak|sonar|parler|parlare)\s+(?:like\s+a\s+native|como\s+un\s+nativo|comme\s+un\s+natif|come\s+un\s+madrelingua)\b",
]


def validate_roleplay_script(
    script_dict: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """
    Validates roleplay JSON structure:
    1. Key presence: title, hook, DIALOGUE_PART_1..4, PAYOFF.
    2. Character presence: BOTH PERSON_ONE and PERSON_TWO must speak in every dialogue part!
    3. Narrator isolation: Narrator must NEVER speak inside dialogue parts.
    4. Anti-tutor checks: No banned cliché patterns.
    5. Spoken word count: strictly between 135 and 185 spoken words.
    """
    result = ValidationResult()

    if not isinstance(script_dict, dict):
        result.add_error("Script payload is not a JSON object.")
        return result

    # Check root vs nested script
    script_body = script_dict.get("script") if isinstance(script_dict.get("script"), dict) else script_dict

    # Normalize case of keys
    key_map = {str(k).upper(): k for k in script_body.keys()}

    # 1. Title and Hook
    if not script_body.get("title") and not script_body.get("TITLE"):
        result.add_error("Missing mandatory key: 'title'")

    hook_key = key_map.get("HOOK")
    hook_val = str(script_body.get(hook_key, "")).strip() if hook_key else ""
    if not hook_val:
        result.add_error("Missing mandatory key: 'hook'")
    else:
        for pat in BANNED_TUTOR_PATTERNS:
            if re.search(pat, hook_val, re.IGNORECASE):
                result.add_error(f"Hook contains banned cliché pattern matching '{pat}'")

    # 2. Payoff
    payoff_key = key_map.get("PAYOFF")
    payoff_val = str(script_body.get(payoff_key, "")).strip() if payoff_key else ""
    if not payoff_val:
        result.add_error("Missing mandatory key: 'PAYOFF'")
    else:
        for pat in BANNED_TUTOR_PATTERNS:
            if re.search(pat, payoff_val, re.IGNORECASE):
                result.add_error(f"Payoff contains banned tutor pattern matching '{pat}'")

    # 3. Dialogue Parts: Strict Two-Character Alternation
    for part_name in EXPECTED_ROLEPLAY_PARTS:
        real_key = key_map.get(part_name)
        if not real_key:
            result.add_error(f"Missing mandatory dialogue part: '{part_name}'")
            continue

        part_text = str(script_body.get(real_key, "")).strip()
        if not part_text:
            result.add_error(f"'{part_name}' is empty.")
            continue

        # Check for banned Narrator leak in dialogue
        if re.search(r"\bNARRATOR\b", part_text, re.IGNORECASE):
            result.add_error(
                f"'{part_name}' illegally contains 'NARRATOR'. Narrator is forbidden in dialogue sections!"
            )

        # Check that BOTH PERSON_ONE and PERSON_TWO are present
        has_p1 = bool(re.search(r"\bPERSON[_\s]*(?:ONE|1)\b", part_text, re.IGNORECASE))
        has_p2 = bool(re.search(r"\bPERSON[_\s]*(?:TWO|2)\b", part_text, re.IGNORECASE))

        if not has_p1:
            result.add_error(
                f"'{part_name}' is missing PERSON_ONE! Each dialogue part must contain both characters."
            )
        if not has_p2:
            result.add_error(
                f"'{part_name}' is missing PERSON_TWO! Each dialogue part must contain both characters."
            )

    # 4. Spoken word count validation
    spoken_words = count_spoken_words(script_body)
    result.spoken_words = spoken_words

    if spoken_words < MIN_ROLEPLAY_WORDS:
        result.add_error(
            f"Spoken word count too low: {spoken_words} words (minimum required is {MIN_ROLEPLAY_WORDS})."
        )
    elif spoken_words > MAX_ROLEPLAY_WORDS:
        result.add_error(
            f"Spoken word count too high: {spoken_words} words (maximum allowed is {MAX_ROLEPLAY_WORDS})."
        )

    # 5. Language Check (prevent English leakage in French, Spanish, Italian scripts)
    target_lang = str(
        (input_data.get("LANGUAGE") or input_data.get("language") or "") if input_data else ""
    ).strip().lower()
    full_text = " ".join(str(v) for v in script_body.values())

    if target_lang and target_lang != "english":
        english_indicators = {
            "the", "this", "that", "with", "your", "about", "imagine", "trying",
            "saying", "sounds", "like", "common", "idiom", "leaving", "someone",
            "means", "when", "after", "before", "people", "would", "could", "should",
            "because", "friend", "making", "mistake", "theater", "lucky"
        }
        text_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{2,}\b", full_text)]
        eng_count = sum(1 for w in text_words if w in english_indicators)
        if len(text_words) > 0 and (eng_count / len(text_words)) > 0.12:
            result.add_error(
                f"Language mismatch: Script was generated in English, but target language is {target_lang.upper()}! "
                f"The entire script must be written 100% in {target_lang.upper()}."
            )

    # 6. Target Expression Presence in Dialogue
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
    if target_expr and target_expr.upper() != script_id and len(target_expr) < 60:
        dialogue_corpus = " ".join(
            str(script_body.get(key_map.get(part, part), ""))
            for part in EXPECTED_ROLEPLAY_PARTS
        ).lower()
        expr_clean = target_expr.lower().strip()
        expr_keywords = [w for w in re.findall(r"\b[\w'-]+\b", expr_clean) if len(w) >= 3]

        expr_in_dialogue = expr_clean in dialogue_corpus
        keywords_in_dialogue = (
            all(w in dialogue_corpus for w in expr_keywords)
            if expr_keywords
            else expr_in_dialogue
        )
        if not (expr_in_dialogue or keywords_in_dialogue):
            result.add_error(
                f"Target expression '{target_expr}' was not spoken in any dialogue part! At least one character must speak the expression."
            )

    return result

