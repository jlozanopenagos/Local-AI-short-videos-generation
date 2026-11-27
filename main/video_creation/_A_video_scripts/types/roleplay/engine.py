"""
types/roleplay/engine.py — Dedicated domain engine for ROLEPLAY shorts.
Enforces strict 2-speaker interaction in every part and authentic dialogue pacing.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from ...common.base_engine import BaseScriptEngine, ValidationResult
from ...common.text_utils import clean_narrator_prefix
from ...registry import register_script_engine
from .prompts import build_roleplay_prompt
from .validator import validate_roleplay_script


@register_script_engine
class RoleplayEngine(BaseScriptEngine):
    """Domain engine for authentic two-character roleplay scripts."""

    script_type: str = "roleplay"
    type_codes: list[str] = ["R"]

    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        return build_roleplay_prompt(input_data)

    def validate(
        self,
        script_dict: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        return validate_roleplay_script(script_dict, input_data)

    def sanitize(
        self,
        script_dict: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes roleplay components:
        1. Strips 'Narrator:' prefixes from hook and payoff.
        2. Ensures clean linebreaks before PERSON_TWO in dialogue parts.
        """
        cleaned = dict(script_dict)
        script_body = cleaned.get("script") if isinstance(cleaned.get("script"), dict) else cleaned
        script_body = dict(script_body)

        # 1. Clean narrator prefixes
        if "hook" in script_body:
            script_body["hook"] = clean_narrator_prefix(str(script_body["hook"]))
        if "PAYOFF" in script_body:
            script_body["PAYOFF"] = clean_narrator_prefix(str(script_body["PAYOFF"]))
        elif "payoff" in script_body:
            script_body["payoff"] = clean_narrator_prefix(str(script_body["payoff"]))

        # 2. Normalize dialogue turn separation
        for part_name in ("DIALOGUE_PART_1", "DIALOGUE_PART_2", "DIALOGUE_PART_3", "DIALOGUE_PART_4"):
            for k in list(script_body.keys()):
                if k.upper() == part_name:
                    text = str(script_body[k]).strip()
                    # Ensure newline before PERSON_TWO if on same line
                    text = re.sub(
                        r"(?<!\n)\s*(PERSON[_\s]*(?:TWO|2)\b)",
                        r"\n\1",
                        text,
                        flags=re.IGNORECASE,
                    )
                    script_body[k] = text

        if isinstance(cleaned.get("script"), dict):
            cleaned["script"] = script_body
            return cleaned
        return script_body

