"""
webui/jobs/adapters/assembly.py — Stage G (Video Assembly) adapter for batch & mass video production.
Supports upfront pre-flight validation, automatic reuse of up-to-date subtitles in mass batches,
and a producer-consumer parallel FFmpeg worker pool while preserving single-ID behavior.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import get_script_output_dir
from core.state_manager import StateManager
from video_creation._G_video_assembly.service import (
    process_script,
    resolve_assembly_prerequisites,
)
from video_creation._G_video_assembly.core.transcriber import Transcriber
from video_creation._G_video_assembly.core.subtitle_builder import SubtitleBuilder
from video_creation._G_video_assembly.core.video_assembler import VideoAssembler
from webui.jobs.adapters.base import BaseStageAdapter


class _LockedTranscriber:
    """Serializes calls to a single shared Whisper Transcriber across parallel assembly workers."""

    def __init__(self, transcriber: Any, lock: threading.Lock):
        self._transcriber = transcriber
        self._lock = lock

    def transcribe(self, *args, **kwargs):
        with self._lock:
            return self._transcriber.transcribe(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._transcriber, name)


class _ThreadSafeStateManager:
    """Thread-safe proxy around StateManager for concurrent mass assembly workers."""

    def __init__(self, state_manager: StateManager, lock: threading.Lock):
        self._sm = state_manager
        self._lock = lock

    def script_exists(self, script_id: str) -> bool:
        with self._lock:
            return self._sm.script_exists(script_id)

    def get_script_state(self, script_id: str) -> dict:
        with self._lock:
            return self._sm.get_script_state(script_id)

    def save_script_state(self, script_id: str, data: dict) -> Any:
        with self._lock:
            return self._sm.save_script_state(script_id, data)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sm, name)


def _has_fresh_subtitles(script_id: str, script_data: dict, base_dir: Path) -> bool:
    """Returns True when a non-empty `.ass` subtitle file exists and is at least as new as the master WAV."""
    try:
        label = (
            script_data.get("metadata", {}).get("LABEL")
            or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE", "english")
        )
        script_output_dir = get_script_output_dir(script_id, label, base_dir)
        ass_path = script_output_dir / f"script_{script_id}_subtitles.ass"
        if not ass_path.is_file() or ass_path.stat().st_size <= 0:
            return False

        audio_path_str = script_data.get("assets", {}).get("audio_path")
        audio_path = Path(audio_path_str) if audio_path_str else None
        if audio_path is None or not audio_path.is_file():
            audio_path = script_output_dir / f"script_{script_id}_master.wav"
        if not audio_path.is_file():
            return False

        return ass_path.stat().st_mtime >= audio_path.stat().st_mtime
    except Exception:
        return False


class AssemblyAdapter(BaseStageAdapter):
    """Executes Stage G mass video assembly."""

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
        skip_existing = bool(options.get("skip_existing", False))
        force = not skip_existing
        keep_subtitles = bool(options.get("keep_subtitles", False))
        force_subtitles = bool(options.get("force_subtitles", False))
        has_explicit_auto = "auto_keep_subtitles" in options
        auto_keep_subtitles = bool(options.get("auto_keep_subtitles", True))
        max_attempts = int(options.get("max_attempts", 3))

        default_workers = max(1, int(os.getenv("ASSEMBLY_MAX_WORKERS", "3")))
        requested_workers = max(1, int(options.get("workers", default_workers)))

        total = len(script_ids)
        success_count = 0
        failed_ids: List[str] = []

        emit_log(f"Starting forced Video Assembly for {total} script(s)...")

        # Phase 0: Upfront pre-flight validation before loading heavy Whisper/FFmpeg engines
        preflight_ready: List[tuple[str, dict]] = []
        skipped_or_failed = 0

        for script_id in script_ids:
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            if not sm.script_exists(script_id):
                emit_log(f"[{script_id}] ERROR: Script state does not exist.")
                failed_ids.append(script_id)
                skipped_or_failed += 1
                continue

            script_data = sm.get_script_state(script_id)
            status = script_data.get("status", {})

            if not force and status.get("video_assembly") == "done":
                emit_log(f"[{script_id}] Video already assembled — skipping.")
                success_count += 1
                skipped_or_failed += 1
                continue

            has_voice, has_images, _, _ = resolve_assembly_prerequisites(
                script_data, base_dir=self.base_dir
            )
            if not has_voice or not has_images:
                missing = []
                if not has_voice:
                    missing.append("Voice Audio (Stage B)")
                if not has_images:
                    missing.append("Images (Stage C)")
                emit_log(f"[{script_id}] Skipping assembly — prerequisites missing: {', '.join(missing)}.")
                failed_ids.append(script_id)
                skipped_or_failed += 1
                continue

            if status.get("voice_generation") != "done":
                emit_log(
                    f"[{script_id}] Notice: voice_generation is '{status.get('voice_generation', 'missing')}' "
                    "in state, but audio/timings exist on disk — proceeding."
                )
            if status.get("image_generation") != "done":
                emit_log(
                    f"[{script_id}] Notice: image_generation is '{status.get('image_generation', 'missing')}' "
                    "in state, but scene images exist on disk — proceeding."
                )

            preflight_ready.append((script_id, script_data))

        if not preflight_ready or check_cancelled():
            emit_progress(total, total, None)
            emit_log(f"Assembly job finished: {success_count}/{total} successful.")
            return {
                "success_count": success_count,
                "failed_ids": failed_ids,
                "total": total,
            }

        is_mass_batch = len(preflight_ready) >= 2 and requested_workers > 1
        use_auto_reuse = auto_keep_subtitles and (is_mass_batch or (has_explicit_auto and auto_keep_subtitles))

        runnable_items: List[Tuple[str, dict, bool]] = []
        for script_id, script_data in preflight_ready:
            if keep_subtitles:
                regen_subs = False
            elif force_subtitles:
                regen_subs = True
            elif use_auto_reuse and _has_fresh_subtitles(script_id, script_data, self.base_dir):
                regen_subs = False
                emit_log(f"[{script_id}] Reusing up-to-date subtitles (newer than master audio).")
            else:
                regen_subs = True
            runnable_items.append((script_id, script_data, regen_subs))

        worker_count = min(requested_workers, len(runnable_items)) if is_mass_batch else 1
        any_needs_subs = any(regen for _, _, regen in runnable_items)

        # Instantiate core assembly engines only when needed, sized for parallel execution
        transcriber: Optional[Any] = None
        builder: Optional[SubtitleBuilder] = None
        assembler: Optional[VideoAssembler] = None
        try:
            if any_needs_subs:
                emit_log("Initializing Video Assembly engines (Whisper transcriber, ASS builder, FFmpeg assembler)...")
                transcriber = Transcriber()
                builder = SubtitleBuilder()
            else:
                emit_log("All ready scripts have up-to-date subtitles — skipping Whisper model load.")
                emit_log("Initializing FFmpeg Video Assembler...")

            if worker_count > 1:
                per_worker_threads = max(2, (os.cpu_count() or 4) // worker_count)
                assembler = VideoAssembler(ffmpeg_threads=per_worker_threads)
            else:
                assembler = VideoAssembler()
            emit_log("✓ Assembly engines initialized.")
        except Exception as init_exc:
            emit_log(f"Warning: Engine pre-initialization notice: {init_exc}. Will fall back to per-script init if needed.")

        def _assemble_one(
            script_id: str,
            script_data: dict,
            script_regen_subs: bool,
            active_sm: Any,
            active_transcriber: Any,
        ) -> bool:
            last_err = ""
            for attempt in range(1, max_attempts + 1):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at script {script_id}.")
                    return False

                try:
                    emit_log(
                        f"[{script_id}] Assembling short video (subtitles, audio, visuals, closure) "
                        f"(attempt {attempt}/{max_attempts})..."
                    )
                    t0 = time.time()
                    ok = process_script(
                        script_data=script_data,
                        state_manager=active_sm,
                        transcriber=active_transcriber,
                        builder=builder,
                        assembler=assembler,
                        base_dir=self.base_dir,
                        regenerate_subtitles=script_regen_subs,
                        auto=True,
                    )
                    dur = time.time() - t0
                    if ok:
                        emit_log(f"[{script_id}] ✓ Video assembly completed in {dur:.1f}s.")
                        return True

                    last_err = f"Assembly returned false after {dur:.1f}s"
                    emit_log(f"[{script_id}] Video assembly attempt {attempt}/{max_attempts} failed.")
                    if attempt < max_attempts:
                        time.sleep(2.0)
                except Exception as exc:
                    last_err = str(exc)
                    emit_log(f"[{script_id}] Video assembly attempt {attempt}/{max_attempts} exception: {last_err}")
                    if attempt < max_attempts:
                        time.sleep(2.0)

            if not check_cancelled():
                emit_log(f"[{script_id}] ERROR: Video assembly failed after {max_attempts} attempts: {last_err}")
            return False

        if worker_count <= 1:
            for offset_idx, (script_id, script_data, script_regen_subs) in enumerate(runnable_items):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at script {script_id}.")
                    break
                emit_progress(skipped_or_failed + offset_idx, total, script_id)
                if _assemble_one(script_id, script_data, script_regen_subs, sm, transcriber):
                    success_count += 1
                elif not check_cancelled():
                    failed_ids.append(script_id)
        else:
            emit_log(
                f"Running mass Video Assembly with {worker_count} parallel worker(s) "
                f"for {len(runnable_items)} ready script(s)..."
            )
            shared_transcriber = (
                _LockedTranscriber(transcriber, threading.Lock())
                if transcriber is not None
                else None
            )
            shared_sm = _ThreadSafeStateManager(sm, threading.Lock())
            completed_done = skipped_or_failed
            failed_set: set[str] = set()
            progress_lock = threading.Lock()

            def _worker_task(item: Tuple[str, dict, bool]) -> Tuple[str, bool]:
                s_id, s_data, s_regen = item
                ok = _assemble_one(s_id, s_data, s_regen, shared_sm, shared_transcriber)
                with progress_lock:
                    nonlocal completed_done, success_count
                    if ok:
                        success_count += 1
                    elif not check_cancelled():
                        failed_set.add(s_id)
                    completed_done += 1
                    emit_progress(completed_done, total, s_id)
                return s_id, ok

            emit_progress(completed_done, total, runnable_items[0][0])
            pending_iter = iter(runnable_items)
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                in_flight = set()
                for _ in range(worker_count):
                    item = next(pending_iter, None)
                    if item is None or check_cancelled():
                        break
                    in_flight.add(executor.submit(_worker_task, item))

                while in_flight:
                    done_futs, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                    for fut in done_futs:
                        fut.result()
                    if not check_cancelled():
                        while len(in_flight) < worker_count:
                            nxt = next(pending_iter, None)
                            if nxt is None or check_cancelled():
                                break
                            in_flight.add(executor.submit(_worker_task, nxt))

            for script_id, _, _ in runnable_items:
                if script_id in failed_set:
                    failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Assembly job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }
