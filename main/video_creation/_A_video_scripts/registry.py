"""
registry.py — Central engine registry and dispatch factory for script formats.
Maps script type names ('game', 'roleplay', 'expression', 'fun_facts') and type codes
('G', 'R', 'E', 'F') or canonical IDs (e.g. 'SG01', 'ER05') to their dedicated domain engines.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Type

from .common.base_engine import BaseScriptEngine

logger = logging.getLogger("script_registry")


class ScriptEngineRegistry:
    """Thread-safe catalog of domain script engines."""

    _engines_by_type: Dict[str, BaseScriptEngine] = {}
    _engines_by_code: Dict[str, BaseScriptEngine] = {}

    @classmethod
    def register(cls, engine_cls: Type[BaseScriptEngine]) -> Type[BaseScriptEngine]:
        """Registers an engine class under its canonical script_type and all its type_codes."""
        instance = engine_cls()
        canon_type = instance.script_type.lower().strip()
        cls._engines_by_type[canon_type] = instance

        for code in instance.type_codes:
            clean_code = code.upper().strip()
            cls._engines_by_code[clean_code] = instance

        logger.debug(
            f"Registered script engine '{canon_type}' for codes: {instance.type_codes}"
        )
        return engine_cls

    @classmethod
    def _load_builtins(cls) -> None:
        """Lazily imports and explicitly registers built-in domain engines."""
        try:
            from .types.game.engine import GameEngine
            cls.register(GameEngine)
        except Exception as e:
            logger.debug(f"Could not load GameEngine: {e}")
        try:
            from .types.roleplay.engine import RoleplayEngine
            cls.register(RoleplayEngine)
        except Exception as e:
            logger.debug(f"Could not load RoleplayEngine: {e}")
        try:
            from .types.expression.engine import ExpressionEngine
            cls.register(ExpressionEngine)
        except Exception as e:
            logger.debug(f"Could not load ExpressionEngine: {e}")
        try:
            from .types.fun_facts.engine import FunFactsEngine
            cls.register(FunFactsEngine)
        except Exception as e:
            logger.debug(f"Could not load FunFactsEngine: {e}")

    @classmethod
    def get_engine(cls, identifier: str) -> Optional[BaseScriptEngine]:
        """
        Resolves a domain engine from:
        1. Exact type name (e.g. 'game', 'roleplay', 'expression', 'fun_facts')
        2. Single-letter type code (e.g. 'G', 'R', 'E', 'F')
        3. Canonical Script ID (e.g. 'SG01' -> 'G' -> GameEngine, 'ER05' -> 'R' -> RoleplayEngine)
        """
        if not identifier:
            return None

        if not cls._engines_by_type:
            cls._load_builtins()

        clean = str(identifier).strip()

        # 1. Check exact type name
        lower = clean.lower()
        if lower in cls._engines_by_type:
            return cls._engines_by_type[lower]

        # Normalize common aliases
        if lower in ("funfacts", "fun_fact", "facts"):
            return cls._engines_by_type.get("fun_facts")

        # 2. Check 1-letter code directly
        upper = clean.upper()
        if upper in cls._engines_by_code:
            return cls._engines_by_code[upper]

        # 3. Check canonical Script ID (e.g. SG01, ER05, FE12, S_F01)
        # Matches <Lang:1-letter><Type:1-letter><Index:2-digits>
        m = re.match(r"^[A-Z]([A-Z])\d{2,}$", upper)
        if m:
            code = m.group(1)
            if code in cls._engines_by_code:
                return cls._engines_by_code[code]

        # Fallback check for underscore format e.g. S_F01
        m_under = re.match(r"^[A-Z]_([A-Z])\d{2,}$", upper)
        if m_under:
            code = m_under.group(1)
            if code in cls._engines_by_code:
                return cls._engines_by_code[code]

        return None

    @classmethod
    def list_supported_types(cls) -> List[str]:
        """Returns sorted list of registered script types."""
        return sorted(cls._engines_by_type.keys())

    @classmethod
    def clear(cls) -> None:
        """Clears all registered engines (useful for tests)."""
        cls._engines_by_type.clear()
        cls._engines_by_code.clear()


def register_script_engine(cls: Type[BaseScriptEngine]) -> Type[BaseScriptEngine]:
    """Decorator to register a BaseScriptEngine subclass in the central registry."""
    return ScriptEngineRegistry.register(cls)

