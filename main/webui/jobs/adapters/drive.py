"""
webui/jobs/adapters/drive.py — Google Drive upload adapter for WebUI Job Queue.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.state_manager import StateManager
from connectivity.drive_sync.drive_client import GoogleDriveClient
from connectivity.drive_sync.sync_service import upload_script_to_drive
from webui.jobs.adapters.base import BaseStageAdapter


class DriveAdapter(BaseStageAdapter):
    """Executes on-demand Google Drive uploads via the WebUI job runner."""

    def run(
        self,
        script_ids: List[str],
        options: Dict[str, Any],
        emit_log: Callable[[str], None],
        emit_progress: Callable[[int, int, str], None],
        check_cancelled: Callable[[], bool],
    ) -> Dict[str, Any]:
        sm = StateManager(base_dir=BASE_DIR)
        total = len(script_ids)
        success_count = 0
        failed_ids: List[str] = []

        emit_log(f"Starting Google Drive upload for {total} script(s)...")

        # Authenticate client once for the entire batch
        try:
            client = GoogleDriveClient()
            client.authenticate()
        except Exception as exc:
            err_msg = f"Failed to initialize Google Drive client: {exc}"
            emit_log(f"ERROR: {err_msg}")
            return {
                "success_count": 0,
                "failed_count": total,
                "failed_ids": script_ids,
                "error": err_msg,
            }

        for idx, script_id in enumerate(script_ids, start=1):
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            emit_progress(idx - 1, total, script_id)

            if not sm.script_exists(script_id):
                emit_log(f"[{script_id}] ERROR: Script state does not exist in state/.")
                failed_ids.append(script_id)
                continue

            emit_log(f"[{script_id}] Uploading video and thumbnail to Google Drive...")

            try:
                def progress_cb(pct: float) -> None:
                    pass

                res = upload_script_to_drive(
                    script_id=script_id,
                    client=client,
                    state_mgr=sm,
                    progress_callback=progress_cb,
                )
                deleted_cnt = res.get("deleted_existing_count", 0)
                if deleted_cnt > 0:
                    emit_log(
                        f"[{script_id}] Deleted {deleted_cnt} existing item(s) on Drive and uploaded new version -> {res['folder_url']}"
                    )
                else:
                    emit_log(f"[{script_id}] SUCCESS -> {res['folder_url']}")
                success_count += 1
            except Exception as exc:
                emit_log(f"[{script_id}] ERROR: {exc}")
                failed_ids.append(script_id)

        emit_progress(total, total, "")
        emit_log(f"Google Drive Upload finished: {success_count}/{total} successful.")

        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
        }
