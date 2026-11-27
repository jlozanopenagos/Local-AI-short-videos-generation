"""
api.py — Programmatic interface to _A_video_scripts for the WebUI and automated workflows.
Decouples script generation from the terminal CLI and coordinates domain engines.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .common.base_engine import BaseScriptEngine, ScriptGenerationResult
from .registry import ScriptEngineRegistry

logger = logging.getLogger("scripts_api")


def get_engine_for_script(script_id_or_type: str) -> Optional[BaseScriptEngine]:
    """Resolves the appropriate domain engine for a script ID or format name."""
    return ScriptEngineRegistry.get_engine(script_id_or_type)


def generate_script_for_payload(
    input_data: Dict[str, Any],
    on_token: Optional[Callable[[str], None]] = None,
    max_retries: int = 2,
) -> ScriptGenerationResult:
    """
    Executes script generation for an input payload using its dedicated domain engine.
    """
    script_id = input_data.get("SCRIPT_ID") or input_data.get("script_id") or ""
    video_type = input_data.get("TYPE") or input_data.get("type") or ""

    engine = None
    if script_id:
        engine = ScriptEngineRegistry.get_engine(script_id)
    if not engine and video_type:
        engine = ScriptEngineRegistry.get_engine(video_type)

    if not engine:
        raise ValueError(
            f"No registered script engine found for script_id='{script_id}', type='{video_type}'. "
            f"Supported types: {ScriptEngineRegistry.list_supported_types()}"
        )

    logger.info(f"Generating script '{script_id}' using engine '{engine.script_type}'")
    return engine.generate(input_data, on_token=on_token, max_retries=max_retries)

