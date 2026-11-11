"""
text_utils.py — Shared text processing, spoken-word metric calculation, and JSON extraction.
Ensures Stage A word counts accurately mirror Stage B TTS speech without phantom metadata bloat.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

# Matches speaker tags at line starts or inline, e.g. "PERSON_ONE:", "PERSON_TWO (Happy):", "NARRATOR:"
SPEAKER_PREFIX_PATTERN = re.compile(
    r"^\s*(?:PERSON[_\s]*(?:ONE|TWO|1|2)|NARRATOR|HOST|CHARACTER[_\s]*\d+)(?:\s*\([^)]*\))?\s*[:\-]\s*",
    flags=re.IGNORECASE | re.MULTILINE,
)

# Matches parenthetical cues and stage directions, e.g. (Curious & energetic), (laughing), [whispering]
STAGE_DIRECTION_PATTERN = re.compile(r"[\(\[][^)\]]*[\)\]]")

# Matches leading narrator prefix specifically for hook / payoff sanitization (English, Spanish, French, Italian)
NARRATOR_PREFIX_PATTERN = re.compile(
    r"^\s*(?:NARRATOR|NARRADOR|NARRATEUR|NARRATORE)\s*(?:\([^)]*\))?\s*[:\-]\s*",
    flags=re.IGNORECASE,
)


def clean_narrator_prefix(text: str) -> str:
    """Strips leading 'Narrator:' or 'Narrator (cheerful):' prefix from narration text."""
    if not text:
        return ""
    return NARRATOR_PREFIX_PATTERN.sub("", text.strip()).strip()


def strip_speaker_tags(text: str) -> str:
    """Strips character tags like 'PERSON_ONE:' or 'PERSON_TWO (curious):' from dialogue lines."""
    if not text:
        return ""
    return SPEAKER_PREFIX_PATTERN.sub("", text)


def strip_stage_directions(text: str) -> str:
    """Strips parenthetical emotion cues and stage directions like '(excited)' or '[sighs]'."""
    if not text:
        return ""
    return STAGE_DIRECTION_PATTERN.sub(" ", text)


def extract_spoken_text(text: str) -> str:
    """
    Extracts the clean, pronounceable spoken dialogue from a raw script line
    by eliminating speaker labels and parenthetical actor instructions.
    """
    if not text:
        return ""
    cleaned = strip_speaker_tags(text)
    cleaned = strip_stage_directions(cleaned)
    # Collapse multiple whitespaces
    return " ".join(cleaned.split())


def count_spoken_words(content: Union[str, Dict[str, Any]]) -> int:
    """
    Calculates the true spoken word count for a script or text fragment.
    Excludes speaker labels ('PERSON_ONE:'), emotion cues ('(curious & energetic)'),
    and non-spoken metadata to align Stage A validation with Stage B audio duration.
    """
    if not content:
        return 0

    if isinstance(content, dict):
        total = 0
        for key, val in content.items():
            # Skip metadata fields that are never spoken aloud
            if str(key).lower() in ("chalkboard_exercise", "title", "description", "tags", "hashtags"):
                continue
            if isinstance(val, str):
                spoken = extract_spoken_text(val)
                total += len(spoken.split())
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        total += len(extract_spoken_text(item).split())
        return total

    # If it's a string
    spoken = extract_spoken_text(str(content))
    return len(spoken.split())


def extract_json_from_llm_response(raw_text: str) -> Dict[str, Any]:
    """
    Extracts and parses a JSON object from raw LLM output, handling markdown
    fences (```json ... ```), preamble, or trailing conversational text.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response received from LLM.")

    text = raw_text.strip()

    # 1. Attempt fenced code block extraction
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 2. Attempt outermost curly braces extraction
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = text[start_idx : end_idx + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as err:
            raise ValueError(f"Found JSON-like block but failed to parse: {err}") from err

    # 3. Direct JSON attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        raise ValueError(f"Could not extract valid JSON from LLM response: {err}") from err

