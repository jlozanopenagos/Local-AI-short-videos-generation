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
    "vibrant flat colors, bold outlines, expressive character design with large clear cartoon eyes, "
    "visible white sclera and specular pupil highlights, rich detailed environmental interior background "
    "with depth and warm atmospheric lighting."
)

NEGATIVE_PROMPT_SHIELD = (
    "(thematic setting visible, explicit footwear on feet, NO bare feet, NO dot eyes, "
    "NO minimalist faces, NO blank backgrounds, NO 3D, NO realism, NO photograph, NO text, "
    "NO speech bubbles, NO floating symbols)"
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
        content_meta.get("topic")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or content_meta.get("target_expression")
        or metadata.get("TITLE")
        or ""
    )
    scenario = str(content_meta.get("story_scenario") or prompt_params.get("ROLEPLAY_SCENARIO") or "")
    lexical = str(content_meta.get("lexical_field") or prompt_params.get("LEXICAL_FIELD") or "")
    raw_script = str(script_data.get("script_text") or "")
    lang = str(content_meta.get("language") or metadata.get("LABEL") or "English").title()

    combined = f"{raw_topic} {scenario} {lexical} {raw_script}".lower()

    domain_rules = [
        (
            "Family, Home & Holiday Gatherings",
            [
                "parenti", "genitori", "family", "famiglia", "familia", "famille",
                "parents", "relatives", "cugini", "cousin", "nonni", "grandparents",
                "casa", "home", "house", "dinner", "cena", "pranzo", "natale", "christmas",
                "holiday", "festa", "fratello", "sorella", "brother", "sister",
                "mamma", "papà", "mom", "dad", "living room", "kitchen", "cucina",
                "tablecloth", "sofa", "porch", "patio", "ancestor", "heritage"
            ],
            f"Ground this visual world in an authentic {lang} domestic or family setting "
            f"(e.g. a warm holiday dining room with festive table setting, a lively family kitchen, "
            f"an intimate living room gathering, or an outdoor courtyard porch) directly reflecting family life and shared meals."
        ),
        (
            "Food, Culinary & Dining",
            [
                "food", "cibo", "comida", "nourriture", "eat", "eating", "mangiare",
                "comer", "manger", "restaurant", "ristorante", "restaurante", "cafe",
                "café", "trattoria", "pizza", "pasta", "cooking", "cuoco", "chef",
                "recipe", "ricetta", "breakfast", "colazione", "desayuno", "lunch",
                "dish", "beverage", "espresso", "cappuccino", "tasting", "pastry", "wine"
            ],
            f"Ground this visual world in a vibrant culinary or dining setting in {lang} culture "
            f"(e.g. a neighborhood trattoria dining table, an open kitchen pass, an outdoor cafe terrace, "
            f"a lively food hall, or a coffee counter)."
        ),
        (
            "Travel, Transit & Commute",
            [
                "travel", "viaggio", "viaje", "voyage", "train", "treno", "tren",
                "airport", "aeroporto", "aeropuerto", "gare", "stazione", "estación",
                "station", "ticket", "biglietto", "billete", "bus", "autobus", "subway",
                "metro", "tram", "hotel", "albergo", "suitcase", "valigia", "maleta",
                "baggage", "flight", "volo", "vuelo", "trip", "tourism", "turista",
                "luggage", "platform", "backpack", "ferry"
            ],
            f"Ground this visual world in an authentic travel or transit hub "
            f"(e.g. a railway station platform with vintage departures board, a tramway interchange, "
            f"an airport check-in concourse, or a scenic transit stop)."
        ),
        (
            "Academic, School & Study Life",
            [
                "school", "scuola", "escuela", "école", "class", "classe", "aula",
                "exam", "esame", "examen", "test", "study", "studiare", "estudiar",
                "étudier", "teacher", "professore", "profesor", "prof", "student",
                "studente", "homework", "compiti", "tarea", "devoirs", "library",
                "biblioteca", "bibliothèque", "grade", "voto", "nota", "university",
                "università", "campus", "blackboard", "chalkboard", "desk"
            ],
            f"Ground this visual world in an authentic student academic environment "
            f"(e.g. a university library study nook with green-shaded brass lamps, a campus project table, "
            f"a student common room, or a classroom study corner)."
        ),
        (
            "Workplace & Professional Life",
            [
                "work", "lavoro", "trabajo", "travail", "office", "ufficio", "oficina",
                "bureau", "boss", "capo", "jefe", "colleague", "collega", "colega",
                "meeting", "riunione", "reunión", "job", "interview", "colloquio",
                "entrevista", "company", "azienda", "empresa", "email", "client", "career"
            ],
            f"Ground this visual world in a realistic professional or vocational workspace "
            f"(e.g. a shared creative studio, a municipal client counter, an architectural drafting atelier, "
            f"or an open-plan office discussion nook)."
        ),
        (
            "Shopping, Markets & Commerce",
            [
                "shop", "negozio", "tienda", "magasin", "store", "buy", "comprare",
                "comprar", "acheter", "price", "prezzo", "precio", "prix", "clothes",
                "vestiti", "ropa", "vêtements", "market", "mercato", "mercado", "marché",
                "supermarket", "cashier", "cassa", "caja", "boutique", "receipt", "shopping"
            ],
            f"Ground this visual world in a lively commercial or market space "
            f"(e.g. a bustling neighborhood open-air market, a vintage storefront counter, "
            f"or a specialty goods boutique)."
        ),
        (
            "Sports, Outdoor & Fitness",
            [
                "sport", "calcio", "football", "soccer", "gym", "palestra", "gimnasio",
                "fitness", "run", "correre", "correr", "courir", "match", "partita",
                "partido", "coach", "allenatore", "entrenador", "court", "field", "stadium",
                "basketball", "tennis", "skate", "cycling"
            ],
            f"Ground this visual world in an active sports or recreation environment "
            f"(e.g. a community sports club bleacher, an outdoor court sideline, a skate park perimeter, "
            f"or a lakeside athletic path)."
        ),
        (
            "Arts, Music & Culture",
            [
                "music", "musica", "musique", "song", "canzone", "canción", "chanson",
                "art", "arte", "cinema", "film", "movie", "theatre", "teatro", "théâtre",
                "concert", "concerto", "dance", "ballo", "danza", "danse", "instrument",
                "guitar", "piano", "museum", "museo", "gallery", "exhibition"
            ],
            f"Ground this visual world in an expressive creative or cultural space "
            f"(e.g. an intimate music practice studio, a cinema lobby, an art gallery corridor, "
            f"or a theater backstage)."
        ),
        (
            "Healthcare & Wellbeing",
            [
                "doctor", "dottore", "médico", "médecin", "hospital", "ospedale", "hopital",
                "pharmacy", "farmacia", "pharmacie", "sick", "malato", "enfermo", "malade",
                "pain", "dolore", "dolor", "douleur", "medicine", "medicina", "médicament",
                "health", "salute", "salud", "santé", "dentist", "dentista"
            ],
            f"Ground this visual world in a healthcare or wellness setting "
            f"(e.g. an authentic neighborhood pharmacy counter, a clinic waiting room with paned windows, "
            f"or an apothecary consultation nook)."
        ),
    ]

    for domain_name, kw_list, guidance in domain_rules:
        if any(re.search(r'\b' + re.escape(w) + r'\b', combined) for w in kw_list):
            return domain_name, guidance

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
    Ensures that an Expression, Game, Roleplay, and Fun Facts Short sharing the same
    expression receive distinctly different scene archetypes, props, and moods.
    """
    vt = (video_type or "EXPRESSION").upper().strip()
    if vt in ("GAME", "QUIZ"):
        return (
            "VIDEO TYPE ARCHETYPE: GAME / QUIZ (Interactive Challenge Arena)\n"
            "- Core Visual Objective: High-stakes interactive dilemma, puzzle challenge, or competitive test of wits.\n"
            "- Setting Mood: Playful competitive focus, suspenseful countdown tension, active problem-solving.\n"
            "- Mandatory Challenge Props: Include concrete interactive quiz/challenge items between characters "
            "(e.g. a wooden challenge board or notebook, an hourglass timer, answer placards, scorecards, brass study bells, or flashcards).\n"
            "- Poses & Expressions: High-energy concentration, playful rivalry, dilemma gestures, or triumphant breakthrough."
        )
    elif vt in ("ROLEPLAY", "ROLE_PLAY"):
        return (
            "VIDEO TYPE ARCHETYPE: ROLEPLAY (Character Drama & Interpersonal Banter)\n"
            "- Core Visual Objective: Character-driven emotional exchange, comedic misunderstanding, or interpersonal debate.\n"
            "- Setting Mood: Close interpersonal shared space emphasizing conversational proxemics across a table or counter.\n"
            "- Mandatory Conversational Foil Props: A concrete physical object causing or anchoring the discussion "
            "(e.g. a disputed handwritten list, a shared schedule, a mobile screen, blueprints, or physical items being compared).\n"
            "- Poses & Expressions: Expressive conversational acting contrast (one character animatedly arguing or explaining "
            "with expressive hand gestures, while the counterpart reacts with skepticism, curiosity, or sudden realization)."
        )
    elif vt in ("FUN_FACTS", "FACTS"):
        return (
            "VIDEO TYPE ARCHETYPE: FUN FACTS (Curiosity & Cultural Discovery)\n"
            "- Core Visual Objective: Documentary exploration, historical curiosity, or surprising cultural revelation.\n"
            "- Setting Mood: Wonder, exploratory depth, intrigue, and cultural mystery.\n"
            "- Mandatory Discovery Props: Concrete items of investigation (e.g. magnifying glass, vintage maps, open reference encyclopedias, antique cultural artifacts).\n"
            "- Poses & Expressions: Fascinated discovery, pointing out an unexpected detail, shared wonder."
        )
    else:  # EXPRESSION (default)
        return (
            "VIDEO TYPE ARCHETYPE: EXPRESSION (Everyday Cultural Observation)\n"
            "- Core Visual Objective: Natural, authentic demonstration of an idiom or cultural phrase in everyday real-world life.\n"
            "- Setting Mood: Relatable everyday social observation, relaxed conversational rhythm, warmth.\n"
            "- Mandatory Natural Props: Everyday carry items grounding the moment (e.g. espresso cups, shopping bags, rolled newspaper, bicycle, umbrella).\n"
            "- Poses & Expressions: Natural social observation, relaxed gestures, everyday conversational warmth."
        )


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

    # Detect semantic domain and video type archetypes
    detected_domain, domain_guidance = detect_script_domain(script_data)
    video_type_directive = get_video_type_directive(video_type)

    # Determine gender words for characters
    c1_gender = "boy"
    c2_gender = "girl"
    if isinstance(speakers_gender, dict):
        p1 = str(speakers_gender.get("PERSON_ONE") or speakers_gender.get("NARRATOR") or "").lower()
        p2 = str(speakers_gender.get("PERSON_TWO") or "").lower()
        if "f" in p1 or "girl" in p1 or "woman" in p1:
            c1_gender = "girl"
        if "m" in p2 or "boy" in p2 or "man" in p2:
            c2_gender = "boy"

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

    previous_contrast = ""
    if existing_gp:
        previous_contrast = (
            f"PREVIOUS DRAFT (FOR CONTRAST ONLY — DO NOT COPY OR REPEAT THIS SETTING):\n"
            f"\"{existing_gp}\"\n"
            "MANDATE: Invent a COMPLETELY DIFFERENT physical setting, atmosphere, and props from the draft above.\n\n"
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
        "Define locked physical character traits to maintain 100% visual identity continuity:\n"
        "[CHARACTER_ANCHORS]\n"
        f"CHAR_1: 15-16yo high-school student {c1_gender} | hair: <explicit hair color and cut/style> | attire: <explicit top garment, bottom garment> | shoes: <explicit footwear>\n"
        f"CHAR_2: 15-16yo high-school student {c2_gender} | hair: <explicit hair color and cut/style> | attire: <explicit top garment, bottom garment> | shoes: <explicit footwear>\n"
        "[/CHARACTER_ANCHORS]\n\n"
        "PART B: MASTER NARRATIVE SCENE (PARTS 1 TO 7 ONLY)\n"
        "Follow this exact 7-part narrative structure in a single cohesive, richly detailed paragraph (~110-145 words):\n"
        "1. CAMERA SHOT & FRAMING: Open with 'Medium wide eye-level shot.' to guarantee lens perspective.\n"
        "2. THEMATIC SCENE CONTEXT: Ground the physical setting authentically in the SEMANTIC DOMAIN and VIDEO TYPE ARCHETYPE above. "
        "⚠️ ANTI-CLICHÉ BAN: Strictly DO NOT use generic AI clichés: BANNED are generic modern coffee shops, plain empty classrooms, pottery/ceramic workshops, rooftop greenhouses, and random flea markets. Ground the setting authentically in the dialogue domain.\n"
        f"3. CHARACTER 1 (Subject): Integrate CHAR_1 using the exact hair, wardrobe, and shoes defined in Part A, with expressive cartoon facial acting (large clear cartoon eyes, visible white sclera, specular pupil highlights).\n"
        "4. CHARACTER 2 (Counterpart): Integrate CHAR_2 in an active complementary pose matching their Part A definition.\n"
        "5. MIDGROUND ANCHOR PROPS: Concrete physical objects on the table/counter between characters matching the video type archetype.\n"
        "6. ARCHITECTURAL BACKGROUND: Cultural and architectural textures providing regional depth.\n"
        "7. CINEMATIC LIGHTING & SHADOWS: Warm/cool color contrast (e.g. amber sunbeams casting slate-blue directional cast shadows across the floor).\n\n"
        "OUTPUT RULE: Return ONLY Part A and Part B. Zero conversational filler, zero quotes, zero markdown commentary outside the block."
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
                    if parsed_anchors and isinstance(script_data, dict):
                        if "assets" not in script_data or not isinstance(script_data["assets"], dict):
                            script_data["assets"] = {}
                        script_data["assets"]["character_anchors"] = parsed_anchors

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
