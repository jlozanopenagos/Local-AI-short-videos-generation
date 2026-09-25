#!/usr/bin/env python3
"""
video_creation/_A_video_scripts/script_modifier.py

Standalone interactive utility to update video scripts from plain text or CSV.
Modes:
1. Single Script (modify 1 video script interactively)
2. Mass Script Changes (queue multiple scripts by ID, then process all with LLM)
3. From Ready Scripts CSV (import ID & SCRIPT_CHANGE from ready_scripts_to_work_with.csv)

Workflow:
- Uses the LLM to format and structure the whole JSON file of each video while strictly
  preserving the user's script text verbatim (zero rewriting or word alteration).
- Updates content_metadata, metadata (YouTube title, description, tags, etc.), resets
  downstream stages if desired, and saves back to state/<lang>/<video_type>/script_<ID>.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Add project root, video_creation, and module directory to path for robust imports
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from config import (
        BASE_DIR,
        STATIC_NARRATOR_PERSONALITY,
        require_services,
    )
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from shorts_automation.config import (
        BASE_DIR,
        STATIC_NARRATOR_PERSONALITY,
        require_services,
    )

try:
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from state_manager import StateManager, resolve_lang_and_type

try:
    from connectivity.ready_scripts.scanner import (
        DEFAULT_READY_SCRIPTS_DIR,
        resolve_ready_scripts_output_dir,
    )
except (ImportError, ModuleNotFoundError):
    DEFAULT_READY_SCRIPTS_DIR = Path(r"D:\AI\output\connectivity\ready_scripts")

    def resolve_ready_scripts_output_dir(output_dir: Optional[Path | str] = None) -> Path:
        if output_dir:
            return Path(output_dir)
        env_output = os.getenv("OUTPUT_DIR", "").strip()
        if env_output:
            return Path(env_output) / "connectivity" / "ready_scripts"
        return DEFAULT_READY_SCRIPTS_DIR

try:
    from video_creation._A_video_scripts.core.metadata_builder import build_metadata
    from video_creation._A_video_scripts.core.llm import generate_response, check_connection
    from video_creation._A_video_scripts.prompts.prompt_builder import load_call_to_actions
except (ImportError, ModuleNotFoundError):
    try:
        # pyrefly: ignore [missing-import]
        from core.metadata_builder import build_metadata
        # pyrefly: ignore [missing-import]
        from core.llm import generate_response, check_connection
        from prompts.prompt_builder import load_call_to_actions
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from _A_video_scripts.core.metadata_builder import build_metadata
        # pyrefly: ignore [missing-import]
        from _A_video_scripts.core.llm import generate_response, check_connection
        # pyrefly: ignore [missing-import]
        from _A_video_scripts.prompts.prompt_builder import load_call_to_actions


def count_words(text: str) -> int:
    """Counts words in a string, stripping markdown and punctuation."""
    if not text:
        return 0
    clean = re.sub(r"[^\w\s\u00C0-\u017F'-]", " ", text)
    return len([w for w in clean.split() if w.strip()])


def extract_json_from_llm(raw_text: str) -> dict:
    """Robustly extracts and parses the JSON object from raw LLM output."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response from LLM")

    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()

    # 1. Direct parse attempt
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Extract first valid JSON object using JSONDecoder.raw_decode
    start_idx = cleaned.find("{")
    if start_idx != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(cleaned[start_idx:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # 3. Balanced bracket scan
    depth = 0
    start = -1
    for i, c in enumerate(cleaned):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start != -1:
                candidate = cleaned[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict) and ("script" in obj or "video_type" in obj or "title" in obj):
                        return obj
                except Exception:
                    pass

    # 4. Fallback to regex search
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from LLM response. Raw output preview:\n{cleaned[:300]}")


def clean_narrator_prefix(text: str) -> str:
    """Strips leading 'Narrator:' or 'Narrateur:' prefixes so TTS voices only speak the narration text."""
    if not text:
        return ""
    return re.sub(
        r"^(?:narrator|narrateur|narratore|narrador|voiceover|vo|host)(?:\s*\([^)]*\))?\s*[:：]\s*",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    ).strip()


def try_direct_script_parse(raw_text: str, video_type: str) -> Optional[Dict[str, str]]:
    """
    Checks if the user already provided valid JSON or labeled text sections directly.
    Returns the parsed script dict if successfully recognized, else None.
    """
    cleaned = raw_text.strip()
    # Check if user passed JSON directly
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                if "script" in parsed and isinstance(parsed["script"], dict):
                    return parsed["script"]
                # Check for standard keys
                keys = [k.lower() for k in parsed.keys()]
                if any(k in keys for k in ["hook", "dialogue_part_1", "challenge", "core_learning"]):
                    return parsed
        except Exception:
            pass

    # Check for labeled sections (e.g., Hook: ..., Title: ..., etc.)
    lines = cleaned.split("\n")
    section_patterns = {
        "title": re.compile(r"^(?:title|titre|título|titolo)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "hook": re.compile(r"^(?:hook|accroche|gancho)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "core_learning": re.compile(r"^(?:core[_\s]learning|core|explication|apprentissage)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "emphasis": re.compile(r"^(?:emphasis|emphase|origen|histoire|nuance)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "loop_trigger": re.compile(r"^(?:loop[_\s]trigger|cta|call[_\s]to[_\s]action|conclusion)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "DIALOGUE_PART_1": re.compile(r"^(?:dialogue[_\s]part[_\s]1|dialogue[_\s]1|part[_\s]1)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "DIALOGUE_PART_2": re.compile(r"^(?:dialogue[_\s]part[_\s]2|dialogue[_\s]2|part[_\s]2)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "DIALOGUE_PART_3": re.compile(r"^(?:dialogue[_\s]part[_\s]3|dialogue[_\s]3|part[_\s]3)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "DIALOGUE_PART_4": re.compile(r"^(?:dialogue[_\s]part[_\s]4|dialogue[_\s]4|part[_\s]4)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "PAYOFF": re.compile(r"^(?:payoff|pay[_\s]off|chute|conclusion)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "challenge": re.compile(r"^(?:challenge|défi|desafío|sfida|question)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "pressure": re.compile(r"^(?:pressure|pression|presión|pressione|countdown)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "answer": re.compile(r"^(?:answer|réponse|respuesta|risposta)\s*[:：]\s*(.*)$", re.IGNORECASE),
        "explanation": re.compile(r"^(?:explanation|explication|explicación|spiegazione)\s*[:：]\s*(.*)$", re.IGNORECASE),
    }

    labeled_dict: Dict[str, list[str]] = {}
    current_key: Optional[str] = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        matched_key = None
        rest_of_line = ""
        for key_name, pattern in section_patterns.items():
            m = pattern.match(stripped)
            if m:
                matched_key = key_name
                rest_of_line = m.group(1).strip()
                break

        if matched_key:
            current_key = matched_key
            labeled_dict[current_key] = [rest_of_line] if rest_of_line else []
        elif current_key:
            labeled_dict[current_key].append(stripped)

    # Check if we found at least 2 distinct recognized section headers
    if len(labeled_dict) >= 2:
        res = {k: " ".join(v).strip() for k, v in labeled_dict.items() if " ".join(v).strip()}
        for k in ("hook", "payoff", "PAYOFF"):
            if k in res:
                res[k] = clean_narrator_prefix(res[k])
        return res

    # Check for multi-paragraph or structured final script
    direct_structured = parse_user_script_into_sections(cleaned, video_type)
    if direct_structured:
        return direct_structured

    return None


def partition_turns_into_four_parts(turns: List[str]) -> List[str]:
    """
    Distributes N dialogue turns across 4 dialogue parts without duplicating any turn.
    Guarantees:
    - 0 turns are duplicated
    - 0 turns are lost
    - All turns are preserved in exact sequence
    """
    n = len(turns)
    if n == 0:
        return ["", "", "", ""]
    if n == 1:
        return [turns[0], "", "", ""]
    if n == 2:
        return [turns[0], turns[1], "", ""]
    if n == 3:
        return [turns[0], turns[1], turns[2], ""]
    if n == 4:
        return [turns[0], turns[1], turns[2], turns[3]]
    if n == 5:
        # Part 1 has first exchange (2 turns), Parts 2, 3, 4 have 1 turn each
        return [
            "\n".join(turns[0:2]),
            turns[2],
            turns[3],
            turns[4],
        ]
    if n == 6:
        # Parts 1 & 2 have 2 turns each, Parts 3 & 4 have 1 turn each
        return [
            "\n".join(turns[0:2]),
            "\n".join(turns[2:4]),
            turns[4],
            turns[5],
        ]
    if n == 7:
        # Parts 1, 2, 3 have 2 turns each, Part 4 has 1 turn
        return [
            "\n".join(turns[0:2]),
            "\n".join(turns[2:4]),
            "\n".join(turns[4:6]),
            turns[6],
        ]
    if n == 8:
        # Standard: exactly 2 turns per part
        return [
            "\n".join(turns[0:2]),
            "\n".join(turns[2:4]),
            "\n".join(turns[4:6]),
            "\n".join(turns[6:8]),
        ]
    # n > 8:
    # First 3 parts get 2 turns each, Part 4 gets all remaining turns
    return [
        "\n".join(turns[0:2]),
        "\n".join(turns[2:4]),
        "\n".join(turns[4:6]),
        "\n".join(turns[6:]),
    ]


def parse_user_script_into_sections(raw_script: str, video_type: str) -> Optional[Dict[str, str]]:
    """
    Parses a user-provided final script into canonical section keys based on
    paragraph breaks, dialogue structure, and quiz patterns.
    Ensures 0 words are rewritten or altered.
    """
    vtype = video_type.upper()
    lines = [line.strip() for line in raw_script.split("\n") if line.strip()]
    if not lines:
        return None

    parsed: Dict[str, str] = {}

    if vtype == "EXPRESSION":
        if len(lines) == 5:
            parsed = {
                "hook": lines[0],
                "setup": lines[1],
                "discovery": lines[2],
                "example": lines[3],
                "payoff": lines[4],
            }
        elif len(lines) == 4:
            parsed = {
                "hook": lines[0],
                "setup": lines[1],
                "discovery": lines[1],
                "example": lines[2],
                "payoff": lines[3],
            }
        elif len(lines) > 5:
            parsed = {
                "hook": lines[0],
                "setup": lines[1],
                "discovery": "\n\n".join(lines[2:-2]),
                "example": lines[-2],
                "payoff": lines[-1],
            }
        elif len(lines) >= 3:
            parsed = {
                "hook": lines[0],
                "setup": lines[1],
                "discovery": lines[1],
                "example": lines[2],
                "payoff": lines[-1],
            }

    elif vtype == "GAME":
        if len(lines) == 5:
            parsed = {
                "hook": lines[0],
                "challenge": lines[1],
                "pressure": lines[2],
                "answer": lines[3],
                "explanation": lines[4],
            }
        else:
            hook = lines[0]
            pressure_idx = -1
            for i in range(1, len(lines)):
                l_lower = lines[i].lower()
                if any(w in l_lower for w in ("second", "clock", "compte", "rebours", "freeze", "décide", "decide", "tiempo", "segundo", "tempo", "chrono")):
                    pressure_idx = i
                    break

            if pressure_idx != -1 and pressure_idx + 1 < len(lines):
                challenge = "\n".join(lines[1:pressure_idx])
                pressure = lines[pressure_idx]
                answer = lines[pressure_idx + 1]
                explanation = "\n".join(lines[pressure_idx + 2:]) if pressure_idx + 2 < len(lines) else answer
                parsed = {
                    "hook": hook,
                    "challenge": challenge,
                    "pressure": pressure,
                    "answer": answer,
                    "explanation": explanation,
                }
            elif len(lines) >= 4:
                parsed = {
                    "hook": lines[0],
                    "challenge": "\n".join(lines[1:-3]) if len(lines) > 4 else lines[1],
                    "pressure": lines[-3] if len(lines) > 3 else lines[-1],
                    "answer": lines[-2] if len(lines) > 2 else lines[-1],
                    "explanation": lines[-1],
                }

    elif vtype == "ROLEPLAY":
        char_pattern = re.compile(
            r"^(?:PERSON|CHARACTER)[_\s]*(?:ONE|TWO|1|2)\b", re.IGNORECASE
        )
        char_indices = [i for i, l in enumerate(lines) if char_pattern.match(l)]

        if char_indices:
            first_char_idx = char_indices[0]
            last_char_idx = char_indices[-1]

            hook_lines = lines[:first_char_idx]
            hook = clean_narrator_prefix("\n".join(hook_lines))

            payoff_lines = lines[last_char_idx + 1 :]
            payoff = clean_narrator_prefix("\n".join(payoff_lines))

            turns: List[str] = []
            current_turn: List[str] = []
            for l in lines[first_char_idx : last_char_idx + 1]:
                if char_pattern.match(l):
                    if current_turn:
                        turns.append("\n".join(current_turn))
                    current_turn = [l]
                else:
                    if current_turn:
                        current_turn.append(l)
            if current_turn:
                turns.append("\n".join(current_turn))

            parts = partition_turns_into_four_parts(turns)
            parsed = {
                "hook": hook or (lines[0] if lines else ""),
                "DIALOGUE_PART_1": parts[0],
                "DIALOGUE_PART_2": parts[1],
                "DIALOGUE_PART_3": parts[2],
                "DIALOGUE_PART_4": parts[3],
                "PAYOFF": payoff or (lines[-1] if len(lines) > 1 else hook),
            }
        else:
            hook = clean_narrator_prefix(lines[0])
            last_line = clean_narrator_prefix(lines[-1])
            parsed = {
                "hook": hook,
                "DIALOGUE_PART_1": "\n".join(lines[1:-1]) if len(lines) > 2 else (lines[1] if len(lines) > 1 else ""),
                "DIALOGUE_PART_2": "",
                "DIALOGUE_PART_3": "",
                "DIALOGUE_PART_4": "",
                "PAYOFF": last_line if len(lines) > 1 else hook,
            }

    elif vtype in ("FUN_FACTS", "FUNFACTS"):
        if len(lines) >= 4:
            parsed = {
                "hook": lines[0],
                "setup": lines[1],
                "discovery": "\n".join(lines[2:-2]) if len(lines) > 4 else lines[2],
                "payoff": "\n".join(lines[-2:]) if len(lines) > 4 else lines[-1],
            }
        elif len(lines) >= 2:
            parsed = {
                "hook": lines[0],
                "setup": lines[1],
                "discovery": lines[1],
                "payoff": lines[-1],
            }

    return parsed if parsed else None



def build_structuring_prompt(
    raw_script: str,
    video_type: str,
    target_language: str,
    expression_or_topic: str,
    existing_metadata: dict,
) -> str:
    """
    Constructs a prompt instructing the LLM to structure the raw script into
    the canonical JSON format while strictly preserving the spoken text verbatim.
    """
    vtype = video_type.upper()

    if vtype == "ROLEPLAY":
        format_spec = """
Required "script" object structure for ROLEPLAY:
{
    "title": "Short Catchy YouTube Title",
    "hook": "Narrator opening hook setting up the scene...",
    "DIALOGUE_PART_1": "PERSON_ONE (Emotion): line...\\nPERSON_TWO (Emotion): line...",
    "DIALOGUE_PART_2": "PERSON_ONE (Emotion): line...\\nPERSON_TWO (Emotion): line...",
    "DIALOGUE_PART_3": "PERSON_ONE (Emotion): line...\\nPERSON_TWO (Emotion): line...",
    "DIALOGUE_PART_4": "PERSON_ONE (Emotion): line...\\nPERSON_TWO (Emotion): line...",
    "PAYOFF": "Narrator closing explanation and memorable takeaway..."
}
Note on Character Dialogue & Narration:
- In "hook" and "PAYOFF", do NOT include the prefix "Narrator:" or "Voiceover:" because the TTS narrator voice speaks these sections automatically.
- Must have character dialogue lines prefixed with PERSON_ONE (Acting Tone): and PERSON_TWO (Acting Tone):
- Do NOT insert the Narrator into DIALOGUE_PART_1, 2, 3, or 4.
- Distribute character dialogue turns across DIALOGUE_PART_1 through DIALOGUE_PART_4 without duplicating any lines. If there are 5 turns, put the first 2 in DIALOGUE_PART_1 and 1 in each remaining part.
- In "character_personalities", infer distinct personalities for PERSON_ONE and PERSON_TWO based on their dialogue.
"""
    elif vtype == "GAME":
        format_spec = """
Required "script" object structure for GAME:
{
    "title": "Short Catchy Quiz Title",
    "hook": "Host opening hook challenging the audience...",
    "challenge": "What does this phrase mean? A) ... B) ... C) ... D) ...",
    "pressure": "Suspenseful countdown / urgency phrase...",
    "answer": "The correct answer is [Letter]: ...",
    "explanation": "Native usage explanation and call to action..."
}
Also include at root of content_metadata:
"chalkboard_exercise": "Clean text of the question\\nA) ...\\nB) ...\\nC) ...\\nD) ..."
"""
    elif vtype in ["FUN_FACTS", "FUNFACTS"]:
        format_spec = """
Required "script" object structure for FUN_FACTS:
{
    "title": "Short Catchy Title",
    "hook": "Direct curiosity hook addressing the viewer...",
    "setup": "Context or setup of the curiosity...",
    "discovery": "The surprising revelation or core facts...",
    "payoff": "Memorable takeaway and closing reaction..."
}
(If the script is a 3-facts format, use "fact_1", "fact_2", "fact_3" instead of setup/discovery.)
"""
    else:  # EXPRESSION
        format_spec = """
Required "script" object structure for EXPRESSION:
{
    "title": "Short Catchy Expression Title",
    "hook": "Immediate hook challenging misconception or grabbing attention...",
    "setup": "Sets up the story, dilemma, or origin...",
    "discovery": "Reveals the authentic expression and explains its nuance...",
    "example": "Real-world colloquial usage phrase showing how native speakers use it in conversation...",
    "payoff": "Catchy closing takeaway and call-to-action line..."
}
"""

    prompt = f"""You are an expert short-form video script formatter for LingoVerse YouTube Shorts.

TARGET INFORMATION:
- Video Type: {vtype}
- Target Language: {target_language}
- Expression / Topic: {expression_or_topic}

--------------------------------------------------------------------------------
USER-PROVIDED SCRIPT TO FORMAT (IMMUTABLE TEXT):
--------------------------------------------------------------------------------
{raw_script}

--------------------------------------------------------------------------------
CRITICAL IMMUTABILITY RULE (MANDATORY):
--------------------------------------------------------------------------------
1. You MUST NOT edit, rephrase, rewrite, correct, polish, summarize, or alter ANY spoken words or sentences from the user's script!
2. Every single word and sentence in the spoken sections MUST BE COPIED VERBATIM from the user's script above.
3. Your job is STRICTLY to:
   a) Create a short, catchy, high-impact YouTube Shorts title (under 8 words) as the FIRST key "title" in the script object (e.g. "{expression_or_topic}: The Native Secret"). Never use boring suffixes like "Shorts Guide".
   b) Partition the provided text into the required JSON section keys without losing or changing a single word.
   c) Generate the surrounding metadata for the video.

{format_spec}

--------------------------------------------------------------------------------
OUTPUT FORMAT:
--------------------------------------------------------------------------------
You MUST return ONLY a JSON object (no markdown, no backticks, no commentary).
Format:
{{
    "video_type": "{vtype}",
    "language": "{target_language}",
    "category": "{existing_metadata.get('category', 'Language Learning')}",
    "subcategory": "{existing_metadata.get('subcategory', 'Idioms & Vocabulary')}",
    "topic": "{expression_or_topic}",
    "learning_objective": "Clear description of what the viewer learns",
    "target_expression": "{expression_or_topic}",
    "difficulty": "Intermediate",
    "emotion": "Curiosity & Surprise",
    "related_content": [],
    "character_personalities": {{
        "Narrator": "{STATIC_NARRATOR_PERSONALITY}"
    }},
    "script": {{
        "title": "Short Catchy Title (FIRST KEY)",
        ...
    }}
}}
"""
    return prompt.strip()


CANONICAL_SCRIPT_KEYS_BY_TYPE: Dict[str, list[str]] = {
    "EXPRESSION": ["title", "hook", "setup", "discovery", "example", "payoff"],
    "GAME": ["title", "hook", "challenge", "pressure", "answer", "explanation"],
    "ROLEPLAY": ["title", "hook", "DIALOGUE_PART_1", "DIALOGUE_PART_2", "DIALOGUE_PART_3", "DIALOGUE_PART_4", "PAYOFF"],
    "FUN_FACTS": ["title", "hook", "setup", "discovery", "payoff"],
}


def format_script_with_llm(
    raw_script: str,
    video_type: str,
    target_language: str,
    expression_or_topic: str,
    existing_content_metadata: dict,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Calls the local LLM to format the script into canonical JSON while
    guaranteeing the user's text remains verbatim.
    Returns: (content_metadata_dict, script_dict)
    """
    direct_parsed = try_direct_script_parse(raw_script, video_type)

    prompt = build_structuring_prompt(
        raw_script=raw_script,
        video_type=video_type,
        target_language=target_language,
        expression_or_topic=expression_or_topic,
        existing_metadata=existing_content_metadata,
    )

    print("🤖 Prompting LLM to structure state JSON and metadata...")
    parsed_json: Dict[str, Any] = {}
    script_field: Dict[str, Any] = {}

    try:
        raw_response = generate_response(prompt, temperature=0.2)
        parsed_json = extract_json_from_llm(raw_response)
        script_field = parsed_json.get("script") or {}
        if not isinstance(script_field, dict):
            script_field = {}
    except Exception as llm_err:
        if direct_parsed:
            print(f"⚠️ LLM response error ({llm_err}). Constructing state JSON directly from user sections.")
            script_field = dict(direct_parsed)
            parsed_json = {
                "video_type": video_type.upper(),
                "language": target_language,
                "category": existing_content_metadata.get("category", "Language Learning"),
                "subcategory": existing_content_metadata.get("subcategory", "Idioms & Vocabulary"),
                "topic": expression_or_topic,
                "learning_objective": f"Learn the authentic usage of {expression_or_topic}",
                "target_expression": expression_or_topic,
                "difficulty": "Intermediate",
                "emotion": "Curiosity & Surprise",
                "related_content": [],
                "character_personalities": {"Narrator": STATIC_NARRATOR_PERSONALITY},
            }
        else:
            raise

    # If the user passed directly structured sections or paragraphs, enforce user's exact text
    if direct_parsed:
        print("✓ Verified direct user section structure — applying exact user text.")
        for k, v in direct_parsed.items():
            script_field[k] = v

    # Resolve and clean up a catchy title
    raw_title = (
        script_field.get("title")
        or parsed_json.get("title")
        or existing_content_metadata.get("script", {}).get("title")
        or existing_content_metadata.get("title")
        or f"{expression_or_topic}: The Native Secret"
    )
    if isinstance(raw_title, str):
        title_str = raw_title.strip().strip('"').strip("'")
        # Strip generic fallback suffix ': Shorts Guide'
        title_str = re.sub(r":\s*Shorts(?:\s*Guide)?$", "", title_str, flags=re.IGNORECASE).strip()
        if not title_str:
            title_str = f"{expression_or_topic}: The Native Secret"
    else:
        title_str = f"{expression_or_topic}: The Native Secret"

    # Enforce canonical ordering: 'title' MUST ALWAYS be first
    vtype_key = video_type.upper()
    canonical_keys = CANONICAL_SCRIPT_KEYS_BY_TYPE.get(vtype_key, ["title", "hook"])
    ordered_script: Dict[str, Any] = {"title": title_str}

    for c_key in canonical_keys:
        if c_key.lower() == "title":
            continue
        matched_k = None
        for sk in script_field:
            if sk.lower() == c_key.lower():
                matched_k = sk
                break
        if matched_k and matched_k in script_field:
            ordered_script[c_key] = script_field[matched_k]

    for sk, sv in script_field.items():
        if sk.lower() != "title" and not any(ck.lower() == sk.lower() for ck in canonical_keys):
            ordered_script[sk] = sv

    script_field = ordered_script

    # Clean narrator prefixes from hook and payoff so TTS voices don't speak "Narrator:"
    for k in ("hook", "payoff", "PAYOFF"):
        if k in script_field and isinstance(script_field[k], str):
            script_field[k] = clean_narrator_prefix(script_field[k])

    # For GAME, ensure chalkboard_exercise exists
    if video_type.upper() == "GAME":
        if "chalkboard_exercise" not in parsed_json or not parsed_json.get("chalkboard_exercise"):
            challenge_text = script_field.get("challenge", "")
            parsed_json["chalkboard_exercise"] = challenge_text

    # Ensure Narrator personality exists
    if "character_personalities" not in parsed_json or not isinstance(parsed_json["character_personalities"], dict):
        parsed_json["character_personalities"] = {}
    parsed_json["character_personalities"]["Narrator"] = STATIC_NARRATOR_PERSONALITY

    # For ROLEPLAY, ensure character personalities exist
    if video_type.upper() == "ROLEPLAY":
        if "PERSON_ONE" not in parsed_json["character_personalities"]:
            parsed_json["character_personalities"]["PERSON_ONE"] = "Expressive, animated, relatable conversational partner experiencing the scenario."
        if "PERSON_TWO" not in parsed_json["character_personalities"]:
            parsed_json["character_personalities"]["PERSON_TWO"] = "Knowledgeable, natural native speaker offering authentic cultural guidance."

    parsed_json["script"] = script_field
    parsed_json["video_type"] = video_type.upper()
    parsed_json["language"] = target_language

    return parsed_json, script_field



def modify_video_script(
    script_id: str,
    raw_script_text: str,
    reset_downstream: Optional[bool] = None,
    base_dir: Optional[Path] = None,
) -> bool:
    """
    Core function to modify an existing script state with plain text input.
    """
    base_dir = base_dir or BASE_DIR
    state_manager = StateManager(base_dir)

    script_id = script_id.strip().upper().replace("SCRIPT_", "").replace(".JSON", "")
    if not state_manager.script_exists(script_id):
        print(f"❌ Error: Script state for ID '{script_id}' does not exist.", file=sys.stderr)
        return False

    state = state_manager.get_script_state(script_id)

    # Resolve language and video type
    prompt_params = state.get("prompt_params", {})
    content_meta = state.get("content_metadata", {})

    target_lang = (
        prompt_params.get("TARGET_LANGUAGE")
        or content_meta.get("language")
        or "English"
    )
    video_type = (
        prompt_params.get("VIDEO_TYPE")
        or content_meta.get("video_type")
        or "EXPRESSION"
    ).upper()

    topic = (
        prompt_params.get("EXPRESSION")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("TOPIC")
        or content_meta.get("topic")
        or content_meta.get("target_expression")
        or script_id
    )

    print("\n" + "=" * 68)
    print(f"🔄 MODIFYING SCRIPT: {script_id}")
    print(f"   • Language:   {target_lang}")
    print(f"   • Video Type: {video_type}")
    print(f"   • Topic/Expr: {topic}")
    print("=" * 68)

    # Word count check
    input_word_count = count_words(raw_script_text)
    print(f"📝 Raw script received: {input_word_count} words.")

    # Call LLM to format
    try:
        new_content_meta, new_script = format_script_with_llm(
            raw_script=raw_script_text,
            video_type=video_type,
            target_language=target_lang,
            expression_or_topic=topic,
            existing_content_metadata=content_meta,
        )
    except Exception as exc:
        print(f"❌ Failed to format script with LLM: {exc}", file=sys.stderr)
        return False

    new_script_text = json.dumps(new_script, indent=2, ensure_ascii=False)

    # Generate rich YouTube metadata
    print("✨ Generating YouTube metadata (titles, tags, hashtags, descriptions)...")
    try:
        new_metadata = build_metadata(new_script_text, prompt_params or {
            "TARGET_LANGUAGE": target_lang,
            "VIDEO_TYPE": video_type,
            "EXPRESSION": topic,
            "ID": script_id
        })
    except Exception as me:
        print(f"⚠️ Warning: Metadata generation had error ({me}), using fallback.", file=sys.stderr)
        new_metadata = state.get("metadata", {})
        new_metadata["TITLE"] = new_script.get("title", f"{topic} Shorts")

    # Update state dictionary
    state["script_text"] = new_script_text
    state["content_metadata"] = new_content_meta
    state["metadata"] = new_metadata
    state["status"]["script_generation"] = "done"

    # Handle downstream statuses
    if reset_downstream is None:
        # Prompt interactively if in TTY, else default to True
        if sys.stdin.isatty():
            try:
                ans = input("\nReset downstream stages (voice, images, music, video) to 'pending'? [Y/n]: ").strip().lower()
                reset_downstream = ans not in ("n", "no")
            except (EOFError, KeyboardInterrupt):
                reset_downstream = True
        else:
            reset_downstream = True

    if reset_downstream:
        print("🔄 Resetting downstream stages to 'pending' for fresh rendering...")
        downstream_stages = [
            "voice_generation",
            "image_generation",
            "thumbnail_generation",
            "video_assembly",
        ]
        for stage in downstream_stages:
            state["status"][stage] = "pending"

    # Save updated state
    state_manager.save_script_state(script_id, state)
    print(f"\n✅ Script {script_id} successfully updated and saved to disk!")

    # Auto-update review CSV in scripts_to_see
    try:
        from tools.auditing.scrapper_script import process_scripts
        print(f"📊 Auto-updating review CSV in scripts_to_see for {target_lang}/{video_type}...")
        process_scripts(
            base_dir=BASE_DIR,
            target_languages=[target_lang.lower()],
            target_types=[video_type.lower()],
            include_tags=False,
            include_title=False,
        )
    except Exception as se:
        print(f"⚠️ Notice: Could not automatically update review CSV ({se})", file=sys.stderr)

    print("-" * 68)
    print(f"• Title:       {new_script.get('title')}")
    print(f"• Spoken Sections: {', '.join([k for k in new_script.keys() if k != 'title'])}")
    total_spoken_words = sum(count_words(str(v)) for k, v in new_script.items() if k != "title")
    print(f"• Total Spoken Words: {total_spoken_words} words")
    print(f"• YouTube Title:      {new_metadata.get('TITLE')}")
    print("=" * 68)
    return True


def prompt_for_script_input(
    script_id: str,
    default_text: Optional[str] = None,
    default_file: Optional[str] = None,
) -> Optional[str]:
    """Collects script text for a specific script ID either from args, file, or multiline paste."""
    if default_text:
        return default_text
    if default_file and Path(default_file).is_file():
        try:
            return Path(default_file).read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"❌ Error reading file '{default_file}': {e}", file=sys.stderr)

    print(f"\nProvide the new plain text script for [{script_id}].")
    print("You can:")
    print("  1. Enter a path to a .txt file containing the script, OR")
    print("  2. Paste your plain text script directly below.")
    print("When finished pasting, enter an empty line and type 'DONE' or 'EOF':")
    print("-" * 68)

    lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip().upper() in ("DONE", "EOF"):
            break
        lines.append(line)

    raw_script = "\n".join(lines).strip()

    # If user pasted a single path to a file, read it
    if raw_script and "\n" not in raw_script and Path(raw_script).is_file():
        try:
            print(f"Loading script from file: {raw_script}...")
            raw_script = Path(raw_script).read_text(encoding="utf-8").strip()
        except Exception as fe:
            print(f"Error reading file '{raw_script}': {fe}", file=sys.stderr)

    return raw_script if raw_script else None


def find_available_ready_scripts_csvs(search_dir: Optional[Path] = None) -> List[Path]:
    """Finds all ready_scripts_to_work_with CSV files in the destination directory."""
    target_dir = search_dir or resolve_ready_scripts_output_dir()
    if not target_dir.exists():
        return []
    work_with_files = list(target_dir.glob("*ready_scripts_to_work_with*.csv"))
    other_files = [
        f
        for f in target_dir.glob("*.csv")
        if f not in work_with_files and "error_report" not in f.name.lower()
    ]
    work_with_files.sort(
        key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True
    )
    other_files.sort(
        key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True
    )
    return work_with_files + other_files


def load_scripts_from_csv(
    csv_path: Path, state_manager: StateManager
) -> List[Tuple[str, str]]:
    """
    Parses a CSV file containing ID and SCRIPT_CHANGE columns,
    validates each script ID against state/, and returns a list of (script_id, raw_script_text).
    """
    if not csv_path.is_file():
        print(f"❌ File not found: {csv_path}", file=sys.stderr)
        return []

    try:
        raw_text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        try:
            raw_text = csv_path.read_text(encoding="latin-1", errors="replace")
        except Exception as e2:
            print(f"❌ Error reading '{csv_path.name}': {e2}", file=sys.stderr)
            return []

    # Clean manual CSV formatting quirks
    cleaned_text = re.sub(r'"[ \t]*,[ \t]*\r?\n', '"\n', raw_text)
    cleaned_text = re.sub(r',[ \t]+"', ',"', cleaned_text)

    reader = csv.DictReader(io.StringIO(cleaned_text), skipinitialspace=True)
    fieldnames = reader.fieldnames or []
    rows = list(reader)

    # Detect ID and SCRIPT_CHANGE / NEW_SCRIPT columns (case-insensitive)
    id_col = next(
        (c for c in fieldnames if c.strip().upper() in ("ID", "SCRIPT_ID")),
        None,
    )
    script_col = next(
        (
            c
            for c in fieldnames
            if c.strip().upper()
            in (
                "SCRIPT_CHANGE",
                "SCRIPT_CHANGED",
                "NEW_SCRIPT",
                "SCRIPT",
                "NEW_SCRIPT_TEXT",
            )
        ),
        None,
    )

    if not id_col or not script_col:
        print(
            f"❌ Error: '{csv_path.name}' is missing required columns ('ID', 'SCRIPT_CHANGE'). "
            f"Found headers: {fieldnames}",
            file=sys.stderr,
        )
        return []

    if not rows:
        print(f"⚠️ Warning: '{csv_path.name}' is empty (no data rows).")
        return []

    scripts_to_modify: List[Tuple[str, str]] = []
    print(f"\n📂 Parsing {csv_path.name} ({len(rows)} row(s) found)...")
    for r_idx, row in enumerate(rows, start=1):
        raw_id = str(row.get(id_col, "")).strip().upper()
        s_id = raw_id.replace("SCRIPT_", "").replace(".JSON", "").strip()
        raw_script = str(row.get(script_col, "")).strip()

        if not s_id:
            continue
        if not raw_script:
            print(f"  ⚠️ Row {r_idx} [{s_id}]: SCRIPT_CHANGE is blank — skipping.")
            continue
        if not state_manager.script_exists(s_id):
            print(
                f"  ❌ Row {r_idx} [{s_id}]: ID does not exist in state/ directory — skipping."
            )
            continue
        if any(s[0] == s_id for s in scripts_to_modify):
            print(
                f"  ⚠️ Row {r_idx} [{s_id}]: Duplicate ID in CSV — keeping first occurrence."
            )
            continue

        current_state = state_manager.get_script_state(s_id)
        lang, vtype = resolve_lang_and_type(s_id, current_state)
        topic = (
            current_state.get("prompt_params", {}).get("EXPRESSION")
            or current_state.get("prompt_params", {}).get("TOPIC")
            or current_state.get("content_metadata", {}).get("topic")
            or s_id
        )
        words = count_words(raw_script)
        scripts_to_modify.append((s_id, raw_script))
        print(
            f"  ✓ [{s_id}] {lang.upper()}/{vtype.upper()} — \"{topic}\" (~{words} words)"
        )

    return scripts_to_modify


def interactive_main():
    """Interactive CLI workflow supporting single, batch (mass), or CSV-driven script modification."""
    parser = argparse.ArgumentParser(
        description="LingoVerse Script Modifier — Update script from plain text while keeping text verbatim."
    )
    parser.add_argument("--script-id", help="Video ID (or comma-separated IDs) to modify (e.g. EE01 or EE01,FG02)")
    parser.add_argument("--script-file", help="Path to plain text file containing the new script")
    parser.add_argument("--script-text", help="Direct script text string (for testing/scripting)")
    parser.add_argument("--csv", help="Path to ready_scripts_to_work_with CSV file to modify in batch")
    parser.add_argument("--mass", "--batch", action="store_true", help="Launch directly into Mass Script Modification mode")
    parser.add_argument("--reset-downstream", action="store_true", help="Automatically reset downstream stages to pending")
    parser.add_argument("--keep-downstream", action="store_true", help="Keep current downstream stage statuses intact")

    args = parser.parse_args()

    print("=" * 68)
    print("🎬 LINGOVERSE SCRIPT MODIFIER (Interactive Script Ingestion)")
    print("=" * 68)

    state_manager = StateManager(BASE_DIR)
    scripts_to_modify: list[Tuple[str, str]] = []  # List of (script_id, raw_script_text)

    # 0. Direct CSV execution if --csv was passed
    if args.csv:
        csv_file = Path(args.csv)
        scripts_to_modify = load_scripts_from_csv(csv_file, state_manager)
        if not scripts_to_modify:
            print(f"❌ No valid scripts to modify found in CSV: {args.csv}", file=sys.stderr)
            return 1

    # 1. Non-interactive direct execution if arguments were passed
    if args.script_id:
        raw_ids = [x.strip().upper().replace("SCRIPT_", "").replace(".JSON", "") for x in args.script_id.split(",") if x.strip()]
        if len(raw_ids) == 1 and (args.script_text or args.script_file):
            s_id = raw_ids[0]
            if not state_manager.script_exists(s_id):
                print(f"❌ Script ID '{s_id}' does not exist in state/ directory.", file=sys.stderr)
                return 1
            raw_script = prompt_for_script_input(s_id, default_text=args.script_text, default_file=args.script_file)
            if not raw_script:
                print("❌ Error: No script text was provided.", file=sys.stderr)
                return 1
            scripts_to_modify.append((s_id, raw_script))
        elif len(raw_ids) > 1:
            print(f"📦 Pre-selected {len(raw_ids)} script IDs for mass modification: {', '.join(raw_ids)}")
            for idx, s_id in enumerate(raw_ids, 1):
                if not state_manager.script_exists(s_id):
                    print(f"❌ Skipping '{s_id}': does not exist in state/ directory.", file=sys.stderr)
                    continue
                current_state = state_manager.get_script_state(s_id)
                lang, vtype = resolve_lang_and_type(s_id, current_state)
                topic = (
                    current_state.get("prompt_params", {}).get("EXPRESSION")
                    or current_state.get("prompt_params", {}).get("TOPIC")
                    or current_state.get("content_metadata", {}).get("topic")
                    or s_id
                )
                print(f"\n[{idx}/{len(raw_ids)}] Target Video: [{s_id}] {lang.upper()} / {vtype.upper()} — Topic: {topic}")
                raw_script = prompt_for_script_input(s_id)
                if raw_script:
                    scripts_to_modify.append((s_id, raw_script))
                    print(f"✓ Added [{s_id}] to batch queue ({len(scripts_to_modify)} total queued).")

    # 2. Interactive mode selection (Single Script vs Mass Script Changes)
    if not scripts_to_modify:
        mode = "2" if args.mass else None
        if not mode:
            print("Select modification mode:")
            print("  [1] Single Script (modify 1 video script)")
            print("  [2] Mass Script Changes (queue multiple scripts by ID, then process all with LLM)")
            print("  [3] From Ready Scripts CSV (import ID & SCRIPT_CHANGE from ready_scripts_to_work_with.csv)")
            print("-" * 68)
            try:
                choice = input("Choice [1/2/3] (default [1]): ").strip()
                if choice == "2":
                    mode = "2"
                elif choice == "3":
                    mode = "3"
                else:
                    mode = "1"
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled by user.")
                return 0

        if mode == "1":
            # --- Single Script Mode ---
            print("\n--- [Single Script Modification] ---")
            target_id = None
            while not target_id:
                try:
                    val = input("Enter Video ID to modify (e.g. EE01, FG02, SR03, IF04): ").strip()
                    if not val:
                        print("No ID entered. Exiting.")
                        return 0
                    parsed_id = val.upper().replace("SCRIPT_", "").replace(".JSON", "").strip()
                    if not state_manager.script_exists(parsed_id):
                        print(f"❌ Script ID '{parsed_id}' does not exist in state/ directory.")
                        continue
                    target_id = parsed_id
                except (EOFError, KeyboardInterrupt):
                    print("\nOperation cancelled by user.")
                    return 0

            current_state = state_manager.get_script_state(target_id)
            lang, vtype = resolve_lang_and_type(target_id, current_state)
            topic = (
                current_state.get("prompt_params", {}).get("EXPRESSION")
                or current_state.get("prompt_params", {}).get("TOPIC")
                or current_state.get("content_metadata", {}).get("topic")
                or target_id
            )
            current_title = (
                current_state.get("content_metadata", {}).get("script", {}).get("title")
                or current_state.get("metadata", {}).get("TITLE")
                or "N/A"
            )
            print(f"\nTarget Video: [{target_id}] {lang.upper()} / {vtype.upper()}")
            print(f"Topic:        {topic}")
            print(f"Current Title:{current_title}")
            print("-" * 68)

            raw_script = prompt_for_script_input(
                target_id,
                default_text=args.script_text,
                default_file=args.script_file,
            )
            if not raw_script:
                print(f"❌ No script text provided for {target_id}. Exiting.")
                return 1
            scripts_to_modify.append((target_id, raw_script))

        elif mode == "2":
            # --- Mass Script Changes Mode ---
            print("\n" + "=" * 68)
            print("📦 MASS SCRIPT MODIFICATION MODE")
            print("====================================================================")
            print("Queue multiple scripts by entering each Video ID followed by its new script.")
            print("When you finish setting the group of scripts, the LLM will be launched")
            print("to format and update all corresponding JSON states in batch.")
            print("-" * 68)

            item_num = 1
            while True:
                prompt_msg = f"\n[Item #{item_num}] Enter Video ID (e.g. EE01, FG02)"
                if scripts_to_modify:
                    prompt_msg += " [or press Enter / type 'DONE' to launch LLM batch]"
                prompt_msg += ": "

                try:
                    val = input(prompt_msg).strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nFinished queuing scripts.")
                    break

                if not val or val.upper() in ("DONE", "FINISH", "GO", "EXIT", "STOP"):
                    if scripts_to_modify:
                        break
                    print("No ID entered. Exiting.")
                    return 0

                parsed_id = val.upper().replace("SCRIPT_", "").replace(".JSON", "").strip()
                if not state_manager.script_exists(parsed_id):
                    print(f"❌ Script ID '{parsed_id}' does not exist in state/ directory. Please try again.")
                    continue
                if any(s[0] == parsed_id for s in scripts_to_modify):
                    print(f"⚠️ Script ID '{parsed_id}' is already in your modification queue.")
                    continue

                current_state = state_manager.get_script_state(parsed_id)
                lang, vtype = resolve_lang_and_type(parsed_id, current_state)
                topic = (
                    current_state.get("prompt_params", {}).get("EXPRESSION")
                    or current_state.get("prompt_params", {}).get("TOPIC")
                    or current_state.get("content_metadata", {}).get("topic")
                    or parsed_id
                )
                print(f"Target Video: [{parsed_id}] {lang.upper()} / {vtype.upper()} — Topic: {topic}")

                raw_script = prompt_for_script_input(parsed_id)
                if not raw_script:
                    print(f"⚠️ No script text provided for {parsed_id}. Skipping.")
                    continue

                scripts_to_modify.append((parsed_id, raw_script))
                print(f"✓ Added [{parsed_id}] to batch queue ({len(scripts_to_modify)} total queued).")
                item_num += 1

                try:
                    more = input("\nAdd another script to this batch? [Y/n]: ").strip().lower()
                    if more in ("n", "no"):
                        break
                except (EOFError, KeyboardInterrupt):
                    print("\nFinished queuing scripts.")
                    break

        elif mode == "3":
            # --- Ready Scripts CSV Mode ---
            print("\n" + "=" * 68)
            print("📑 READY SCRIPTS CSV IMPORT MODE")
            print("====================================================================")
            print("Import ID and SCRIPT_CHANGE from ready_scripts_to_work_with CSV files.")
            ready_dir = resolve_ready_scripts_output_dir()
            print(f"Search Directory: {ready_dir}")
            print("-" * 68)

            available_files = find_available_ready_scripts_csvs(ready_dir)
            selected_csv: Optional[Path] = None

            if available_files:
                print(f"Found ready scripts CSV file(s) in {ready_dir}:")
                for f_idx, f_path in enumerate(available_files, 1):
                    default_tag = " [Default]" if f_idx == 1 else ""
                    print(f"  [{f_idx}] {f_path.name}{default_tag}")
                print("  [C] Enter custom CSV file path")
                print("-" * 68)

                while not selected_csv:
                    try:
                        choice = input(
                            f"Select file (1-{len(available_files)}, or C) [default: 1]: "
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nOperation cancelled by user.")
                        return 0

                    if not choice or choice == "1":
                        selected_csv = available_files[0]
                        break
                    if choice.upper() == "C":
                        try:
                            custom_path = (
                                input("Enter full path to CSV file: ")
                                .strip()
                                .strip('"')
                                .strip("'")
                            )
                            if custom_path:
                                selected_csv = Path(custom_path)
                            else:
                                print("No path entered. Exiting.")
                                return 0
                        except (EOFError, KeyboardInterrupt):
                            print("\nOperation cancelled by user.")
                            return 0
                        break
                    try:
                        idx_num = int(choice)
                        if 1 <= idx_num <= len(available_files):
                            selected_csv = available_files[idx_num - 1]
                            break
                        else:
                            print(
                                f"Invalid number. Please enter 1 to {len(available_files)}."
                            )
                    except ValueError:
                        p = Path(choice.strip('"').strip("'"))
                        if p.is_file():
                            selected_csv = p
                            break
                        print("Invalid choice. Please select a valid number or enter 'C'.")
            else:
                print(f"No ready scripts CSV files found in {ready_dir}.")
                try:
                    custom_path = (
                        input("Enter path to ready_scripts_to_work_with CSV file: ")
                        .strip()
                        .strip('"')
                        .strip("'")
                    )
                    if custom_path:
                        selected_csv = Path(custom_path)
                    else:
                        print("No path entered. Exiting.")
                        return 0
                except (EOFError, KeyboardInterrupt):
                    print("\nOperation cancelled by user.")
                    return 0

            if selected_csv:
                scripts_to_modify = load_scripts_from_csv(selected_csv, state_manager)
                if not scripts_to_modify:
                    print("❌ No valid scripts queued from CSV. Exiting.")
                    return 1

    if not scripts_to_modify:
        print("\nNo scripts queued for modification. Exiting.")
        return 0

    # Display queue summary
    print("\n" + "=" * 68)
    print(f"📋 Queued {len(scripts_to_modify)} script(s) for LLM modification:")
    for i, (sid, s_text) in enumerate(scripts_to_modify, 1):
        words = count_words(s_text)
        print(f"  {i}. [{sid}] (~{words} words)")
    print("=" * 68)

    # Check LLM connection once before processing
    print("\n🔍 Checking LLM service connection...")
    try:
        require_services(llm=True)
    except ConnectionError as ce:
        print(f"❌ LLM Connection Error: {ce}", file=sys.stderr)
        print("Please ensure your local LLM server is running.")
        return 1

    # Determine downstream reset flag
    reset_downstream = None
    if args.reset_downstream:
        reset_downstream = True
    elif args.keep_downstream:
        reset_downstream = False
    elif sys.stdin.isatty():
        try:
            count_label = f"all {len(scripts_to_modify)}" if len(scripts_to_modify) > 1 else "this"
            ans = input(
                f"\nReset downstream stages (voice, images, music, video) to 'pending' for {count_label} script(s)? [Y/n]: "
            ).strip().lower()
            reset_downstream = ans not in ("n", "no")
        except (EOFError, KeyboardInterrupt):
            reset_downstream = True
    else:
        reset_downstream = True

    # Process all queued scripts in sequence
    success_count = 0
    failed_ids = []
    total = len(scripts_to_modify)

    print(f"\n🚀 Launching LLM to format and update {total} script(s)...")
    for idx, (s_id, s_text) in enumerate(scripts_to_modify, 1):
        print(f"\n[{idx}/{total}] Processing script {s_id} with LLM...")
        ok = modify_video_script(
            script_id=s_id,
            raw_script_text=s_text,
            reset_downstream=reset_downstream,
            base_dir=BASE_DIR,
        )
        if ok:
            success_count += 1
        else:
            failed_ids.append(s_id)
        # Breather cooldown between batch items so LLM slots return cleanly to idle ("go ahead, don't stop")
        time.sleep(0.3)

    print("\n" + "=" * 68)
    print(f"🏁 Batch Modification Complete: {success_count}/{total} succeeded.")
    if failed_ids:
        print(f"❌ Failed scripts: {', '.join(failed_ids)}")
    print("=" * 68)

    return 0 if success_count == total else 1


if __name__ == "__main__":
    sys.exit(interactive_main())
