"""
webui/jobs/models.py — Data models for the Web UI job execution system.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
# pyrefly: ignore[missing-import]
from pydantic import BaseModel, Field


class JobStage(str, Enum):
    SCRIPTS = "scripts"
    VOICE = "voice"
    IMAGES = "images"
    MUSIC = "music"
    ASSEMBLY = "assembly"
    THUMBNAILS = "thumbnails"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobProgress(BaseModel):
    current: int = 0
    total: int = 0
    current_script: Optional[str] = None
    stage_label: str = ""


class JobCreateRequest(BaseModel):
    stage: JobStage
    script_ids: List[str]
    options: Dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    stage: JobStage
    status: JobStatus
    script_ids: List[str]
    progress: JobProgress
    logs: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None

