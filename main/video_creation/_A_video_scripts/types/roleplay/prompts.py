"""
types/roleplay/prompts.py — Prompt builder for authentic two-character roleplay shorts.
"""

from __future__ import annotations

from typing import Any, Dict

from .rules import ROLEPLAY_RULES


def build_roleplay_prompt(input_data: Dict[str, Any]) -> str:
    """Constructs the LLM generation prompt for a roleplay short."""
    script_id = input_data.get("SCRIPT_ID") or input_data.get("script_id") or "RP01"
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

    scenario = (
        input_data.get("ROLEPLAY_SCENARIO")
        or input_data.get("roleplay_scenario")
        or input_data.get("SCENARIO")
        or input_data.get("scenario")
        or ""
    )
    context = input_data.get("CONTEXT") or input_data.get("context") or ""
    subject = input_data.get("SUBJECT") or input_data.get("subject") or ""
    lexical = input_data.get("LEXICAL_FIELD") or input_data.get("lexical_field") or ""
    emotion = input_data.get("EMOTIONAL_TRIGGER") or input_data.get("emotional_trigger") or ""
    special = input_data.get("SPECIAL_TREATMENT") or input_data.get("special_treatment") or ""

    # If expr contains the whole scenario paragraph, extract quoted dialogue phrase if present
    focus_phrase = expr
    if len(expr) > 60:
        import re
        # Look for dialogue introduced at the end of scenario: e.g. ricane : '...' or diciendo '...'
        m_dialogue = re.search(r"[:\s]['\"]([^'\"]*?['\"]?[^'\"]+?)['\"][.!?]?\s*$", expr)
        if m_dialogue:
            focus_phrase = m_dialogue.group(1).strip()
        else:
            quotes = re.findall(r"(?:^|\s)['\"]([^'\"]{3,60})['\"](?:\s|$|[.!?])", expr)
            if quotes:
                focus_phrase = quotes[-1].strip()
            else:
                focus_phrase = ""
        if not scenario:
            scenario = expr

    situation_details = []
    if scenario:
        situation_details.append(f"- DRAMATIC PREMISE (ROLEPLAY_SCENARIO): {scenario} -> Drive the story and characters through this exact situation!")
    if subject:
        situation_details.append(f"- LINGUISTIC FOCUS (SUBJECT): {subject} -> Ensure the dialogue naturally centers on this linguistic phenomenon!")
    if lexical:
        situation_details.append(f"- PHYSICAL SETTING (LEXICAL_FIELD): {lexical} -> Characters must interact with props and vocabulary from this setting!")
    if emotion:
        situation_details.append(f"- CHARACTER ENERGY (EMOTIONAL_TRIGGER): {emotion} -> Infuse character reactions and acting parentheticals with this dynamic!")
    if context:
        situation_details.append(f"- CONTEXT: {context}")
    if special:
        situation_details.append(f"- SPECIAL TREATMENT: {special}")

    situation_block = ""
    if situation_details:
        situation_block = "\nROLEPLAY SITUATION & CONTEXT:\n" + "\n".join(situation_details)

    lang_mandate = ""
    if target_lang.lower() != "english":
        lang_mandate = f"""
-------------------------------------------------------------
CRITICAL LANGUAGE MANDATE (100% {target_lang.upper()} ONLY - ZERO ENGLISH)
-------------------------------------------------------------
- EVERY SINGLE WORD in the entire JSON output ("title", "hook", "DIALOGUE_PART_1..4", "PAYOFF") MUST be written 100% in {target_lang.upper()}!
- Characters MUST speak authentic, colloquial {target_lang.upper()} naturally.
- Do NOT write in English under any circumstances.
"""

    target_mandate = ""
    if focus_phrase:
        target_mandate = f"""
-----------------------------
CRITICAL TARGET PHRASE MANDATE (ZERO TOLERANCE)
-----------------------------
- The core colloquial expression to be integrated into the dialogue is: "{focus_phrase}".
- One of the characters (PERSON_ONE or PERSON_TWO) MUST naturally speak this phrase during the dialogue.
- Do NOT substitute or invent random unrelated slang.
"""

    prompt = f"""You are the master YouTube Shorts script creator for viral, high-retention language learning dialogues.
Generate a complete, authentic ROLEPLAY video script for:
- SCRIPT ID: {script_id}
- TARGET LANGUAGE: {target_lang.upper()}
- TARGET EXPRESSION / PHENOMENON: {focus_phrase or expr or "Authentic peer dialogue"}
- SPECIAL TREATMENT: {special}
{lang_mandate}
{situation_block}
{target_mandate}

{ROLEPLAY_RULES}

-----------------------------
MANDATORY JSON OUTPUT FORMAT
-----------------------------
You MUST return ONLY a valid JSON object matching this exact structure:
{{
  "title": "Catchy situational scene title in {target_lang.upper()} (3-6 words, no emojis)",
  "script": {{
    "title": "Same catchy title in {target_lang.upper()}",
    "hook": "Magnetic situational setup in {target_lang.upper()} (15-20 words, do NOT include 'NARRATOR:' tag)",
    "DIALOGUE_PART_1": "PERSON_ONE (Acting Emotion): Opening realistic conversational line in {target_lang.upper()}...\\nPERSON_TWO (Acting Emotion): Immediate natural peer reaction in {target_lang.upper()}...",
    "DIALOGUE_PART_2": "PERSON_ONE (Acting Emotion): Follow-up line or humorous misunderstanding...\\nPERSON_TWO (Acting Emotion): Spontaneous peer clarification...",
    "DIALOGUE_PART_3": "PERSON_ONE (Acting Emotion): Playful nuance check or emotional reaction...\\nPERSON_TWO (Acting Emotion): Crisp real-life demo of the expression...",
    "DIALOGUE_PART_4": "PERSON_ONE (Acting Emotion): Comedic punchline or relief...\\nPERSON_TWO (Acting Emotion): Final witty remark...",
    "PAYOFF": "Punchy human takeaway + mandatory CTA in {target_lang.upper()} (20-25 words, do NOT include 'NARRATOR:' tag)"
  }}
}}
"""
    return prompt.strip()

