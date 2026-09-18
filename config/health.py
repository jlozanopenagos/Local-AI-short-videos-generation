"""
health.py — Centralized health check & connection verification for AI services (LLM & ComfyUI).

Provides standardized connection tests, structured status reporting, and assertions
for any workflow stage or interactive CLI tool that requires ComfyUI or LLM backends.
"""

from __future__ import annotations

import sys
import logging
from typing import Tuple, Dict, Any, Optional
# pyrefly: ignore [missing-import]
import requests
# pyrefly: ignore [missing-import]
from openai import OpenAI

from pathlib import Path

root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from .settings import (
        COMFY_API_URL,
        LLM_API_BASE_URL,
        LLM_API_KEY,
        LLM_MODEL_NAME,
    )
except ImportError:
    from config.settings import (
        COMFY_API_URL,
        LLM_API_BASE_URL,
        LLM_API_KEY,
        LLM_MODEL_NAME,
    )

logger = logging.getLogger("config.health")


def check_comfy_connection(
    api_url: Optional[str] = None,
    timeout: float = 5.0,
    raise_on_error: bool = False
) -> Tuple[bool, str]:
    """
    Checks if the ComfyUI HTTP server is reachable and responding.

    Returns:
        (is_online: bool, message: str)
    """
    url = (api_url or COMFY_API_URL).rstrip("/")
    endpoint = f"{url}/system_stats"
    try:
        resp = requests.get(endpoint, timeout=timeout)
        resp.raise_for_status()
        return True, f"Reachable at {url}"
    except Exception as exc:
        msg = f"Cannot connect to ComfyUI at {url}: {exc}"
        if raise_on_error:
            raise ConnectionError(
                f"[ComfyUI Offline] {msg}\n"
                f"Please verify ComfyUI is started (e.g. run_nvidia_gpu.bat)."
            ) from exc
        return False, msg


def check_llm_connection(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 5.0,
    raise_on_error: bool = False
) -> Tuple[bool, str]:
    """
    Checks if the local LLM server (llama.cpp / Ollama / OpenAI-compatible) is reachable.

    Returns:
        (is_online: bool, message: str)
    """
    url = (base_url or LLM_API_BASE_URL).rstrip("/")
    key = api_key or LLM_API_KEY or "llama"
    try:
        client = OpenAI(base_url=url, api_key=key, timeout=timeout)
        client.models.list()
        return True, f"Reachable at {url}"
    except Exception as exc:
        msg = f"Cannot connect to LLM server at {url}: {exc}"
        if raise_on_error:
            raise ConnectionError(
                f"[LLM Offline] {msg}\n"
                f"Please verify your local LLM server (llama-server.exe) is running and responsive."
            ) from exc
        return False, msg


def check_all_services(timeout: float = 5.0) -> Dict[str, Dict[str, Any]]:
    """Runs connection checks for all configured external AI backends."""
    comfy_ok, comfy_msg = check_comfy_connection(timeout=timeout)
    llm_ok, llm_msg = check_llm_connection(timeout=timeout)

    return {
        "ComfyUI": {
            "online": comfy_ok,
            "url": COMFY_API_URL,
            "message": comfy_msg,
        },
        "LLM": {
            "online": llm_ok,
            "url": LLM_API_BASE_URL,
            "model": LLM_MODEL_NAME,
            "message": llm_msg,
        },
    }


def require_services(
    comfy: bool = False,
    llm: bool = False,
    timeout: float = 5.0,
    verbose: bool = True
) -> None:
    """
    Asserts that required backend services are active before running a workflow.
    Prints status and raises ConnectionError immediately if an expected service is down.
    """
    failed = []

    if comfy:
        ok, msg = check_comfy_connection(timeout=timeout)
        if ok:
            if verbose:
                print(f"  [OK] ComfyUI reachable at {COMFY_API_URL}")
        else:
            if verbose:
                print(f"  [FAIL] ComfyUI is NOT reachable at {COMFY_API_URL}")
            failed.append(("ComfyUI", COMFY_API_URL, msg))

    if llm:
        ok, msg = check_llm_connection(timeout=timeout)
        if ok:
            if verbose:
                print(f"  [OK] LLM server responsive at {LLM_API_BASE_URL} ({LLM_MODEL_NAME})")
        else:
            if verbose:
                print(f"  [FAIL] LLM server is NOT reachable at {LLM_API_BASE_URL}")
            failed.append(("LLM", LLM_API_BASE_URL, msg))

    if failed:
        errors = "\n".join([f" - {name} ({url}): {msg}" for name, url, msg in failed])
        raise ConnectionError(
            f"\nPre-flight service verification failed:\n{errors}\n"
            "Please ensure required background servers are running before executing this workflow."
        )


def main() -> int:
    """CLI diagnostics runner."""
    print("=" * 60)
    print("          AI SERVICES HEALTH & DIAGNOSTICS")
    print("=" * 60)

    results = check_all_services()
    all_ok = True

    for name, info in results.items():
        status = "[ONLINE] " if info["online"] else "[OFFLINE]"
        print(f"\n{status} {name}:")
        print(f"  URL:     {info['url']}")
        if "model" in info:
            print(f"  Model:   {info['model']}")
        print(f"  Details: {info['message']}")
        if not info["online"]:
            all_ok = False

    print("\n" + "-" * 60)
    if all_ok:
        print("[SUCCESS] All required AI services are online and responsive.")
        return 0
    else:
        print("[ERROR] One or more services are OFFLINE. Please start them before continuing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
