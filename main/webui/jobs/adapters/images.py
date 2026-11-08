"""
webui/jobs/adapters/images.py — Stage C (Scene Image Generation) adapter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    COMFY_API_URL,
    IMAGE_WORKFLOW_PATH,
    LLM_API_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL_NAME,
)
from core.llama_manager import get_llama_manager
from core.state_manager import StateManager
from video_creation._C_image_generation.core.comfy_client import ImageComfyClient
from video_creation._C_image_generation.core.prompt_builder import VisualPromptBuilder
from video_creation._C_image_generation.main import process_script
from webui.jobs.adapters.base import BaseStageAdapter


class ImagesAdapter(BaseStageAdapter):
    """Executes Stage C scene illustration generation."""

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
        seed = int(options.get("seed", 0))

        total = len(script_ids)
        success_count = 0
        failed_ids = []

        workflow_path = Path(IMAGE_WORKFLOW_PATH)
        if not workflow_path.is_absolute():
            workflow_path = BASE_DIR / workflow_path

        emit_log(f"Initializing image clients for {total} script(s)...")
        comfy_client = ImageComfyClient(
            api_url=COMFY_API_URL,
            workflow_path=workflow_path,
            poll_timeout=3600,
            poll_interval=2,
        )

        llm_timeout = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "180"))
        prompt_builder = VisualPromptBuilder(
            api_base_url=LLM_API_BASE_URL,
            api_key=LLM_API_KEY,
            model_name=LLM_MODEL_NAME,
            request_timeout=llm_timeout,
        )

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
            if not force and status.get("image_generation") == "done":
                emit_log(f"[{script_id}] Images already generated — skipping.")
                success_count += 1
                continue

            try:
                emit_log(f"[{script_id}] Generating scene illustrations with ComfyUI...")
                ok = process_script(
                    script_data=script_data,
                    state_manager=sm,
                    comfy_client=comfy_client,
                    prompt_builder=prompt_builder,
                    force=force,
                    seed=seed,
                    base_dir=BASE_DIR,
                )
                if ok:
                    emit_log(f"[{script_id}] Scene images generated successfully.")
                    success_count += 1
                else:
                    emit_log(f"[{script_id}] FAILED to generate scene images.")
                    failed_ids.append(script_id)
            except Exception as exc:
                emit_log(f"[{script_id}] EXCEPTION in image generation: {exc}")
                failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Image job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

