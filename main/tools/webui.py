"""
tools/webui.py — Local Web UI launcher CLI.

Usage (from main/):
    py tools/webui.py                 # Serve on http://127.0.0.1:8190
    py tools/webui.py --open          # Open default browser automatically
    py tools/webui.py --port 8200     # Custom port
    py tools/webui.py --dev           # Dev mode (enables CORS for Vite dev server on :5173)
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import uvicorn
    import fastapi
except ImportError:
    print(
        "[ERROR] 'fastapi' and 'uvicorn' are required to run the Web UI.\n"
        "Please install them via: py -m pip install fastapi \"uvicorn[standard]\"",
        file=sys.stderr,
    )
    sys.exit(1)

from webui.settings import (
    WEBUI_HOST,
    WEBUI_PORT,
    WEBUI_DEV_MODE,
    WEBUI_OPEN_BROWSER,
)


def _open_browser_when_ready(url: str, delay: float = 1.2) -> None:
    def _worker():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser(description="LingoVerse Studio Local Web UI Server")
    parser.add_argument("--host", default=WEBUI_HOST, help=f"Host address to bind (default: {WEBUI_HOST})")
    parser.add_argument("--port", type=int, default=WEBUI_PORT, help=f"Port to bind (default: {WEBUI_PORT})")
    parser.add_argument("--open", action="store_true", default=WEBUI_OPEN_BROWSER, help="Open default web browser upon launch")
    parser.add_argument("--dev", action="store_true", default=WEBUI_DEV_MODE, help="Enable dev mode (CORS for Vite :5173)")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload")

    args = parser.parse_args()

    if args.dev:
        os.environ["WEBUI_DEV_MODE"] = "true"

    url = f"http://{args.host}:{args.port}"
    print("=" * 60)
    print("        LINGOVERSE SHORTS STUDIO — LOCAL WEB UI")
    print("=" * 60)
    print(f"• Localhost URL: {url}")
    print(f"• OpenAPI Docs:  {url}/docs")
    print(f"• Mode:          {'DEV (CORS enabled for :5173)' if args.dev else 'PRODUCTION (Serving static bundle)'}")
    print("=" * 60 + "\n")

    if args.open:
        print(f"Opening browser at {url}...")
        _open_browser_when_ready(url)

    from webui.server import create_app
    app = create_app()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

