"""
gemini_auditor.py — External creative auditor for Master Story World & General Prompts.

Uses Google Gemini (gemini-2.5-flash / gemini-1.5-flash) to review the script context
and eliminate local LLM bias, providing a fresh, vivid, authentic thematic setting
and character wardrobe while strictly adhering to 2D cartoon narrative style.

Engineered for strict token conservation:
- Compact input context (~250-350 tokens)
- Hard output token cap (maxOutputTokens: 350)
- Lightweight direct REST API via requests (zero heavy SDK dependencies)
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)

GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
FALLBACK_MODEL = "gemini-1.5-flash"


def _clean_gemini_output(raw_text: str) -> str:
    """Cleans up Gemini output to guarantee raw prompt text with zero markdown or conversational baggage."""
    text = (raw_text or "").strip()

    # 1. Strip markdown code fences (```markdown ... ``` or ```text ... ``` or ``` ... ```)
    fence_pattern = r"^```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)\n?```$"
    m = re.match(fence_pattern, text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()

    # 2. Strip conversational prefixes like "Here is the new general prompt:", "New Prompt:", etc.
    prefix_pattern = r"^(?:(?:Here is|Here's) (?:the |a )?(?:new |audited |revised )?(?:general |master )?prompt[:\s]*|(?:General Prompt|Master Story World|Prompt)[:\s]*)\s*"
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()

    # 3. Strip outer enclosing double or single quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return text


def audit_general_prompt(
    script_data: Dict[str, Any],
    current_prompt: str = "",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Calls Google Gemini REST API to audit and rewrite the Master Story World / General Prompt.

    Parameters
    ----------
    script_data:
        Full script state dict from StateManager.
    current_prompt:
        Existing general prompt to be audited/reimagined. If empty, falls back to script state.
    api_key:
        Gemini API key. If omitted, checks GEMINI_API_KEY env var or config.
    model:
        Gemini model identifier (default: gemini-2.5-flash, fallback: gemini-1.5-flash).
    timeout:
        Network request timeout in seconds.

    Returns
    -------
    str: The clean, diversified General Prompt.
    """
    resolved_api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not resolved_api_key:
        try:
            import config
            resolved_api_key = getattr(config, "GEMINI_API_KEY", "").strip()
        except Exception:
            pass

    if not resolved_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Please add GEMINI_API_KEY to your .env file."
        )

    resolved_model = (model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")).strip()
    if not resolved_model:
        resolved_model = "gemini-2.5-flash"

    # Extract script metadata concisely
    script_id = script_data.get("id") or script_data.get("script_id") or "SCRIPT"
    content_meta = script_data.get("content_metadata", {})
    prompt_params = script_data.get("prompt_params", {})
    metadata = script_data.get("metadata", {})

    language = content_meta.get("language") or metadata.get("LABEL") or "English"
    video_type = (content_meta.get("video_type") or prompt_params.get("VIDEO_TYPE") or "EXPRESSION").upper()
    topic = (
        content_meta.get("topic")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or content_meta.get("target_expression")
        or metadata.get("TITLE")
        or ""
    )

    # Format speakers/gender description
    speakers_gender = content_meta.get("speakers_gender", {})
    if isinstance(speakers_gender, dict) and speakers_gender:
        gender_desc = ", ".join(f"{k}: {v}" for k, v in speakers_gender.items())
    else:
        gender_desc = "one 15-16yo high-school student boy, one 15-16yo high-school student girl"

    # Compact script text (prefer raw text or compact json)
    raw_script = script_data.get("script_text", "")
    if isinstance(raw_script, dict):
        script_text = json.dumps(raw_script, ensure_ascii=False)
    else:
        script_text = str(raw_script)

    existing_gp = (current_prompt or script_data.get("assets", {}).get("general_prompt", "")).strip()

    # Build concise, token-efficient prompt
    prompt_text = (
        "You are an expert visual director for 2D cartoon narrative animations (Z-Image-Turbo/Lumina2).\n"
        "Audit and creatively rewrite the Master Story World & General Prompt for this Short to eliminate local AI bias and repetitive settings.\n\n"
        f"SCRIPT ID: {script_id}\n"
        f"LANGUAGE: {language} ({video_type})\n"
        f"TOPIC/SITUATION: {topic}\n"
        f"SCRIPT DIALOGUE:\n{script_text}\n\n"
        f"CURRENT GENERAL PROMPT TO REIMAGINE:\n\"{existing_gp}\"\n\n"
        "AUDIT DIRECTIVES (TOKEN MINIMAL):\n"
        "1. PHYSICAL SETTING: Invent an authentic, distinctive, visually rich real-world physical setting tailored to the dialogue/topic "
        "(e.g. vintage flea market, bustling train station platform, cozy radio booth, artisan ceramic workshop, sunny outdoor skate plaza, rooftop botanical greenhouse, vintage diner). "
        "Strictly ban generic modern coffee shops, plain cafeterias, or blank empty rooms.\n"
        f"2. CHARACTERS: Two 15-16yo high-school students ({gender_desc}) with distinct hairstyles, expressive facial design, and specific thematic wardrobes matching the setting.\n"
        "3. ART STYLE: Polished modern 2D cartoon narrative illustration, stylized 2D animation art style, vibrant flat colors, bold outlines, expressive character design with large clear cartoon eyes, visible white sclera and specular pupil highlights, rich detailed background with depth and warm lighting.\n"
        "4. NEGATIVE TAGS (MANDATORY AT END): (thematic setting visible, explicit footwear on feet, NO bare feet, NO dot eyes, NO minimalist faces, NO blank backgrounds, NO 3D, NO realism, NO photograph, NO text, NO speech bubbles, NO floating symbols)\n"
        "5. STRICT FORMAT: Return ONLY the final prompt text (around 80-120 words). No commentary, no explanations, no quotes, no markdown fences."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_text
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 350,
        },
    }

    models_to_try = [resolved_model]
    if resolved_model != FALLBACK_MODEL:
        models_to_try.append(FALLBACK_MODEL)

    last_error = None
    for cur_model in models_to_try:
        url = GEMINI_API_URL_TEMPLATE.format(model=cur_model)
        try:
            logger.info("[%s] Sending prompt audit request to Gemini (%s)...", script_id, cur_model)
            response = requests.post(
                url,
                params={"key": resolved_api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError(f"Gemini returned no candidates in response: {data}")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts or "text" not in parts[0]:
                    raise ValueError(f"Gemini returned empty parts in candidate: {candidates[0]}")

                raw_generated = parts[0]["text"]
                cleaned_prompt = _clean_gemini_output(raw_generated)

                if not cleaned_prompt:
                    raise ValueError("Gemini returned blank prompt after cleaning.")

                logger.info(
                    "[%s] Successfully audited prompt with Gemini (%d chars).",
                    script_id, len(cleaned_prompt)
                )
                return cleaned_prompt

            elif response.status_code == 404 and cur_model != FALLBACK_MODEL:
                logger.warning(
                    "[%s] Gemini model '%s' returned 404 Not Found. Falling back to '%s'...",
                    script_id, cur_model, FALLBACK_MODEL
                )
                continue
            else:
                err_text = response.text[:300]
                raise RuntimeError(
                    f"Gemini API returned HTTP {response.status_code}: {err_text}"
                )

        except Exception as exc:
            last_error = exc
            if cur_model != models_to_try[-1]:
                logger.warning("[%s] Failed with model %s (%s). Retrying fallback...", script_id, cur_model, exc)
                continue

    raise last_error or RuntimeError(f"[{script_id}] Gemini audit failed.")
