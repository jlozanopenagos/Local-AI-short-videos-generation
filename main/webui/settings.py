"""
webui/settings.py — Configuration and environment settings for the Local Web UI.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

WEBUI_HOST = os.getenv("WEBUI_HOST", "127.0.0.1")
WEBUI_PORT = int(os.getenv("WEBUI_PORT", "8190"))
WEBUI_DEV_MODE = os.getenv("WEBUI_DEV_MODE", "false").lower() in ("1", "true", "yes")
WEBUI_OPEN_BROWSER = os.getenv("WEBUI_OPEN_BROWSER", "false").lower() in ("1", "true", "yes")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
