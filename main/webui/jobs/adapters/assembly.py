"""
webui/jobs/adapters/assembly.py — Stage G (Video Assembly) adapter for batch & mass video production.
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
from video_creation._G_video_assembly.core.transcriber import Transcriber
from video_creation._G_video_assembly.core.subtitle_builder import SubtitleBuilder
from video_creation._G_video_assembly.core.video_assembler import VideoAssembler
from webui.jobs.adapters.base import BaseStageAdapter


class AssemblyAdapter(BaseStageAdapter):
    """Executes Stage G mass video assembly."""

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

        # Instantiate core assembly workers once to reuse memory and models across mass batches
        transcriber = None
        builder = None
        assembler = None
        try:
            emit_log("Initializing Video Assembly engines (Whisper transcriber, ASS builder, FFmpeg assembler)...")
            transcriber = Transcriber()
            builder = SubtitleBuilder()
            assembler = VideoAssembler()
            emit_log("✓ Assembly engines initialized.")
        except Exception as init_exc:
            emit_log(f"Warning: Engine pre-initialization notice: {init_exc}. Will fall back to per-script init if needed.")

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

            # Verify prerequisites
            has_voice = status.get("voice_generation") == "done"
            has_images = status.get("image_generation") == "done"
            if not has_voice or not has_images:
                missing = []
                if not has_voice:
                    missing.append("Voice Audio (Stage B)")
                if not has_images:
                    missing.append("Images (Stage C)")
                emit_log(f"[{script_id}] Skipping assembly — prerequisites missing: {', '.join(missing)}.")
                failed_ids.append(script_id)
                continue

            max_attempts = int(options.get("max_attempts", 3))
            assembly_succeeded = False
            last_err = ""

            for attempt in range(1, max_attempts + 1):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at script {script_id}.")
                    break

                try:
                    emit_log(f"[{script_id}] Assembling short video (subtitles, audio, visuals, closure) (attempt {attempt}/{max_attempts})...")
                    t0 = time.time()
                    ok = process_script(
                        script_data=script_data,
                        state_manager=sm,
                        transcriber=transcriber,
                        builder=builder,
                        assembler=assembler,
                        base_dir=BASE_DIR,
                        regenerate_subtitles=force,
                        auto=True,
                    )
                    dur = time.time() - t0
                    if ok:
                        emit_log(f"[{script_id}] ✓ Video assembly completed in {dur:.1f}s.")
                        success_count += 1
                        assembly_succeeded = True
                        break
                    else:
                        last_err = f"Assembly returned false after {dur:.1f}s"
                        emit_log(f"[{script_id}] Video assembly attempt {attempt}/{max_attempts} failed.")
                        if attempt < max_attempts:
                            time.sleep(2.0)
                except Exception as exc:
                    last_err = str(exc)
                    emit_log(f"[{script_id}] Video assembly attempt {attempt}/{max_attempts} exception: {last_err}")
                    if attempt < max_attempts:
                        time.sleep(2.0)

            if not assembly_succeeded and not check_cancelled():
                emit_log(f"[{script_id}] ERROR: Video assembly failed after {max_attempts} attempts: {last_err}")
                failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Assembly job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }
