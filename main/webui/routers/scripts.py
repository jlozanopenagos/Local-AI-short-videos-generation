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

        # Parse stages
        stages = {
            "scripts": "done" if s.get("script_text") else "missing",
            "voice": status.get("voice_generation", "done" if assets.get("audio_path") else "missing"),
            "images": status.get("image_generation", "done" if assets.get("image_dir") else "missing"),
            "music": status.get("music_selection", "missing"),
            "thumbnails": status.get("thumbnail_generation", "done" if assets.get("thumbnail_path") else "missing"),
            "assembly": status.get("video_assembly", "done" if (assets.get("video_path") or assets.get("final_video_path")) else "missing"),
        }
        for k, v in stages.items():
            if str(v).lower() in ("done", "completed"):
                stages[k] = "done"
            elif str(v).lower() in ("pending", "in_progress", "ready", "running"):
                stages[k] = "pending"
            else:
                stages[k] = "missing"

        # Character info
        speakers_gender = meta.get("speakers_gender") or {}
        gender = "default"
        if isinstance(speakers_gender, dict) and speakers_gender.get("PERSON_ONE"):
            gender = str(speakers_gender.get("PERSON_ONE"))
        elif meta.get("gender"):
            gender = str(meta.get("gender"))

        results.append({
            "id": s_id,
            "script_id": s_id,
            "language": s_lang.split("|")[0].strip() if "|" in s_lang else s_lang,
            "type": s_type,
            "video_type": s_type,
            "topic": topic,
            "status": status,
            "stages": stages,
            "character": {
                "gender": gender,
                "description": meta.get("character_description", "Standard"),
            },
            "assets": {
                "audio": assets.get("audio_path") or assets.get("narration_audio"),
                "images": [],
                "thumbnail": assets.get("thumbnail_path"),
                "video": assets.get("video_path") or assets.get("final_video_path"),
            },
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
    meta = state_data.get("content_metadata") or {}
    p_params = state_data.get("prompt_params") or {}
    raw_meta = state_data.get("metadata") or {}
    status = state_data.get("status") or {}
    assets = state_data.get("assets") or {}

    s_lang = (meta.get("language") or raw_meta.get("LABEL") or "").lower()
    s_type = (meta.get("video_type") or p_params.get("VIDEO_TYPE") or raw_meta.get("VIDEO_TYPE") or "").lower()
    topic = (
        meta.get("topic")
        or meta.get("target_expression")
        or p_params.get("EXPRESSION")
        or p_params.get("ROLEPLAY_SCENARIO")
        or p_params.get("TOPIC")
        or ""
    )

    stages = {
        "scripts": "done" if state_data.get("script_text") else "missing",
        "voice": status.get("voice_generation", "done" if assets.get("audio_path") else "missing"),
        "images": status.get("image_generation", "done" if assets.get("image_dir") else "missing"),
        "music": status.get("music_selection", "missing"),
        "thumbnails": status.get("thumbnail_generation", "done" if assets.get("thumbnail_path") else "missing"),
        "assembly": status.get("video_assembly", "done" if (assets.get("video_path") or assets.get("final_video_path")) else "missing"),
    }
    for k, v in stages.items():
        if str(v).lower() in ("done", "completed"):
            stages[k] = "done"
        elif str(v).lower() in ("pending", "in_progress", "ready", "running"):
            stages[k] = "pending"
        else:
            stages[k] = "missing"

    # Resolve image files
    img_list = []
    image_dir_str = assets.get("image_dir")
    if image_dir_str:
        p = Path(image_dir_str)
        if p.exists() and p.is_dir():
            img_list = [str(f) for f in sorted(p.glob("*.png"))]

    # Resolve scenes
    scenes = []
    dialogues = state_data.get("dialogues") or []
    visual_prompts = state_data.get("visual_prompts") or {}
    if dialogues:
        for idx, d in enumerate(dialogues):
            sc_type = d.get("scene") or f"scene_{idx + 1}"
            scenes.append({
                "scene_type": sc_type,
                "voice_line": d.get("line") or d.get("text") or "",
                "image_file": img_list[idx] if idx < len(img_list) else None,
                "prompt": visual_prompts.get(sc_type) or visual_prompts.get(str(idx + 1)) or "",
            })
    elif state_data.get("script_text"):
        lines = [ln.strip() for ln in state_data.get("script_text", "").splitlines() if ln.strip()]
        for idx, ln in enumerate(lines[:5]):
            scenes.append({
                "scene_type": f"scene_{idx + 1}",
                "voice_line": ln,
                "image_file": img_list[idx] if idx < len(img_list) else None,
                "prompt": "",
            })

    speakers_gender = meta.get("speakers_gender") or {}
    gender = "default"
    if isinstance(speakers_gender, dict) and speakers_gender.get("PERSON_ONE"):
        gender = str(speakers_gender.get("PERSON_ONE"))
    elif meta.get("gender"):
        gender = str(meta.get("gender"))

    # Return merged state
    return {
        **state_data,
        "id": canonical_id,
        "script_id": canonical_id,
        "topic": topic,
        "language": s_lang.split("|")[0].strip() if "|" in s_lang else s_lang,
        "type": s_type,
        "video_type": s_type,
        "story_scenario": meta.get("story_scenario") or p_params.get("ROLEPLAY_SCENARIO") or "",
        "base_setting": meta.get("base_setting") or meta.get("setting") or "",
        "lexical_field": meta.get("lexical_field") or "",
        "character": {
            "gender": gender,
            "description": meta.get("character_description", "Standard"),
        },
        "stages": stages,
        "assets": {
            "audio": assets.get("audio_path") or assets.get("narration_audio"),
            "images": img_list,
            "thumbnail": assets.get("thumbnail_path"),
            "video": assets.get("video_path") or assets.get("final_video_path"),
        },
        "scenes": scenes,
    }

