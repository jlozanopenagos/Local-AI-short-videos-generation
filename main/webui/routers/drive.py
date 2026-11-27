"""
webui/routers/drive.py — REST API endpoints for Google Drive uploads.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# pyrefly: ignore[missing-import]
from fastapi import APIRouter, HTTPException, Request
# pyrefly: ignore[missing-import]
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from connectivity.drive_sync.drive_client import GoogleDriveClient, DEFAULT_ROOT_FOLDER_ID
from connectivity.drive_sync.sync_service import upload_script_to_drive, upload_completed_scripts_to_drive
from core.state_manager import StateManager

logger = logging.getLogger("webui.drive")

router = APIRouter(prefix="/api/drive", tags=["Google Drive"])


class DriveUploadBatchRequest(BaseModel):
    script_ids: Optional[List[str]] = Field(default=None, description="Optional list of specific script IDs")
    language: Optional[str] = Field(default=None, description="Optional language filter")
    video_type: Optional[str] = Field(default=None, description="Optional video type filter")


class SingleDriveUploadRequest(BaseModel):
    scope: str = Field(default="all", description="all | video | thumbnail")


@router.get("/status")
def get_drive_status() -> Dict[str, Any]:
    """Checks Google Drive configuration and credentials availability."""
    cred_path = GoogleDriveClient._resolve_credentials_path()
    has_credentials = cred_path is not None and cred_path.exists()
    root_id = (DEFAULT_ROOT_FOLDER_ID or os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")).strip()
    return {
        "configured": has_credentials,
        "credentials_found": has_credentials,
        "credentials_file": cred_path.name if cred_path else None,
        "root_folder_id": root_id,
        "root_folder_url": f"https://drive.google.com/drive/folders/{root_id}" if root_id else "",
    }


@router.post("/scripts/{script_id}/upload")
def upload_single_script(
    script_id: str,
    request: Request,
    payload: Optional[SingleDriveUploadRequest] = None,
) -> Dict[str, Any]:
    """Uploads a script's final video and/or thumbnail(s) to Google Drive."""
    sid = script_id.upper().strip()
    scope_raw = (payload.scope if payload else "all").strip().lower()
    scope = "thumbnail" if scope_raw == "thumbnails" else scope_raw
    if scope not in ("all", "video", "thumbnail"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported upload scope '{payload.scope if payload else ''}'. Expected 'all', 'video', or 'thumbnail'.",
        )

    app_base_dir = getattr(request.app.state, "base_dir", None)
    sm = StateManager(base_dir=app_base_dir or BASE_DIR)
    if not sm.script_exists(sid):
        raise HTTPException(status_code=404, detail=f"Script state '{sid}' not found")

    try:
        result = upload_script_to_drive(
            script_id=sid,
            state_mgr=sm,
            assets_scope=scope,
            base_dir=app_base_dir,
        )
        try:
            state_doc = sm.get_script_state(sid)
            if isinstance(state_doc, dict) and isinstance(state_doc.get("id"), str):
                from webui.routers.scripts import _update_cached_script
                _update_cached_script(sid, state_doc)
        except Exception:
            pass

        scope_label = {
            "all": "video and thumbnail",
            "video": "video",
            "thumbnail": "thumbnail(s)",
        }[scope]
        return {
            "success": True,
            "message": f"Script {sid} {scope_label} uploaded successfully to Google Drive",
            "data": result,
        }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=400, detail=str(fnf))
    except Exception as exc:
        logger.error("[%s] Drive upload failed (scope=%s): %s", sid, scope, exc)
        raise HTTPException(status_code=500, detail=str(exc))

