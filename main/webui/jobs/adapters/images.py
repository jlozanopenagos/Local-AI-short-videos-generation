"""
webui/jobs/adapters/images.py — Stage C (Scene Image Generation) adapter.
"""

from __future__ import annotations

import os
import random
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
from video_creation._C_image_generation.service import (
    ensure_image_prompts_for_script,
    process_script,
)
from webui.jobs.adapters.base import BaseStageAdapter


class ImagesAdapter(BaseStageAdapter):
    """Executes Stage C scene illustration generation with batched prompt pre-generation."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or BASE_DIR

    def run(
        self,
        script_ids: List[str],
        options: Dict[str, Any],
        emit_log: Callable[[str], None],
        emit_progress: Callable[[int, int, str], None],
        check_cancelled: Callable[[], bool],
    ) -> Dict[str, Any]:
        sm = StateManager(base_dir=self.base_dir)
        force = options.get("force", False)
        regenerate_prompts = options.get("regenerate_prompts", False)
        preserve_general_prompt = bool(options.get("preserve_general_prompt", False))
        raw_seed = options.get("seed")
        seed = int(raw_seed) if (raw_seed is not None and int(raw_seed) > 0) else None

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

        single_scene = options.get("scene") or options.get("scene_type")
        custom_prompt = options.get("prompt")

        # =========================================================================
        # PHASE 1: BATCH PROMPT GENERATION (Initialize LLM ONCE for all scripts)
        # =========================================================================
        scripts_needing_prompts = []
        if single_scene:
            emit_log(f"Single scene redo requested for '{single_scene}'. Skipping LLM batch prompt generation.")
            ensure_llama_stopped()
        else:
            for script_id in script_ids:
                if not sm.script_exists(script_id):
                    continue
                s_data = sm.get_script_state(script_id)
                status = s_data.get("status", {})
                if not (force or regenerate_prompts) and status.get("image_generation") == "done":
                    continue
                existing_gp = (s_data.get("assets", {}).get("general_prompt") or "").strip()
                existing_prompts = s_data.get("assets", {}).get("image_prompts", {})
                if force or regenerate_prompts or not existing_gp or not existing_prompts:
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
                            if preserve_general_prompt and (s_data.get("assets", {}).get("general_prompt") or "").strip():
                                emit_log(f"  [{s_id}] Preserving saved general prompt and regenerating scene-specific prompts...")
                            ensure_image_prompts_for_script(
                                script_data=s_data,
                                state_manager=sm,
                                prompt_builder=prompt_builder,
                                force=bool(force or regenerate_prompts),
                                base_dir=self.base_dir,
                                preserve_general_prompt=preserve_general_prompt,
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

            # Single scene execution branch
            if single_scene:
                sec_lower = str(single_scene).strip().lower()
                prompt_to_use = custom_prompt
                if not prompt_to_use:
                    prompts_map = script_data.get("assets", {}).get("image_prompts") or {}
                    visual_prompts = script_data.get("visual_prompts") or {}
                    prompt_to_use = (
                        prompts_map.get(sec_lower)
                        or prompts_map.get(single_scene)
                        or visual_prompts.get(sec_lower)
                        or visual_prompts.get(single_scene)
                    )

                if not prompt_to_use or not str(prompt_to_use).strip():
                    err = f"No prompt found for scene '{single_scene}' in script '{script_id}'."
                    emit_log(f"[{script_id}] ERROR: {err}")
                    failed_ids.append(script_id)
                    continue

                from config.settings import (
                    IMAGE_DEFAULT_STEPS,
                    IMAGE_DEFAULT_WIDTH,
                    IMAGE_DEFAULT_HEIGHT,
                    IMAGE_STALL_TIMEOUT,
                    get_script_output_dir,
                )
                from core.state_manager import resolve_lang_and_type
                from video_creation._C_image_generation.core.prompt_builder import sanitize_and_style_prompt

                lang, _ = resolve_lang_and_type(script_id, script_data)
                out_dir = get_script_output_dir(script_id, language=lang, base_dir=self.base_dir) / "images"
                out_dir.mkdir(parents=True, exist_ok=True)
                dest_path = out_dir / f"script_{script_id}_{sec_lower}.png"

                styled_prompt = sanitize_and_style_prompt(str(prompt_to_use).strip())
                img_seed = seed if seed > 0 else random.randint(1, 10**15)

                emit_log(f"[{script_id}] Rendering scene '{sec_lower}' illustration in ComfyUI (seed: {img_seed})...")
                t0 = time.time()
                try:
                    comfy_client.generate_image(
                        prompt_text=styled_prompt,
                        filename_prefix=f"Z-Image/script_{script_id}_{sec_lower}",
                        dest_path=dest_path,
                        seed=img_seed,
                        steps=IMAGE_DEFAULT_STEPS,
                        width=IMAGE_DEFAULT_WIDTH,
                        height=IMAGE_DEFAULT_HEIGHT,
                        stall_timeout=IMAGE_STALL_TIMEOUT,
                    )
                    dur = time.time() - t0
                    emit_log(f"[{script_id}] ✓ Scene '{sec_lower}' rendered successfully in {dur:.1f}s -> {dest_path.name}")

                    # Update script state & in-memory cache
                    assets = script_data.setdefault("assets", {})
                    img_prompts = assets.setdefault("image_prompts", {})
                    img_prompts[sec_lower] = str(prompt_to_use).strip()
                    assets["image_dir"] = str(out_dir)
                    img_list = assets.get("images")
                    if not isinstance(img_list, list):
                        img_list = []
                    dest_str = str(dest_path)
                    if dest_str not in img_list:
                        img_list.append(dest_str)
                    assets["images"] = img_list

                    sm.save_script_state(script_id, script_data)
                    from webui.routers.scripts import _update_cached_script
                    _update_cached_script(script_id, script_data)
                    success_count += 1
                except Exception as exc:
                    emit_log(f"[{script_id}] ERROR generating scene '{sec_lower}': {exc}")
                    failed_ids.append(script_id)
                continue

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
                        base_dir=self.base_dir,
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

        emit_progress(total, total, None)
        emit_log(f"Image job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

