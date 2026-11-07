"""
webui/routers/system.py — System health, service supervisors (ComfyUI & LLM), and log endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.comfy_manager import get_comfy_manager
from core.llama_manager import get_llama_manager
from config.settings import OUTPUT_DIR

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status")
def get_system_status() -> Dict[str, Any]:
    """Returns real-time status of ComfyUI, llama.cpp, and storage backends."""
    cm = get_comfy_manager()
    lm = get_llama_manager()

    comfy_status = cm.get_status()
    llm_status = lm.get_status()

    return {
        "comfy": comfy_status,
        "llm": llm_status,
        "output_dir_exists": OUTPUT_DIR.exists(),
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
    }


@router.post("/comfy/start")
def start_comfy(timeout: int = 120, wait: bool = True) -> Dict[str, Any]:
    """Starts the ComfyUI headless process."""
    cm = get_comfy_manager()
    ok = cm.start(timeout=timeout, wait=wait)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to start ComfyUI. Check system logs.")
    return {"status": "success", "message": "ComfyUI started successfully", "info": cm.get_status()}


@router.post("/comfy/stop")
def stop_comfy() -> Dict[str, Any]:
    """Gracefully terminates the ComfyUI headless process."""
    cm = get_comfy_manager()
    cm.stop()
    return {"status": "success", "message": "ComfyUI stopped", "info": cm.get_status()}


@router.post("/comfy/restart")
def restart_comfy(timeout: int = 120) -> Dict[str, Any]:
    """Restarts the ComfyUI headless process."""
    cm = get_comfy_manager()
    ok = cm.restart(timeout=timeout)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to restart ComfyUI.")
    return {"status": "success", "message": "ComfyUI restarted", "info": cm.get_status()}


@router.post("/llm/start")
def start_llm(timeout: int = 60, wait: bool = True) -> Dict[str, Any]:
    """Starts the llama.cpp / Gemma headless server."""
    lm = get_llama_manager()
    ok = lm.start(timeout=timeout, wait=wait)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to start llama.cpp server. Check logs.")
    return {"status": "success", "message": "llama.cpp server started successfully", "info": lm.get_status()}


@router.post("/llm/stop")
def stop_llm() -> Dict[str, Any]:
    """Stops the llama.cpp server to release GPU VRAM."""
    lm = get_llama_manager()
    lm.stop()
    return {"status": "success", "message": "llama.cpp stopped and VRAM released", "info": lm.get_status()}


@router.post("/llm/restart")
def restart_llm(timeout: int = 60) -> Dict[str, Any]:
    """Restarts the llama.cpp server."""
    lm = get_llama_manager()
    ok = lm.restart(timeout=timeout)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to restart llama.cpp server.")
    return {"status": "success", "message": "llama.cpp restarted", "info": lm.get_status()}


@router.get("/logs/{service}")
def get_service_logs(service: str, lines: int = Query(default=100, ge=1, le=1000)) -> Dict[str, Any]:
    """Returns recent log lines for ComfyUI or LLM server."""
    if service.lower() in ("comfy", "comfyui"):
        log_file = get_comfy_manager().log_file
    elif service.lower() in ("llm", "llama", "llamacpp"):
        log_file = get_llama_manager().log_file
    else:
        raise HTTPException(status_code=400, detail=f"Unknown service '{service}'. Choose 'comfy' or 'llm'.")

    if not log_file.exists():
        return {"service": service, "lines": [], "path": str(log_file)}

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            tail = [l.rstrip("\r\n") for l in all_lines[-lines:]]
            return {"service": service, "lines": tail, "path": str(log_file)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {exc}")
