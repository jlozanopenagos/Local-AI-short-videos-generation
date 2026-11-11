"""
types/fun_facts/prompts.py — Prompt builder for linguistic trivia and fun facts shorts.
"""

from __future__ import annotations

from typing import Any, Dict

from .rules import FUN_FACTS_RULES


def build_fun_facts_prompt(input_data: Dict[str, Any]) -> str:
    """Constructs the LLM generation prompt for a fun facts short."""
    script_id = input_data.get("SCRIPT_ID") or input_data.get("script_id") or "FACT01"
    target_lang = input_data.get("LANGUAGE") or input_data.get("language") or "English"
    topic = (
        input_data.get("TOPIC")
        or input_data.get("topic")
        or input_data.get("SUBJECT")
        or input_data.get("subject")
        or input_data.get("TARGET_EXPRESSION")
        or input_data.get("target_expression")
        or "Surprising Language Fact"
    )
    if str(topic).strip().upper() == str(script_id).strip().upper():
        topic = "Surprising Language Fact"

    context = input_data.get("CONTEXT") or input_data.get("context") or ""
    fact_details = input_data.get("FACT_DETAILS") or input_data.get("fact_details") or ""
    hook_angle = input_data.get("HOOK_ANGLE") or input_data.get("hook_angle") or input_data.get("ANGLE") or ""
    pillar = input_data.get("PILLAR") or input_data.get("pillar") or ""
    format_type = input_data.get("FORMAT") or input_data.get("format") or ""

    user_text = input_data.get("USER_PROVIDED_SCRIPT") or input_data.get("user_provided_script") or ""
    adaptation_block = ""
    if user_text:
        adaptation_block = f"""
EXTERNAL CONTENT TO ADAPT & POLISH:
\"\"\"{user_text}\"\"\"
Please reformat and calibrate this content into our viral high-retention structure below.
"""

    emotion = input_data.get("EMOTIONAL_TRIGGER") or input_data.get("emotional_trigger") or ""

    fact_details_block = []
    if hook_angle:
        fact_details_block.append(f"- OPENING HOOK ANGLE (HOOK_ANGLE): {hook_angle} -> Use this counter-intuitive puzzle to open the 'hook'!")
    if fact_details:
        fact_details_block.append(f"- FACTUAL EVIDENCE (FACT_DETAILS): {fact_details} -> Unpack these verified historical/linguistic facts in 'setup' and 'discovery'!")
    if pillar:
        fact_details_block.append(f"- LINGUISTIC PILLAR (PILLAR): {pillar} -> Frame the story through this academic/cultural domain!")
    if format_type:
        fact_details_block.append(f"- NARRATIVE FORMAT (FORMAT): {format_type}")
    if emotion:
        fact_details_block.append(f"- COGNITIVE REACTION (EMOTIONAL_TRIGGER): {emotion} -> Guide viewer from curiosity to total astonishment!")
    if context:
        fact_details_block.append(f"- CONTEXT: {context}")

    details_section = ""
    if fact_details_block:
        details_section = "\nFACT DETAILS & ANGLE:\n" + "\n".join(fact_details_block)

    target_mandate = f"""
-----------------------------
CRITICAL TOPIC MANDATE (ZERO TOLERANCE)
-----------------------------
- The exact language curiosity being taught is: "{topic}".
- The script MUST reveal and explain this exact linguistic mystery or cultural trivia.
- You MUST use the provided Fact Details. Do NOT invent fictional history or substitute an unrelated topic.
"""

    prompt = f"""You are the master YouTube Shorts script creator for viral language trivia and cultural curiosities.
Generate a complete, fascinating FUN FACTS video script for:
- SCRIPT ID: {script_id}
- TARGET LANGUAGE: {target_lang.upper()}
- TOPIC / CURIOSITY: {topic}
{details_section}
{target_mandate}
{adaptation_block}

{FUN_FACTS_RULES}

-----------------------------
MANDATORY JSON OUTPUT FORMAT
-----------------------------
You MUST return ONLY a valid JSON object matching this exact structure:
{{
  "title": "Fascinating 3-6 word title in {target_lang.upper()} (no emojis)",
  "script": {{
    "title": "Same catchy title in {target_lang.upper()}",
    "hook": "Magnetic curiosity gap hook in {target_lang.upper()}",
    "setup": "Surprising background or origin in {target_lang.upper()}",
    "discovery": "The astonishing twist or insight in {target_lang.upper()}",
    "explanation": "Crisp real-world connection in {target_lang.upper()}",
    "payoff": "Memorable takeaway + CTA in {target_lang.upper()}"
  }}
}}
"""
    return prompt.strip()

