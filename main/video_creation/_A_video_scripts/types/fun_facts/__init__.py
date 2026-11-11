"""Domain module for FUN FACTS scripts."""

from __future__ import annotations

from .engine import FunFactsEngine
from .prompts import build_fun_facts_prompt
from .rules import FUN_FACTS_RULES
from .validator import validate_fun_facts_script

__all__ = ["FunFactsEngine", "build_fun_facts_prompt", "FUN_FACTS_RULES", "validate_fun_facts_script"]

