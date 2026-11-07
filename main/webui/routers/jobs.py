"""
webui/routers/jobs.py — REST and WebSocket endpoints for job creation, status, and log streaming.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from webui.jobs.manager import get_job_manager
from webui.jobs.models import JobCreateRequest, JobResponse

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])
ws_router = APIRouter(tags=["WebSockets"])


@router.post("", status_code=202, response_model=JobResponse)
def create_job(request: JobCreateRequest) -> JobResponse:
    """Enqueues a new background pipeline stage execution job."""
    if not request.script_ids:
        raise HTTPException(status_code=400, detail="Must provide at least one script_id.")

    jm = get_job_manager()
    job = jm.enqueue_job(request)
    return job


@router.get("", response_model=List[JobResponse])
def list_jobs(limit: int = 50) -> List[JobResponse]:
    """Lists recent pipeline jobs."""
    jm = get_job_manager()
    return jm.list_jobs(limit=limit)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    """Gets current status, progress, and logs for a specific job."""
    jm = get_job_manager()
    job = jm.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancels a queued or currently executing job."""
    jm = get_job_manager()
    ok = jm.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job '{job_id}' (does not exist or already finished).")
    return {"status": "success", "message": f"Job '{job_id}' cancelled."}


@ws_router.websocket("/ws/jobs/{job_id}")
async def job_websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint streaming live logs and progress events for a specific job.
    """
    jm = get_job_manager()
    job = jm.get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()
    # Send initial state snapshot
    await websocket.send_json({"type": "job_snapshot", "job": job.model_dump()})

    jm.register_subscriber(job_id, websocket)
    try:
        while True:
            # Keep-alive ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        jm.remove_subscriber(job_id, websocket)


@ws_router.websocket("/ws/system")
async def system_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint streaming global queue and system health events.
    """
    jm = get_job_manager()
    await websocket.accept()
    jm.register_system_subscriber(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        jm.remove_system_subscriber(websocket)
