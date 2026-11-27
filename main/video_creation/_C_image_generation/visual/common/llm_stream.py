"""
visual/common/llm_stream.py — JSON payload extraction and shared LLM helpers.
"""
from __future__ import annotations

import json
import re


def _extract_json_payload(raw_text: str) -> dict:
    """Extracts a JSON dictionary from LLM response text robustly."""
    cleaned = raw_text.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except Exception:
            pass

    brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except Exception:
            pass

    return {}
