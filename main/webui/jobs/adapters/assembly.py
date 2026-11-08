"""
webui/jobs/adapters/assembly.py — Stage G (Video Assembly) adapter.
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
from video_creation._G_video_assembly.main import process_script
from webui.jobs.adapters.base import BaseStageAdapter


class AssemblyAdapter(BaseStageAdapter):
    """Executes Stage G video assembly."""

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

        emit_log(f"Starting Video Assembly for {total} script(s)...")

        for idx, script_id in enumerate(script_ids, start=1):
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            emit_progress(idx - 1, total, script_id)

            if not sm.script_exists(script_id):
                emit_log(f"[{script_id}] ERROR: Script state does not exist.")
                failed_ids.append(script_id)
                continue

            script_data = sm.get_script_state(script_id)
            status = script_data.get("status", {})
            if not force and status.get("video_assembly") == "done":
                emit_log(f"[{script_id}] Video already assembled — skipping.")
                success_count += 1
                continue

            try:
                emit_log(f"[{script_id}] Assembling short video (subtitles, audio, visuals, closure)...")
                t0 = time.time()
                ok = process_script(
                    script_data=script_data,
                    state_manager=sm,
                    base_dir=BASE_DIR,
                    auto=True,
                )
                dur = time.time() - t0
                if ok:
                    emit_log(f"[{script_id}] ✓ Video assembly completed in {dur:.1f}s.")
                    success_count += 1
                else:
                    emit_log(f"[{script_id}] ✗ FAILED video assembly after {dur:.1f}s.")
                    failed_ids.append(script_id)
            except Exception as exc:
                emit_log(f"[{script_id}] EXCEPTION in video assembly: {exc}")
                failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Assembly job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

