"""
types/expression/prompts.py — Prompt builder for viral linguistic expression shorts.
"""

from __future__ import annotations

from typing import Any, Dict

from .rules import EXPRESSION_RULES


def build_expression_prompt(input_data: Dict[str, Any]) -> str:
    """Constructs the LLM generation prompt for an expression short."""
    script_id = input_data.get("SCRIPT_ID") or input_data.get("script_id") or "EXP01"
    target_lang = input_data.get("LANGUAGE") or input_data.get("language") or "English"
    expr = (
        input_data.get("TARGET_EXPRESSION")
        or input_data.get("target_expression")
        or input_data.get("EXPRESSION")
        or input_data.get("expression")
        or ""
    )
    # Sanitize if expr accidentally matches script_id
    if str(expr).strip().upper() == str(script_id).strip().upper():
        expr = ""

    scenario = input_data.get("SCENARIO") or input_data.get("scenario") or ""
    context = input_data.get("CONTEXT") or input_data.get("context") or ""
    angle = input_data.get("ANGLE") or input_data.get("angle") or input_data.get("HOOK_ANGLE") or ""
    lexical = input_data.get("LEXICAL_FIELD") or input_data.get("lexical_field") or ""
    subject = input_data.get("SUBJECT") or input_data.get("subject") or ""
    emotion = input_data.get("EMOTIONAL_TRIGGER") or input_data.get("emotional_trigger") or ""
    special = input_data.get("SPECIAL_TREATMENT") or input_data.get("special_treatment") or ""

    context_details = []
    if subject:
        subject_guide = f"- LINGUISTIC FOCUS (SUBJECT): {subject}"
        subj_lower = subject.lower()
        if "stress" in subj_lower or "heteronym" in subj_lower:
            subject_guide += " -> Teach the acoustic syllable stress shift and how emphasis changes meaning!"
        elif "confused" in subj_lower or "minimal pair" in subj_lower:
            subject_guide += " -> Teach the subtle distinction that non-natives mix up and natives notice immediately!"
        elif "idiom" in subj_lower or "modismo" in subj_lower:
            subject_guide += " -> Contrast the ridiculous literal meaning against the natural native usage!"
        context_details.append(subject_guide)

    if angle:
        context_details.append(f"- NARRATIVE ANGLE (ANGLE): {angle} -> Use this exact contrast/twist to build the 'hook' and 'setup'!")
    if context:
        context_details.append(f"- REAL-WORLD SITUATION (CONTEXT): {context} -> Anchor the situation and the 'example' dialogue in this setting!")
    if lexical:
        context_details.append(f"- THEMATIC VOCABULARY (LEXICAL_FIELD): {lexical} -> Infuse the dialogue and imagery with props and terms from this domain!")
    if emotion:
        context_details.append(f"- EMOTIONAL RESONANCE (EMOTIONAL_TRIGGER): {emotion} -> Infuse the hook, delivery, and payoff with this tone!")
    if scenario:
        context_details.append(f"- SCENARIO: {scenario}")
    if special:
        context_details.append(f"- SPECIAL FOCUS: {special}")

    context_block = ""
    if context_details:
        context_block = "\nSTORY CONTEXT & PEDAGOGICAL ANGLE:\n" + "\n".join(context_details)

    lang_mandate = ""
    if target_lang.lower() != "english":
        lang_mandate = f"""
-------------------------------------------------------------
CRITICAL LANGUAGE MANDATE (100% {target_lang.upper()} ONLY - ZERO ENGLISH)
-------------------------------------------------------------
- EVERY SINGLE WORD in the entire JSON output ("title", "hook", "setup", "discovery", "example", "payoff") MUST be written 100% in {target_lang.upper()}!
- STRICTLY FORBIDDEN: Do NOT write in English. Do NOT explain or translate in English.
- This short is produced FOR native / fluent {target_lang.upper()} viewers.
- Hook, setup, discovery, example, and payoff MUST be natural, authentic, viral {target_lang.upper()}.
"""

    target_mandate = ""
    if expr:
        target_mandate = f"""
-----------------------------
CRITICAL TARGET EXPRESSION MANDATE (ZERO TOLERANCE)
-----------------------------
- The exact expression being taught is: "{expr}".
- In "discovery": You MUST explicitly introduce, explain, or reveal the phrase "{expr}".
- In "example": You MUST demonstrate natural spoken dialogue containing "{expr}".
- STRICTLY FORBIDDEN: Do NOT substitute this phrase with another idiom, and do NOT invent alternative sayings (e.g. do not invent phrases like 'May the universe be on your side'). The video MUST be 100% about "{expr}".
"""

    prompt = f"""You are the master YouTube Shorts script creator for high-retention linguistic insights.
Generate a complete, viral EXPRESSION video script for:
- SCRIPT ID: {script_id}
- TARGET LANGUAGE: {target_lang.upper()}
- TARGET EXPRESSION: {expr}
{lang_mandate}
{context_block}
{target_mandate}

{EXPRESSION_RULES}

-----------------------------
MANDATORY JSON OUTPUT FORMAT
-----------------------------
You MUST return ONLY a valid JSON object matching this exact structure:
{{
  "title": "Catchy 3-6 word title in {target_lang.upper()} (no emojis)",
  "script": {{
    "title": "Same catchy title in {target_lang.upper()}",
    "hook": "Magnetic, fast-paced curiosity hook in {target_lang.upper()}",
    "setup": "Vivid context, contrast, or cultural dilemma in {target_lang.upper()}",
    "discovery": "The aha moment revealing the authentic idiom or nuance in {target_lang.upper()}",
    "example": "Natural, complete colloquial example spoken by natives in {target_lang.upper()}",
    "payoff": "Memorable human observation and mandatory CTA line in {target_lang.upper()}"
  }}
}}
"""
    return prompt.strip()

