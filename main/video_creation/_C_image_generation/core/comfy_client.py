"""
comfy_client.py — ComfyUI API client for Z-Image-Turbo image generation.

Mirrors the architecture of _B_voice_generation/core/comfy_client.py
but is specialised for image workflows:
  - Loads and converts the node-editor workflow JSON at startup
  - Injects: positive prompt text, seed, filename prefix
  - Polls for completion
  - Downloads the generated image via /view
"""

from __future__ import annotations

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


# ── Node IDs in AcademiaSD_Z-Image.json (confirmed from workflow inspection) ──
_NODE_POSITIVE_PROMPT = "6"   # CLIPTextEncode (Positive Prompt)
_NODE_KSAMPLER        = "3"   # KSampler (seed lives here)
_NODE_SAVE_IMAGE      = "9"   # SaveImage (filename_prefix lives here)
_NODE_LATENT_IMAGE    = "13"  # EmptySD3LatentImage (width/height live here)


class ImageComfyClient:
    """
    Thin wrapper around the ComfyUI HTTP API for image generation.

    Parameters
    ----------
    api_url:
        Base URL of the running ComfyUI instance, e.g. ``http://127.0.0.1:8188``.
    workflow_path:
        Absolute path to ``AcademiaSD_Z-Image.json`` (node-editor format).
    poll_timeout:
        Maximum seconds to wait for a generation to finish.
    poll_interval:
        Seconds between each status poll.
    """

    def __init__(
        self,
        api_url: str,
        workflow_path: Path,
        poll_timeout: int = 180,
        poll_interval: float = 2.0,
    ) -> None:
        self.api_url       = api_url.rstrip("/")
        self.workflow_path = workflow_path
        self.poll_timeout  = poll_timeout
        self.poll_interval = poll_interval

        self._api_template = self._load_and_convert_workflow()

    def check_connection(self) -> None:
        """Check if ComfyUI is reachable."""
        from config import check_comfy_connection
        check_comfy_connection(self.api_url, raise_on_error=True)

    def free_memory(self, unload_models: bool = False) -> bool:
        """Forces ComfyUI to clear VRAM cache."""
        url = f"{self.api_url}/free"
        payload = {"unload_models": unload_models, "free_memory": True}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Could not free memory via API: %s", e)
            return False

    def interrupt(self) -> bool:
        """Interrupts currently executing prompt in ComfyUI."""
        url = f"{self.api_url}/interrupt"
        try:
            resp = requests.post(url, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Could not interrupt ComfyUI execution: %s", e)
            return False

    def clear_queue(self) -> bool:
        """Clears all pending items in ComfyUI queue."""
        url = f"{self.api_url}/queue"
        try:
            resp = requests.post(url, json={"clear": True}, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Could not clear ComfyUI queue: %s", e)
            return False

    def ensure_clean_slate(self) -> None:
        """Checks if ComfyUI has stuck running or pending tasks and cleans them up."""
        try:
            resp = requests.get(f"{self.api_url}/queue", timeout=15)
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
        """
        # Deep copy so the template is never mutated between calls
        wf: dict[str, Any] = json.loads(json.dumps(self._api_template))

        # Inject positive prompt text
        if _NODE_POSITIVE_PROMPT in wf:
            wf[_NODE_POSITIVE_PROMPT]["inputs"]["text"] = prompt_text
        else:
            raise KeyError(
                f"Positive prompt node '{_NODE_POSITIVE_PROMPT}' not found in converted workflow. "
                "Has the workflow JSON changed? Re-inspect AcademiaSD_Z-Image.json."
            )

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
            response = requests.post(url, json=payload, timeout=120)
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
            response = requests.get(url, timeout=30)
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

        response = requests.get(url, params=params, stream=True, timeout=30)
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
        stall_timeout: int = 90,
    ) -> Path:
        """
        Run the full Z-Image-Turbo generation pipeline for a single image with auto-retry and watchdog.
        """
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
                time.sleep(1.5)
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
                    time.sleep(1.5)

        raise last_error or RuntimeError("Failed to generate image after retries.")


# ── Node IDs for flux1_dev_uso_reference_image_gen.json (API format) ──────────
_FLUX_NODE_POSITIVE_PROMPT = "112:6"
_FLUX_NODE_KSAMPLER        = "112:31"
_FLUX_NODE_SAVE_IMAGE      = "9"
_FLUX_NODE_LATENT_IMAGE    = "112:110"
_FLUX_NODE_LOAD_IMAGE      = "47"


class ChalkboardComfyClient(ImageComfyClient):
    """
    ComfyUI client tailored for the Flux Reference Image workflow (chalkboard generation).
    """
    def __init__(
        self,
        api_url: str,
        workflow_path: Path,
        comfy_input_dir: Path,
        poll_timeout: int = 1200,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(api_url, workflow_path, poll_timeout, poll_interval)
        self.comfy_input_dir = comfy_input_dir

    def _prepare_flux_workflow(
        self,
        prompt_text: str,
        filename_prefix: str,
        reference_image_name: str,
        seed: int,
        steps: int,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        with self.workflow_path.open("r", encoding="utf-8") as fh:
            wf = json.load(fh)

        if _FLUX_NODE_POSITIVE_PROMPT in wf:
            wf[_FLUX_NODE_POSITIVE_PROMPT]["inputs"]["text"] = prompt_text
        if _FLUX_NODE_KSAMPLER in wf:
            wf[_FLUX_NODE_KSAMPLER]["inputs"]["seed"] = seed
            wf[_FLUX_NODE_KSAMPLER]["inputs"]["steps"] = steps
        if _FLUX_NODE_LATENT_IMAGE in wf:
            wf[_FLUX_NODE_LATENT_IMAGE]["inputs"]["width"] = width
            wf[_FLUX_NODE_LATENT_IMAGE]["inputs"]["height"] = height
        if _FLUX_NODE_SAVE_IMAGE in wf:
            wf[_FLUX_NODE_SAVE_IMAGE]["inputs"]["filename_prefix"] = filename_prefix
        if _FLUX_NODE_LOAD_IMAGE in wf:
            wf[_FLUX_NODE_LOAD_IMAGE]["inputs"]["image"] = reference_image_name

        return wf

    def generate_chalkboard(
        self,
        prompt_text: str,
        filename_prefix: str,
        dest_path: Path,
        reference_image_path: Path,
        seed: int | None = None,
        steps: int = 20,
        width: int = 576,
        height: int = 1024,
        max_retries: int = 3,
        stall_timeout: int = 240,
    ) -> Path:
        import shutil

        self.ensure_clean_slate()

        last_error = None
        for attempt in range(1, max_retries + 1):
            cur_seed = seed if seed is not None else random.randint(1, 10**15)

            ref_name = f"ref_{reference_image_path.name}"
            comfy_input_path = self.comfy_input_dir / ref_name
            shutil.copy2(reference_image_path, comfy_input_path)

            wf = self._prepare_flux_workflow(
                prompt_text=prompt_text,
                filename_prefix=filename_prefix,
                reference_image_name=ref_name,
                seed=cur_seed,
                steps=steps,
                width=width,
                height=height,
            )

            try:
                prompt_id = self._queue_prompt(wf)
                history = self._poll_for_completion(prompt_id, timeout_seconds=stall_timeout)

                filename, subfolder, file_type = self._find_image_output(history)
                self._download_image(filename, subfolder, file_type, dest_path)

                try:
                    if comfy_input_path.exists():
                        comfy_input_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete temp reference image {comfy_input_path}: {e}")

                time.sleep(0.3)
                return dest_path

            except TimeoutError as te:
                last_error = te
                _safe_print(
                    f"[Watchdog] ComfyUI chalkboard generation stalled (> {stall_timeout}s). Auto-interrupting...",
                )
                self.interrupt()
                time.sleep(1.5)
                if attempt < max_retries:
                    _safe_print(
                        f"[Watchdog] Retrying chalkboard generation (attempt {attempt + 1}/{max_retries})... "
                        f"\"Go ahead, don't stop!\"",
                    )
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    logger.warning(
                        "ComfyUI chalkboard error (%s). Retrying (attempt %d/%d)...",
                        exc, attempt + 1, max_retries,
                    )
                    self.interrupt()
                    time.sleep(1.5)

        raise last_error or RuntimeError("Failed to generate chalkboard image after retries.")

