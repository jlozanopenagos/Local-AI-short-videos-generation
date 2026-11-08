"""
webui/jobs/adapters/thumbnails.py — Stage F (Thumbnail Generation) adapter.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.state_manager import StateManager
from video_creation._F_thumbnail_image_generation.main import generate_thumbnail_for_script
from webui.jobs.adapters.base import BaseStageAdapter


class ThumbnailsAdapter(BaseStageAdapter):
    """Executes Stage F chalkboard thumbnail generation."""

    def run(
        self,
        script_ids: List[str],
        options: Dict[str, Any],
        emit_log: Callable[[str], None],
        emit_progress: Callable[[int, int, str], None],
        check_cancelled: Callable[[], bool],
    ) -> Dict[str, Any]:
        sm = StateManager(base_dir=BASE_DIR)
        force = options.get("force", False)

        total = len(script_ids)
        success_count = 0
        failed_ids = []

        emit_log(f"Starting Thumbnail Generation for {total} script(s)...")

        for idx, script_id in enumerate(script_ids, start=1):
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            emit_progress(idx - 1, total, script_id)

            if not sm.script_exists(script_id):
                emit_log(f"[{script_id}] ERROR: Script state does not exist in state/.")
                failed_ids.append(script_id)
                continue

            state_data = sm.get_script_state(script_id)
            status = state_data.get("status", {})
            if not force and status.get("thumbnail_generation") == "done":
                emit_log(f"[{script_id}] Thumbnail already exists — skipping (use force to overwrite).")
                success_count += 1
                continue

            try:
                emit_log(f"[{script_id}] Rendering chalkboard title thumbnail...")
                t0 = time.time()
                ok = generate_thumbnail_for_script(state_data, state_mgr=sm, base_dir=BASE_DIR)
                dur = time.time() - t0
                if ok:
                    emit_log(f"[{script_id}] ✓ Thumbnail successfully rendered in {dur:.1f}s.")
                    success_count += 1
                else:
                    emit_log(f"[{script_id}] ✗ FAILED to generate thumbnail after {dur:.1f}s.")
                    failed_ids.append(script_id)
            except Exception as exc:
                emit_log(f"[{script_id}] EXCEPTION: {exc}")
                failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Thumbnail job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

