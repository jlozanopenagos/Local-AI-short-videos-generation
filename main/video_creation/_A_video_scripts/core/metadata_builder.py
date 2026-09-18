"""Build all video metadata in a single LLM call that returns JSON."""

from __future__ import annotations

import json
import re

try:
    # pyrefly: ignore [missing-import]
    from core.llm import generate_response
    from prompts.prompts_data import METADATA_PROMPT
except (ImportError, ModuleNotFoundError):
    from video_creation._A_video_scripts.core.llm import generate_response
    from video_creation._A_video_scripts.prompts.prompts_data import METADATA_PROMPT

# Keys we expect back from the LLM (must match config/prompts.py field names)
_EXPECTED_KEYS = ("title", "description", "short_description", "tags", "hashtags", "label", "filename")

# Maps LLM JSON keys → METADATA.csv column names
_KEY_MAP = {
    "title":             "TITLE",
    "description":       "DESCRIPTION",
    "short_description": "SHORT_DESCRIPTION",
    "tags":              "TAGS",
    "hashtags":          "HASHTAGS",
    "label":             "LABEL",
    "filename":          "FILENAME",
}

_FALLBACK_VALUES: dict[str, str] = {
    "title":             "TITLE_GENERATION_FAILED",
    "description":       "DESCRIPTION_GENERATION_FAILED",
    "short_description": "SHORT_DESC_GENERATION_FAILED",
    "tags":              "TAGS_GENERATION_FAILED",
    "hashtags":          "HASHTAGS_GENERATION_FAILED",
    "label":             "LABEL_GENERATION_FAILED",
    "filename":          "filename_generation_failed.mp4",
}


def _extract_json(raw: str) -> dict:
    """Try to extract a JSON object from the LLM response.

    The LLM might wrap the JSON in markdown fences or add trailing text.
    We strip fences first, then attempt a parse; if that fails we search
    for the first '{...}' block in the response.
    """
    # Strip markdown code fences if present
    stripped = re.sub(r"```(?:json)?", "", raw).strip()

    # Fast path: the whole response is valid JSON
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first {...} block
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


def build_metadata(script: str, params: dict) -> dict:
    """Generate all metadata from script + params in a single LLM call.

    Returns a dict with uppercase CSV column names as keys.
    Falls back to placeholder strings for any field the LLM omits or
    if the response cannot be parsed as JSON.
    """
    input_data = (
        f"SCRIPT:\n{script}\n\n"
        f"PARAMS:\n{params}"
    )

    combined_prompt = f"{METADATA_PROMPT}\n\n---\n\n{input_data}"
    raw = generate_response(combined_prompt)

    parsed = _extract_json(raw)

    # Build output, filling in fallbacks for any missing field
    result: dict[str, str] = {}
    for llm_key, csv_col in _KEY_MAP.items():
        value = parsed.get(llm_key, "").strip()
        result[csv_col] = value if value else _FALLBACK_VALUES[llm_key]

    return result