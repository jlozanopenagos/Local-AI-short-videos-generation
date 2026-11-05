"""Build all video metadata in a single LLM call that returns JSON."""

from __future__ import annotations

import json
import re

try:
    # pyrefly: ignore [missing-import]
    from core.llm import generate_response
    from prompts.prompts_data import METADATA_PROMPT, get_metadata_prompt
except (ImportError, ModuleNotFoundError):
    from video_creation._A_video_scripts.core.llm import generate_response
    from video_creation._A_video_scripts.prompts.prompts_data import METADATA_PROMPT, get_metadata_prompt

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

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"
    "\U00002600-\U000026FF"  # miscellaneous symbols
    "\U00002300-\U000023FF"  # miscellaneous technical
    "]+",
    flags=re.UNICODE,
)

BANNED_SUFFIX_PATTERNS = [
    re.compile(r"\s*[:：\-–—]\s*(?:the\s+)?native\s+secret\b.*$", re.IGNORECASE),
    re.compile(r"\s*[:：\-–—]\s*(?:le\s+)?secret\s+des\s+natifs\b.*$", re.IGNORECASE),
    re.compile(r"\s*[:：\-–—]\s*(?:il\s+)?segreto\s+dei\s+nativi\b.*$", re.IGNORECASE),
    re.compile(r"\s*[:：\-–—]\s*(?:el\s+)?secreto\s+de\s+los\s+nativos\b.*$", re.IGNORECASE),
    re.compile(r"\s*[:：\-–—]\s*(?:the\s+)?secret\s*$", re.IGNORECASE),
    re.compile(r"\s*[:：\-–—]\s*shorts\s+guide\b.*$", re.IGNORECASE),
    re.compile(r"\s*[:：\-–—]\s*game\s+changer\b.*$", re.IGNORECASE),
]


def strip_emojis(text: str) -> str:
    """Removes all emojis and pictographs from text."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", str(text))
    return re.sub(r"\s+", " ", cleaned).strip()


def sanitize_title(title: str) -> str:
    """Strips emojis, quotes, and formulaic clichés from titles."""
    if not title:
        return ""
    cleaned = strip_emojis(title).strip().strip('"').strip("'")
    for pattern in BANNED_SUFFIX_PATTERNS:
        cleaned = pattern.sub("", cleaned).strip()
    return cleaned


def _extract_json(raw: str) -> dict:
    """Try to extract a JSON object from the LLM response."""
    stripped = re.sub(r"```(?:json)?", "", raw).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

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

    vtype = str(params.get("VIDEO_TYPE", "EXPRESSION")).upper()
    lang = str(params.get("TARGET_LANGUAGE", "English"))

    prompt_template = get_metadata_prompt(vtype, lang)
    combined_prompt = f"{prompt_template}\n\n---\n\n{input_data}"
    raw = generate_response(combined_prompt)

    parsed = _extract_json(raw)

    # Build output, filling in fallbacks for any missing field
    result: dict[str, str] = {}
    for llm_key, csv_col in _KEY_MAP.items():
        value = parsed.get(llm_key, "").strip()
        result[csv_col] = value if value else _FALLBACK_VALUES[llm_key]

    # Sanitize title (zero emojis, zero banned suffixes)
    if result.get("TITLE"):
        result["TITLE"] = sanitize_title(result["TITLE"])

    # Strip emojis from description fields as well
    if result.get("DESCRIPTION"):
        result["DESCRIPTION"] = strip_emojis(result["DESCRIPTION"])
    if result.get("SHORT_DESCRIPTION"):
        result["SHORT_DESCRIPTION"] = strip_emojis(result["SHORT_DESCRIPTION"])

    return result
