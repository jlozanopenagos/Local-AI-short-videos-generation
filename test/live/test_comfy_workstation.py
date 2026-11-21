"""Opt-in check of the configured workstation's real ComfyUI models."""
import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from soundfile import info

from core.state_manager import StateManager
from test.webui.test_workspace_workflow import FIXTURE, write_png
from webui.server import create_app

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.getenv("SHORTS_LIVE_COMFY") != "1", reason="Set SHORTS_LIVE_COMFY=1 to use the configured GPU"),
]


def test_comfy_voice_and_images_through_queue(tmp_path):
    state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    state["status"] = {"script_generation": "done", "voice_generation": "pending", "image_generation": "pending"}
    state["assets"]["image_prompts"] = {
        "hook": "A colorful cartoon theater with an actor waiting backstage",
        "answer": "A colorful cartoon actor smiling on a theater stage",
        "explanation": "A colorful cartoon theater troupe taking a bow",
    }
    manager = StateManager(tmp_path)
    manager.save_script_state("EG01", state)
    images = tmp_path / "input/images/game_images"
    write_png(images / "empty_chalkboard.png", "#16483e")
    write_png(images / "english/english_waiting.png", "#313d4e")

    with TestClient(create_app(tmp_path)) as client:
        for stage in ("voice", "images"):
            response = client.post("/api/jobs", json={
                "stage": stage, "script_ids": ["EG01"],
                "options": {"max_attempts": 1, "candidates": 1},
            })
            assert response.status_code == 202, response.text
            job_id = response.json()["job_id"]
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                job = client.get(f"/api/jobs/{job_id}").json()
                if job["status"] in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(1)
            assert job["status"] == "completed", "\n".join(job["logs"])

    generated = manager.get_script_state("EG01")
    assert info(generated["assets"]["audio_path"]).frames > 0
    with Image.open(Path(generated["assets"]["image_dir"]) / "script_EG01_hook.png") as image:
        image.verify()
