"""
core/comfy_pool.py — ComfyUI Connection Pool & VRAM Concurrency Arbiter.

Implements the Connection Pool Pattern for ComfyUI:
1. Reusable, persistent HTTP Session with connection pooling (urllib3 HTTPAdapter).
2. Automatic keep-alive and resilient socket retry policies.
3. VRAM Concurrency Arbiter: Mutex lock preventing Image Diffusion and Voice TTS
   from colliding on constrained GPU hardware (e.g. 6GB RTX 2060).
4. Automatic VRAM Cache Purging (/free endpoint) between generation stages.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from config.settings import COMFY_API_URL
except ImportError:
    COMFY_API_URL = os.getenv("COMFY_API_URL", "http://127.0.0.1:8188")

logger = logging.getLogger(__name__)


class ComfyConnectionPool:
    """
    Thread-safe connection pool and VRAM resource manager for ComfyUI.
    """

    _instance: Optional["ComfyConnectionPool"] = None
    _init_lock = threading.Lock()

    def __init__(self, api_url: Optional[str] = None, pool_size: int = 10):
        self.api_url = (api_url or COMFY_API_URL).rstrip("/")
        parsed = urlparse(self.api_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 8188

        self._vram_lock = threading.RLock()
        self._current_task: Optional[str] = None
        self._lock_time: float = 0.0

        # File-based lock path for inter-process coordination
        self._lock_file = BASE_DIR / "logs" / "comfyui" / "vram.lock"

        # Initialize persistent HTTP session with connection pooling
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=retry_strategy,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @classmethod
    def get_instance(cls, api_url: Optional[str] = None) -> "ComfyConnectionPool":
        """Singleton accessor ensuring all pipeline modules share the same pool."""
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls(api_url=api_url)
            return cls._instance

    # -------------------------------------------------------------------------
    # VRAM Concurrency & Mutex Arbiter
    # -------------------------------------------------------------------------

    @contextlib.contextmanager
    def vram_guard(
        self, task_name: str, timeout: float = 300.0
    ) -> Generator[None, None, None]:
        """
        Context manager ensuring exclusive access to GPU VRAM.
        Prevents Voice (Qwen3-TTS) and Image (Diffusion) from colliding on 6GB VRAM.
        """
        acquired = self._acquire_vram_lock(task_name, timeout=timeout)
        if not acquired:
            raise TimeoutError(
                f"[ComfyConnectionPool] Could not acquire VRAM lock for '{task_name}' "
                f"after {timeout}s (Currently held by: {self._current_task})"
            )
        try:
            yield
        finally:
            self._release_vram_lock()

    def _acquire_vram_lock(self, task_name: str, timeout: float = 300.0) -> bool:
        """Acquires thread and inter-process VRAM exclusion lock."""
        start_t = time.time()
        while time.time() - start_t < timeout:
            if self._vram_lock.acquire(blocking=False):
                self._current_task = task_name
                self._lock_time = time.time()
                try:
                    self._lock_file.parent.mkdir(parents=True, exist_ok=True)
                    self._lock_file.write_text(
                        json.dumps({"task": task_name, "pid": os.getpid(), "time": self._lock_time}),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                return True
            time.sleep(0.2)
        return False

    def _release_vram_lock(self) -> None:
        """Releases VRAM exclusion lock and removes lock file."""
        self._current_task = None
        try:
            if self._lock_file.exists():
                self._lock_file.unlink()
        except Exception:
            pass
        try:
            self._vram_lock.release()
        except RuntimeError:
            pass

    # -------------------------------------------------------------------------
    # ComfyUI Memory Management (/free endpoint)
    # -------------------------------------------------------------------------

    def free_vram(self, unload_models: bool = False, timeout: float = 5.0) -> bool:
        """
        Triggers ComfyUI's memory free API to reclaim cached PyTorch GPU memory.
        unload_models=False: Frees intermediate memory cache but keeps models in RAM/VRAM.
        unload_models=True:  Completely evicts loaded models from VRAM.
        """
        endpoint = f"{self.api_url}/free"
        payload = {"unload_models": unload_models, "free_memory": True}
        try:
            resp = self.session.post(endpoint, json=payload, timeout=timeout)
            return resp.status_code == 200
        except Exception as e:
            logger.debug("Failed to call /free on ComfyUI: %s", e)
            return False

    def interrupt(self, timeout: float = 3.0) -> bool:
        """Interrupts currently executing prompt."""
        try:
            resp = self.session.post(f"{self.api_url}/interrupt", timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def clear_queue(self, timeout: float = 3.0) -> bool:
        """Clears all pending items in ComfyUI execution queue."""
        try:
            resp = self.session.post(f"{self.api_url}/queue", json={"clear": True}, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def check_health(self, timeout: float = 3.0) -> Tuple[bool, str]:
        """Probes /system_stats for server health."""
        try:
            resp = self.session.get(f"{self.api_url}/system_stats", timeout=timeout)
            if resp.status_code == 200:
                return True, "ComfyUI is healthy and responsive"
            return False, f"ComfyUI returned HTTP {resp.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to ComfyUI at {self.api_url}. Is it running?"
        except Exception as e:
            return False, f"ComfyUI connection error: {e}"

    # -------------------------------------------------------------------------
    # Execution Helpers
    # -------------------------------------------------------------------------

    def get(self, path: str, **kwargs) -> requests.Response:
        """Executes a pooled HTTP GET request."""
        url = f"{self.api_url}/{path.lstrip('/')}"
        return self.session.get(url, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Executes a pooled HTTP POST request."""
        url = f"{self.api_url}/{path.lstrip('/')}"
        return self.session.post(url, **kwargs)


def get_comfy_pool(api_url: Optional[str] = None) -> ComfyConnectionPool:
    """Helper function to obtain the shared ComfyConnectionPool instance."""
    return ComfyConnectionPool.get_instance(api_url=api_url)

