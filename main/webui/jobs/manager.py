"""
webui/jobs/manager.py — Thread-safe Job Queue, Single-GPU Lane Worker, and WebSocket Dispatcher.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# pyrefly: ignore[missing-import]
from fastapi import WebSocket

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from webui.jobs.models import (
    JobCreateRequest,
    JobProgress,
    JobResponse,
    JobStage,
    JobStatus,
)
from webui.jobs.adapters.base import BaseStageAdapter
from webui.jobs.adapters.scripts import ScriptsAdapter
from webui.jobs.adapters.thumbnails import ThumbnailsAdapter
from webui.jobs.adapters.voice import VoiceAdapter
from webui.jobs.adapters.images import ImagesAdapter
from webui.jobs.adapters.assembly import AssemblyAdapter
from webui.jobs.adapters.chalkboard import ChalkboardAdapter
from webui.jobs.adapters.drive import DriveAdapter

logger = logging.getLogger("webui.jobs")


class _JobLogCapture:
    """Captures sys.stdout/sys.stderr within a worker job run and emits clean lines per thread."""

    def __init__(self, emit_fn: Callable[[str], None], original_stream):
        self.emit_fn = emit_fn
        self.original_stream = original_stream
        self._buffers: Dict[int, str] = {}
        self._lock = threading.Lock()

    def write(self, s: str) -> int:
        if not s:
            return 0

        tid = threading.get_ident()
        lines_to_emit: List[str] = []
        with self._lock:
            if self.original_stream:
                try:
                    self.original_stream.write(s)
                    self.original_stream.flush()
                except Exception:
                    pass

            buf = self._buffers.get(tid, "") + s
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                clean = line.replace("\r", " ").strip()
                # Ignore empty lines or long decorative divider lines (e.g. === or ---)
                if clean and not (clean.startswith("=") and clean.endswith("=") and len(clean) > 10):
                    lines_to_emit.append(clean)
            if buf:
                self._buffers[tid] = buf
            else:
                self._buffers.pop(tid, None)

        for clean in lines_to_emit:
            self.emit_fn(clean)
        return len(s)

    def flush(self) -> None:
        leftovers: List[str] = []
        with self._lock:
            for buf in self._buffers.values():
                if buf.strip():
                    clean = buf.replace("\r", " ").strip()
                    if clean and not (clean.startswith("=") and clean.endswith("=") and len(clean) > 10):
                        leftovers.append(clean)
            self._buffers.clear()
            if self.original_stream:
                try:
                    self.original_stream.flush()
                except Exception:
                    pass

        for clean in leftovers:
            self.emit_fn(clean)


class _JobLoggingHandler(logging.Handler):
    """Intercepts logging calls from underlying modules during a job run."""

    def __init__(self, emit_fn: Callable[[str], None]):
        super().__init__()
        self.emit_fn = emit_fn

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            clean = msg.replace("\r", " ").strip()
            if clean:
                self.emit_fn(clean)
        except Exception:
            pass


class JobManager:
    """
    Manages in-memory job queues and sequential worker execution.
    Guarantees a single GPU execution lane so multiple stages/jobs never contend for VRAM.
    """

    def __init__(self, base_dir=None, *, on_job_finished=None):
        self._on_job_finished = on_job_finished
        self._jobs: Dict[str, JobResponse] = {}
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._cancelled_jobs: Set[str] = set()
        self._current_job_id: Optional[str] = None
        self._lock = threading.Lock()
        self._closed = False

        # WebSocket subscribers: job_id -> set of (ws, loop)
        self._subscribers: Dict[str, Set[tuple[WebSocket, asyncio.AbstractEventLoop]]] = {}
        self._system_subscribers: Set[tuple[WebSocket, asyncio.AbstractEventLoop]] = set()

        # Registered stage adapters
        self._adapters: Dict[JobStage, BaseStageAdapter] = {
            JobStage.SCRIPTS: ScriptsAdapter(base_dir),
            JobStage.VOICE: VoiceAdapter(base_dir),
            JobStage.IMAGES: ImagesAdapter(base_dir),
            JobStage.THUMBNAILS: ThumbnailsAdapter(base_dir),
            JobStage.ASSEMBLY: AssemblyAdapter(base_dir),
            JobStage.CHALKBOARD: ChalkboardAdapter(base_dir),
            JobStage.DRIVE_UPLOAD: DriveAdapter(base_dir),
        }

        # Start background worker daemon
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def close(self) -> None:
        """Stop accepting work and let the current adapter unwind before shutdown."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            active_ids = [
                job_id for job_id, job in self._jobs.items()
                if job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
            ]
        for job_id in active_ids:
            self.cancel_job(job_id)
        self._queue.put(None)
        self._worker_thread.join(timeout=30)
        if self._worker_thread.is_alive():
            logger.warning("Production worker did not stop within 30 seconds.")

    def register_adapter(self, stage: JobStage, adapter: BaseStageAdapter) -> None:
        """Registers a stage execution adapter."""
        self._adapters[stage] = adapter

    def enqueue_job(self, request: JobCreateRequest) -> JobResponse:
        """Creates and enqueues a new workflow execution job."""
        job_id = str(uuid.uuid4())[:8].upper()
        initial_progress = JobProgress(
            current=0,
            total=len(request.script_ids),
            current_script=None,
            stage_label=request.stage.value.capitalize(),
        )

        job = JobResponse(
            job_id=job_id,
            stage=request.stage,
            status=JobStatus.QUEUED,
            script_ids=request.script_ids,
            options=request.options,
            progress=initial_progress,
            logs=[f"[{time.strftime('%H:%M:%S')}] Job enqueued for {len(request.script_ids)} script(s)."],
            created_at=time.time(),
        )

        with self._lock:
            if self._closed:
                raise RuntimeError("Production worker is closed.")
            self._jobs[job_id] = job
            self._queue.put(job_id)

        self._broadcast_job_event(job_id, {"type": "job_queued", "job": job.model_dump()})
        return job

    def get_job(self, job_id: str) -> Optional[JobResponse]:
        """Retrieves a job by its unique identifier."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[JobResponse]:
        """Lists recent jobs ordered by creation time descending."""
        with self._lock:
            sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return sorted_jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """Marks a queued or running job as cancelled."""
        adapter_to_cancel = None
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False

            self._cancelled_jobs.add(job_id)
            prev_status = job.status
            job.status = JobStatus.CANCELLED
            job.finished_at = time.time()
            if prev_status == JobStatus.QUEUED:
                job.logs.append(f"[{time.strftime('%H:%M:%S')}] Job cancelled while queued.")
            else:
                job.logs.append(f"[{time.strftime('%H:%M:%S')}] Job cancellation requested by user. Halting active tasks...")
                if self._current_job_id == job_id:
                    adapter_to_cancel = self._adapters.get(job.stage)

        if adapter_to_cancel and hasattr(adapter_to_cancel, "cancel"):
            try:
                adapter_to_cancel.cancel()
            except Exception as e:
                logger.warning(f"Error calling cancel() on adapter for stage '{job.stage}': {e}")

        self._broadcast_job_event(job_id, {"type": "job_cancelled", "job_id": job_id, "status": "cancelled"})
        return True

    def is_cancelled(self, job_id: str) -> bool:
        """Checks if a job was marked cancelled."""
        return job_id in self._cancelled_jobs

    # -------------------------------------------------------------------------
    # WebSocket Event Broadcasting
    # -------------------------------------------------------------------------

    def register_subscriber(self, job_id: str, ws: WebSocket, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Subscribes a WebSocket client to a specific job's live feed."""
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
        with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = set()
            self._subscribers[job_id].add((ws, loop))

    def remove_subscriber(self, job_id: str, ws: WebSocket) -> None:
        """Unsubscribes a WebSocket client from a job."""
        with self._lock:
            if job_id in self._subscribers:
                self._subscribers[job_id] = {item for item in self._subscribers[job_id] if item[0] != ws}

    def register_system_subscriber(self, ws: WebSocket, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Subscribes a WebSocket client to global system and queue events."""
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
        with self._lock:
            self._system_subscribers.add((ws, loop))

    def remove_system_subscriber(self, ws: WebSocket) -> None:
        """Unsubscribes a WebSocket client from system events."""
        with self._lock:
            self._system_subscribers = {item for item in self._system_subscribers if item[0] != ws}

    def _broadcast_job_event(self, job_id: str, event_data: Dict[str, Any]) -> None:
        """Dispatches an event payload to active job and system subscribers."""
        dead_items = []
        with self._lock:
            targets = list(self._subscribers.get(job_id, set())) + list(self._system_subscribers)

        for ws, loop in targets:
            try:
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(ws.send_json(event_data), loop)
            except Exception:
                dead_items.append((ws, loop))

        if dead_items:
            with self._lock:
                if job_id in self._subscribers:
                    for d in dead_items:
                        self._subscribers[job_id].discard(d)
                for d in dead_items:
                    self._system_subscribers.discard(d)

    # -------------------------------------------------------------------------
    # Single-GPU Execution Worker Loop
    # -------------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Sequential worker daemon that processes jobs one by one."""
        while True:
            job_id = self._queue.get()
            try:
                if job_id is None:
                    return

                with self._lock:
                    job = self._jobs.get(job_id)
                    if not job or job.status == JobStatus.CANCELLED:
                        continue

                    job.status = JobStatus.RUNNING
                    job.started_at = time.time()
                    self._current_job_id = job_id

                self._broadcast_job_event(job_id, {"type": "job_started", "job_id": job_id})
                self._execute_job(job)
                if self._on_job_finished:
                    self._on_job_finished()

            except Exception as exc:
                logger.error(f"[Worker Error] Unhandled exception in job loop: {exc}", exc_info=True)
            finally:
                with self._lock:
                    self._current_job_id = None
                self._queue.task_done()

    def _execute_job(self, job: JobResponse) -> None:
        """Executes a single job using its registered stage adapter."""
        job_id = job.job_id
        stage = job.stage
        adapter = self._adapters.get(stage)

        def emit_log(line: str) -> None:
            timestamped = f"[{time.strftime('%H:%M:%S')}] {line}"
            with self._lock:
                job.logs.append(timestamped)
                # Cap log history at 1000 lines
                if len(job.logs) > 1000:
                    job.logs.pop(0)
            self._broadcast_job_event(job_id, {"type": "job_log", "job_id": job_id, "log": timestamped})

        def emit_progress(current: int, total: int, current_script: Optional[str]) -> None:
            with self._lock:
                job.progress.current = current
                job.progress.total = total
                job.progress.current_script = current_script
            self._broadcast_job_event(
                job_id,
                {
                    "type": "job_progress",
                    "job_id": job_id,
                    "progress": job.progress.model_dump(),
                },
            )

        if not adapter:
            err = f"No execution adapter registered for stage '{stage.value}'."
            emit_log(f"ERROR: {err}")
            with self._lock:
                job.status = JobStatus.FAILED
                job.finished_at = time.time()
                job.error = err
            self._broadcast_job_event(job_id, {"type": "job_failed", "job_id": job_id, "error": err})
            return

        try:
            emit_log(f"Executing stage '{stage.value}'...")

            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            capture_stdout = _JobLogCapture(emit_log, orig_stdout)
            capture_stderr = _JobLogCapture(emit_log, orig_stderr)
            log_handler = _JobLoggingHandler(emit_log)
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)

            sys.stdout = capture_stdout
            sys.stderr = capture_stderr
            try:
                result = adapter.run(
                    script_ids=job.script_ids,
                    options=getattr(job, "options", {}) or {},
                    emit_log=emit_log,
                    emit_progress=emit_progress,
                    check_cancelled=lambda: self.is_cancelled(job_id),
                )
            finally:
                capture_stdout.flush()
                capture_stderr.flush()
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
                root_logger.removeHandler(log_handler)

            with self._lock:
                if self.is_cancelled(job_id):
                    job.status = JobStatus.CANCELLED
                elif result.get("failed_ids") and not result.get("success_count"):
                    job.status = JobStatus.FAILED
                    job.error = f"Failed for all script(s): {', '.join(result.get('failed_ids', []))}"
                else:
                    job.status = JobStatus.COMPLETED
                job.finished_at = time.time()

            event_type = "job_cancelled" if job.status == JobStatus.CANCELLED else ("job_completed" if job.status == JobStatus.COMPLETED else "job_failed")
            self._broadcast_job_event(job_id, {"type": event_type, "job_id": job_id, "result": result})

        except Exception as exc:
            with self._lock:
                cancelled = self.is_cancelled(job_id)
                job.status = JobStatus.CANCELLED if cancelled else JobStatus.FAILED
                job.finished_at = time.time()
                if not cancelled:
                    job.error = str(exc)
            if cancelled:
                emit_log("Job execution halted (cancelled by user).")
                self._broadcast_job_event(job_id, {"type": "job_cancelled", "job_id": job_id})
            else:
                emit_log(f"FATAL EXCEPTION: {exc}")
                self._broadcast_job_event(job_id, {"type": "job_failed", "job_id": job_id, "error": str(exc)})
