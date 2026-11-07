"""
webui/routers/scripts.py — Query and inspect scripts and pipeline state.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.state_manager import StateManager
from core.expression_db import is_expression_done

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])


def _get_state_manager() -> StateManager:
    return StateManager(BASE_DIR)


@router.get("")
def list_scripts(
    language: Optional[str] = Query(default=None, description="Filter by language (e.g. english, french, spanish, italian)"),
    video_type: Optional[str] = Query(default=None, description="Filter by video type (e.g. expression, game, roleplay, fun_facts)"),
    status_stage: Optional[str] = Query(default=None, description="Stage name to check (e.g. voice_generation, image_generation)"),
    status_value: Optional[str] = Query(default=None, description="Expected stage status (e.g. pending, done)"),
    limit: int = Query(default=200, ge=1, le=2000),
) -> List[Dict[str, Any]]:
    """Returns a list of scripts with summary metadata and pipeline statuses."""
    sm = _get_state_manager()
    all_scripts = sm.get_all_scripts()
    results = []

    for s in all_scripts:
        s_id = s.get("id")
        if not s_id:
            continue

        meta = s.get("content_metadata") or {}
        p_params = s.get("prompt_params") or {}
        raw_meta = s.get("metadata") or {}

        s_lang = (meta.get("language") or raw_meta.get("LABEL") or "").lower()
        if language and language.lower() not in s_lang:
            continue

        s_type = (meta.get("video_type") or p_params.get("VIDEO_TYPE") or raw_meta.get("VIDEO_TYPE") or "").lower()
        if video_type and video_type.lower() != s_type:
            continue

        status = s.get("status") or {}
        if status_stage:
            stage_val = status.get(status_stage, "pending")
            if status_value and stage_val != status_value:
                continue

        topic = (
            meta.get("topic")
            or meta.get("target_expression")
            or p_params.get("EXPRESSION")
            or p_params.get("ROLEPLAY_SCENARIO")
            or p_params.get("TOPIC")
            or ""
        )

        assets = s.get("assets") or {}

        results.append({
            "id": s_id,
            "language": s_lang.split("|")[0].strip() if "|" in s_lang else s_lang,
            "video_type": s_type,
            "topic": topic,
            "status": status,
            "has_voice": bool(assets.get("audio_path") or assets.get("narration_audio")),
            "has_images": bool(assets.get("image_dir")),
            "has_video": bool(assets.get("video_path") or assets.get("final_video_path")),
            "has_thumbnail": bool(assets.get("thumbnail_path")),
            "is_db_done": is_expression_done(s_id),
        })

        if len(results) >= limit:
            break

    return results


@router.get("/{script_id}")
def get_script(script_id: str) -> Dict[str, Any]:
    """Returns full script state, dialogues, prompts, and asset metadata."""
    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found in state store.")

    state_data = sm.get_script_state(canonical_id)
    return state_data
