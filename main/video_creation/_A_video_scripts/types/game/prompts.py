"""
types/game/prompts.py — Prompt builder for linguistic game scripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from .rules import GAME_RULES


def build_game_prompt(input_data: Dict[str, Any]) -> str:
    """Constructs the LLM generation prompt for a game short."""
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

    is_stress = bool(
        "stress" in special.lower()
        or "heteronym" in special.lower()
        or re.search(r"\b[A-Z]{2,}[a-z]+|\b[a-z]+[A-Z]{2,}", expr)
    )

    stress_instructions = ""
    if is_stress:
        stress_instructions = f"""
CRITICAL WORD STRESS / HETERONYM CONTRAST:
- The target pair is: '{expr}'
- In 'chalkboard_exercise', line 1 has the test sentence with the blank (___). The options MUST display the distinct uppercase syllable stress:
  [Sentence with ___ in {target_lang.upper()}]
  A) [First option, e.g. PROject or a project]
  B) [Second option, e.g. proJECT or to project]
- In spoken 'challenge' (audio narration), the Narrator reads the complete test sentence naturally with proper pronunciation, then voices the choices without raw blanks or spelling out all-caps letters:
  e.g. "The committee decided to project the quarterly results. Which one did you hear? A: a project.  B: to project."
"""

    context_details = []
    if subject:
        subj_guide = f"- LINGUISTIC FOCUS (SUBJECT): {subject}"
        s_lower = subject.lower()
        if "stress" in s_lower or "heteronym" in s_lower:
            subj_guide += " -> The quiz MUST test syllable stress distinction!"
        elif "idiom" in s_lower or "modismo" in s_lower:
            subj_guide += " -> The quiz MUST test the true idiomatic meaning vs a funny literal trap!"
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
{context_block}
{stress_instructions}
{target_mandate}

{GAME_RULES}

-----------------------------
MANDATORY JSON OUTPUT FORMAT
-----------------------------
You MUST return ONLY a valid JSON object matching this exact structure:
{{
  "title": "Catchy 3-6 word title in {target_lang.upper()} without emojis",
  "script": {{
    "title": "Same catchy title in {target_lang.upper()}",
    "hook": "Magnetic, fast-paced hook in {target_lang.upper()}",
    "challenge": "Spoken sentence without blanks + voiced options (A: ...  B: ...) in {target_lang.upper()}",
    "pressure": "Punchy countdown/urgency line in {target_lang.upper()}",
    "answer": "Direct reveal of winning option with linguistic punch in {target_lang.upper()}",
    "explanation": "Crisp real-life explanation and CTA/loop in {target_lang.upper()}"
  }},
  "chalkboard_exercise": "[Sentence with ___ in {target_lang.upper()}]\\nA) [Option A]\\nB) [Option B]"
}}
"""
    return prompt.strip()

