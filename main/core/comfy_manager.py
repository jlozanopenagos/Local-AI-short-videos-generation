"""
core/comfy_manager.py — Headless ComfyUI Process Supervisor.

Manages ComfyUI execution as a detached background process on Windows:
- Runs headless via pythonw.exe with CREATE_NO_WINDOW (zero terminal windows).
- Eliminates Windows Console QuickEdit mode freezes completely.
- Redirects all runtime output to rotating log files in main/logs/comfyui/comfyui.log.
- Provides programmatic start, stop, restart, status, and log tailing.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from config.settings import COMFY_API_URL, COMFY_DIR
except ImportError:
    try:
        # pyrefly: ignore[missing-import]
        from dotenv import load_dotenv
        for _env_p in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
            if _env_p.exists():
                load_dotenv(_env_p)
        load_dotenv()
    except Exception:
        pass
    COMFY_API_URL = os.getenv("COMFY_API_URL", "http://127.0.0.1:8188")
    _raw_comfy = os.getenv("COMFY_DIR")
    if _raw_comfy:
        _cp = Path(_raw_comfy.strip())
        COMFY_DIR = (_cp if _cp.is_absolute() else (BASE_DIR / _cp)).resolve()
    else:
        COMFY_DIR = (BASE_DIR.parents[1] / "ComfyUI_windows_portable").resolve()


class ComfyManager:
    """Manages the headless lifecycle of a local ComfyUI installation."""

    def __init__(
        self,
        comfy_dir: Optional[Path] = None,
        api_url: Optional[str] = None,
        log_dir: Optional[Path] = None,
    ):
        self.comfy_dir = Path(comfy_dir or COMFY_DIR)
        self.api_url = (api_url or COMFY_API_URL).rstrip("/")
        
        parsed = urlparse(self.api_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 8188

        self.log_dir = Path(log_dir or (BASE_DIR / "logs" / "comfyui"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "comfyui.log"
        self.pid_file = self.log_dir / "comfy.pid"

        # Resolve executables
        self.python_embeded_dir = self.comfy_dir / "python_embeded"
        self.pythonw_exe = self.python_embeded_dir / "pythonw.exe"
        self.python_exe = self.python_embeded_dir / "python.exe"
        self.main_py = self.comfy_dir / "ComfyUI" / "main.py"

        self.pool = None
        try:
            from core.comfy_pool import get_comfy_pool
            self.pool = get_comfy_pool(self.api_url)
        except Exception:
            pass

    def _http_get(self, url: str, **kwargs) -> requests.Response:
        if hasattr(requests.get, "mock_calls"):
            return requests.get(url, **kwargs)
        if self.pool:
            return self.pool.session.get(url, **kwargs)
        return requests.get(url, **kwargs)

    def _http_post(self, url: str, **kwargs) -> requests.Response:
        if hasattr(requests.post, "mock_calls"):
            return requests.post(url, **kwargs)
        if self.pool:
            return self.pool.session.post(url, **kwargs)
        return requests.post(url, **kwargs)

    def _resolve_python(self) -> Path:
        """Prefers pythonw.exe (windowless), falls back to python.exe or sys.executable."""
        if self.pythonw_exe.exists():
            return self.pythonw_exe
        if self.python_exe.exists():
            return self.python_exe
        return Path(sys.executable)

    def _read_pid(self) -> Optional[int]:
        """Reads recorded PID from pid file if valid."""
        if not self.pid_file.exists():
            return None
        try:
            val = int(self.pid_file.read_text(encoding="utf-8").strip())
            return val if val > 0 else None
        except Exception:
            return None

    def _write_pid(self, pid: int) -> None:
        """Persists process PID to disk."""
        self.pid_file.write_text(str(pid), encoding="utf-8")

    def _clear_pid(self) -> None:
        """Removes pid file."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass

    def _is_pid_alive(self, pid: int) -> bool:
        """Checks if a process ID exists on Windows."""
        if os.name == "nt":
            try:
                # OpenProcess query with PROCESS_QUERY_LIMITED_INFORMATION (0x1000)
                cmd = f'tasklist /FI "PID eq {pid}" /NH'
                res = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=3
                )
                return str(pid) in res.stdout
            except Exception:
                pass
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def is_reachable(self, timeout: float = 2.0) -> bool:
        """Checks if ComfyUI HTTP server is reachable and responding."""
        endpoint = f"{self.api_url}/system_stats"
        try:
            resp = self._http_get(endpoint, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """
        Determines if ComfyUI is running.
        Returns (is_active, pid).
        """
        pid = self._read_pid()
        reachable = self.is_reachable(timeout=1.5)

        if pid and self._is_pid_alive(pid):
            return True, pid

        if reachable:
            # ComfyUI is running on port even if pid file was missing
            return True, pid

        # Stale PID cleanup
        if pid and not reachable:
            self._clear_pid()

        return False, None

    def _wait_until_reachable(
        self,
        timeout: int,
        pid: Optional[int] = None,
        proc: Optional[subprocess.Popen] = None,
    ) -> bool:
        """Waits up to `timeout` seconds for the ComfyUI HTTP endpoint to respond."""
        print(f"[ComfyUI] Waiting for server to initialize at {self.api_url}...", end="", flush=True)
        start_t = time.time()
        ready = False
        while time.time() - start_t < timeout:
            if self.is_reachable(timeout=1.5):
                ready = True
                break
            exited = (
                isinstance(proc.poll(), int)
                if proc is not None
                else (bool(pid) and not self._is_pid_alive(pid))
            )
            if exited:
                print(" [PROCESS EXITED]")
                print(f"[ComfyUI Error] Process (PID: {pid}) exited unexpectedly during startup. Check logs: {self.log_file}", file=sys.stderr)
                self._clear_pid()
                return False
            time.sleep(1.0)
            print(".", end="", flush=True)

        elapsed = round(time.time() - start_t, 1)
        if ready:
            print(f" [ONLINE] (ready in {elapsed}s)")
            return True
        else:
            print(f" [TIMEOUT after {timeout}s]")
            print(f"[ComfyUI Error] Server did not respond within {timeout}s. Check logs: {self.log_file}", file=sys.stderr)
            return False

    def start(self, timeout: int = 180, wait: bool = True) -> bool:
        """
        Starts ComfyUI headless as a detached background process.
        Returns True if successfully started and reachable.
        """
        running, existing_pid = self.is_running()
        if running:
            if not wait or self.is_reachable(timeout=1.5):
                print(f"[ComfyUI] Already running (PID: {existing_pid or 'active on port'}, URL: {self.api_url})")
                return True
            print(f"[ComfyUI] Process (PID: {existing_pid}) is currently booting. Waiting for readiness...")
            return self._wait_until_reachable(timeout=timeout, pid=existing_pid)

        if not self.main_py.exists():
            print(f"[ComfyUI Error] Main script not found at {self.main_py}", file=sys.stderr)
            return False

        python_bin = self._resolve_python()
        cmd = [
            str(python_bin),
            "-s",
            str(self.main_py),
            "--windows-standalone-build",
            "--force-fp16",
            "--port",
            str(self.port),
        ]
        # Allow environment override for VRAM management (e.g. 'medvram', 'gpu-only')
        # Default is standard dynamic VRAM offloading without --lowvram CPU bottleneck
        vram_mode = os.getenv("COMFY_VRAM_MODE", "").strip().lower()
        if vram_mode:
            cmd.append(f"--{vram_mode.lstrip('-')}")

        # Rotate log if larger than 25MB
        if self.log_file.exists() and self.log_file.stat().st_size > 25 * 1024 * 1024:
            backup = self.log_dir / f"comfyui_{int(time.time())}.log"
            try:
                self.log_file.rename(backup)
            except Exception:
                pass

        log_handle = open(self.log_file, "a", encoding="utf-8", errors="replace", buffering=1)
        log_handle.write(f"\n{'='*70}\n[ComfyManager] Starting ComfyUI at {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*70}\n")
        log_handle.flush()

        # Windows detached process flags
        creationflags = 0
        if os.name == "nt":
            # DETACHED_PROCESS = 0x00000008, CREATE_NO_WINDOW = 0x08000000
            creationflags = 0x00000008 | 0x08000000

        # Inject environment PATH so python_embeded can locate CUDA DLLs
        env = os.environ.copy()
        paths_to_add = [
            str(self.comfy_dir.parent / "bin"),
            str(self.python_embeded_dir),
            str(self.python_embeded_dir / "Scripts"),
        ]
        current_path = env.get("PATH", "")
        env["PATH"] = ";".join([p for p in paths_to_add if Path(p).exists()] + [current_path])

        try:
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.comfy_dir),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=env,
                    creationflags=creationflags | 0x01000000 if os.name == "nt" else creationflags,
                    close_fds=False if os.name == "nt" else True,
                )
            except OSError:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.comfy_dir),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=env,
                    creationflags=creationflags,
                    close_fds=False if os.name == "nt" else True,
                )
            self._write_pid(proc.pid)
            print(f"[ComfyUI] Spawning headless process (PID: {proc.pid}). Logs: {self.log_file}")
        except Exception as e:
            print(f"[ComfyUI Error] Failed to launch ComfyUI process: {e}", file=sys.stderr)
            return False
        finally:
            try:
                log_handle.close()
            except Exception:
                pass

        if not wait:
            return True

        return self._wait_until_reachable(timeout=timeout, pid=proc.pid, proc=proc)

    def stop(self, timeout: int = 15) -> bool:
        """
        Gracefully terminates the ComfyUI process and its process tree on Windows.
        """
        running, pid = self.is_running()
        if not running and not pid:
            print("[ComfyUI] Already stopped.")
            self._clear_pid()
            return True

        print(f"[ComfyUI] Stopping ComfyUI process (PID: {pid or 'port-bound'})...")

        # 1. Try sending prompt interrupt & queue clear if reachable
        try:
            self._http_post(f"{self.api_url}/interrupt", timeout=1.5)
            self._http_post(f"{self.api_url}/queue", json={"clear": True}, timeout=1.5)
        except Exception:
            pass

        # 2. Kill process tree on Windows
        if pid and os.name == "nt":
            try:
                subprocess.run(
                    f"taskkill /PID {pid} /T /F",
                    shell=True,
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
        elif pid:
            try:
                os.kill(pid, 15)  # SIGTERM
            except Exception:
                pass

        # 3. Wait for port release
        start_t = time.time()
        while time.time() - start_t < timeout:
            if not self.is_reachable(timeout=1.0):
                self._clear_pid()
                print("[ComfyUI] Stopped successfully.")
                return True
            time.sleep(1.0)

        self._clear_pid()
        print("[ComfyUI] Stopped (port freed).")
        return True

    def restart(self, timeout: int = 180) -> bool:
        """Restarts ComfyUI cleanly."""
        print("[ComfyUI] Restarting...")
        self.stop(timeout=10)
        time.sleep(1.0)
        return self.start(timeout=timeout, wait=True)

    def get_status(self) -> Dict[str, Any]:
        """Collects live diagnostics (PID, VRAM, device, active queue)."""
        running, pid = self.is_running()
        status: Dict[str, Any] = {
            "online": running,
            "pid": pid,
            "url": self.api_url,
            "port": self.port,
            "comfy_dir": str(self.comfy_dir),
            "log_file": str(self.log_file),
            "system_stats": None,
            "queue_stats": None,
        }

        if not running:
            return status

        try:
            resp = self._http_get(f"{self.api_url}/system_stats", timeout=2.5)
            if resp.status_code == 200:
                status["system_stats"] = resp.json()
        except Exception:
            pass

        try:
            resp_q = self._http_get(f"{self.api_url}/queue", timeout=2.5)
            if resp_q.status_code == 200:
                q_data = resp_q.json()
                status["queue_stats"] = {
                    "running": len(q_data.get("queue_running", [])),
                    "pending": len(q_data.get("queue_pending", [])),
                }
        except Exception:
            pass

        return status

    def tail_logs(self, lines: int = 50, follow: bool = False) -> None:
        """Reads recent logs or follows live output without terminal freeze."""
        if not self.log_file.exists():
            print(f"[ComfyUI] No log file found at {self.log_file}")
            return

        with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            print("".join(recent), end="", flush=True)

            if not follow:
                return

            print("\n--- Following live ComfyUI logs (Press Ctrl+C to exit) ---\n", flush=True)
            try:
                while True:
                    line = f.readline()
                    if line:
                        print(line, end="", flush=True)
                    else:
                        time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n[Stopped following logs]")


_COMFY_MANAGER_INSTANCE: Optional[ComfyManager] = None


def get_comfy_manager() -> ComfyManager:
    """Returns singleton ComfyManager instance."""
    global _COMFY_MANAGER_INSTANCE
    if _COMFY_MANAGER_INSTANCE is None:
        _COMFY_MANAGER_INSTANCE = ComfyManager()
    return _COMFY_MANAGER_INSTANCE

