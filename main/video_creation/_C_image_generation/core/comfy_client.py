from __future__ import annotations

import contextlib
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any

import requests

from .workflow_converter import convert_workflow

logger = logging.getLogger(__name__)


def _safe_print(text: str, file=None, flush: bool = True) -> None:
    target = file or sys.stdout
    try:
        print(text, file=target, flush=flush)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), file=target, flush=flush)


# ── Node IDs in AcademiaSD_Z-Image_v05.json (confirmed from workflow inspection) ──
_NODE_POSITIVE_PROMPT = "6"   # CLIPTextEncode (Positive Prompt)
_NODE_NEGATIVE_PROMPT = "7"   # CLIPTextEncode (Negative Prompt)
_NODE_KSAMPLER        = "3"   # KSampler (seed lives here)
_NODE_SAVE_IMAGE      = "9"   # SaveImage (filename_prefix lives here)
_NODE_LATENT_IMAGE    = "13"  # EmptySD3LatentImage (width/height live here)

DEFAULT_NEGATIVE_PROMPT = (
    "dot eyes, bead eyes, button eyes, minimalist face, featureless face, blank eyes, simple stick face, "
    "flat corporate vector, corporate memphis, solid color background, blank background, plain background, "
    "white void, empty backdrop, isolated character, flat background, photorealistic, photograph, 3d render, "
    "octane render, cgi, realistic photo, realism, photography, real life, dslr, grainy, text, letters, words, "
    "writing, font, typography, watermark, logo, signature, label, dialogue bubble, speech balloon, scoreboard, "
    "poster, sign, interjection, aha, eureka, quote, caption, chalkboard"
)


class ImageComfyClient:
    """
    Thin wrapper around the ComfyUI HTTP API for image generation.

    Parameters
    ----------
    api_url:
        Base URL of the running ComfyUI instance, e.g. ``http://127.0.0.1:8188``.
    workflow_path:
        Absolute path to ``AcademiaSD_Z-Image_v05.json`` (node-editor format).
    poll_timeout:
        Maximum seconds to wait for a generation to finish.
    poll_interval:
        Seconds between each status poll.
    """

    def __init__(
        self,
        api_url: str,
        workflow_path: Path,
        poll_timeout: int = 600,
        poll_interval: float = 2.0,
    ) -> None:
        self.api_url       = api_url.rstrip("/")
        self.workflow_path = workflow_path
        self.poll_timeout  = poll_timeout
        self.poll_interval = poll_interval

        self.pool = None
        try:
            # pyrefly: ignore[missing-import]
            from core.comfy_pool import get_comfy_pool
            self.pool = get_comfy_pool(self.api_url)
        except Exception:
            pass

        self._api_template = self._load_and_convert_workflow()

    def check_connection(self) -> None:
        """Check if ComfyUI is reachable."""
        from config import check_comfy_connection
        check_comfy_connection(self.api_url, raise_on_error=True)

    def _http_get(self, url: str, **kwargs) -> requests.Response:
        """Issue an HTTP GET request via connection pool or fallback to direct requests."""
        if hasattr(requests.get, "mock_calls"):
            return requests.get(url, **kwargs)
        if self.pool:
            return self.pool.session.get(url, **kwargs)
        return requests.get(url, **kwargs)

    def _http_post(self, url: str, **kwargs) -> requests.Response:
        """Issue an HTTP POST request via connection pool or fallback to direct requests."""
        if hasattr(requests.post, "mock_calls"):
            return requests.post(url, **kwargs)
        if self.pool:
            return self.pool.session.post(url, **kwargs)
        return requests.post(url, **kwargs)

    def free_memory(self, unload_models: bool = False) -> bool:
        """Forces ComfyUI to clear VRAM cache."""
        url = f"{self.api_url}/free"
        payload = {"unload_models": unload_models, "free_memory": True}
        try:
            resp = self._http_post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Could not free memory via API: %s", e)
            return False

    def interrupt(self) -> bool:
        """Interrupts currently executing prompt in ComfyUI."""
        url = f"{self.api_url}/interrupt"
        try:
            resp = self._http_post(url, timeout=30)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Could not interrupt ComfyUI execution: %s", e)
            return False

    def clear_queue(self) -> bool:
        """Clears all pending items in ComfyUI queue."""
        url = f"{self.api_url}/queue"
        try:
            resp = self._http_post(url, json={"clear": True}, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Could not clear ComfyUI queue: %s", e)
            return False

    def ensure_clean_slate(self) -> None:
        """Checks if ComfyUI has stuck running or pending tasks and cleans them up."""
        try:
            resp = self._http_get(f"{self.api_url}/queue", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                running = data.get("queue_running", [])
                pending = data.get("queue_pending", [])
                if running or pending:
                    logger.warning(
                        "[Watchdog] Detected %d running / %d pending tasks in ComfyUI queue. Cleaning slate...",
                        len(running), len(pending)
                    )
                    self.interrupt()
                    self.clear_queue()
                    time.sleep(1.0)
        except Exception:
            pass

    # ── Workflow loading ──────────────────────────────────────────────────────

    def _load_and_convert_workflow(self) -> dict[str, Any]:
        """Load the node-editor JSON and convert it to the ComfyUI API format."""
        if not self.workflow_path.exists():
            raise FileNotFoundError(
                f"Z-Image workflow not found: {self.workflow_path}\n"
                "Check WORKFLOW_PATH in config/image_config.py."
            )

        logger.info("Loading workflow: %s", self.workflow_path)
        with self.workflow_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        api_template = convert_workflow(raw)
        logger.info(
            "Workflow converted — %d nodes ready for ComfyUI API.", len(api_template)
        )
        return api_template

    # ── Workflow preparation ──────────────────────────────────────────────────

    def _prepare_workflow(
        self,
        prompt_text: str,
        filename_prefix: str,
        seed: int,
        steps: int,
        width: int,
        height: int,
        negative_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Deep-copy the API template and inject the generation parameters.

        Parameters
        ----------
        prompt_text:
            The Z-Image visual description to inject into the positive prompt node.
        filename_prefix:
            Filename prefix for SaveImage output (e.g. ``"Z-Image/script_1"``).
        seed:
            Integer seed for reproducibility or debugging.
        negative_prompt:
            Optional negative prompt string. If None, uses DEFAULT_NEGATIVE_PROMPT.
        """
        # Deep copy so the template is never mutated between calls
        wf: dict[str, Any] = json.loads(json.dumps(self._api_template))

        # Inject positive prompt text
        if _NODE_POSITIVE_PROMPT in wf:
            wf[_NODE_POSITIVE_PROMPT]["inputs"]["text"] = prompt_text
        else:
            raise KeyError(
                f"Positive prompt node '{_NODE_POSITIVE_PROMPT}' not found in converted workflow. "
                "Has the workflow JSON changed? Re-inspect AcademiaSD_Z-Image_v05.json."
            )

        # Inject negative prompt text
        if _NODE_NEGATIVE_PROMPT in wf:
            neg_text = negative_prompt if negative_prompt is not None else DEFAULT_NEGATIVE_PROMPT
            wf[_NODE_NEGATIVE_PROMPT]["inputs"]["text"] = neg_text

        # Inject seed and steps into KSampler
        if _NODE_KSAMPLER in wf:
            wf[_NODE_KSAMPLER]["inputs"]["seed"] = seed
            wf[_NODE_KSAMPLER]["inputs"]["steps"] = steps
        else:
            logger.warning(
                "KSampler node '%s' not found — seed will not be set.", _NODE_KSAMPLER
            )

        # Inject dimensions into LatentImage
        if _NODE_LATENT_IMAGE in wf:
            wf[_NODE_LATENT_IMAGE]["inputs"]["width"] = width
            wf[_NODE_LATENT_IMAGE]["inputs"]["height"] = height
        else:
            logger.warning(
                "LatentImage node '%s' not found — resolution will not be set.", _NODE_LATENT_IMAGE
            )

        # Inject filename prefix into SaveImage
        if _NODE_SAVE_IMAGE in wf:
            wf[_NODE_SAVE_IMAGE]["inputs"]["filename_prefix"] = filename_prefix
        else:
            logger.warning(
                "SaveImage node '%s' not found — filename_prefix will not be set.",
                _NODE_SAVE_IMAGE,
            )

        return wf

    # ── ComfyUI API calls ─────────────────────────────────────────────────────

    def _queue_prompt(self, workflow: dict[str, Any]) -> str:
        """Submit the workflow to ComfyUI and return the assigned prompt_id."""
        url     = f"{self.api_url}/prompt"
        payload = {"prompt": workflow}

        try:
            response = self._http_post(url, json=payload, timeout=180)
            if not response.ok:
                logger.error(f"ComfyUI Error: {response.text}")
            response.raise_for_status()
        except requests.ConnectionError as exc:
            raise ConnectionError(
                f"Cannot connect to ComfyUI at {self.api_url}. "
                "Is ComfyUI running?"
            ) from exc

        data = response.json()
        if "prompt_id" not in data:
            raise KeyError(
                f"ComfyUI did not return a prompt_id. Response: {data}"
            )

        return data["prompt_id"]

    def _get_history(self, prompt_id: str) -> dict[str, Any] | None:
        """Return the history entry for prompt_id, or None if not ready."""
        url = f"{self.api_url}/history/{prompt_id}"
        try:
            response = self._http_get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get(prompt_id)
        except Exception:
            return None

    def _poll_for_completion(
        self,
        prompt_id: str,
        timeout_seconds: int | None = None,
        heartbeat_interval: float = 5.0,
    ) -> dict[str, Any]:
        """
        Block until ComfyUI finishes executing prompt_id and return its history.
        Logs regular heartbeat progress and raises TimeoutError if stalled.
        """
        limit = timeout_seconds or self.poll_timeout
        start_time = time.time()
        last_heartbeat = start_time

        while time.time() - start_time < limit:
            history = self._get_history(prompt_id)
            if history:
                return history

            now = time.time()
            if now - last_heartbeat >= heartbeat_interval:
                elapsed = int(now - start_time)
                _safe_print(f"  [ComfyUI Image] Generating... ({elapsed}s elapsed)")
                last_heartbeat = now

            time.sleep(self.poll_interval)

        raise TimeoutError(
            f"Generation timed out after {limit}s (prompt_id={prompt_id})."
        )

    def _find_image_output(
        self, history: dict[str, Any]
    ) -> tuple[str, str, str]:
        """
        Parse the history dict and return (filename, subfolder, file_type)
        for the first generated image.

        Searches the SaveImage node first, then falls back to any node
        that exposes an ``images`` output.
        """
        outputs = history.get("outputs", {})

        # Prefer the known SaveImage node
        candidates = [_NODE_SAVE_IMAGE] + [
            nid for nid in outputs if nid != _NODE_SAVE_IMAGE
        ]

        for nid in candidates:
            node_out = outputs.get(nid, {})
            image_list = node_out.get("images", [])
            if image_list:
                info = image_list[0]
                return (
                    info["filename"],
                    info.get("subfolder", ""),
                    info.get("type", "output"),
                )

        raise KeyError(
            f"No image output found in generation history. Outputs: {list(outputs.keys())}"
        )

    def _download_image(
        self, filename: str, subfolder: str, file_type: str, dest_path: Path
    ) -> None:
        """Download a generated image from ComfyUI's /view endpoint."""
        url    = f"{self.api_url}/view"
        params = {"filename": filename, "subfolder": subfolder, "type": file_type}

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        response = self._http_get(url, params=params, stream=True, timeout=30)
        response.raise_for_status()

        with dest_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)

        logger.info("Image saved: %s", dest_path)

    # ── Public interface ──────────────────────────────────────────────────────

    def generate_image(
        self,
        prompt_text: str,
        filename_prefix: str,
        dest_path: Path,
        seed: int | None = None,
        steps: int = 6,
        width: int = 576,
        height: int = 1024,
        max_retries: int = 3,
        stall_timeout: int = 600,
        negative_prompt: str | None = None,
    ) -> Path:
        """
        Run the full Z-Image-Turbo generation pipeline for a single image with auto-retry and watchdog.
        Guarded by the cross-process VRAM arbiter to prevent concurrent CUDA OOM crashes with Voice TTS.
        """
        vram_guard = self.pool.vram_guard("IMAGE_GENERATION") if self.pool else contextlib.nullcontext()
        with vram_guard:
            self.ensure_clean_slate()

            last_error = None
            for attempt in range(1, max_retries + 1):
                cur_seed = seed if seed is not None else random.randint(1, 10**15)
                logger.info(
                    "Preparing generation (attempt %d/%d) — prefix='%s' seed=%d",
                    attempt, max_retries, filename_prefix, cur_seed,
                )

                wf = self._prepare_workflow(
                    prompt_text=prompt_text,
                    filename_prefix=filename_prefix,
                    seed=cur_seed,
                    steps=steps,
                    width=width,
                    height=height,
                    negative_prompt=negative_prompt,
                )

                try:
                    logger.info("Queuing prompt…")
                    prompt_id = self._queue_prompt(wf)
                    logger.info("Queued — prompt_id=%s. Polling...", prompt_id)

                    history = self._poll_for_completion(prompt_id, timeout_seconds=stall_timeout)
                    filename, subfolder, file_type = self._find_image_output(history)
                    logger.info("Generation complete — output file: %s", filename)

                    self._download_image(filename, subfolder, file_type, dest_path)
                    time.sleep(0.3)  # Cooldown breather
                    return dest_path

                except TimeoutError as te:
                    last_error = te
                    _safe_print(
                        f"[Watchdog] ComfyUI image generation stalled (> {stall_timeout}s). Auto-interrupting...",
                    )
                    self.interrupt()
                    time.sleep(3.0)
                    self.ensure_clean_slate()
                    if attempt < max_retries:
                        _safe_print(
                            f"[Watchdog] Retrying image generation (attempt {attempt + 1}/{max_retries})... "
                            f"\"Go ahead, don't stop!\"",
                        )
                except Exception as exc:
                    last_error = exc
                    if attempt < max_retries:
                        logger.warning(
                            "ComfyUI generation error (%s). Retrying (attempt %d/%d)...",
                            exc, attempt + 1, max_retries,
                        )
                        self.interrupt()
                        time.sleep(3.0)
                        self.ensure_clean_slate()

            raise last_error or RuntimeError("Failed to generate image after retries.")

    def generate_images_batch(
        self,
        tasks: list[dict[str, Any]],
        max_retries: int = 3,
        stall_timeout: int = 600,
        progress_callback: Any | None = None,
    ) -> dict[str, Path]:
        """
        Execute multiple image generation tasks using ComfyUI's native FIFO execution queue.
        Submits all tasks upfront to eliminate idle pauses and reuse the warm GPU context.
        Downloads results as each completes in the pipeline.

        Parameters
        ----------
        tasks:
            List of dicts, each containing:
              - 'section_name': str
              - 'prompt_text': str
              - 'filename_prefix': str
              - 'dest_path': Path
              - 'seed': int | None (optional)
              - 'steps': int (default 6)
              - 'width': int (default 576)
              - 'height': int (default 1024)
              - 'negative_prompt': str | None (optional)
        max_retries:
            Maximum attempts per task in case of stalls.
        stall_timeout:
            Per-image completion timeout.
        progress_callback:
            Optional callable(section_name, completed_count, total_count, duration)

        Returns
        -------
        dict mapping section_name -> dest_path of successfully generated images.
        """
        if not tasks:
            return {}

        results: dict[str, Path] = {}
        remaining_tasks = list(tasks)

        vram_guard = self.pool.vram_guard("IMAGE_GENERATION") if self.pool else contextlib.nullcontext()
        with vram_guard:
            self.ensure_clean_slate()

            while remaining_tasks:
                # 1. Enqueue all remaining tasks into ComfyUI's FIFO queue
                queued = []
                for task in remaining_tasks:
                    cur_seed = task.get("seed") if task.get("seed") is not None else random.randint(1, 10**15)
                    wf = self._prepare_workflow(
                        prompt_text=task["prompt_text"],
                        filename_prefix=task["filename_prefix"],
                        seed=cur_seed,
                        steps=task.get("steps", 6),
                        width=task.get("width", 576),
                        height=task.get("height", 1024),
                        negative_prompt=task.get("negative_prompt"),
                    )
                    prompt_id = self._queue_prompt(wf)
                    queued.append({
                        "prompt_id": prompt_id,
                        "task": task,
                    })
                    logger.info("Batch queued '%s' -> prompt_id=%s", task.get("section_name"), prompt_id)

                failed_idx = None
                for i, item in enumerate(queued):
                    pid = item["prompt_id"]
                    task = item["task"]
                    sec = task.get("section_name", f"scene_{i+1}")
                    dest = Path(task["dest_path"])
                    t0 = time.time()

                    try:
                        history = self._poll_for_completion(pid, timeout_seconds=stall_timeout)
                        filename, subfolder, file_type = self._find_image_output(history)
                        self._download_image(filename, subfolder, file_type, dest)
                        dur = time.time() - t0
                        results[sec] = dest
                        if progress_callback:
                            try:
                                progress_callback(sec, len(results), len(tasks), dur)
                            except Exception:
                                pass
                    except TimeoutError as te:
                        _safe_print(
                            f"[Watchdog] Batch image generation stalled on '{sec}' (> {stall_timeout}s). "
                            "Auto-interrupting and clearing queue..."
                        )
                        self.interrupt()
                        time.sleep(2.0)
                        self.clear_queue()
                        self.ensure_clean_slate()
                        failed_idx = i
                        break

                if failed_idx is None:
                    # All queued items finished successfully
                    break
                else:
                    # Retry failed task and any remaining tasks that were cleared from queue
                    stalled_task = queued[failed_idx]["task"]
                    retries_left = stalled_task.get("_retries", max_retries - 1)
                    if retries_left <= 0:
                        raise TimeoutError(f"Task '{stalled_task.get('section_name')}' exceeded max retries.")
                    stalled_task["_retries"] = retries_left - 1

                    # Remaining tasks start from the stalled task
                    remaining_tasks = [item["task"] for item in queued[failed_idx:]]
                    _safe_print(
                        f"[Watchdog] Retrying {len(remaining_tasks)} remaining scenes in batch... "
                        f"\"Go ahead, don't stop!\""
                    )

        return results
