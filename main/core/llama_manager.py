"""
core/llama_manager.py — Headless llama.cpp Process Supervisor.

Manages llama-server.exe execution as a detached background process on Windows:
- Runs headless with CREATE_NO_WINDOW (zero terminal windows).
- Eliminates Windows Console QuickEdit mode freezes completely.
- Redirects all runtime output to rotating log files in main/logs/llamacpp/llama.log.
- Provides programmatic start, stop, restart, status, log tailing, and auto-management context managers.
- Supports automatic GPU handoff: turns ON for prompt generation and OFF before ComfyUI image rendering
  to free ~2.0 GB VRAM on 6GB GPUs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from config.settings import LLM_API_BASE_URL, LLM_MODEL_NAME
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
    LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://127.0.0.1:8080/v1")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "Gemma-4-E2B")

# Auto-discovery for llama.cpp root folder:
# 1. LLM_DIR in .env
# 2. Sibling directory: BASE_DIR.parents[1] / "llama.ccp"
_raw_llm_dir = os.getenv("LLM_DIR")
if _raw_llm_dir:
    _lp = Path(_raw_llm_dir.strip())
    DEFAULT_LLM_DIR = (_lp if _lp.is_absolute() else (BASE_DIR / _lp)).resolve()
elif (BASE_DIR.parents[1] / "llama.ccp").exists():
    DEFAULT_LLM_DIR = (BASE_DIR.parents[1] / "llama.ccp").resolve()
elif (BASE_DIR.parent / "llama.ccp").exists():
    DEFAULT_LLM_DIR = (BASE_DIR.parent / "llama.ccp").resolve()
elif (BASE_DIR / "llama.ccp").exists():
    DEFAULT_LLM_DIR = (BASE_DIR / "llama.ccp").resolve()
else:
    DEFAULT_LLM_DIR = (BASE_DIR.parents[1] / "llama.ccp").resolve()

DEFAULT_LLM_BAT = os.getenv("LLM_BAT_SCRIPT", "_Gemma4-E2B.bat")


class LlamaManager:
    """Manages the headless lifecycle of a local llama.cpp / llama-server installation."""

    def __init__(
        self,
        llm_dir: Optional[Path | str] = None,
        api_url: Optional[str] = None,
        bat_script: Optional[str] = None,
        log_dir: Optional[Path | str] = None,
    ):
        self.llm_dir = Path(llm_dir or DEFAULT_LLM_DIR)
        self.api_url = (api_url or LLM_API_BASE_URL).rstrip("/")
        self.bat_script = bat_script or DEFAULT_LLM_BAT
        
        # Parse host and port
        parsed = urlparse(self.api_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 8080

        # Logging directory
        self.log_dir = Path(log_dir or (BASE_DIR / "logs" / "llamacpp"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "llama.log"
        self.pid_file = self.log_dir / "llama.pid"

        self.server_exe = self.llm_dir / "llama-server.exe"
        self.bat_file = self.llm_dir / self.bat_script

    def _read_pid(self) -> Optional[int]:
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text(encoding="utf-8").strip())
                return pid
            except (ValueError, OSError):
                return None
        return None

    def _write_pid(self, pid: int) -> None:
        try:
            self.pid_file.write_text(str(pid), encoding="utf-8")
        except OSError:
            pass

    def _clear_pid(self) -> None:
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except OSError:
                pass

    def _is_pid_alive(self, pid: int) -> bool:
        """Verifies if a process ID is active and corresponds to a llama process on Windows."""
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                out = subprocess.check_output(
                    f"tasklist /FI \"PID eq {pid}\" /FO CSV /NH",
                    shell=True,
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                if not out or "No tasks are running" in out:
                    return False
                return str(pid) in out
            except Exception:
                return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    def is_reachable(self, timeout: float = 1.5) -> bool:
        """Checks if llama-server HTTP endpoint responds."""
        base_endpoint = self.api_url.replace("/v1", "")
        test_endpoints = [f"{self.api_url}/models", f"{base_endpoint}/health", f"{base_endpoint}/props"]
        for ep in test_endpoints:
            try:
                resp = requests.get(ep, timeout=timeout)
                if resp.status_code in (200, 204):
                    return True
            except Exception:
                continue
        return False

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """
        Determines if llama-server is running.
        Returns (is_active, pid).
        """
        pid = self._read_pid()
        reachable = self.is_reachable(timeout=1.0)

        if pid and self._is_pid_alive(pid):
            return True, pid

        if reachable:
            # Active on port even if PID file was missing
            # Try to discover PID via netstat
            discovered_pid = self._discover_pid_from_port()
            if discovered_pid:
                self._write_pid(discovered_pid)
                return True, discovered_pid
            return True, pid

        # Stale PID cleanup
        if pid and not reachable:
            self._clear_pid()

        return False, None

    def _discover_pid_from_port(self) -> Optional[int]:
        """Discovers process ID listening on the configured port."""
        if os.name == "nt":
            try:
                out = subprocess.check_output(
                    f"netstat -ano | findstr :{self.port}",
                    shell=True,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                for line in out.splitlines():
                    if "LISTENING" in line:
                        parts = line.strip().split()
                        return int(parts[-1])
            except Exception:
                pass
        return None

    def _parse_bat_args(self) -> list[str]:
        """Parses command-line arguments from the .bat script to launch llama-server directly."""
        if not self.bat_file.exists():
            return []
        try:
            content = self.bat_file.read_text(encoding="utf-8", errors="replace")
            # Unescape line continuations: ^\n or ^\r\n
            content = re.sub(r"\^\r?\n", " ", content)
            # Normalize Windows batch mid-token quotes: "Dir With Spaces"\file -> "Dir With Spaces\file"
            content = re.sub(r'"([^"]+)"\\([^\s]+)', r'"\1\\\2"', content)
            # Remove any trailing carets
            content = content.replace("^", " ")
            
            import shlex
            raw_tokens = shlex.split(content, posix=False)
            tokens = []
            for t in raw_tokens:
                cleaned = t.strip('"').strip("'").strip()
                if not cleaned or cleaned.lower().endswith("llama-server.exe"):
                    continue
                tokens.append(cleaned)
            return tokens
        except Exception as exc:
            print(f"[LlamaManager Warning] Could not parse .bat script: {exc}", file=sys.stderr)
            return []

    def _wait_until_reachable(
        self,
        timeout: int,
        pid: Optional[int] = None,
        proc: Optional[subprocess.Popen] = None,
    ) -> bool:
        """Waits up to `timeout` seconds for the llama-server HTTP endpoint to respond."""
        print(f"[LlamaServer] Waiting for server to initialize at {self.api_url}...", end="", flush=True)
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
                print(f"[LlamaServer Error] Process (PID: {pid}) exited unexpectedly during startup. Check logs: {self.log_file}", file=sys.stderr)
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
            print(f"[LlamaServer Error] Server did not respond within {timeout}s. Check logs: {self.log_file}", file=sys.stderr)
            return False

    def start(self, timeout: int = 60, wait: bool = True) -> bool:
        """
        Starts llama-server headless as a detached background process.
        Returns True if successfully started and reachable.
        """
        running, existing_pid = self.is_running()
        if running:
            if not wait or self.is_reachable(timeout=1.5):
                print(f"[LlamaServer] Already running (PID: {existing_pid or 'active on port'}, URL: {self.api_url})")
                return True
            print(f"[LlamaServer] Process (PID: {existing_pid}) is booting. Waiting for readiness...")
            return self._wait_until_reachable(timeout=timeout, pid=existing_pid)

        if not self.server_exe.exists() and not self.bat_file.exists():
            print(f"[LlamaServer Error] llama-server executable or .bat not found in {self.llm_dir}", file=sys.stderr)
            return False

        # Prefer direct execution of llama-server.exe with parsed .bat args for native PID tracking
        parsed_args = self._parse_bat_args()
        if self.server_exe.exists() and parsed_args:
            cmd = [str(self.server_exe)] + parsed_args
            if "--port" not in parsed_args and "-p" not in parsed_args:
                cmd.extend(["--port", str(self.port)])
        elif self.server_exe.exists():
            cmd = [str(self.server_exe), "--port", str(self.port)]
        elif self.bat_file.exists():
            cmd = ["cmd.exe", "/c", self.bat_file.name]
        else:
            print(f"[LlamaServer Error] No .bat or server executable found in {self.llm_dir}", file=sys.stderr)
            return False

        # Rotate log if larger than 25MB
        if self.log_file.exists() and self.log_file.stat().st_size > 25 * 1024 * 1024:
            backup = self.log_dir / f"llama_{int(time.time())}.log"
            try:
                self.log_file.rename(backup)
            except Exception:
                pass

        log_handle = open(self.log_file, "a", encoding="utf-8", errors="replace", buffering=1)
        log_handle.write(f"\n{'='*70}\n[LlamaManager] Starting llama-server at {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*70}\n")
        log_handle.flush()

        # Windows detached process flags
        creationflags = 0
        if os.name == "nt":
            # DETACHED_PROCESS = 0x00000008, CREATE_NO_WINDOW = 0x08000000
            creationflags = 0x00000008 | 0x08000000

        try:
            # Try with CREATE_BREAKAWAY_FROM_JOB (0x01000000) so process survives parent job closures if permitted
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.llm_dir),
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags | 0x01000000,
                    close_fds=False if os.name == "nt" else True,
                )
            except OSError:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.llm_dir),
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                    close_fds=False if os.name == "nt" else True,
                )
            self._write_pid(proc.pid)
            print(f"[LlamaServer] Spawning headless process (PID: {proc.pid}). Logs: {self.log_file}")
        except Exception as e:
            print(f"[LlamaServer Error] Failed to launch llama-server process: {e}", file=sys.stderr)
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
        Gracefully terminates the llama-server process tree on Windows to free VRAM.
        """
        running, pid = self.is_running()
        if not running and not pid:
            print("[LlamaServer] Already stopped.")
            self._clear_pid()
            return True

        print(f"[LlamaServer] Stopping llama-server process (PID: {pid or 'port-bound'})...")

        # Kill process tree on Windows
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
        elif os.name == "nt":
            # Kill by image name if PID was unknown
            try:
                subprocess.run(
                    "taskkill /IM llama-server.exe /T /F",
                    shell=True,
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

        # Wait until port is released
        start_t = time.time()
        while time.time() - start_t < timeout:
            if not self.is_reachable(timeout=0.5):
                print("[LlamaServer] Successfully stopped (VRAM released).")
                self._clear_pid()
                return True
            time.sleep(0.5)

        self._clear_pid()
        print(f"[LlamaServer Warning] Port {self.port} might still be bound.")
        return True

    def restart(self, timeout: int = 60) -> bool:
        """Restarts llama-server."""
        self.stop()
        time.sleep(1.0)
        return self.start(timeout=timeout, wait=True)

    def ensure_llama_stopped(self, timeout: int = 15) -> bool:
        """Alias for stop() ensuring server is stopped to release VRAM."""
        running, _ = self.is_running()
        if not running and not self.is_reachable():
            return True
        return self.stop(timeout=timeout)

    def ensure_llama_running(self, timeout: int = 60) -> bool:
        """Alias for start() ensuring server is online and reachable."""
        if self.is_reachable():
            return True
        return self.start(timeout=timeout, wait=True)

    def get_status(self) -> Dict[str, Any]:
        """Returns structured health and status dictionary."""
        active, pid = self.is_running()
        reachable = self.is_reachable(timeout=1.0)
        return {
            "status": "ONLINE" if (active and reachable) else "OFFLINE",
            "active": active,
            "reachable": reachable,
            "pid": pid,
            "port": self.port,
            "api_url": self.api_url,
            "llm_dir": str(self.llm_dir),
            "log_file": str(self.log_file),
            "model_name": LLM_MODEL_NAME,
        }


_LLAMA_MANAGER_INSTANCE: Optional[LlamaManager] = None


def get_llama_manager() -> LlamaManager:
    """Returns singleton LlamaManager instance."""
    global _LLAMA_MANAGER_INSTANCE
    if _LLAMA_MANAGER_INSTANCE is None:
        _LLAMA_MANAGER_INSTANCE = LlamaManager()
    return _LLAMA_MANAGER_INSTANCE


def ensure_llama_running(timeout: int = 60) -> bool:
    """
    Ensures llama-server is running and reachable.
    Starts it if offline.
    """
    mgr = get_llama_manager()
    if mgr.is_reachable():
        return True
    return mgr.start(timeout=timeout, wait=True)


def ensure_llama_stopped(timeout: int = 15) -> bool:
    """
    Ensures llama-server is stopped to release VRAM.
    """
    mgr = get_llama_manager()
    running, _ = mgr.is_running()
    if not running and not mgr.is_reachable():
        return True
    return mgr.stop(timeout=timeout)


@contextmanager
def active_llama_session(timeout: int = 60, auto_stop: bool = True) -> Generator[LlamaManager, None, None]:
    """
    Context manager for automated GPU memory lifecycle management.
    Starts llama-server if not already online.
    When exiting the block, if it was started by this context manager and auto_stop=True,
    it cleanly terminates llama-server to release GPU VRAM for downstream renderers (ComfyUI / TTS).
    """
    mgr = get_llama_manager()
    started_by_us = False

    if not mgr.is_reachable():
        print("[LlamaManager] Activating LLM session on-demand...")
        success = mgr.start(timeout=timeout, wait=True)
        if not success:
            raise RuntimeError(f"Failed to start llama-server within {timeout}s. Check logs: {mgr.log_file}")
        started_by_us = True
    else:
        print("[LlamaManager] LLM session already active.")

    try:
        yield mgr
    finally:
        if started_by_us and auto_stop:
            print("[LlamaManager] Releasing LLM session and freeing VRAM...")
            mgr.stop()


