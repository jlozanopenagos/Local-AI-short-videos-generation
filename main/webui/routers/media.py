"""
webui/routers/media.py — Secure media streaming for images, audio, video, and thumbnails.

Enforces strict path containment within OUTPUT_DIR (plus game assets) to protect local privacy.
Supports HTTP 206 Partial Content (Range header) for audio/video seeking in browser players.
"""

from __future__ import annotations

import mimetypes
import os
import sys
from pathlib import Path
from typing import Generator

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import OUTPUT_DIR, GAME_IMAGES_DIR

router = APIRouter(prefix="/api/media", tags=["Media"])

ALLOWED_ROOTS = [OUTPUT_DIR.resolve()]
if GAME_IMAGES_DIR.exists():
    ALLOWED_ROOTS.append(GAME_IMAGES_DIR.resolve())


def _resolve_safe_path(requested_path: str) -> Path:
    """
    Resolves requested relative or normalized path against ALLOWED_ROOTS.
    Rejects directory traversal (..) or access outside allowed roots.
    """
    clean = requested_path.strip().lstrip("/\\")
    if ".." in clean or clean.startswith("~"):
        raise HTTPException(status_code=403, detail="Path traversal forbidden.")

    # Try matching against each allowed root
    for root in ALLOWED_ROOTS:
        candidate = (root / clean).resolve()
        if candidate.is_relative_to(root) and candidate.exists() and candidate.is_file():
            return candidate

    raise HTTPException(status_code=404, detail="Media file not found or access denied.")


def _range_streamer(path: Path, start: int, end: int, chunk_size: int = 64 * 1024) -> Generator[bytes, None, None]:
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_bytes = min(remaining, chunk_size)
            data = f.read(read_bytes)
            if not data:
                break
            remaining -= len(data)
            yield data


@router.get("")
@router.get("/{path:path}")
def get_media(request: Request, path: str = "", file: str = ""):
    """
    Streams media file with HTTP Range support for audio and video seeking.
    Supports either URL path segment (/api/media/rel/path.png) or query param (/api/media?file=rel/path.png).
    """
    target = file if file else path
    safe_path = _resolve_safe_path(target)
    file_size = safe_path.stat().st_size
    content_type, _ = mimetypes.guess_type(str(safe_path))
    if not content_type:
        content_type = "application/octet-stream"

    range_header = request.headers.get("range")
    if not range_header:
        # Full file response
        return FileResponse(
            path=str(safe_path),
            media_type=content_type,
            filename=safe_path.name,
        )

    # Partial content (HTTP 206) for media seeking
    try:
        # Format: bytes=start-end
        range_spec = range_header.strip().replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else (file_size - 1)
        if end >= file_size:
            end = file_size - 1
        if start > end or start >= file_size:
            raise ValueError
    except Exception:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    content_length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": content_type,
    }

    return StreamingResponse(
        _range_streamer(safe_path, start, end),
        status_code=206,
        headers=headers,
    )
