"""
webui/jobs/adapters/voice.py — Stage B (Voice Generation) adapter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    COMFY_API_URL,
    COMFY_INPUT_DIR,
    COMFY_OUTPUT_DIR,
    OPEN_SWARA_DIR,
    VOICE_WORKFLOW_PATH,
)
from core.llama_manager import get_llama_manager
from core.state_manager import StateManager
from video_creation._B_voice_generation.core.comfy_client import ComfyClient
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
from video_creation._B_voice_generation.main import process_script
from webui.jobs.adapters.base import BaseStageAdapter


class VoiceAdapter(BaseStageAdapter):
    """Executes Stage B multi-character voice generation."""

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

        # Free VRAM before voice generation so Qwen3-TTS has maximum GPU memory
        emit_log("Ensuring LLM server is stopped to release VRAM for audio synthesis...")
        get_llama_manager().ensure_llama_stopped()

        emit_log(f"Initializing voice clients for {total} script(s)...")
        voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)
        comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)

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
            if not force and status.get("voice_generation") == "done":
                emit_log(f"[{script_id}] Voice already generated — skipping.")
                success_count += 1
                continue

            try:
                emit_log(f"[{script_id}] Synthesizing multi-character audio track...")
                script_force = force or (status.get("voice_generation") == "pending")
                ok = process_script(
                    script_data=script_data,
                    state_manager=sm,
                    comfy_client=comfy_client,
                    voice_manager=voice_manager,
                    force=script_force,
                    base_dir=BASE_DIR,
                )
                if ok:
                    emit_log(f"[{script_id}] Voice synthesis successful.")
                    success_count += 1
                else:
                    emit_log(f"[{script_id}] FAILED to generate voice.")
                    failed_ids.append(script_id)
            except Exception as exc:
                emit_log(f"[{script_id}] EXCEPTION in voice synthesis: {exc}")
                failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Voice job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

