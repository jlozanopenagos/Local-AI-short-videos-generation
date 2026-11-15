#!/usr/bin/env python3
"""
harmonize_state_jsons.py — Harmonize All State JSON Files to Canonical Schema.

Performs:
1. Harmonizes Roleplay keys to uniform lowercase (dialogue_part_1..4, payoff).
2. Cleans non-spoken metadata out of script dictionaries.
3. Formats GAME chalkboard_exercise with clean line breaks per option.
4. Re-serializes script_text to exactly match content_metadata.script.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = BASE_DIR / "state"

ROLEPLAY_KEY_MAP = {
    "DIALOGUE_PART_1": "dialogue_part_1",
    "DIALOGUE_PART_2": "dialogue_part_2",
    "DIALOGUE_PART_3": "dialogue_part_3",
    "DIALOGUE_PART_4": "dialogue_part_4",
    "PAYOFF": "payoff",
    "HOOK": "hook",
    "TITLE": "title",
    "SETUP": "setup",
    "DISCOVERY": "discovery",
    "EXAMPLE": "example",
    "CHALLENGE": "challenge",
    "PRESSURE": "pressure",
    "ANSWER": "answer",
    "EXPLANATION": "explanation",
}

NON_SPOKEN_METADATA_KEYS = {
    "game_archetype", "difficulty", "learning_objective", "category",
    "subcategory", "video_type", "language", "tags", "hashtags",
    "target_expression", "topic", "related_content", "character_personalities",
    "chalkboard_exercise", "anchor_environment", "character_anchors", "speakers_voice",
    "speakers_gender", "cast_meta"
}


def harmonize_state_file(path: Path) -> bool:
    try:
        raw_content = path.read_text(encoding="utf-8")
        data = json.loads(raw_content)
    except Exception as e:
        print(f"Error reading {path.name}: {e}", file=sys.stderr)
        return False

    if not isinstance(data, dict):
        return False

    modified = False

    content_meta = data.setdefault("content_metadata", {})
    if not isinstance(content_meta, dict):
        content_meta = {}
        data["content_metadata"] = content_meta
        modified = True

    # Remove buggy nested content_metadata if present
    if "content_metadata" in content_meta:
        del content_meta["content_metadata"]
        modified = True

    script = content_meta.get("script", {})
    if not isinstance(script, dict):
        script = {}
        content_meta["script"] = script

    # If PAYOFF or payoff was misplaced at content_metadata root, restore to script
    for root_payoff_key in ("PAYOFF", "payoff"):
        if root_payoff_key in content_meta:
            if "payoff" not in script and "PAYOFF" not in script:
                script["payoff"] = content_meta[root_payoff_key]
                modified = True
            del content_meta[root_payoff_key]
            modified = True

    new_script: Dict[str, Any] = {}

    # Put title first
    title_val = script.get("title") or script.get("TITLE") or ""
    if title_val:
        new_script["title"] = title_val

    for k, v in script.items():
        if k.lower() == "title":
            continue

        # Check for non-spoken metadata inside script
        if k.lower() in NON_SPOKEN_METADATA_KEYS:
            if k not in content_meta:
                content_meta[k] = v
            modified = True
            continue

        clean_k = ROLEPLAY_KEY_MAP.get(k, k.lower() if k.isupper() else k)
        if clean_k != k:
            modified = True
        new_script[clean_k] = v

    if new_script != script:
        content_meta["script"] = new_script
        modified = True

    # Check script_text harmonization
    expected_script_text = json.dumps(new_script, indent=2, ensure_ascii=False)
    if data.get("script_text") != expected_script_text:
        data["script_text"] = expected_script_text
        modified = True

    # For GAME scripts: format chalkboard_exercise with line breaks
    vtype = (
        content_meta.get("video_type")
        or data.get("prompt_params", {}).get("VIDEO_TYPE")
        or ""
    ).upper()

    if vtype == "GAME":
        cb = content_meta.get("chalkboard_exercise", "")
        if not cb:
            chal = new_script.get("challenge", "")
            if chal:
                cb = chal
                content_meta["chalkboard_exercise"] = cb
                modified = True

        if isinstance(cb, str) and cb:
            # Check if options are inline without newlines
            if "A:" in cb and "B:" in cb and "\nA:" not in cb:
                formatted_cb = re.sub(r"\s+([A-D]\s*[:\)\.\-])", r"\n\1", cb).strip()
                if formatted_cb != cb:
                    content_meta["chalkboard_exercise"] = formatted_cb
                    modified = True

    if modified:
        new_raw = json.dumps(data, indent=4, ensure_ascii=False) + "\n"
        path.write_text(new_raw, encoding="utf-8")
        return True

    return False


def main():
    state_files = sorted(STATE_DIR.rglob("script_*.json"))
    print(f"Scanning {len(state_files)} state JSON files...")

    harmonized_count = 0
    for sf in state_files:
        if harmonize_state_file(sf):
            harmonized_count += 1

    print(f"Harmonization complete! {harmonized_count} file(s) updated to canonical schema.")
    print(f"Total healthy files: {len(state_files)}")


if __name__ == "__main__":
    main()
