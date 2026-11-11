"""
types/expression/engine.py — Dedicated domain engine for EXPRESSION shorts.
Focuses on authentic storytelling, colloquial usage, and punchy delivery.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ...common.base_engine import BaseScriptEngine, ValidationResult
from ...common.text_utils import clean_narrator_prefix
from ...registry import register_script_engine
from .prompts import build_expression_prompt
from .validator import validate_expression_script


@register_script_engine
class ExpressionEngine(BaseScriptEngine):
    """Domain engine for viral linguistic expression scripts."""

    script_type: str = "expression"
    type_codes: list[str] = ["E"]

    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        return build_expression_prompt(input_data)

    def validate(
        self,
        script_dict: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        return validate_expression_script(script_dict, input_data)

    def sanitize(
        self,
        script_dict: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Strips 'Narrator:' prefixes from hook and payoff."""
        cleaned = dict(script_dict)
        script_body = cleaned.get("script") if isinstance(cleaned.get("script"), dict) else cleaned
        script_body = dict(script_body)

        if "hook" in script_body:
            script_body["hook"] = clean_narrator_prefix(str(script_body["hook"]))
        if "payoff" in script_body:
            script_body["payoff"] = clean_narrator_prefix(str(script_body["payoff"]))

        if isinstance(cleaned.get("script"), dict):
            cleaned["script"] = script_body
            return cleaned
        return script_body

