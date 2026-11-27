"""
sync_service.py — High-level Google Drive orchestration service for Shorts Automation.

Handles:
- Mapping script metadata to the exact target folder hierarchy:
  Root (GOOGLE_DRIVE_ROOT_FOLDER_ID)
    -> <language> (english, french, italian, spanish)
      -> <video_type> (expressions, fun_facts, game, role_play)
        -> <script_id> (e.g. EE01, FR21, IG09)
          -> <script_id>.mp4 (Clean video name)
          -> <script_id>_thumbnail.png (Clean thumbnail name)
- Asset discovery and fallbacks.
- Updating StateManager with drive_upload status and folder URLs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Video type canonical mapping to exact requested Drive folder names
VIDEO_TYPE_FOLDER_MAP = {
    "expression": "expressions",
    "expressions": "expressions",
    "fun_facts": "fun_facts",
    "funfacts": "fun_facts",
    "facts": "fun_facts",
    "game": "game",
    "games": "game",
    "quiz": "game",
    "roleplay": "role_play",
    "role_play": "role_play",
}


def map_video_type_to_folder(vtype: str) -> str:
    """Maps internal video_type string to the target Google Drive folder name."""
    clean = (vtype or "expression").lower().strip()
    return VIDEO_TYPE_FOLDER_MAP.get(clean, clean)


def map_language_to_folder(lang: str) -> str:
    """Normalizes language name to lowercase Google Drive folder name."""
    clean = (lang or "english").lower().strip()
    if "french" in clean or clean == "fr":
        return "french"
    elif "italian" in clean or clean == "it":
        return "italian"
    elif "spanish" in clean or clean == "es":
        return "spanish"
    return "english"


def resolve_script_assets(
    script_data: Dict[str, Any],
    base_dir: Optional[Path] = None,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Locates the final assembled video and the thumbnail file on disk.
    Returns (video_path, thumbnail_path).
    """
    script_id = script_data.get("id") or script_data.get("script_id") or "UNKNOWN"
    assets = script_data.get("assets", {})

    video_path_str = (
        assets.get("final_video")
        or assets.get("video_path")
        or assets.get("final_video_path")
        or assets.get("video")
    )
    thumb_path_str = assets.get("thumbnail_path") or assets.get("thumbnail")

    resolved_video: Optional[Path] = None
    resolved_thumb: Optional[Path] = None

    if video_path_str:
        p = Path(video_path_str)
        if p.exists():
            resolved_video = p

    if thumb_path_str:
        p = Path(thumb_path_str)
        if p.exists():
            resolved_thumb = p

    # Fallback search if paths were moved or not saved explicitly
    if resolved_video is None or resolved_thumb is None:
        try:
            from config import get_script_output_dir, resolve_script_language, resolve_script_video_type
            lang = resolve_script_language(script_data)
            vtype = resolve_script_video_type(script_data)
            out_dir = get_script_output_dir(script_id, lang, base_dir, video_type=vtype)

            if resolved_video is None:
                cand_video = out_dir / f"script_{script_id}_final.mp4"
                if cand_video.exists():
                    resolved_video = cand_video

            if resolved_thumb is None:
                cand_thumb = out_dir / "thumbnail.png"
                if cand_thumb.exists():
                    resolved_thumb = cand_thumb
        except Exception as exc:
            logger.debug("[%s] Error checking fallback output paths: %s", script_id, exc)

    return resolved_video, resolved_thumb


def resolve_script_thumbnails(
    script_data: Dict[str, Any],
    base_dir: Optional[Path] = None,
) -> List[Tuple[Optional[str], Path]]:
    """Resolves all thumbnail files on disk for a script.

    Returns a list of `(variant_name_or_None, local_path)`:
    - Spanish scripts with LatAm + Spain variants return `[("latam", ...), ("spain", ...)]`.
    - Single-thumbnail scripts return `[(None, Path(...))]`.
    """
    script_id = script_data.get("id") or script_data.get("script_id") or "UNKNOWN"
    assets = script_data.get("assets", {}) or {}
    variants_raw = assets.get("thumbnail_variants")

    resolved: List[Tuple[Optional[str], Path]] = []
    if isinstance(variants_raw, dict) and variants_raw:
        preferred_order = ["latam", "spain"]
        ordered_keys = [k for k in preferred_order if k in variants_raw] + [
            k for k in sorted(variants_raw) if k not in preferred_order
        ]
        for v_key in ordered_keys:
            p_str = variants_raw.get(v_key)
            if p_str:
                p = Path(p_str)
                if p.exists():
                    resolved.append((str(v_key), p))
        if resolved:
            return resolved

    try:
        from config import get_script_output_dir, resolve_script_language, resolve_script_video_type

        lang = resolve_script_language(script_data)
        vtype = resolve_script_video_type(script_data)
        out_dir = get_script_output_dir(script_id, lang, base_dir, video_type=vtype)
        if lang == "spanish":
            for v_key in ("latam", "spain"):
                cand = out_dir / f"thumbnail_{v_key}.png"
                if cand.exists():
                    resolved.append((v_key, cand))
            if resolved:
                return resolved
    except Exception as exc:
        logger.debug("[%s] Error checking variant thumbnail paths: %s", script_id, exc)

    _, single_thumb = resolve_script_assets(script_data, base_dir=base_dir)
    if single_thumb is not None:
        return [(None, single_thumb)]
    return []


def upload_script_to_drive(
    script_id: str,
    client: Optional[Any] = None,
    state_mgr: Optional[Any] = None,
    credentials_path: Optional[str | Path] = None,
    root_folder_id: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    assets_scope: str = "all",
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Uploads a script's final video and/or thumbnail(s) to Google Drive under:
    Root / <language> / <video_type> / <script_id> /

    `assets_scope`:
      - "all": requires and uploads both final video and thumbnail(s) (default).
      - "video": uploads only the final `.mp4` video without touching thumbnails.
      - "thumbnail": uploads only the rendered thumbnail `.png`(s) without touching video.

    Returns a dict with execution details and drive URLs.
    """
    from connectivity.drive_sync.drive_client import GoogleDriveClient, DEFAULT_ROOT_FOLDER_ID
    # pyrefly: ignore[missing-import]
    from state_manager import StateManager
    from config import resolve_script_language, resolve_script_video_type

    scope_norm = (assets_scope or "all").strip().lower()
    if scope_norm == "thumbnails":
        scope_norm = "thumbnail"
    if scope_norm not in ("all", "video", "thumbnail"):
        raise ValueError(f"Unsupported assets_scope '{assets_scope}'. Expected 'all', 'video', or 'thumbnail'.")

    include_video = scope_norm in ("all", "video")
    include_thumbnail = scope_norm in ("all", "thumbnail")

    sm = state_mgr or StateManager(base_dir=base_dir) if base_dir else (state_mgr or StateManager())
    if hasattr(sm, "load_script_state"):
        res = sm.load_script_state(script_id)
        if isinstance(res, dict):
            script_data = res
        elif hasattr(sm, "get_script_state"):
            script_data = sm.get_script_state(script_id)
        else:
            script_data = res
    elif hasattr(sm, "get_script_state"):
        script_data = sm.get_script_state(script_id)
    else:
        raise AttributeError("StateManager has neither get_script_state nor load_script_state")
    if not script_data:
        raise ValueError(f"Script state not found for ID: {script_id}")

    root_id = root_folder_id or DEFAULT_ROOT_FOLDER_ID
    drive_client = client or GoogleDriveClient(
        credentials_path=credentials_path,
        root_folder_id=root_id,
    )

    # 1. Resolve local files requested by `assets_scope` BEFORE creating/modifying anything in Drive
    video_path: Optional[Path] = None
    thumb_entries: List[Tuple[Optional[str], Path]] = []

    if include_video:
        video_path, _ = resolve_script_assets(script_data, base_dir=base_dir)
        if not video_path or not video_path.exists():
            raise FileNotFoundError(
                f"[{script_id}] Final video file not found on disk. Assemble the video first before uploading."
            )

    if include_thumbnail:
        thumb_entries = resolve_script_thumbnails(script_data, base_dir=base_dir)
        if not thumb_entries:
            if scope_norm == "thumbnail":
                raise FileNotFoundError(
                    f"[{script_id}] Thumbnail file not found on disk. Render the thumbnail first before uploading to Google Drive."
                )
            raise FileNotFoundError(
                f"[{script_id}] Thumbnail file not found on disk. Both video and thumbnail are required before uploading to Google Drive."
            )

    # 2. Determine target Drive folder hierarchy
    raw_lang = resolve_script_language(script_data)
    raw_vtype = resolve_script_video_type(script_data)

    target_lang = map_language_to_folder(raw_lang)
    target_vtype = map_video_type_to_folder(raw_vtype)

    logger.info(
        "[%s] Navigating Google Drive folders (scope=%s): Root -> %s -> %s -> %s",
        script_id, scope_norm, target_lang, target_vtype, script_id
    )

    # Step 1: Language folder (e.g. english)
    lang_folder_id = drive_client.get_or_create_folder(target_lang, parent_id=drive_client.root_folder_id)

    # Step 2: Video Type folder (e.g. expressions)
    type_folder_id = drive_client.get_or_create_folder(target_vtype, parent_id=lang_folder_id)

    # Step 3: Script ID folder (e.g. EE01)
    script_folder_id = drive_client.get_or_create_folder(script_id, parent_id=type_folder_id)

    folder_url = f"https://drive.google.com/drive/folders/{script_folder_id}"
    video_name = f"{script_id}.mp4"
    thumb_targets = [
        (
            variant,
            local_p,
            f"{script_id}_thumbnail_{variant}.png" if variant else f"{script_id}_thumbnail.png",
        )
        for variant, local_p in thumb_entries
    ]

    previous_files: List[Dict[str, Any]] = []
    if include_video:
        previous_files.extend(drive_client.list_named_files(script_folder_id, video_name))
    if include_thumbnail:
        for _variant, _local_p, rname in thumb_targets:
            previous_files.extend(drive_client.list_named_files(script_folder_id, rname))

    video_upload_res: Optional[Dict[str, Any]] = None
    uploaded_thumbs: List[Tuple[Optional[str], str, Dict[str, Any]]] = []

    if include_video and video_path is not None:
        video_upload_res = drive_client.upload_or_update_file(
            local_path=video_path,
            remote_filename=video_name,
            parent_folder_id=script_folder_id,
            mime_type="video/mp4",
            progress_callback=progress_callback,
            replace_existing=False,
        )

    if include_thumbnail:
        try:
            for variant, local_p, rname in thumb_targets:
                res = drive_client.upload_or_update_file(
                    local_path=local_p,
                    remote_filename=rname,
                    parent_folder_id=script_folder_id,
                    mime_type="image/png",
                    replace_existing=False,
                )
                uploaded_thumbs.append((variant, rname, res))
        except Exception:
            if video_upload_res and video_upload_res.get("id"):
                drive_client.delete_file(video_upload_res["id"], video_name)
            for _v, rname, res in uploaded_thumbs:
                if res and res.get("id"):
                    drive_client.delete_file(res["id"], rname)
            raise

    # 5. Update State (preserving Drive fields of any untouched asset scope)
    assets = script_data.setdefault("assets", {})
    assets["drive_folder_id"] = script_folder_id
    assets["drive_folder_url"] = folder_url

    if video_upload_res is not None:
        assets["drive_video_id"] = video_upload_res.get("id")
        assets["drive_video_url"] = video_upload_res.get("web_view_link")

    primary_thumb_res: Optional[Dict[str, Any]] = None
    if uploaded_thumbs:
        primary_thumb_res = uploaded_thumbs[0][2]
        assets["drive_thumbnail_id"] = primary_thumb_res.get("id")
        assets["drive_thumbnail_url"] = primary_thumb_res.get("web_view_link")

        variant_drive_map = {
            variant: {
                "id": res.get("id"),
                "name": rname,
                "url": res.get("web_view_link"),
            }
            for variant, rname, res in uploaded_thumbs
            if variant
        }
        if variant_drive_map:
            assets["drive_thumbnails"] = variant_drive_map
        else:
            assets.pop("drive_thumbnails", None)

    status = script_data.setdefault("status", {})
    if scope_norm == "all" or (assets.get("drive_video_id") and assets.get("drive_thumbnail_id")):
        status["drive_upload"] = "done"

    sm.save_script_state(script_id, script_data)
    new_file_ids = set()
    if video_upload_res and video_upload_res.get("id"):
        new_file_ids.add(video_upload_res["id"])
    for _v, _rn, res in uploaded_thumbs:
        if res and res.get("id"):
            new_file_ids.add(res["id"])

    deleted_existing_count = 0
    for previous in previous_files:
        file_id = previous.get("id")
        if file_id and file_id not in new_file_ids:
            deleted_existing_count += drive_client.delete_file(file_id, previous.get("name", ""))
    logger.info("[%s] Drive upload complete (scope=%s)! Folder URL: %s", script_id, scope_norm, folder_url)

    return {
        "script_id": script_id,
        "assets_scope": scope_norm,
        "language": target_lang,
        "video_type": target_vtype,
        "folder_id": script_folder_id,
        "folder_url": folder_url,
        "deleted_existing_count": deleted_existing_count,
        "video": video_upload_res,
        "thumbnail": primary_thumb_res,
        "thumbnails": [res for _v, _rn, res in uploaded_thumbs],
    }


def upload_completed_scripts_to_drive(
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    client: Optional[Any] = None,
    state_mgr: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Finds all scripts with video_assembly == 'done' and uploads them to Drive in batch.
    """
    # pyrefly: ignore[missing-import]
    from state_manager import StateManager
    from config import resolve_script_language, resolve_script_video_type

    sm = state_mgr or StateManager()
    if hasattr(sm, "get_all_scripts"):
        scripts_list = sm.get_all_scripts()
        all_states = {s.get("id") or s.get("script_id"): s for s in scripts_list}
    elif hasattr(sm, "load_all_script_states"):
        all_states = sm.load_all_script_states()
    else:
        all_states = {}

    results: List[Dict[str, Any]] = []
    for sid, data in all_states.items():
        if data.get("status", {}).get("video_assembly") != "done":
            continue

        if language:
            slang = resolve_script_language(data)
            if map_language_to_folder(slang) != map_language_to_folder(language):
                continue

        if video_type:
            svtype = resolve_script_video_type(data)
            if map_video_type_to_folder(svtype) != map_video_type_to_folder(video_type):
                continue

        try:
            res = upload_script_to_drive(sid, client=client, state_mgr=sm)
            results.append(res)
        except Exception as exc:
            logger.error("[%s] Failed to upload to Drive: %s", sid, exc)
            results.append({"script_id": sid, "error": str(exc)})

    return results

