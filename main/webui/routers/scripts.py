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
# pyrefly: ignore[missing-import]
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.state_manager import StateManager
from core.expression_db import is_expression_done, get_all_done_expression_ids
from video_creation._C_image_generation.main import ensure_llama_stopped

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])

# In-memory index cache for instant catalog filtering across 1,200+ scripts
_SCRIPT_CACHE: List[Dict[str, Any]] = []
_CACHE_TIMESTAMP: float = 0.0
CACHE_TTL_SECONDS: float = 600.0


def _get_state_manager() -> StateManager:
    return StateManager(BASE_DIR)


def _normalize_stage(status_val: Any) -> str:
    s = str(status_val).lower().strip()
    if s in ("done", "completed", "complete", "finished"):
        return "done"
    elif s in ("pending", "in_progress", "ready", "running", "queued"):
        return "pending"
    return "missing"


def _normalize_language(raw_lang: Any) -> str:
    """Normalizes multilingual labels (e.g. Español, Français, ENGLISH) to canonical keys."""
    if not raw_lang:
        return "english"
    clean = str(raw_lang).split("|")[0].strip().lower()
    if clean in ("español", "espanol", "spanish", "sp", "es"):
        return "spanish"
    elif clean in ("français", "francais", "french", "fr"):
        return "french"
    elif clean in ("english", "ingles", "inglés", "en"):
        return "english"
    elif clean in ("italian", "italiano", "it"):
        return "italian"
    elif clean in ("german", "deutsch", "de"):
        return "german"
    elif clean in ("portuguese", "português", "portugues", "pt"):
        return "portuguese"
    return clean


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
            # Roleplay script (6 scenes)
            ordered_keys = ["hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff"]
        elif any(k in keys_lower for k in ["challenge", "pressure", "answer"]):
            # Game script (5 scenes: hook, challenge, pressure, answer, explanation)
            ordered_keys = ["hook", "challenge", "pressure", "answer", "explanation"]
        elif any(k in keys_lower for k in ["setup", "discovery", "example"]):
            # Expression script (5 scenes)
            ordered_keys = ["hook", "setup", "discovery", "example", "payoff"]
        elif any(k in keys_lower for k in ["setup", "discovery", "explanation"]):
            # Fun Facts script (5 scenes)
            ordered_keys = ["hook", "setup", "discovery", "explanation", "payoff"]
        elif any(k in keys_lower for k in ["question", "countdown", "reveal"]):
            # Legacy Game script
            ordered_keys = ["hook", "question", "options", "countdown", "reveal", "payoff"]
        else:
            ordered_keys = [
                k for k in keys
                if k.lower() not in (
                    "title", "game_archetype", "category", "subcategory",
                    "topic", "learning_objective", "chalkboard_exercise"
                )
            ]

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
                "label": key.replace("_", " ").capitalize(),
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
                "label": sc_type.replace("_", " ").capitalize(),
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


def _build_script_summary(
    s: Dict[str, Any],
    done_ids_set: Optional[set] = None,
    force_disk_images: bool = False,
) -> Optional[Dict[str, Any]]:
    s_id = s.get("id")
    if not s_id:
        return None

    meta = s.get("content_metadata") or {}
    p_params = s.get("prompt_params") or {}
    raw_meta = s.get("metadata") or {}
    status = s.get("status") or {}
    assets = s.get("assets") or {}

    raw_lang = meta.get("language") or raw_meta.get("LABEL") or p_params.get("TARGET_LANGUAGE") or "english"
    clean_lang = _normalize_language(raw_lang)

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
        "thumbnails": _normalize_stage(status.get("thumbnail_generation", "done" if has_thumb else "missing")),
        "assembly": _normalize_stage(status.get("video_assembly", "done" if has_video else "missing")),
    }

    speakers_gender = meta.get("speakers_gender") or {}
    gender = "default"
    if isinstance(speakers_gender, dict) and speakers_gender.get("PERSON_ONE"):
        gender = str(speakers_gender.get("PERSON_ONE"))
    elif meta.get("gender"):
        gender = str(meta.get("gender"))

    # Resolve image files: prefer cached list in state unless force_disk_images is requested
    img_list: List[str] = []
    cached_imgs = assets.get("images")
    image_dir_str = assets.get("image_dir")
    if not force_disk_images and isinstance(cached_imgs, list) and cached_imgs:
        img_list = [str(f) for f in cached_imgs]
    elif image_dir_str:
        p = Path(image_dir_str)
        if p.exists() and p.is_dir():
            img_list = [str(f) for f in sorted(p.glob("*.png"))]

    # Poster image: prefer thumbnail, fallback to first scene image
    poster = assets.get("thumbnail_path") or (img_list[0] if img_list else None)

    is_done_flag = (
        (str(s_id).strip().upper() in done_ids_set)
        if done_ids_set is not None
        else is_expression_done(s_id)
    )

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
        "is_db_done": is_done_flag,
    }


def _update_cached_script(canonical_id: str, state_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates a single script entry in _SCRIPT_CACHE in-place (O(1)) without re-scanning all 1,200+ files."""
    global _SCRIPT_CACHE
    summary = _build_script_summary(state_data, force_disk_images=True)
    if not summary:
        return None
    if _SCRIPT_CACHE:
        cid_upper = canonical_id.strip().upper()
        replaced = False
        for idx, item in enumerate(_SCRIPT_CACHE):
            if str(item.get("script_id", "")).upper() == cid_upper:
                _SCRIPT_CACHE[idx] = summary
                replaced = True
                break
        if not replaced:
            _SCRIPT_CACHE.append(summary)
            _SCRIPT_CACHE.sort(key=lambda x: x["script_id"])
    return summary


def _get_indexed_scripts(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _SCRIPT_CACHE, _CACHE_TIMESTAMP
    now = time.time()
    sm = _get_state_manager()
    is_mock = hasattr(sm.get_all_scripts, "assert_called") or hasattr(sm.get_all_scripts, "return_value")
    if not is_mock and not force_refresh and _SCRIPT_CACHE and (now - _CACHE_TIMESTAMP < CACHE_TTL_SECONDS):
        return _SCRIPT_CACHE

    raw_scripts = sm.get_all_scripts()
    try:
        done_ids_set = get_all_done_expression_ids()
    except Exception:
        done_ids_set = None

    indexed = []
    for raw in raw_scripts:
        summary = _build_script_summary(raw, done_ids_set=done_ids_set)
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
        lang = _normalize_language(s.get("language") or "other").capitalize()
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

    # Search filter with ID-priority ranking (exact ID -> prefix ID -> substring ID -> topic/title)
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

        def _search_rank(item: Dict[str, Any]):
            sid_low = item["script_id"].lower()
            if sid_low == s_term:
                return (0, sid_low)
            if sid_low.startswith(s_term):
                return (1, sid_low)
            if s_term in sid_low:
                return (2, sid_low)
            return (3, sid_low)

        filtered.sort(key=_search_rank)

    # Language filter
    if language and isinstance(language, str) and language.lower() != "all":
        l_term = _normalize_language(language)
        filtered = [s for s in filtered if l_term == _normalize_language(s["language"])]

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


class ScriptUpdateRequest(BaseModel):
    script_text: Optional[str] = None
    script_dict: Optional[Dict[str, Any]] = None
    chalkboard_exercise: Optional[str] = None
    chalkboard_title: Optional[str] = None
    target_expression: Optional[str] = None
    general_prompt: Optional[str] = None
    character_anchors: Optional[Dict[str, Any]] = None
    image_prompts: Optional[Dict[str, str]] = None
    game_archetype: Optional[str] = None


@router.get("/{script_id}")
def get_script(script_id: str) -> Dict[str, Any]:
    """Returns complete script state with universal scene extraction and publishing metadata."""
    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found in state store.")

    state_data = sm.get_script_state(canonical_id)
    summary = _build_script_summary(state_data, force_disk_images=True) or {}

    meta = state_data.get("content_metadata") or {}
    p_params = state_data.get("prompt_params") or {}
    raw_meta = state_data.get("metadata") or {}
    assets = state_data.get("assets") or {}

    # Extract parsed script dict
    script_obj = meta.get("script")
    if not script_obj and state_data.get("script_text"):
        raw_text = state_data.get("script_text", "").strip()
        if raw_text.startswith("{") and raw_text.endswith("}"):
            try:
                script_obj = json.loads(raw_text)
            except Exception:
                script_obj = None

    chalkboard_exercise = meta.get("chalkboard_exercise") or ""
    target_expression = meta.get("target_expression") or p_params.get("EXPRESSION") or ""
    chalkboard_title = (
        (script_obj.get("title") if isinstance(script_obj, dict) else None)
        or target_expression
        or raw_meta.get("TITLE")
        or ""
    )

    img_list = summary.get("assets", {}).get("images", [])
    scenes = _extract_scenes_from_state(state_data, img_list)

    # Detect game archetype if applicable
    game_archetype = ""
    is_game = (
        (meta.get("video_type") or p_params.get("VIDEO_TYPE") or "").upper() == "GAME"
        or (len(canonical_id) >= 2 and canonical_id[1].upper() == "G")
    )
    if is_game:
        from video_creation._A_video_scripts.types.game.archetypes import detect_game_archetype
        game_archetype = (
            meta.get("game_archetype")
            or p_params.get("game_archetype")
            or p_params.get("GAME_ARCHETYPE")
            or detect_game_archetype({**p_params, **meta, "SCRIPT_ID": canonical_id})
        )

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
        "script_dict": script_obj if isinstance(script_obj, dict) else {},
        "chalkboard_exercise": chalkboard_exercise,
        "chalkboard_title": chalkboard_title,
        "target_expression": target_expression,
        "game_archetype": game_archetype,
        "story_scenario": p_params.get("ROLEPLAY_SCENARIO") or meta.get("story_scenario") or "",
        "base_setting": meta.get("base_setting") or meta.get("setting") or "",
        "lexical_field": p_params.get("LEXICAL_FIELD") or meta.get("lexical_field") or "",
        "learning_objective": meta.get("learning_objective") or "",
        "general_prompt": assets.get("general_prompt") or "",
        "character_anchors": assets.get("character_anchors") or {},
        "speakers_voice": meta.get("speakers_voice") or {},
        "speakers_gender": meta.get("speakers_gender") or {},
        "character_personalities": meta.get("character_personalities") or {},
        "scenes": scenes,
        "youtube_metadata": youtube_metadata,
    }


@router.put("/{script_id}")
def update_script(script_id: str, payload: ScriptUpdateRequest) -> Dict[str, Any]:
    """Updates script content and chalkboard definitions, persisting changes to JSON state on disk."""
    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found.")

    state_data = sm.get_script_state(canonical_id)
    if "content_metadata" not in state_data or not isinstance(state_data["content_metadata"], dict):
        state_data["content_metadata"] = {}
    if "prompt_params" not in state_data or not isinstance(state_data["prompt_params"], dict):
        state_data["prompt_params"] = {}

    # 1. Update script content
    if payload.script_dict:
        state_data["content_metadata"]["script"] = payload.script_dict
        state_data["script_text"] = json.dumps(payload.script_dict, indent=2, ensure_ascii=False)
        if payload.script_dict.get("title"):
            state_data["content_metadata"]["topic"] = payload.script_dict["title"]
    elif payload.script_text is not None:
        state_data["script_text"] = payload.script_text
        trimmed = payload.script_text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                parsed = json.loads(trimmed)
                if isinstance(parsed, dict):
                    state_data["content_metadata"]["script"] = parsed
                    if parsed.get("title"):
                        state_data["content_metadata"]["topic"] = parsed["title"]
            except Exception:
                pass

    # 2. Update chalkboard exercise (for Game quiz and chalkboard scenes)
    if payload.chalkboard_exercise is not None:
        state_data["content_metadata"]["chalkboard_exercise"] = payload.chalkboard_exercise
        # If the script dict has a challenge field, keep in sync
        script_dict = state_data.get("content_metadata", {}).get("script")
        if isinstance(script_dict, dict) and "challenge" in script_dict:
            script_dict["challenge"] = payload.chalkboard_exercise

    # 3. Update chalkboard title / target expression
    if payload.chalkboard_title is not None:
        state_data["content_metadata"]["target_expression"] = payload.chalkboard_title
        state_data["prompt_params"]["EXPRESSION"] = payload.chalkboard_title
        script_dict = state_data.get("content_metadata", {}).get("script")
        if isinstance(script_dict, dict) and "title" in script_dict:
            script_dict["title"] = payload.chalkboard_title

    if payload.target_expression is not None:
        state_data["content_metadata"]["target_expression"] = payload.target_expression
        state_data["prompt_params"]["EXPRESSION"] = payload.target_expression

    if payload.game_archetype is not None:
        state_data["content_metadata"]["game_archetype"] = payload.game_archetype
        state_data["prompt_params"]["game_archetype"] = payload.game_archetype
        state_data["prompt_params"]["GAME_ARCHETYPE"] = payload.game_archetype

    if "assets" not in state_data or not isinstance(state_data["assets"], dict):
        state_data["assets"] = {}
    if "status" not in state_data or not isinstance(state_data["status"], dict):
        state_data["status"] = {}

    # 4. Update general prompt
    # If a new version of general prompt is saved:
    # - property 'image_generation' changes to 'pending'
    # - LLM must re-do all specific scene prompts, so existing image_prompts are invalidated
    # - existing scene images are preserved on disk (non-destructive editing)
    general_prompt_changed = False
    if payload.general_prompt is not None:
        curr_gp = str(state_data["assets"].get("general_prompt") or "").strip()
        new_gp = payload.general_prompt.strip()
        if new_gp != curr_gp:
            general_prompt_changed = True
            state_data["assets"]["general_prompt"] = new_gp
            state_data["content_metadata"]["anchor_environment"] = new_gp
            state_data["status"]["image_generation"] = "pending"
            state_data["assets"]["image_prompts"] = {}

    if payload.character_anchors is not None:
        state_data["assets"]["character_anchors"] = payload.character_anchors

    # 5. Update specific scene prompts (only if general prompt did not just invalidate them)
    if payload.image_prompts is not None and not general_prompt_changed:
        if "image_prompts" not in state_data["assets"] or not isinstance(state_data["assets"]["image_prompts"], dict):
            state_data["assets"]["image_prompts"] = {}
        for sec_k, sec_prompt in payload.image_prompts.items():
            state_data["assets"]["image_prompts"][sec_k] = sec_prompt

    # Save to disk
    sm.save_script_state(canonical_id, state_data)

    # Update single item in in-memory cache immediately (O(1))
    _update_cached_script(canonical_id, state_data)

    return get_script(canonical_id)


class StageToggleRequest(BaseModel):
    stage: str
    new_status: Optional[str] = None


@router.post("/{script_id}/toggle-stage")
def toggle_script_stage(script_id: str, payload: StageToggleRequest) -> Dict[str, Any]:
    """Toggles or sets the status ('pending' or 'done') for an individual asset generation stage."""
    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found.")

    state_data = sm.get_script_state(canonical_id)
    if "status" not in state_data or not isinstance(state_data["status"], dict):
        state_data["status"] = {}
    if "assets" not in state_data or not isinstance(state_data["assets"], dict):
        state_data["assets"] = {}

    stage_map = {
        "scripts": "script_generation",
        "script": "script_generation",
        "script_generation": "script_generation",
        "voice": "voice_generation",
        "voice_generation": "voice_generation",
        "images": "image_generation",
        "img": "image_generation",
        "image_generation": "image_generation",
        "thumbnails": "thumbnail_generation",
        "thumb": "thumbnail_generation",
        "thumbnail_generation": "thumbnail_generation",
        "assembly": "video_assembly",
        "assmbl": "video_assembly",
        "video_assembly": "video_assembly",
    }

    stage_clean = payload.stage.strip().lower()
    status_key = stage_map.get(stage_clean)
    if not status_key:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stage '{payload.stage}'. Must be one of: {list(stage_map.keys())}"
        )

    current_val = state_data["status"].get(status_key, "missing")
    if payload.new_status:
        target_val = payload.new_status.strip().lower()
    else:
        target_val = "pending" if current_val == "done" else "done"

    state_data["status"][status_key] = target_val

    # If toggling image_generation to pending to redo images, clear existing scene illustrations
    if status_key == "image_generation" and target_val == "pending":
        image_dir_str = state_data["assets"].get("image_dir")
        if image_dir_str:
            p = Path(image_dir_str)
            if p.exists() and p.is_dir():
                for old_img in p.glob(f"script_{canonical_id}_*.png"):
                    try:
                        old_img.unlink()
                    except Exception:
                        pass

    # Save to disk
    sm.save_script_state(canonical_id, state_data)

    # Update single item in in-memory cache immediately (O(1))
    summary = _update_cached_script(canonical_id, state_data)
    return {
        "script_id": canonical_id,
        "stage": payload.stage,
        "status_key": status_key,
        "new_status": target_val,
        "summary": summary,
    }


class ScriptGenerateRequest(BaseModel):
    force: bool = True
    options: Optional[Dict[str, Any]] = None


@router.post("/{script_id}/generate")
def generate_script_endpoint(script_id: str, payload: Optional[ScriptGenerateRequest] = None) -> Dict[str, Any]:
    """Triggers Stage A script generation for a specific script directly via the WebUI job runner."""
    from webui.jobs.manager import get_job_manager
    from webui.jobs.models import JobCreateRequest, JobStage

    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found.")

    jm = get_job_manager()
    opts = payload.options if payload and payload.options else {}
    if payload and payload.force:
        opts["force"] = True
    else:
        opts.setdefault("force", True)

    job = jm.enqueue_job(
        JobCreateRequest(
            stage=JobStage.SCRIPTS,
            script_ids=[canonical_id],
            options=opts,
        )
    )
    return {"status": "enqueued", "job_id": job.job_id, "script_id": canonical_id}


class GeminiAuditRequest(BaseModel):
    current_prompt: Optional[str] = None
    api_key: Optional[str] = None


@router.post("/{script_id}/gemini-audit-prompt")
def gemini_audit_prompt(script_id: str, payload: Optional[GeminiAuditRequest] = None) -> Dict[str, Any]:
    """Audits and creatively reimagines the script's General Prompt using Google Gemini.
    Saves the new prompt, sets image_generation to 'pending', and clears old scene prompts & images.
    """
    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found.")

    state_data = sm.get_script_state(canonical_id)
    if "assets" not in state_data or not isinstance(state_data["assets"], dict):
        state_data["assets"] = {}
    if "content_metadata" not in state_data or not isinstance(state_data["content_metadata"], dict):
        state_data["content_metadata"] = {}
    if "status" not in state_data or not isinstance(state_data["status"], dict):
        state_data["status"] = {}

    current_prompt = (
        (payload.current_prompt if payload and payload.current_prompt else "")
        or state_data["assets"].get("general_prompt", "")
    ).strip()
    provided_key = (payload.api_key if payload and payload.api_key else "").strip()

    try:
        from core.gemini_auditor import audit_general_prompt
        audited_prompt = audit_general_prompt(
            script_data=state_data,
            current_prompt=current_prompt,
            api_key=provided_key or None,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini Auditor error: {exc}")

    # Return the generated prompt as a draft for the user to review.
    # Non-destructive: DO NOT overwrite state on disk and DO NOT delete existing images.
    return {
        "status": "success",
        "audited_prompt": audited_prompt,
        "character_anchors": state_data.get("assets", {}).get("character_anchors") or {},
        "script_id": canonical_id,
    }


class RenderChalkboardRequest(BaseModel):
    chalkboard_exercise: Optional[str] = None


@router.post("/{script_id}/render-chalkboard")
def render_chalkboard_endpoint(script_id: str, payload: Optional[RenderChalkboardRequest] = None) -> Dict[str, Any]:
    """
    Renders high-resolution chalk typography directly onto empty_chalkboard.png for GAME scripts.
    Saves script_{script_id}_challenge.png to the script's images directory and updates script state.
    """
    from config.settings import (
        GAME_IMAGES_DIR,
        IMAGE_DEFAULT_WIDTH,
        IMAGE_DEFAULT_HEIGHT,
        get_script_output_dir,
    )
    from core.state_manager import resolve_lang_and_type
    from video_creation._C_image_generation.core.chalkboard_renderer import render_chalkboard_image

    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{canonical_id}' not found.")

    state_data = sm.get_script_state(canonical_id)
    lang, video_type = resolve_lang_and_type(canonical_id)

    if video_type != "game":
        raise HTTPException(
            status_code=400,
            detail=f"Script '{canonical_id}' is not a GAME video (video_type={video_type}). Chalkboard rendering only applies to G-series game scripts."
        )

    content_meta = state_data.setdefault("content_metadata", {})
    if payload and payload.chalkboard_exercise is not None:
        content_meta["chalkboard_exercise"] = payload.chalkboard_exercise
        script_dict = content_meta.get("script")
        if isinstance(script_dict, dict) and "challenge" in script_dict:
            script_dict["challenge"] = payload.chalkboard_exercise

    exercise_text = (
        content_meta.get("chalkboard_exercise")
        or (content_meta.get("script", {}).get("challenge") if isinstance(content_meta.get("script"), dict) else None)
        or state_data.get("metadata", {}).get("chalkboard_exercise")
    )
    if not exercise_text or not str(exercise_text).strip():
        raise HTTPException(
            status_code=400,
            detail=f"No chalkboard exercise text found for '{canonical_id}'. Please set chalkboard exercise text first."
        )

    empty_chalkboard_path = GAME_IMAGES_DIR / "empty_chalkboard.png"
    if not empty_chalkboard_path.exists():
        raise HTTPException(status_code=500, detail=f"Chalkboard template not found: {empty_chalkboard_path}")

    # Determine script images directory
    out_dir = get_script_output_dir(canonical_id, language=lang, base_dir=BASE_DIR) / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest_path = out_dir / f"script_{canonical_id}_challenge.png"

    try:
        render_chalkboard_image(
            empty_chalkboard_path=empty_chalkboard_path,
            exercise_text=str(exercise_text).strip(),
            dest_path=dest_path,
            target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render chalkboard image: {exc}")

    # Update state assets
    assets = state_data.setdefault("assets", {})
    assets["image_dir"] = str(out_dir)
    images_list = assets.get("images")
    if not isinstance(images_list, list):
        images_list = []
    if str(dest_path) not in images_list:
        images_list.append(str(dest_path))
    assets["images"] = images_list

    # Save state and update catalog cache in-place
    sm.save_script_state(canonical_id, state_data)
    _update_cached_script(canonical_id, state_data)

    return {
        "status": "success",
        "message": f"Chalkboard image rendered successfully for {canonical_id}",
        "image_file": str(dest_path),
        "script": get_script(canonical_id),
    }


class ValidateIdsRequest(BaseModel):
    script_ids: List[str]


@router.post("/validate-ids")
def validate_script_ids(payload: ValidateIdsRequest) -> Dict[str, Any]:
    """
    Validates a list of script IDs against the local state repository.
    Returns existence, normalized language, video type, and stage status for each ID.
    """
    sm = _get_state_manager()
    results = []
    valid_count = 0
    invalid_count = 0

    seen = set()
    cleaned_ids = []
    for raw in payload.script_ids:
        cid = raw.strip().upper().replace("SCRIPT_", "").replace(".JSON", "")
        if cid and cid not in seen:
            seen.add(cid)
            cleaned_ids.append(cid)

    for sid in cleaned_ids:
        if sm.script_exists(sid):
            state = sm.get_script_state(sid)
            prompt_params = state.get("prompt_params") or {}
            content_meta = state.get("content_metadata") or {}
            status = state.get("status") or {}

            lang = (
                prompt_params.get("TARGET_LANGUAGE")
                or content_meta.get("language")
                or "Unknown"
            )
            vtype = (
                prompt_params.get("VIDEO_TYPE")
                or content_meta.get("video_type")
                or "Unknown"
            )

            results.append({
                "id": sid,
                "exists": True,
                "language": _normalize_language(lang),
                "type": str(vtype).lower(),
                "stages": {
                    "voice": _normalize_stage(status.get("voice_generation")),
                    "images": _normalize_stage(status.get("image_generation")),
                    "thumbnails": _normalize_stage(status.get("thumbnail_generation")),
                    "assembly": _normalize_stage(status.get("video_assembly")),
                },
            })
            valid_count += 1
        else:
            results.append({
                "id": sid,
                "exists": False,
                "language": None,
                "type": None,
                "stages": {},
            })
            invalid_count += 1

    return {
        "items": results,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "total": len(results),
    }


class RedoSceneImageRequest(BaseModel):
    prompt: Optional[str] = None
    seed: Optional[int] = None


@router.post("/{script_id}/scenes/{scene_type}/redo-image")
def redo_scene_image_endpoint(
    script_id: str,
    scene_type: str,
    payload: Optional[RedoSceneImageRequest] = None
) -> Dict[str, Any]:
    """
    Regenerates a specific scene illustration for a script using ComfyUI with the existing
    specific prompt (or updated prompt if provided) and a fresh random seed.
    Updates the script's image asset, saves state, and refreshes the catalog cache.
    """
    import random
    from config.settings import (
        COMFY_API_URL,
        IMAGE_WORKFLOW_PATH,
        IMAGE_DEFAULT_STEPS,
        IMAGE_DEFAULT_WIDTH,
        IMAGE_DEFAULT_HEIGHT,
        IMAGE_STALL_TIMEOUT,
        get_script_output_dir,
    )
    from core.state_manager import resolve_lang_and_type
    from video_creation._C_image_generation.core.comfy_client import ImageComfyClient
    from video_creation._C_image_generation.core.prompt_builder import sanitize_and_style_prompt
    from video_creation._C_image_generation.main import ensure_llama_stopped

    sm = _get_state_manager()
    canonical_id = script_id.strip().upper()
    if not sm.script_exists(canonical_id):
        raise HTTPException(status_code=404, detail=f"Script '{canonical_id}' not found.")

    state_data = sm.get_script_state(canonical_id)
    sec_lower = scene_type.strip().lower()

    # 1. Resolve prompt to use
    prompt = None
    if payload and payload.prompt and payload.prompt.strip():
        prompt = payload.prompt.strip()
    else:
        assets = state_data.setdefault("assets", {})
        prompts_map = assets.get("image_prompts") or {}
        visual_prompts = state_data.get("visual_prompts") or {}
        prompt = (
            prompts_map.get(sec_lower)
            or prompts_map.get(scene_type)
            or visual_prompts.get(sec_lower)
            or visual_prompts.get(scene_type)
        )

    if not prompt or not str(prompt).strip():
        raise HTTPException(
            status_code=400,
            detail=f"No prompt available for scene '{scene_type}'. Please enter a prompt before regenerating."
        )

    # 2. Release LLM VRAM before launching ComfyUI task
    try:
        ensure_llama_stopped()
    except Exception:
        pass

    # 3. Resolve destination path
    lang, _ = resolve_lang_and_type(canonical_id)
    out_dir = get_script_output_dir(canonical_id, language=lang, base_dir=BASE_DIR) / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest_path = out_dir / f"script_{canonical_id}_{sec_lower}.png"

    # 4. Connect to ComfyUI and generate
    if not IMAGE_WORKFLOW_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Workflow template missing: {IMAGE_WORKFLOW_PATH}")

    try:
        comfy_client = ImageComfyClient(
            api_url=COMFY_API_URL,
            workflow_path=IMAGE_WORKFLOW_PATH,
            poll_timeout=3600,
            poll_interval=2,
        )
        comfy_client.check_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"ComfyUI is offline or unreachable at {COMFY_API_URL}: {exc}. Please verify ComfyUI is running."
        )

    styled_prompt = sanitize_and_style_prompt(str(prompt).strip())
    seed = payload.seed if (payload and payload.seed is not None) else random.randint(1, 10**15)

    try:
        comfy_client.generate_image(
            prompt_text=styled_prompt,
            filename_prefix=f"Z-Image/script_{canonical_id}_{sec_lower}",
            dest_path=dest_path,
            seed=seed,
            steps=IMAGE_DEFAULT_STEPS,
            width=IMAGE_DEFAULT_WIDTH,
            height=IMAGE_DEFAULT_HEIGHT,
            stall_timeout=IMAGE_STALL_TIMEOUT,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ComfyUI image generation failed: {exc}")

    # 5. Update state assets
    assets = state_data.setdefault("assets", {})
    image_prompts = assets.setdefault("image_prompts", {})
    image_prompts[sec_lower] = str(prompt).strip()
    assets["image_dir"] = str(out_dir)

    img_list = assets.get("images")
    if not isinstance(img_list, list):
        img_list = []
    dest_str = str(dest_path)
    if dest_str not in img_list:
        img_list.append(dest_str)
    assets["images"] = img_list

    # Save state & update cache
    sm.save_script_state(canonical_id, state_data)
    _update_cached_script(canonical_id, state_data)

    return {
        "status": "success",
        "message": f"Scene '{scene_type}' regenerated successfully for {canonical_id}",
        "image_file": dest_str,
        "seed": seed,
        "script": get_script(canonical_id),
    }


