"""
webui/routers/drive.py — REST API endpoints for Google Drive uploads.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# pyrefly: ignore[missing-import]
from fastapi import APIRouter, HTTPException
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


@router.get("/status")
def get_drive_status() -> Dict[str, Any]:
    """Checks Google Drive configuration and credentials availability."""
    cred_path = GoogleDriveClient._resolve_credentials_path()
    has_credentials = cred_path is not None and cred_path.exists()
    return {
        "configured": has_credentials,
        "credentials_found": has_credentials,
        "credentials_file": cred_path.name if cred_path else None,
        "root_folder_id": DEFAULT_ROOT_FOLDER_ID,
        "root_folder_url": f"https://drive.google.com/drive/folders/{DEFAULT_ROOT_FOLDER_ID}",
    }


@router.post("/scripts/{script_id}/upload")
def upload_single_script(script_id: str) -> Dict[str, Any]:
    """Uploads a completed script's video and thumbnail to Google Drive."""
    sid = script_id.upper().strip()
    sm = StateManager(base_dir=BASE_DIR)
    if not sm.script_exists(sid):
        raise HTTPException(status_code=404, detail=f"Script state '{sid}' not found")

    try:
        result = upload_script_to_drive(script_id=sid, state_mgr=sm)
        return {
            "success": True,
            "message": f"Script {sid} uploaded successfully to Google Drive",
            "data": result,
        }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=400, detail=str(fnf))
    except Exception as exc:
        logger.error("[%s] Drive upload failed: %s", sid, exc)
        raise HTTPException(status_code=500, detail=str(exc))

