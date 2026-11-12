"""
gemini_auditor.py — External creative auditor for Master Story World & General Prompts.

Uses Google Gemini to review the script context and eliminate local LLM bias,
generating an authentic, vivid, non-repetitive physical setting and character ensemble.

Architecture (Option 1: Modular 7-Part Generator + Python Static Tail + Result Checker):
- Gemini generates strictly Parts 1 to 7 (Camera framing, Setting, Character 1, Character 2,
  Midground Props, Background Architecture, Lighting & Shadows).
- Parts 8 (Style Pillars) and 9 (Negative Shield) are constant and appended automatically in Python,
  saving ~90-110 output tokens per call and preventing truncation.
- Result Checker validates completeness, word count, entity pillars, and sentence endings,
  automatically retrying up to 3 times if cut off or truncated.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

MAIN_DIR = Path(__file__).resolve().parent.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

logger = logging.getLogger(__name__)

GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]

# ==============================================================================
# IMMUTABLE PRODUCTION ANCHORS (PARTS 8 & 9)
# Appended automatically in Python to eliminate token waste and guarantee adherence
# ==============================================================================

POSITIVE_STYLE_PILLAR = (
    "Clean modern 2D cartoon narrative illustration, stylized 2D animation art style, "
    "vibrant flat colors, bold outlines, expressive character design with large clear cartoon eyes, "
    "visible white sclera and specular pupil highlights, rich detailed environmental interior background "
    "with depth and warm atmospheric lighting."
)

NEGATIVE_PROMPT_SHIELD = (
    "(thematic setting visible, explicit footwear on feet, NO bare feet, NO dot eyes, "
    "NO minimalist faces, NO blank backgrounds, NO 3D, NO realism, NO photograph, NO text, "
    "NO speech bubbles, NO floating symbols)"
)


def _clean_gemini_output(raw_text: str) -> str:
    """Cleans up Gemini output to guarantee raw prompt text with zero markdown or conversational baggage."""
    text = (raw_text or "").strip()

    # 1. Strip markdown code fences (```markdown ... ``` or ```text ... ``` or ``` ... ```)
    fence_pattern = r"^```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)\n?```$"
    m = re.match(fence_pattern, text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()

    # 2. Strip conversational prefixes
    prefix_pattern = (
        r"^(?:(?:Here is|Here's) (?:the |a )?(?:new |audited |revised )?(?:general |master )?prompt[:\s]*|"
        r"(?:General Prompt|Master Story World|Prompt|Visual Prompt|Core Prompt)[:\s]*)\s*"
    )
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()

    # 3. Strip outer enclosing double or single quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return text


def _strip_redundant_tails(text: str) -> str:
    """Removes any accidental duplicate style tags or negative shields if Gemini echoed them."""
    cleaned = text.strip()
    # Strip trailing parenthetical negative shields
    cleaned = re.sub(r'\(thematic setting visible[^)]*\)', '', cleaned, flags=re.IGNORECASE).strip()
    # Strip any trailing "Clean modern 2D cartoon narrative illustration..."
    cleaned = re.sub(
        r'Clean modern 2D cartoon narrative illustration.*$',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL
    ).strip()
    return cleaned.rstrip('. ')


def validate_gemini_core_prompt(
    text: str,
    finish_reason: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Automated Result Checker:
    Validates that Gemini returned a complete, rich, non-truncated visual prompt core (Parts 1-7).
    """
    if finish_reason == "MAX_TOKENS":
        return False, "Output was truncated (hit maxOutputTokens ceiling)"

    cleaned = text.strip()
    if not cleaned:
        return False, "Output is blank"

    # Check for sentence completion first (must end with terminal punctuation)
    tail = cleaned.rstrip(' "\'')
    if not tail.endswith(('.', '!', '?', ';')):
        return False, f"Prompt was cut off mid-sentence (ends with: '{cleaned[-30:]}')"

    words = cleaned.split()
    if len(words) < 55:
        return False, f"Prompt core too short ({len(words)} words; minimum 55 required for complete 7-part scene)"

    lower = cleaned.lower()

    # Pillar: Camera framing (Part 1)
    has_camera = any(w in lower for w in [
        "shot", "angle", "view", "eye-level", "framing", "perspective", "close-up", "wide"
    ])
    if not has_camera:
        return False, "Missing Camera Shot & Framing Angle (Part 1)"

    # Pillar: Characters & Wardrobe (Parts 3-4)
    has_character = any(w in lower for w in [
        "character", "student", "boy", "girl", "narrator", "peer", "friend",
        "intern", "colleague", "wear", "wearing", "jacket", "shirt", "cardigan",
        "trousers", "skirt", "blouse", "shoes", "loafers", "boots"
    ])
    if not has_character:
        return False, "Missing Character Ensemble & Wardrobe descriptions (Parts 3-4)"

    # Pillar: Lighting & Atmosphere (Part 7)
    has_lighting = any(w in lower for w in [
        "light", "lighting", "sun", "sunlight", "shadow", "shadows", "amber",
        "glow", "glowing", "beam", "warm", "cool", "lamp", "rays", "illuminated"
    ])
    if not has_lighting:
        return False, "Missing Lighting & Shadow Architecture (Part 7)"

    return True, "Valid"


def audit_general_prompt(
    script_data: Dict[str, Any],
    current_prompt: str = "",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Calls Google Gemini REST API to audit and rewrite the Master Story World / General Prompt.
    Uses Option 1: Modular 7-Part generation with Result Checker and automatic 3-attempt retry loop.

    Parameters
    ----------
    script_data:
        Full script state dict from StateManager.
    current_prompt:
        Existing general prompt to be audited/reimagined. If empty, falls back to script state.
    api_key:
        Gemini API key. If omitted, checks GEMINI_API_KEY env var or config.
    model:
        Gemini model identifier (default: gemini-2.5-flash, fallback: gemini-3.5-flash-lite).
    timeout:
        Network request timeout in seconds.

    Returns
    -------
    str: The complete, validated 9-part General Prompt with Parts 8 & 9 seamlessly appended.
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

    resolved_model = (model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)).strip()
    if not resolved_model:
        resolved_model = DEFAULT_MODEL

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

    # Compact script text
    raw_script = script_data.get("script_text", "")
    if isinstance(raw_script, dict):
        script_text = json.dumps(raw_script, ensure_ascii=False)
    else:
        script_text = str(raw_script)

    existing_gp = (current_prompt or script_data.get("assets", {}).get("general_prompt", "")).strip()

    # Dynamic creative lenses to force distinct, non-repetitive story worlds across successive runs
    creative_lenses = [
        "Artisanal & tactile craftsmanship (e.g. vintage printmaking studio, custom leathercraft bench, architectural blueprint drafting)",
        "Atmospheric daylight & architectural textures (e.g. amber sunbeams piercing paned storefront glass, slate-blue herringbone floor shadows)",
        "Vibrant cultural & vocational micro-world (e.g. vintage vinyl audio archive, municipal record hall, botanical pavilion, antique watchmaker bench)",
        "Lively character interaction & specialized setting tools (e.g. tailoring scissors, brass cash registers, drafting compasses, espresso machines)",
        "Dramatic spatial depth & layered background accents (e.g. mezzanine railings, paned street-facing windows with passersby, illuminated warm-wood shelving)",
    ]
    chosen_lens = random.choice(creative_lenses)
    run_seed = random.randint(100000, 999999)

    previous_contrast = ""
    if existing_gp:
        previous_contrast = (
            f"PREVIOUS DRAFT (FOR CONTRAST ONLY — DO NOT COPY OR REPEAT THIS SETTING):\n"
            f"\"{existing_gp}\"\n"
            "MANDATE: Invent a COMPLETELY DIFFERENT physical setting, atmosphere, and props from the draft above.\n\n"
        )

    # Build prompt enforcing ONLY Parts 1 to 7 and Anti-Cliché mandate
    prompt_text = (
        "You are an elite Visual Storyboard Director and Concept Artist for high-retention 2D animation Shorts.\n"
        "Your task is to audit and creatively write the Master Visual Story World for this Short to eliminate repetitive AI tropes.\n\n"
        f"CREATIVE DIRECTIVE [RUN #{run_seed}]:\n"
        f"Creative Focus for this take: {chosen_lens}.\n\n"
        f"SCRIPT ID: {script_id}\n"
        f"LANGUAGE: {language} ({video_type})\n"
        f"TOPIC/SITUATION: {topic}\n"
        f"SCRIPT DIALOGUE:\n{script_text}\n\n"
        f"{previous_contrast}"
        "==================================================\n"
        "STRICT PRODUCTION MANDATE (PARTS 1 TO 7 ONLY):\n"
        "==================================================\n"
        "Generate ONLY the narrative visual scene core (Parts 1 to 7). DO NOT include art style tags or negative prompt exclusions (these are appended automatically downstream).\n\n"
        "Follow this exact 7-part narrative structure in a single cohesive, richly detailed paragraph (~110-150 words):\n"
        "1. CAMERA SHOT & FRAMING: Open with 'Medium wide eye-level shot.' to guarantee lens perspective.\n"
        "2. THEMATIC SCENE CONTEXT: Ground the physical setting in an authentic, distinct real-world environment derived directly from the dialogue's concrete situation, conflict, or occupations.\n"
        "   ⚠️ ANTI-CLICHÉ BAN: Strictly DO NOT use generic AI clichés: BANNED are flea markets, pottery/ceramic workshops, rooftop greenhouses, generic modern coffee shops, or plain empty classrooms. Invent settings specifically reflecting the dialogue's reality (e.g. vintage record archive, municipal records office, antique clock repair workshop, architectural blueprint atelier, neighborhood tailor shop, sunlit bakery courtyard, maritime docks, tramway terminus).\n"
        f"3. CHARACTER 1 (Subject): One 15-16yo high-school student ({gender_desc}) with distinctive hairstyle (e.g. textured curls, sleek angled bob, braided half-up, tapered fade), expressive cartoon facial acting (wide cartoon eyes, specular pupil highlights), and layered, setting-appropriate wardrobe with explicit footwear.\n"
        f"4. CHARACTER 2 (Counterpart): The second 15-16yo student in an active complementary pose, with unique hair, wardrobe, and shoes.\n"
        "5. MIDGROUND ANCHOR PROPS: Concrete physical objects on the counter, table, or between characters that prevent hallucinations and anchor the interaction.\n"
        "6. ARCHITECTURAL BACKGROUND: Detailed cultural and architectural background textures providing authentic environmental depth.\n"
        "7. CINEMATIC LIGHTING & SHADOWS: Warm/cool color contrast (e.g. amber sunbeams casting slate-blue directional cast shadows across the floor).\n\n"
        "OUTPUT RULE: Return ONLY the raw prompt text for Parts 1 to 7. Zero markdown fences, zero quotes, zero commentary."
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
            "temperature": 0.95,
            "maxOutputTokens": 800,
        },
    }

    models_to_try = [resolved_model]
    for fb_model in FALLBACK_MODELS:
        if fb_model not in models_to_try:
            models_to_try.append(fb_model)

    last_error = None
    max_validation_attempts = 3

    for cur_model in models_to_try:
        url = GEMINI_API_URL_TEMPLATE.format(model=cur_model)
        for val_attempt in range(1, max_validation_attempts + 1):
            try:
                logger.info(
                    "[%s] Sending prompt audit request to Gemini (%s, attempt %d/%d)...",
                    script_id, cur_model, val_attempt, max_validation_attempts
                )
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

                    cand = candidates[0]
                    finish_reason = cand.get("finishReason", "")
                    content = cand.get("content", {})
                    parts = content.get("parts", [])
                    if not parts or "text" not in parts[0]:
                        raise ValueError(f"Gemini returned empty parts in candidate: {cand}")

                    raw_generated = parts[0]["text"]
                    cleaned_core = _clean_gemini_output(raw_generated)

                    # Automated Result Checker
                    is_valid, reason = validate_gemini_core_prompt(cleaned_core, finish_reason)
                    if not is_valid:
                        logger.warning(
                            "[%s] Gemini prompt validation failed (attempt %d/%d): %s",
                            script_id, val_attempt, max_validation_attempts, reason
                        )
                        if val_attempt < max_validation_attempts:
                            # Adjust temperature slightly to provoke a fresher completion
                            current_temp = payload["generationConfig"].get("temperature", 0.95)
                            payload["generationConfig"]["temperature"] = min(1.0, current_temp + 0.05)
                            time.sleep(1.0)
                            continue
                        else:
                            raise ValueError(f"Gemini output failed validation after {max_validation_attempts} attempts: {reason}")

                    # Strip any accidental duplicate style or negative tags
                    stripped_core = _strip_redundant_tails(cleaned_core)

                    # Stitch complete 9-part Master Story World prompt
                    final_prompt = f"{stripped_core}. {POSITIVE_STYLE_PILLAR} {NEGATIVE_PROMPT_SHIELD}"

                    logger.info(
                        "[%s] Successfully audited and stitched 9-part prompt with Gemini (%d chars).",
                        script_id, len(final_prompt)
                    )
                    return final_prompt

                elif response.status_code == 404:
                    logger.warning(
                        "[%s] Gemini model '%s' returned 404 Not Found. Trying next fallback model...",
                        script_id, cur_model
                    )
                    break
                elif response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        "[%s] Gemini model '%s' returned HTTP %d (%s). Falling back to next available model...",
                        script_id, cur_model, response.status_code, response.text[:200]
                    )
                    break
                else:
                    err_text = response.text[:300]
                    raise RuntimeError(
                        f"Gemini API returned HTTP {response.status_code}: {err_text}"
                    )

            except Exception as exc:
                last_error = exc
                if val_attempt < max_validation_attempts:
                    logger.warning(
                        "[%s] Gemini attempt %d failed: %s. Retrying...",
                        script_id, val_attempt, exc
                    )
                    time.sleep(1.0)
                    continue
                else:
                    break

    raise last_error or RuntimeError(f"[{script_id}] Gemini audit failed.")
