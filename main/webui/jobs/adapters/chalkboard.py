"""
webui/jobs/adapters/chalkboard.py — Game Chalkboard rendering adapter.
Renders high-resolution chalk typography on empty_chalkboard.png for Game scripts (G-series).
Requires zero LLM or ComfyUI services.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import (
    GAME_IMAGES_DIR,
    IMAGE_DEFAULT_WIDTH,
    IMAGE_DEFAULT_HEIGHT,
    get_script_output_dir,
)
from core.state_manager import StateManager, resolve_lang_and_type
from video_creation._C_image_generation.core.chalkboard_renderer import render_chalkboard_image
from webui.jobs.adapters.base import BaseStageAdapter


class ChalkboardAdapter(BaseStageAdapter):
    """Executes native chalk typography rendering on empty_chalkboard.png for Game scripts."""

    def run(
        self,
        script_ids: List[str],
        options: Dict[str, Any],
        emit_log: Callable[[str], None],
        emit_progress: Callable[[int, int, str], None],
        check_cancelled: Callable[[], bool],
    ) -> Dict[str, Any]:
        sm = StateManager(base_dir=BASE_DIR)
        force = options.get("force", True)

        total = len(script_ids)
        success_count = 0
        skipped_count = 0
        failed_ids = []

        empty_chalkboard_path = GAME_IMAGES_DIR / "empty_chalkboard.png"
        if not empty_chalkboard_path.exists():
            emit_log(f"ERROR: Base chalkboard template not found at {empty_chalkboard_path}.")
            return {
                "success_count": 0,
                "failed_ids": list(script_ids),
                "total": total,
            }

        emit_log(f"Starting Chalkboard Image Rendering for {total} script(s)...")

        for idx, script_id in enumerate(script_ids, start=1):
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            emit_progress(idx - 1, total, script_id)
            canonical_id = script_id.strip().upper()

            if not sm.script_exists(canonical_id):
                emit_log(f"[{canonical_id}] ERROR: Script state does not exist.")
                failed_ids.append(canonical_id)
                continue

            lang, video_type = resolve_lang_and_type(canonical_id)
            if video_type != "game":
                emit_log(f"[{canonical_id}] SKIPPED: Script is not a GAME video (video_type={video_type}). Chalkboards apply only to Game quizzes.")
                skipped_count += 1
                continue

            state_data = sm.get_script_state(canonical_id)
            content_meta = state_data.get("content_metadata") or {}
            exercise_text = (
                content_meta.get("chalkboard_exercise")
                or (content_meta.get("script", {}).get("challenge") if isinstance(content_meta.get("script"), dict) else None)
                or state_data.get("metadata", {}).get("chalkboard_exercise")
            )

            if not exercise_text or not str(exercise_text).strip():
                emit_log(f"[{canonical_id}] ERROR: Missing 'chalkboard_exercise' text. Please define chalkboard text first.")
                failed_ids.append(canonical_id)
                continue

            out_dir = get_script_output_dir(canonical_id, language=lang, base_dir=BASE_DIR) / "images"
            out_dir.mkdir(parents=True, exist_ok=True)
            dest_path = out_dir / f"script_{canonical_id}_challenge.png"

            if dest_path.exists() and not force:
                emit_log(f"[{canonical_id}] Chalkboard image already exists: {dest_path.name} — skipping (use force to overwrite).")
                success_count += 1
                continue

            max_attempts = int(options.get("max_attempts", 3))
            chalk_succeeded = False
            last_err = ""

            for attempt in range(1, max_attempts + 1):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at script {canonical_id}.")
                    break

                try:
                    emit_log(f"[{canonical_id}] Rendering high-resolution chalk typography (attempt {attempt}/{max_attempts})...")
                    t0 = time.time()
                    render_chalkboard_image(
                        empty_chalkboard_path=empty_chalkboard_path,
                        exercise_text=str(exercise_text).strip(),
                        dest_path=dest_path,
                        target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT),
                    )
                    dur = time.time() - t0

                    # Update assets in state
                    assets = state_data.setdefault("assets", {})
                    assets["image_dir"] = str(out_dir)
                    images_list = assets.get("images")
                    if not isinstance(images_list, list):
                        images_list = []
                    if str(dest_path) not in images_list:
                        images_list.append(str(dest_path))
                    assets["images"] = images_list

                    sm.save_script_state(canonical_id, state_data)

                    emit_log(f"[{canonical_id}] ✓ Chalkboard challenge image saved in {dur:.2f}s: {dest_path.name}")
                    success_count += 1
                    chalk_succeeded = True
                    break
                except Exception as exc:
                    last_err = str(exc)
                    emit_log(f"[{canonical_id}] Chalkboard attempt {attempt}/{max_attempts} error: {last_err}")
                    if attempt < max_attempts:
                        time.sleep(0.5)

            if not chalk_succeeded and not check_cancelled():
                emit_log(f"[{canonical_id}] ERROR: Chalkboard rendering failed after {max_attempts} attempts: {last_err}")
                failed_ids.append(canonical_id)

        emit_progress(total, total, None)
        emit_log(f"Chalkboard rendering finished: {success_count} succeeded, {skipped_count} skipped, {len(failed_ids)} failed.")

        return {
            "success_count": success_count,
            "skipped_count": skipped_count,
            "failed_ids": failed_ids,
            "total": total,
        }

