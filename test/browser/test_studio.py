"""Browser smoke against the built React application and a real FastAPI worker."""
import json
import os
import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from core.state_manager import StateManager
from test.webui.test_workspace_workflow import FIXTURE, write_png
from webui.server import create_app

pytestmark = pytest.mark.browser


@pytest.fixture
def studio_url(tmp_path):
    app = create_app(tmp_path)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        host, port = listener.getsockname()
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started, "Fixture studio failed to start"
            yield f"http://{host}:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=15)
            assert not thread.is_alive(), "Fixture studio did not shut down"


def test_thumbnail_failure_retry_and_preview(studio_url, tmp_path):
    state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    state.setdefault("status", {})["thumbnail_generation"] = "pending"
    StateManager(tmp_path).save_script_state("EG01", state)
    models = tmp_path / "input/images/thumbnail_models"
    models.mkdir(parents=True)

    with sync_playwright() as playwright:
        executable = os.getenv("STUDIO_TEST_CHROMIUM")
        browser = playwright.chromium.launch(executable_path=executable)
        page = browser.new_page()
        page.goto(studio_url)

        def launch_thumbnail():
            page.get_by_role("button", name="mass creation", exact=True).click()
            page.get_by_text("thumbnail image", exact=True).click()
            page.get_by_placeholder("Paste IDs separated", exact=False).fill("EG01")
            launch = page.get_by_role("button", name="launch mass generation (1 scripts)", exact=True)
            expect(launch).to_be_enabled(timeout=10_000)
            with page.expect_response(lambda response: response.url.endswith("/api/jobs") and response.request.method == "POST") as response:
                launch.click()
            assert response.value.status == 202

        launch_thumbnail()
        expect(page.get_by_text("failed", exact=True).first).to_be_visible(timeout=15_000)
        expect(page.get_by_text("Thumbnail model image not found", exact=False).first).to_be_visible()

        write_png(models / "english/english_thumbnail_model.png", "#234f41")
        launch_thumbnail()
        expect(page.get_by_text("completed", exact=True).first).to_be_visible(timeout=15_000)

        page.get_by_role("button", name="script catalog", exact=True).click()
        page.get_by_text("EG01", exact=True).first.click()
        page.get_by_role("button", name="media players", exact=True).click()
        thumbnail = page.get_by_title("Click to view enlarged thumbnail")
        expect(thumbnail).to_be_visible()
        expect(thumbnail).to_have_js_property("complete", True)
        assert thumbnail.evaluate("(image) => image.naturalWidth") > 0
        browser.close()
