"""
types/game/prompts.py — Prompt builder for linguistic game scripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from .archetypes import (
    ARCHETYPE_METADATA,
    detect_game_archetype,
    get_archetype_prompt_instructions,
)
from .rules import GAME_RULES


def build_game_prompt(input_data: Dict[str, Any]) -> str:
    """Constructs the LLM generation prompt for a game short with archetype specialization."""
    script_id = input_data.get("SCRIPT_ID") or input_data.get("script_id") or "GAME01"
    target_lang = input_data.get("LANGUAGE") or input_data.get("language") or "English"
    expr = (
        input_data.get("TARGET_EXPRESSION")
        or input_data.get("target_expression")
        or input_data.get("EXPRESSION")
        or input_data.get("expression")
        or ""
    )
    if str(expr).strip().upper() == str(script_id).strip().upper():
        expr = ""

    scenario = input_data.get("SCENARIO") or input_data.get("scenario") or ""
    context = input_data.get("CONTEXT") or input_data.get("context") or ""
    subject = input_data.get("SUBJECT") or input_data.get("subject") or ""
    lexical = input_data.get("LEXICAL_FIELD") or input_data.get("lexical_field") or ""
    special = input_data.get("SPECIAL_TREATMENT") or input_data.get("special_treatment") or ""

    # Detect or respect explicitly chosen game archetype
    archetype = detect_game_archetype(input_data)
    archetype_info = ARCHETYPE_METADATA.get(archetype, {})
    archetype_instructions = get_archetype_prompt_instructions(archetype, target_lang, expr)

    context_details = []
    if subject:
        subj_guide = f"- LINGUISTIC FOCUS (SUBJECT): {subject}"
        context_details.append(subj_guide)

    if context:
        context_details.append(f"- MEANING & NUANCE (CONTEXT): {context} -> The correct answer explanation MUST reflect this definition!")
    if lexical:
        context_details.append(f"- THEMATIC DOMAIN (LEXICAL_FIELD): {lexical} -> Set the test sentence and answer scenario in this world!")
    if scenario:
        context_details.append(f"- SCENARIO: {scenario}")

    context_block = ""
    if context_details:
        context_block = "\nCONTEXT & SITUATION:\n" + "\n".join(context_details)

    target_mandate = ""
    if expr:
        target_mandate = f"""
-----------------------------
CRITICAL TARGET CONTRAST MANDATE (ZERO TOLERANCE)
-----------------------------
- The exact target expression/contrast being tested is: "{expr}".
- The 'chalkboard_exercise', the spoken 'challenge', and the 'answer' MUST be specifically built around testing and explaining "{expr}".
- Do NOT test an unrelated random word.
"""

    prompt = f"""You are the master YouTube Shorts script creator for high-retention linguistic challenges.
Generate a complete, viral LINGUISTIC GAME video script for:
- SCRIPT ID: {script_id}
- TARGET LANGUAGE: {target_lang.upper()}
- TARGET WORD / CONTRAST: {expr}
- SELECTED GAME ARCHETYPE: {archetype} ({archetype_info.get('display_name', '')})
{context_block}
{target_mandate}

{archetype_instructions}

{GAME_RULES}

-----------------------------
MANDATORY JSON OUTPUT FORMAT
-----------------------------
You MUST return ONLY a valid JSON object matching this exact structure:
{{
  "title": "Catchy 3-6 word title in {target_lang.upper()} without emojis",
  "game_archetype": "{archetype}",
  "script": {{
    "title": "Same catchy title in {target_lang.upper()}",
    "hook": "Magnetic, fast-paced hook in {target_lang.upper()}",
    "challenge": "Spoken sentence without blanks + voiced options (A: ...  B: ...  C: ...) in {target_lang.upper()}",
    "pressure": "Punchy countdown/urgency line in {target_lang.upper()}",
    "answer": "Direct reveal of winning option with linguistic punch in {target_lang.upper()}",
    "explanation": "Crisp real-life explanation and CTA/loop in {target_lang.upper()}"
  }},
  "chalkboard_exercise": "[Test sentence in {target_lang.upper()}]\\nA) [Option A]\\nB) [Option B]\\nC) [Option C]\\nD) [Option D (if applicable)]"
}}
"""
    return prompt.strip()

