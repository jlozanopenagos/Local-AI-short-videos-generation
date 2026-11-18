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
DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
]

# ==============================================================================
# IMMUTABLE PRODUCTION ANCHORS (PARTS 8 & 9)
# Appended automatically in Python to eliminate token waste and guarantee adherence
# ==============================================================================

POSITIVE_STYLE_PILLAR = (
    "Clean modern 2D cartoon narrative illustration, stylized 2D animation art style, "
    "vibrant flat colors, bold outlines, expressive high-school student character design "
    "(approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child), "
    "expressive stylized cartoon eyes with natural lively shape and warm gaze, "
    "thematically authentic scene-specific wardrobe matching the environment (NO generic modern street clothes, NO plain t-shirts/hoodies), "
    "rich detailed environmental interior background with depth and warm atmospheric lighting."
)

NEGATIVE_PROMPT_SHIELD = (
    "(high-school student protagonist, thematic costume, thematic setting visible, explicit footwear on feet, NO bare feet, "
    "NO mature adult wrinkles, NO elderly, NO young children, NO elementary kids, NO childish proportions, "
    "NO generic casual t-shirts, NO plain hoodies, NO dot eyes, NO minimalist faces, NO blank backgrounds, "
    "NO bulging eyes, NO bug eyes, NO staring unblinking eyes, NO excessively open rounded eyes, NO unnatural wide eyes, "
    "NO deadpan blank face, NO emotionless expression, NO stiff mannequin pose, NO gaunt, NO emaciated, NO stick-figure proportions, "
    "NO 3D, NO 3D render, NO photorealism, NO realism, NO photograph, NO text, NO words, NO letters, NO quotes, "
    "NO signs with text, NO speech bubbles, NO floating symbols, NO subtitles, NO typography, NO watermark)"
)


def detect_script_domain(script_data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Analyzes script metadata, topic, scenario, and dialogue text to identify
    the real-world semantic domain and generate dynamic context guidance.
    """
    content_meta = script_data.get("content_metadata") or {}
    prompt_params = script_data.get("prompt_params") or {}
    metadata = script_data.get("metadata") or {}

    raw_topic = str(
        prompt_params.get("EXPRESSION")
        or prompt_params.get("TOPIC")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or content_meta.get("topic")
        or content_meta.get("target_expression")
        or metadata.get("TITLE")
        or ""
    )
    scenario = str(
        content_meta.get("roleplay_scenario")
        or content_meta.get("story_scenario")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("CONTEXT")
        or content_meta.get("learning_objective")
        or ""
    )
    lexical = str(
        prompt_params.get("LEXICAL_FIELD")
        or content_meta.get("lexical_field")
        or content_meta.get("subcategory")
        or content_meta.get("category")
        or ""
    )
    raw_script = str(script_data.get("script_text") or "")
    lang = str(
        content_meta.get("language")
        or prompt_params.get("TARGET_LANGUAGE")
        or metadata.get("LABEL")
        or "English"
    ).title()

    combined = f"{raw_topic} {scenario} {lexical} {raw_script}".lower()

    from video_creation._C_image_generation.visual.languages import MULTILINGUAL_SEMANTIC_DOMAINS

    for domain_name, kw_list, guidance_tpl in MULTILINGUAL_SEMANTIC_DOMAINS:
        if any(re.search(r'\b' + re.escape(w) + r'\b', combined) for w in kw_list):
            return domain_name, guidance_tpl.format(lang=lang)

    # Default fallback: authentic everyday cultural street/piazza life
    return (
        "Everyday Neighborhood & Social Life",
        f"Ground this visual world in an authentic everyday social setting reflecting {lang} culture "
        f"(e.g. a lively neighborhood piazza corner, a sunlit public park bench by historic facades, "
        f"or an open-air pedestrian promenade) where natural everyday dialogue occurs."
    )


def get_video_type_directive(video_type: str) -> str:
    """
    Returns specialized visual storytelling directives tailored to the video type.
    Delegates directly to the canonical `VisualProfile` in `visual/types/`.
    """
    from video_creation._C_image_generation.visual.types import get_visual_profile

    prof = get_visual_profile(video_type or "EXPRESSION") or get_visual_profile("EXPRESSION")
    if prof is not None:
        return prof.build_general_prompt_archetype_directive()
    return ""


def _parse_character_line(line: str) -> Dict[str, str]:
    parts = line.split("|")
    res: Dict[str, str] = {}
    for p in parts:
        p = p.strip()
        if ":" in p:
            k, v = p.split(":", 1)
            k_low = k.strip().lower()
            v_val = v.strip()
            if "hair" in k_low:
                res["hair"] = v_val
            elif "attire" in k_low or "clothes" in k_low or "outfit" in k_low:
                res["attire"] = v_val
            elif "shoe" in k_low or "footwear" in k_low:
                res["shoes"] = v_val
            elif "char" in k_low:
                res["identity"] = v_val
    return res


def extract_character_anchors_from_output(raw_text: str) -> Tuple[str, Dict[str, str]]:
    """
    Extracts [CHARACTER_ANCHORS] block from Gemini output if present.
    Returns cleaned text without the anchor block, plus the structured character anchors dictionary.
    """
    cleaned = (raw_text or "").strip()
    pattern = r'\[CHARACTER_ANCHORS\](.*?)\[/CHARACTER_ANCHORS\]'
    m = re.search(pattern, cleaned, flags=re.DOTALL | re.IGNORECASE)
    anchors: Dict[str, str] = {}

    if m:
        block = m.group(1).strip()
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

        p1_info: Dict[str, str] = {}
        p2_info: Dict[str, str] = {}
        for line in block.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if "CHAR_1" in line_str.upper():
                p1_info = _parse_character_line(line_str)
            elif "CHAR_2" in line_str.upper():
                p2_info = _parse_character_line(line_str)

        if p1_info:
            anchors["char1_identity"] = p1_info.get("identity", "15-year-old high-school student boy")
            anchors["char1_hair"] = p1_info.get("hair", "short textured dark hair")
            anchors["char1_attire"] = p1_info.get("attire", "a casual overshirt over a tee")
            anchors["char1_shoes"] = p1_info.get("shoes", "sneakers")
            anchors["char1_desc"] = (
                f"{anchors['char1_identity']} with {anchors['char1_hair']} wearing {anchors['char1_attire']} "
                f"and {anchors['char1_shoes']}"
            )
        if p2_info:
            anchors["char2_identity"] = p2_info.get("identity", "15-year-old high-school student girl")
            anchors["char2_hair"] = p2_info.get("hair", "sleek dark bob")
            anchors["char2_attire"] = p2_info.get("attire", "a corduroy jacket")
            anchors["char2_shoes"] = p2_info.get("shoes", "loafers")
            anchors["char2_desc"] = (
                f"{anchors['char2_identity']} with {anchors['char2_hair']} wearing {anchors['char2_attire']} "
                f"and {anchors['char2_shoes']}"
            )

        if "char1_desc" in anchors and "char2_desc" in anchors:
            anchors["continuity_summary"] = (
                f"Character appearance continuity: Character 1 is a {anchors['char1_desc']}; "
                f"Character 2 is a {anchors['char2_desc']}."
            )
        elif "char1_desc" in anchors:
            anchors["continuity_summary"] = (
                f"Character appearance continuity: The protagonist is a {anchors['char1_desc']}."
            )

    return cleaned, anchors


def _clean_gemini_output_with_anchors(raw_text: str) -> Tuple[str, Dict[str, str]]:
    """Cleans up Gemini output and extracts structured character anchors if present."""
    text = (raw_text or "").strip()

    # 1. Strip markdown code fences (```markdown ... ``` or ```text ... ``` or ``` ... ```)
    fence_pattern = r"^```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)\n?```$"
    m = re.match(fence_pattern, text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()

    # 2. Extract structured [CHARACTER_ANCHORS] block if present
    text, anchors = extract_character_anchors_from_output(text)

    # Safety Net: Replace any raw CHAR_1 / CHAR_2 tokens in the narrative scene with full prose descriptions
    if anchors:
        if "char1_desc" in anchors:
            text = re.sub(r'\bCHAR_1\b', anchors['char1_desc'], text)
            text = re.sub(r'\bCharacter 1\b', anchors['char1_desc'], text)
        if "char2_desc" in anchors:
            text = re.sub(r'\bCHAR_2\b', anchors['char2_desc'], text)
            text = re.sub(r'\bCharacter 2\b', anchors['char2_desc'], text)

    # 3. Strip conversational prefixes
    prefix_pattern = (
        r"^(?:(?:Here is|Here's) (?:the |a )?(?:new |audited |revised )?(?:general |master )?prompt[:\s]*|"
        r"(?:General Prompt|Master Story World|Prompt|Visual Prompt|Core Prompt|Narrative Scene|Part 2|Part B)[:\s]*)\s*"
    )
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()

    # 4. Strip outer enclosing double or single quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return text, anchors


def _clean_gemini_output(raw_text: str) -> str:
    """Cleans up Gemini output to guarantee raw prompt text with zero markdown or conversational baggage."""
    text, _ = _clean_gemini_output_with_anchors(raw_text)
    return text


def _strip_redundant_tails(text: str) -> str:
    """Removes any accidental duplicate style tags or negative shields if Gemini echoed them."""
    cleaned = text.strip()
    # Strip trailing parenthetical negative shields
    cleaned = re.sub(r'\((?:high-school student protagonist|thematic setting visible)[^)]*\)', '', cleaned, flags=re.IGNORECASE).strip()
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

    language = (
        content_meta.get("language")
        or prompt_params.get("TARGET_LANGUAGE")
        or metadata.get("LABEL")
        or "English"
    )
    video_type = (
        content_meta.get("video_type")
        or prompt_params.get("VIDEO_TYPE")
        or metadata.get("VIDEO_TYPE")
        or "EXPRESSION"
    ).upper()
    topic = (
        prompt_params.get("EXPRESSION")
        or prompt_params.get("TOPIC")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or content_meta.get("topic")
        or content_meta.get("target_expression")
        or metadata.get("TITLE")
        or ""
    )

    from video_creation._C_image_generation.visual.common.cast import (
        persist_character_anchors_in_state,
        resolve_default_speakers_gender,
    )
    from video_creation._C_image_generation.visual.common.sanitizer import (
        is_present_heteronym_topic,
        sanitize_and_style_prompt,
    )

    # Format speakers/gender description
    raw_speakers_gender = content_meta.get("speakers_gender", {})
    if not isinstance(raw_speakers_gender, dict):
        raw_speakers_gender = {}
    speakers_gender = (
        resolve_default_speakers_gender(raw_speakers_gender, video_type=video_type)
        if raw_speakers_gender or video_type == "ROLEPLAY"
        else {}
    )

    # Compact script text
    raw_script = script_data.get("script_text", "")
    if isinstance(raw_script, dict):
        script_text = json.dumps(raw_script, ensure_ascii=False)
    else:
        script_text = str(raw_script)

    existing_gp = (current_prompt or script_data.get("assets", {}).get("general_prompt", "")).strip()

    # Detect semantic domain and video type archetypes
    detected_domain, domain_guidance = detect_script_domain(script_data)
    video_type_directive = get_video_type_directive(video_type)

    # Determine gender words for characters (Priority: explicit speakers_gender > single-character draft in existing_gp)
    c1_gender = "boy"
    c2_gender = "girl"

    has_explicit_p1 = False
    if isinstance(raw_speakers_gender, dict) and raw_speakers_gender:
        p1_raw = ""
        for k, v in raw_speakers_gender.items():
            if k.lower() in ("person_one", "person_1", "narrator", "narratrice", "host", "speaker"):
                p1_raw = str(v).lower()
                break
        if any(w in p1_raw for w in ("f", "girl", "woman", "female", "chica", "mujer")):
            c1_gender = "girl"
            has_explicit_p1 = True
        elif any(w in p1_raw for w in ("m", "boy", "man", "male", "chico", "hombre")):
            c1_gender = "boy"
            has_explicit_p1 = True

    if not has_explicit_p1 and existing_gp:
        gp_low = existing_gp.lower()
        gp_male_score = len(re.findall(r'\b(boy|male|guy|young man|man|chico|muchacho|hombre|he wears|he stands|his hair|his build)\b', gp_low))
        gp_female_score = len(re.findall(r'\b(girl|female|young woman|woman|lady|chica|muchacha|mujer|she wears|she stands|her hair|her build)\b', gp_low))
        if gp_male_score > gp_female_score:
            c1_gender = "boy"
        elif gp_female_score > gp_male_score:
            c1_gender = "girl"

    # Determine character 2 gender
    if isinstance(speakers_gender, dict) and speakers_gender:
        p2_raw = ""
        for k, v in speakers_gender.items():
            if k.lower() in ("person_two", "person_2"):
                p2_raw = str(v).lower()
                break
        if any(w in p2_raw for w in ("f", "girl", "woman", "female", "chica", "mujer")):
            c2_gender = "girl"
        elif any(w in p2_raw for w in ("m", "boy", "man", "male", "chico", "hombre")):
            c2_gender = "boy"
        else:
            c2_gender = "girl" if c1_gender == "boy" else "boy"
    else:
        c2_gender = "girl" if c1_gender == "boy" else "boy"

    # Dynamic creative lenses focusing on cinematographic perspectives (no hardcoded shops)
    creative_lenses = [
        "Dynamic foreground framing with concrete setting props anchored in the immediate midground",
        "Rich atmospheric natural daylight filtering through windows, casting directional colored floor shadows",
        "Tactile regional materials and authentic architectural depth reflecting the cultural setting",
        "Expressive character interaction and conversational body language anchored around focal setting objects",
        "Deep spatial composition with layered background doorways, arches, or storefront glass adding environmental realism",
    ]
    chosen_lens = random.choice(creative_lenses)
    run_seed = random.randint(100000, 999999)

    # Master story world camera framing opener & cast policy tailored to video type profile
    vt_clean = video_type.upper().strip()
    from video_creation._C_image_generation.visual.types import get_visual_profile

    profile = get_visual_profile(vt_clean) or get_visual_profile("EXPRESSION")
    camera_opener = (
        profile.general_prompt_camera_opener
        if profile is not None
        else "Medium-wide establishing eye-level shot."
    )

    is_solo_format = vt_clean in ("GAME", "FUN_FACTS", "FUNFACTS")
    has_two_characters = not is_solo_format and (
        (profile.has_two_characters_default if profile is not None else vt_clean in ("ROLEPLAY", "ROLE_PLAY"))
        or bool(isinstance(raw_speakers_gender, dict) and "PERSON_TWO" in raw_speakers_gender and raw_speakers_gender.get("PERSON_TWO"))
    )

    def _hair_guidance(g: str) -> str:
        if g == "girl":
            return "feminine hairstyle (e.g. shoulder-length bob, high ponytail, soft wavy hair over shoulders, braids — NO sideburns or buzz cuts)"
        return "masculine hairstyle (e.g. short textured hair with neat side-part, tapered sides, tousled short curls — NO buns, ponytails, braids, or long hair)"

    if has_two_characters:
        part_a_template = (
            "[CHARACTER_ANCHORS]\n"
            f"CHAR_1: 15-16yo high-school student {c1_gender} | hair: <explicit hair color and {_hair_guidance(c1_gender)}> | attire: <explicit top garment, bottom garment matching environment> | shoes: <explicit footwear>\n"
            f"CHAR_2: 15-16yo high-school student {c2_gender} | hair: <explicit hair color and {_hair_guidance(c2_gender)}> | attire: <explicit top garment, bottom garment matching environment> | shoes: <explicit footwear>\n"
            "[/CHARACTER_ANCHORS]"
        )
        char_mandate = (
            f"3. CHARACTER 1 (Subject on the LEFT): Start with 'On the LEFT,' followed by a full inline prose description of the 15-16yo student {c1_gender} incorporating their {_hair_guidance(c1_gender)}, thematic setting-appropriate wardrobe, and footwear (DO NOT write the literal placeholder 'CHAR_1' in Part B; write out their full visual description in prose).\n"
            f"4. CHARACTER 2 (Counterpart on the RIGHT): Start with 'On the RIGHT,' followed by a full inline prose description of the 15-16yo student {c2_gender} incorporating their {_hair_guidance(c2_gender)}, thematic setting-appropriate wardrobe, and footwear (DO NOT write the literal placeholder 'CHAR_2' in Part B; write out their full visual description in prose).\n"
        )
    else:
        part_a_template = (
            "[CHARACTER_ANCHORS]\n"
            f"CHAR_1: 15-16yo high-school student {c1_gender} | hair: <explicit hair color and {_hair_guidance(c1_gender)}> | attire: <explicit top garment, bottom garment matching environment> | shoes: <explicit footwear>\n"
            "[/CHARACTER_ANCHORS]"
        )
        char_mandate = (
            f"3. PROTAGONIST: Full inline prose description of the solo 15-16yo high-school student {c1_gender} incorporating their {_hair_guidance(c1_gender)}, thematic setting-appropriate wardrobe, and footwear (DO NOT write the literal placeholder 'CHAR_1' in Part B; write out their full visual description in prose). SOLO PROTAGONIST MANDATE: DO NOT include a second character or companion in this solo scene.\n"
        )

    previous_contrast = ""
    if existing_gp:
        previous_contrast = (
            f"PREVIOUS DRAFT (FOR CONTRAST ONLY — DO NOT COPY OR REPEAT THIS SETTING):\n"
            f"\"{existing_gp}\"\n"
            "MANDATE: Invent a COMPLETELY DIFFERENT physical setting, atmosphere, and props from the draft above.\n\n"
        )

    placeholder_rule = (
        "NEVER output placeholder tokens like 'CHAR_1' or 'CHAR_2' in Part B!"
        if has_two_characters
        else "NEVER output placeholder tokens like 'CHAR_1' in Part B!"
    )

    # Build prompt enforcing Context Domain, Video Type Archetype, Character Anchors, and 7-part Narrative Scene
    prompt_text = (
        "You are an elite Visual Storyboard Director and Concept Artist for high-retention 2D animation Shorts.\n"
        "Your task is to audit and creatively write the Master Visual Story World for this Short to eliminate repetitive AI tropes.\n\n"
        f"CREATIVE DIRECTIVE [RUN #{run_seed}]:\n"
        f"Cinematographic Focus: {chosen_lens}.\n\n"
        f"SEMANTIC DOMAIN: {detected_domain}\n"
        f"DOMAIN DIRECTIVE: {domain_guidance}\n\n"
        f"{video_type_directive}\n\n"
        f"SCRIPT ID: {script_id}\n"
        f"LANGUAGE: {language} ({video_type})\n"
        f"TOPIC/SITUATION: {topic}\n"
        f"SCRIPT DIALOGUE:\n{script_text}\n\n"
        f"{previous_contrast}"
        "==================================================\n"
        "STRICT PRODUCTION MANDATE (TWO PARTS):\n"
        "==================================================\n"
        "Generate your response in EXACTLY two parts:\n\n"
        "PART A: STRUCTURED CHARACTER ANCHORS (mandatory [CHARACTER_ANCHORS] tags)\n"
        "Define locked physical character traits to maintain 100% visual identity continuity across scenes:\n"
        f"{part_a_template}\n\n"
        "PART B: MASTER NARRATIVE SCENE (PARTS 1 TO 7 ONLY)\n"
        "Follow this exact narrative structure in a single cohesive, richly detailed paragraph (~110-145 words):\n"
        f"1. CAMERA SHOT & FRAMING: Open with '{camera_opener}' to guarantee lens perspective.\n"
        "2. THEMATIC SCENE CONTEXT: Ground the physical setting authentically in the SEMANTIC DOMAIN and VIDEO TYPE ARCHETYPE above. "
        "⚠️ ANTI-CLICHÉ BAN: Strictly DO NOT use generic AI clichés: BANNED are generic modern coffee shops, plain empty classrooms, pottery/ceramic workshops, rooftop greenhouses, and random flea markets. Ground the setting authentically in the dialogue domain.\n"
        f"{char_mandate}"
        "5. MIDGROUND ANCHOR PROPS: Concrete physical objects on the table/counter/space matching the video type archetype.\n"
        "6. ARCHITECTURAL BACKGROUND: Cultural and architectural textures providing regional depth.\n"
        "7. CINEMATIC LIGHTING & SHADOWS: Warm/cool color contrast (e.g. amber sunbeams casting slate-blue directional cast shadows across the floor).\n\n"
        "IMPORTANT RULES:\n"
        f"- In Part B, you must write out FULL prose descriptions of characters. {placeholder_rule}\n"
        "- Describe the STATIC master world environment only. DO NOT generate momentary scene-specific facial acting (e.g. no smirks, raised eyebrows, winks) or fourth-wall gaze commands here, as individual scenes will direct actions.\n"
        "- Return ONLY Part A and Part B. Zero conversational filler, zero quotes, zero markdown commentary outside the block."
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
                    cleaned_core, parsed_anchors = _clean_gemini_output_with_anchors(raw_generated)

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

                    # Strip any accidental duplicate style or negative tags and run Stage C sanitizer
                    stripped_core = _strip_redundant_tails(cleaned_core)
                    allow_gift = is_present_heteronym_topic(topic=str(topic), label=str(language))
                    sanitized_core = _strip_redundant_tails(
                        sanitize_and_style_prompt(stripped_core, allow_gift_box=allow_gift)
                    )

                    # Stitch complete 9-part Master Story World prompt
                    final_prompt = f"{sanitized_core}. {POSITIVE_STYLE_PILLAR} {NEGATIVE_PROMPT_SHIELD}"

                    if isinstance(script_data, dict):
                        cast = persist_character_anchors_in_state(
                            script_data=script_data,
                            general_prompt=final_prompt,
                            speakers_gender=speakers_gender,
                            video_type=vt_clean,
                        )
                        if parsed_anchors:
                            cast_dict = cast if isinstance(cast, dict) else cast.to_dict()
                            merged_anchors = {**cast_dict, **parsed_anchors}
                            script_data.setdefault("assets", {})["character_anchors"] = merged_anchors
                            script_data.setdefault("content_metadata", {})["character_anchors"] = merged_anchors

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
