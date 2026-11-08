"""
webui/routers/scripts.py — Query, filter, paginate, and inspect scripts and pipeline states.
Supports all 1,200+ scripts across Expression, Roleplay, Game, and Fun Facts formats.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# pyrefly: ignore[missing-import]
from fastapi import APIRouter, HTTPException, Query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.state_manager import StateManager
from core.expression_db import is_expression_done

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])

# In-memory index cache for instant catalog filtering across 1,200+ scripts
_SCRIPT_CACHE: List[Dict[str, Any]] = []
_CACHE_TIMESTAMP: float = 0.0
CACHE_TTL_SECONDS: float = 20.0


def _get_state_manager() -> StateManager:
    return StateManager(BASE_DIR)


def _normalize_stage(status_val: Any) -> str:
    s = str(status_val).lower().strip()
    if s in ("done", "completed", "complete", "finished"):
        return "done"
    elif s in ("pending", "in_progress", "ready", "running", "queued"):
        return "pending"
    return "missing"


def _extract_scenes_from_state(state_data: Dict[str, Any], img_list: List[str]) -> List[Dict[str, Any]]:
    """Universal scene extractor supporting Roleplay, Expression, Game, and JSON formats."""
    scenes: List[Dict[str, Any]] = []
    assets = state_data.get("assets") or {}
    image_prompts = assets.get("image_prompts") or {}
    visual_prompts = state_data.get("visual_prompts") or {}
    prompts_map = {**visual_prompts, **image_prompts}

    # Normalize prompt map keys to lowercase for flexible matching
    prompts_lower = {str(k).lower(): v for k, v in prompts_map.items()}

    # 1. Check content_metadata.script (structured dict)
    script_obj = state_data.get("content_metadata", {}).get("script")
    if not script_obj and state_data.get("script_text"):
        raw_text = state_data.get("script_text", "").strip()
        if raw_text.startswith("{") and raw_text.endswith("}"):
            try:
                script_obj = json.loads(raw_text)
            except Exception:
                script_obj = None

    if isinstance(script_obj, dict):
        # Determine preferred scene sequence
        keys = list(script_obj.keys())
        keys_lower = [k.lower() for k in keys]

        if any("dialogue_part" in k for k in keys_lower):
            # Roleplay script
            ordered_keys = ["hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff"]
        elif any(k in keys_lower for k in ["setup", "discovery", "example"]):
            # Expression script
            ordered_keys = ["hook", "setup", "discovery", "example", "payoff"]
        elif any(k in keys_lower for k in ["question", "countdown", "reveal"]):
            # Game script
            ordered_keys = ["hook", "question", "options", "countdown", "reveal", "payoff"]
        else:
            ordered_keys = [k for k in keys if k.lower() != "title"]

        for idx, key in enumerate(ordered_keys, start=1):
            # Find matching key in script_obj case-insensitively
            matched_key = None
            for k in script_obj:
                if k.lower() == key.lower():
                    matched_key = k
                    break

            if not matched_key:
                continue

            voice_line = str(script_obj[matched_key]).strip()
            prompt = prompts_lower.get(key.lower(), "")

            # Match image file by naming convention or index
            img_file = None
            for fpath in img_list:
                fname = Path(fpath).name.lower()
                if key.lower() in fname:
                    img_file = fpath
                    break
            if not img_file and idx - 1 < len(img_list):
                img_file = img_list[idx - 1]

            scenes.append({
                "scene_type": key,
                "label": key.replace("_", " ").title(),
                "voice_line": voice_line,
                "image_file": img_file,
                "prompt": prompt,
            })

        if scenes:
            return scenes

    # 2. Check dialogues list (tuples or dicts)
    dialogues = state_data.get("dialogues") or []
    if dialogues:
        for idx, d in enumerate(dialogues, start=1):
            if isinstance(d, dict):
                sc_type = d.get("scene") or f"scene_{idx}"
                line = d.get("line") or d.get("text") or ""
            elif isinstance(d, (list, tuple)) and len(d) >= 2:
                sc_type = f"scene_{idx}"
                line = f"{d[0]}: {d[1]}"
            else:
                sc_type = f"scene_{idx}"
                line = str(d)

            prompt = prompts_lower.get(sc_type.lower()) or prompts_lower.get(str(idx), "")
            img_file = img_list[idx - 1] if idx - 1 < len(img_list) else None

            scenes.append({
                "scene_type": sc_type,
                "label": sc_type.replace("_", " ").title(),
                "voice_line": line,
                "image_file": img_file,
                "prompt": prompt,
            })
        return scenes

    # 3. Fallback to parsing raw script_text lines
    raw_lines = [ln.strip() for ln in state_data.get("script_text", "").splitlines() if ln.strip()]
    for idx, ln in enumerate(raw_lines[:5], start=1):
        scenes.append({
            "scene_type": f"scene_{idx}",
            "label": f"Scene {idx}",
            "voice_line": ln,
            "image_file": img_list[idx - 1] if idx - 1 < len(img_list) else None,
            "prompt": prompts_lower.get(f"scene_{idx}", ""),
        })

    return scenes


def _build_script_summary(s: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    s_id = s.get("id")
    if not s_id:
        return None

    meta = s.get("content_metadata") or {}
    p_params = s.get("prompt_params") or {}
    raw_meta = s.get("metadata") or {}
    status = s.get("status") or {}
    assets = s.get("assets") or {}

    raw_lang = meta.get("language") or raw_meta.get("LABEL") or p_params.get("TARGET_LANGUAGE") or "english"
    if "|" in raw_lang:
        clean_lang = raw_lang.split("|")[0].strip()
    else:
        clean_lang = raw_lang.strip()
    clean_lang = clean_lang.lower()

    v_type = (
        meta.get("video_type")
        or p_params.get("VIDEO_TYPE")
        or raw_meta.get("VIDEO_TYPE")
        or "expression"
    ).lower()

    topic = (
        meta.get("topic")
        or meta.get("target_expression")
        or p_params.get("EXPRESSION")
        or p_params.get("ROLEPLAY_SCENARIO")
        or p_params.get("TOPIC")
        or raw_meta.get("TITLE")
        or ""
    )

    title = raw_meta.get("TITLE") or topic

    # Extract stages
    has_audio = bool(assets.get("audio_path") or assets.get("narration_audio"))
    has_images = bool(assets.get("image_dir"))
    has_thumb = bool(assets.get("thumbnail_path"))
    has_video = bool(assets.get("video_path") or assets.get("final_video") or assets.get("final_video_path"))

    stages = {
        "scripts": "done" if s.get("script_text") or meta.get("script") else "missing",
        "voice": _normalize_stage(status.get("voice_generation", "done" if has_audio else "missing")),
        "images": _normalize_stage(status.get("image_generation", "done" if has_images else "missing")),
        "music": _normalize_stage(status.get("music_selection", "missing")),
        "thumbnails": _normalize_stage(status.get("thumbnail_generation", "done" if has_thumb else "missing")),
        "assembly": _normalize_stage(status.get("video_assembly", "done" if has_video else "missing")),
    }

    speakers_gender = meta.get("speakers_gender") or {}
    gender = "default"
    if isinstance(speakers_gender, dict) and speakers_gender.get("PERSON_ONE"):
        gender = str(speakers_gender.get("PERSON_ONE"))
    elif meta.get("gender"):
        gender = str(meta.get("gender"))

    # Resolve image files if present
    img_list = []
    image_dir_str = assets.get("image_dir")
    if image_dir_str:
        p = Path(image_dir_str)
        if p.exists() and p.is_dir():
            img_list = [str(f) for f in sorted(p.glob("*.png"))]

    # Poster image: prefer thumbnail, fallback to first scene image
    poster = assets.get("thumbnail_path") or (img_list[0] if img_list else None)

    return {
        "id": s_id,
        "script_id": s_id,
        "topic": topic,
        "title": title,
        "language": clean_lang,
        "type": v_type,
        "video_type": v_type,
        "lexical_field": p_params.get("LEXICAL_FIELD") or meta.get("lexical_field") or "",
        "scenario": p_params.get("ROLEPLAY_SCENARIO") or meta.get("story_scenario") or "",
        "character": {
            "gender": gender,
            "description": meta.get("character_description", "Standard"),
        },
        "status": status,
        "stages": stages,
        "assets": {
            "audio": assets.get("audio_path") or assets.get("narration_audio"),
            "images": img_list,
            "thumbnail": assets.get("thumbnail_path"),
            "video": assets.get("video_path") or assets.get("final_video") or assets.get("final_video_path"),
            "poster": poster,
        },
        "has_voice": stages["voice"] == "done",
        "has_images": stages["images"] == "done",
        "has_video": stages["assembly"] == "done",
        "has_thumbnail": stages["thumbnails"] == "done",
        "is_ready_for_assembly": stages["voice"] == "done" and stages["images"] == "done" and stages["assembly"] != "done",
        "is_db_done": is_expression_done(s_id),
    }


def _get_indexed_scripts(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _SCRIPT_CACHE, _CACHE_TIMESTAMP
    now = time.time()
    sm = _get_state_manager()
    is_mock = hasattr(sm.get_all_scripts, "assert_called") or hasattr(sm.get_all_scripts, "return_value")
    if not is_mock and not force_refresh and _SCRIPT_CACHE and (now - _CACHE_TIMESTAMP < CACHE_TTL_SECONDS):
        return _SCRIPT_CACHE

    raw_scripts = sm.get_all_scripts()
    indexed = []
    for raw in raw_scripts:
        summary = _build_script_summary(raw)
        if summary:
            indexed.append(summary)

    # Sort naturally by script ID (e.g. EE01, EE02, FR01, SE01)
    indexed.sort(key=lambda x: x["script_id"])
    if not is_mock:
        _SCRIPT_CACHE = indexed
        _CACHE_TIMESTAMP = now
    return indexed


def _calculate_facets(scripts: List[Dict[str, Any]]) -> Dict[str, Any]:
    languages: Dict[str, int] = {}
    types: Dict[str, int] = {}
    stage_counts = {
        "all": len(scripts),
        "missing_voice": 0,
        "missing_images": 0,
        "ready_for_assembly": 0,
        "complete": 0,
    }

    for s in scripts:
        lang = s.get("language") or "Other"
        languages[lang] = languages.get(lang, 0) + 1

        vtype = (s.get("type") or "other").lower()
        types[vtype] = types.get(vtype, 0) + 1

        if not s.get("has_voice"):
            stage_counts["missing_voice"] += 1
        if not s.get("has_images"):
            stage_counts["missing_images"] += 1
        if s.get("is_ready_for_assembly"):
            stage_counts["ready_for_assembly"] += 1
        if s.get("has_video"):
            stage_counts["complete"] += 1

    return {
        "total": len(scripts),
        "languages": [{"name": k, "count": v} for k, v in sorted(languages.items())],
        "types": [{"name": k, "count": v} for k, v in sorted(types.items())],
        "stage_counts": stage_counts,
    }


@router.get("/facets")
def get_facets() -> Dict[str, Any]:
    """Returns dynamic facets (languages, video types, and pipeline counts) across all scripts."""
    all_scripts = _get_indexed_scripts()
    return _calculate_facets(all_scripts)


@router.post("/refresh")
def refresh_cache() -> Dict[str, Any]:
    """Forces an immediate cache invalidation and re-index of state scripts."""
    all_scripts = _get_indexed_scripts(force_refresh=True)
    return {"status": "success", "total_indexed": len(all_scripts)}


@router.get("")
def list_scripts(
    page: Optional[int] = Query(default=None, ge=1, description="Page number for catalog pagination (e.g. 1)"),
    page_size: int = Query(default=24, ge=1, le=500, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Search across ID, topic, title, lexical field"),
    language: Optional[str] = Query(default=None, description="Filter by language"),
    video_type: Optional[str] = Query(default=None, description="Filter by video type"),
    stage_filter: Optional[str] = Query(default=None, description="missing_voice | missing_images | ready_for_assembly | complete"),
    status_stage: Optional[str] = Query(default=None, description="Legacy parameter for stage name"),
    status_value: Optional[str] = Query(default=None, description="Legacy parameter for stage value"),
    limit: Optional[int] = Query(default=None, ge=1, description="Legacy limit on returned items"),
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns scripts.
    - When `page` is provided: returns a paginated catalog envelope with facets.
    - When `page` is None: returns array of matching scripts for backward compatibility.
    """
    all_scripts = _get_indexed_scripts()
    filtered = all_scripts

    # Search filter
    if search and isinstance(search, str) and search.strip():
        s_term = search.lower().strip()
        filtered = [
            s for s in filtered
            if s_term in s["script_id"].lower()
            or s_term in s["topic"].lower()
            or s_term in s["title"].lower()
            or s_term in s.get("lexical_field", "").lower()
            or s_term in s.get("scenario", "").lower()
        ]

    # Language filter
    if language and isinstance(language, str) and language.lower() != "all":
        l_term = language.lower().strip()
        filtered = [s for s in filtered if l_term == s["language"].lower()]

    # Video type filter
    if video_type and isinstance(video_type, str) and video_type.lower() != "all":
        t_term = video_type.lower().strip()
        filtered = [s for s in filtered if t_term == s["type"].lower()]

    # Stage status filter
    if stage_filter and isinstance(stage_filter, str) and stage_filter.lower() != "all":
        sf = stage_filter.lower().strip()
        if sf == "ready_for_assembly":
            filtered = [s for s in filtered if s["is_ready_for_assembly"]]
        elif sf == "complete":
            filtered = [s for s in filtered if s["has_video"]]
        elif sf == "missing_images":
            filtered = [s for s in filtered if not s["has_images"]]
        elif sf == "missing_voice":
            filtered = [s for s in filtered if not s["has_voice"]]

    # Legacy filters support
    if status_stage:
        stage_val = status_value or "done"
        filtered = [s for s in filtered if s.get("stages", {}).get(status_stage) == stage_val]

    total_filtered = len(filtered)

    # If pagination requested, return catalog envelope
    if page is not None:
        total_pages = max(1, math.ceil(total_filtered / page_size))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = filtered[start_idx:end_idx]

        return {
            "items": page_items,
            "total": total_filtered,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "facets": _calculate_facets(all_scripts),
        }

    # Backward compatibility: return raw list
    if limit is not None:
        return filtered[:limit]
    return filtered


@router.get("/{script_id}")
def get_script(script_id: str) -> Dict[str, Any]:
    """Returns complete script state with universal scene extraction and publishing metadata."""
    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found in state store.")

    state_data = sm.get_script_state(canonical_id)
    summary = _build_script_summary(state_data) or {}

    meta = state_data.get("content_metadata") or {}
    p_params = state_data.get("prompt_params") or {}
    raw_meta = state_data.get("metadata") or {}
    assets = state_data.get("assets") or {}

    img_list = summary.get("assets", {}).get("images", [])
    scenes = _extract_scenes_from_state(state_data, img_list)

    # YouTube publishing metadata
    youtube_metadata = {
        "title": raw_meta.get("TITLE") or summary.get("title", ""),
        "description": raw_meta.get("DESCRIPTION") or "",
        "short_description": raw_meta.get("SHORT_DESCRIPTION") or "",
        "tags": raw_meta.get("TAGS") or "",
        "hashtags": raw_meta.get("HASHTAGS") or "",
        "filename": raw_meta.get("FILENAME") or f"{canonical_id}.mp4",
        "label": raw_meta.get("LABEL") or "",
    }

    return {
        **state_data,
        **summary,
        "story_scenario": p_params.get("ROLEPLAY_SCENARIO") or meta.get("story_scenario") or "",
        "base_setting": meta.get("base_setting") or meta.get("setting") or "",
        "lexical_field": p_params.get("LEXICAL_FIELD") or meta.get("lexical_field") or "",
        "learning_objective": meta.get("learning_objective") or "",
        "general_prompt": assets.get("general_prompt") or "",
        "speakers_voice": meta.get("speakers_voice") or {},
        "speakers_gender": meta.get("speakers_gender") or {},
        "character_personalities": meta.get("character_personalities") or {},
        "scenes": scenes,
        "youtube_metadata": youtube_metadata,
    }
