"""
webui/server.py — FastAPI application factory, CORS setup, and router mounting.
"""

from __future__ import annotations

import sys
from pathlib import Path

# pyrefly: ignore[missing-import]
from fastapi import FastAPI
# pyrefly: ignore[missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore[missing-import]
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from webui.settings import STATIC_DIR, WEBUI_DEV_MODE
from webui.routers import system, scripts, media, jobs, sheets


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application."""
    app = FastAPI(
        title="LingoVerse Shorts Studio API",
        description="Localhost REST and WebSocket API for AI Shorts Automation.",
        version="1.0.0",
    )

    # CORS configuration: allows Vite dev server when WEBUI_DEV_MODE is enabled
    origins = ["http://127.0.0.1:8190", "http://localhost:8190"]
    if WEBUI_DEV_MODE:
        origins.extend([
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health probe
    @app.get("/healthz")
    def health_check():
        return {"status": "ok"}

    # Include API Routers
    app.include_router(system.router)
    app.include_router(scripts.router)
    app.include_router(media.router)
    app.include_router(jobs.router)
    app.include_router(jobs.ws_router)
    app.include_router(sheets.router)

    # Pre-warm script cache on startup in background
    @app.on_event("startup")
    def startup_cache_warmup():
        import threading
        threading.Thread(target=scripts._get_indexed_scripts, daemon=True).start()

    # Serve SPA index.html with strict no-cache headers so browsers always load the latest bundle
    @app.get("/", include_in_schema=False)
    def serve_spa():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            # pyrefly: ignore[missing-import]
            from fastapi.responses import FileResponse
            return FileResponse(
                str(index_file),
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        # pyrefly: ignore[missing-import]
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h1>WebUI static bundle not found. Please build frontend first.</h1>")

    # Mount static assets directory for Single Page Application
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app

