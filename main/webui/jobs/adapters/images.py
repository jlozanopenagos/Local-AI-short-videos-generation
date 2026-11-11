"""
webui/jobs/adapters/images.py — Stage C (Scene Image Generation) adapter.
"""

from __future__ import annotations

import os
import sys
import time
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
from core.llama_manager import ensure_llama_running, ensure_llama_stopped
from core.state_manager import StateManager
from video_creation._C_image_generation.core.comfy_client import ImageComfyClient
from video_creation._C_image_generation.core.prompt_builder import VisualPromptBuilder
from video_creation._C_image_generation.main import (
    ensure_image_prompts_for_script,
    process_script,
)
from webui.jobs.adapters.base import BaseStageAdapter


class ImagesAdapter(BaseStageAdapter):
    """Executes Stage C scene illustration generation with batched prompt pre-generation."""

    def __init__(self):
        self._active_comfy_client: ImageComfyClient | None = None

    def cancel(self) -> None:
        """Immediately interrupts running ComfyUI generation and clears queue."""
        if self._active_comfy_client:
            try:
                self._active_comfy_client.interrupt()
                self._active_comfy_client.clear_queue()
            except Exception:
                pass

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
        prompt_failed_ids: set[str] = set()

        llm_timeout = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "180"))
        prompt_builder = VisualPromptBuilder(
            api_base_url=LLM_API_BASE_URL,
            api_key=LLM_API_KEY,
            model_name=LLM_MODEL_NAME,
            request_timeout=llm_timeout,
        )

        # =========================================================================
        # PHASE 1: BATCH PROMPT GENERATION (Initialize LLM ONCE for all scripts)
        # =========================================================================
        scripts_needing_prompts = []
        for script_id in script_ids:
            if not sm.script_exists(script_id):
                continue
            s_data = sm.get_script_state(script_id)
            status = s_data.get("status", {})
            if not force and status.get("image_generation") == "done":
                continue
            existing_prompts = s_data.get("assets", {}).get("image_prompts", {})
            if force or not existing_prompts:
                scripts_needing_prompts.append(script_id)

        if scripts_needing_prompts:
            emit_log(
                f"[Phase 1/2] Pre-generating storyboard visual prompts for "
                f"{len(scripts_needing_prompts)} script(s) with single LLM session..."
            )
            ensure_llama_running()
            max_prompt_attempts = int(options.get("max_prompt_attempts", 3))

            for p_idx, s_id in enumerate(scripts_needing_prompts, start=1):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at prompt generation for '{s_id}'.")
                    break
                emit_log(f"  [{p_idx}/{len(scripts_needing_prompts)}] Crafting visual prompts for '{s_id}'...")
                s_data = sm.get_script_state(s_id)
                prompt_ok = False
                last_prompt_err = ""

                for attempt in range(1, max_prompt_attempts + 1):
                    if check_cancelled():
                        emit_log(f"Job cancelled by user during prompt generation for '{s_id}'.")
                        break
                    try:
                        if attempt > 1:
                            emit_log(f"  [{s_id}] Retrying prompt generation (attempt {attempt}/{max_prompt_attempts})...")
                        ensure_image_prompts_for_script(
                            script_data=s_data,
                            state_manager=sm,
                            prompt_builder=prompt_builder,
                            force=force,
                            base_dir=BASE_DIR,
                        )
                        fresh_state = sm.get_script_state(s_id)
                        fresh_prompts = fresh_state.get("assets", {}).get("image_prompts", {})
                        if not fresh_prompts:
                            raise ValueError(f"[{s_id}] No image prompts were saved in state.")

                        emit_log(f"  [{s_id}] ✓ Storyboard prompts saved.")
                        prompt_ok = True
                        break
                    except Exception as exc:
                        last_prompt_err = str(exc)
                        emit_log(f"  [{s_id}] Warning generating storyboard prompts (attempt {attempt}/{max_prompt_attempts}): {last_prompt_err}")
                        if attempt < max_prompt_attempts and not check_cancelled():
                            time.sleep(2.0)

                if not prompt_ok and not check_cancelled():
                    emit_log(f"  [{s_id}] ERROR: Storyboard prompt generation failed after {max_prompt_attempts} attempts: {last_prompt_err}")
                    prompt_failed_ids.add(s_id)
                    failed_ids.append(s_id)

            emit_log("[GPU Handoff] Stopping LLM server once to release ~2.0 GB VRAM for ComfyUI...")
            ensure_llama_stopped()
        else:
            emit_log("All scripts have complete visual prompts. Ensuring LLM is stopped for ComfyUI...")
            ensure_llama_stopped()

        if check_cancelled():
            return {
                "success_count": success_count,
                "failed_ids": failed_ids,
                "total": total,
            }

        # =========================================================================
        # PHASE 2: BATCH COMFYUI RENDERING (Pure GPU Rendering, Zero LLM Cycling)
        # =========================================================================
        workflow_path = Path(IMAGE_WORKFLOW_PATH)
        if not workflow_path.is_absolute():
            workflow_path = BASE_DIR / workflow_path

        emit_log(f"[Phase 2/2] Rendering illustrations in ComfyUI across {total} script(s)...")
        comfy_client = ImageComfyClient(
            api_url=COMFY_API_URL,
            workflow_path=workflow_path,
            poll_timeout=3600,
            poll_interval=2,
        )
        self._active_comfy_client = comfy_client

        try:
            for idx, script_id in enumerate(script_ids, start=1):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at script {script_id}.")
                    break

                emit_progress(idx - 1, total, script_id)

                if script_id in prompt_failed_ids:
                    emit_log(f"[{script_id}] Skipping ComfyUI rendering — storyboard prompt generation previously failed.")
                    continue

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

                script_force = force or (status.get("image_generation") == "pending")
                max_attempts = int(options.get("max_attempts", 3))
                images_succeeded = False
                last_err = ""

                for attempt in range(1, max_attempts + 1):
                    if check_cancelled():
                        emit_log(f"Job cancelled by user at script {script_id}.")
                        break

                    try:
                        emit_log(f"[{script_id}] Rendering scene illustrations in ComfyUI (attempt {attempt}/{max_attempts})...")
                        t0 = time.time()
                        ok = process_script(
                            script_data=script_data,
                            state_manager=sm,
                            comfy_client=comfy_client,
                            prompt_builder=prompt_builder,
                            force=script_force,
                            seed=seed,
                            base_dir=BASE_DIR,
                            check_cancelled=check_cancelled,
                        )
                        dur = time.time() - t0
                        if ok:
                            emit_log(f"[{script_id}] ✓ Scene images completed in {dur:.1f}s.")
                            success_count += 1
                            images_succeeded = True
                            break
                        else:
                            last_err = f"Process returned false after {dur:.1f}s"
                            emit_log(f"[{script_id}] Image attempt {attempt}/{max_attempts} failed.")
                            if attempt < max_attempts and not check_cancelled():
                                time.sleep(3.0)
                    except InterruptedError:
                        emit_log(f"[{script_id}] Generation interrupted by cancellation.")
                        break
                    except Exception as exc:
                        last_err = str(exc)
                        emit_log(f"[{script_id}] Image attempt {attempt}/{max_attempts} exception: {last_err}")
                        if attempt < max_attempts and not check_cancelled():
                            time.sleep(3.0)

                if not images_succeeded and not check_cancelled() and script_id not in failed_ids:
                    emit_log(f"[{script_id}] ERROR: Scene image generation failed after {max_attempts} attempts: {last_err}")
                    failed_ids.append(script_id)
        finally:
            self._active_comfy_client = None

        emit_progress(total, total, None)
        emit_log(f"Image job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

