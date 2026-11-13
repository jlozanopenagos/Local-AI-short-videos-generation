"""
types/game/engine.py — Dedicated domain engine for LINGUISTIC GAME scripts.
Preserves multiline chalkboard visual formatting while producing clean audio for TTS.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from ...common.base_engine import BaseScriptEngine, ValidationResult
from ...common.text_utils import clean_narrator_prefix
from ...registry import register_script_engine
from .prompts import build_game_prompt
from .validator import validate_game_script


@register_script_engine
class GameEngine(BaseScriptEngine):
    """Domain engine for linguistic game scripts."""

    script_type: str = "game"
    type_codes: list[str] = ["G"]

    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        return build_game_prompt(input_data)

    def validate(
        self,
        script_dict: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        return validate_game_script(script_dict, input_data)

    def sanitize(
        self,
        script_dict: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Cleans and normalizes game script components:
        1. Strips 'Narrator:' prefixes from hook and answer.
        2. Neutralizes leaked blanks ('___') in the spoken challenge audio.
        3. Enforces clean 'A: ...  B: ...' format on the spoken challenge.
        4. PRESERVES the multiline visual 'chalkboard_exercise' with '___' and 'A) / B)'
           without overwriting it with the spoken challenge audio line!
        """
        cleaned = dict(script_dict)

        # Handle nested script dict or root dict
        script_body = cleaned.get("script") if isinstance(cleaned.get("script"), dict) else cleaned
        script_body = dict(script_body)

        # 1. Clean narrator prefixes
        if "hook" in script_body:
            script_body["hook"] = clean_narrator_prefix(str(script_body["hook"]))
        if "answer" in script_body:
            script_body["answer"] = clean_narrator_prefix(str(script_body["answer"]))

        # 2. Extract and preserve visual chalkboard exercise
        raw_board = cleaned.get("chalkboard_exercise") or script_body.get("chalkboard_exercise", "")
        board_str = str(raw_board).strip()

        # Extract options from board for challenge synthesis if needed
        board_lines = [l.strip() for l in board_str.splitlines() if l.strip()]
        detected_opts: Dict[str, str] = {}
        for l in board_lines:
            m = re.match(r"^([A-D])\s*[:\)\.\-]\s*(.+)$", l, re.IGNORECASE)
            if m:
                detected_opts[m.group(1).upper()] = m.group(2).strip()

        opt_a = detected_opts.get("A")
        opt_b = detected_opts.get("B")

        # 3. Sanitize spoken challenge audio string
        chal = str(script_body.get("challenge", "")).strip()
        if chal:
            # Strip prompt parentheticals like (noun vs verb)
            chal = re.sub(r"\s*\(.*=.*(?:vs|ou|o|-).*\)", "", chal)
            chal = re.sub(r"\s*\((?:noun|verb|sens):[^\)]*\)", "", chal, flags=re.IGNORECASE)

            # Strip pressure leaks
            for pat in [
                r"\s*(?:Which one is it\?.*)$",
                r"\s*(?:Your answer is coming!.*)$",
                r"\s*(?:Tic-tac\b.*)$",
                r"\s*(?:Trois, deux, un\b.*)$",
                r"\s*(?:Il tempo scorre\b.*)$",
                r"\s*(?:¡?El reloj no perdona\b.*)$",
            ]:
                chal = re.sub(pat, "", chal, flags=re.IGNORECASE).strip()

            # Replace any leaked ___ in spoken challenge with option A
            if re.search(r"_{2,}", chal) and opt_a:
                chal = re.sub(r"\s*_{2,}\s*", f" {opt_a} ", chal)
                chal = re.sub(r"\s+", " ", chal).strip()

            # Ensure options are properly voiced
            has_opts = bool(re.search(r"\bA\s*[:\)\.\-]", chal, re.IGNORECASE) and re.search(r"\bB\s*[:\)\.\-]", chal, re.IGNORECASE))
            if not has_opts and len(detected_opts) >= 2:
                voiced_parts = []
                for letter in ["A", "B", "C", "D"]:
                    if letter in detected_opts:
                        clean_text = detected_opts[letter].rstrip(".?! ") + "."
                        voiced_parts.append(f"{letter}: {clean_text}")
                chal = chal.rstrip(":., ") + ". " + "  ".join(voiced_parts)

            script_body["challenge"] = chal

        # 4. Critical fix: Ensure chalkboard_exercise remains the visual board!
        if isinstance(cleaned.get("script"), dict):
            cleaned["script"] = script_body
            if board_str:
                cleaned["chalkboard_exercise"] = board_str
            if "game_archetype" in cleaned:
                cleaned["script"]["game_archetype"] = cleaned["game_archetype"]
        else:
            cleaned = script_body
            if board_str:
                cleaned["chalkboard_exercise"] = board_str

        return cleaned

