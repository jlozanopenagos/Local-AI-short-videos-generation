"""Exercise the studio's actual job queue and local media stages in a temporary workspace."""
import io
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from requests import Response

from config import VIDEO_HEIGHT, VIDEO_WIDTH
from config.settings import get_script_output_dir
from connectivity.corrected_scripts import fetcher
from core.state_manager import DOWNSTREAM_STAGES, StateManager
from test.unit.test_voice_characterization import RecordingFakeComfyClient, _build_synthetic_open_swara
from webui.server import create_app


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/image_prompts/states/script_EG01.json"
ASSEMBLY_DIR = Path(__file__).resolve().parents[2] / "main/video_creation/_G_video_assembly"


def find_binary(name):
    bundled = ASSEMBLY_DIR / f"{name}.exe"
    path = str(bundled) if bundled.is_file() else shutil.which(name)
    if path is None:
        raise AssertionError(f"{name} is required for the studio workflow test. Install it on PATH.")
    return path


def write_png(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color).save(path)


class ComfyImageResponses:
    """Serve the ComfyUI prompt, history, and image download protocol in-process."""

    def __init__(self):
        self.images = {}

    @staticmethod
    def response(payload):
        response = Response()
        response.status_code = 200
        response._content = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        response._content_consumed = True
        return response

    def post(self, url, *, json, **kwargs):
        assert url.endswith("/prompt"), url
        assert json["prompt"], "Expected a generated ComfyUI workflow"
        index = len(self.images)
        prompt_id = f"prompt-{index}"
        image = io.BytesIO()
        Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (40 + index * 30, 95, 110)).save(image, "PNG")
        self.images[prompt_id] = image.getvalue()
        return self.response({"prompt_id": prompt_id})

    def get(self, url, *, params=None, **kwargs):
        if url.endswith("/view"):
            return self.response(self.images[params["filename"].removesuffix(".png")])
        prompt_id = url.split("/")[-1]
        assert prompt_id in self.images, url
        return self.response({prompt_id: {"outputs": {"1": {"images": [
            {"filename": f"{prompt_id}.png", "subfolder": "", "type": "output"},
        ]}}}})


class TranscriptDouble:
    def transcribe(self, audio_path, **kwargs):
        return [{"word": "Ready", "start": 0.1, "end": 0.4}]


class TestWorkspaceWorkflow(unittest.TestCase):
    def wait_for(self, read, terminal):
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            response = read()
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            if result["status"] in terminal:
                return result
            time.sleep(0.025)
        self.fail(f"Timed out waiting for {terminal}. Last response: {result}")

    def queue(self, client, stage, expected="completed"):
        response = client.post("/api/jobs", json={
            "stage": stage, "script_ids": ["EG01"], "options": {"max_attempts": 1, "candidates": 1},
        })
        self.assertEqual(response.status_code, 202, response.text)
        job_url = f"/api/jobs/{response.json()['job_id']}"
        job = self.wait_for(lambda: client.get(job_url), {"completed", "failed", "cancelled"})
        self.assertEqual(job["status"], expected, "\n".join(job["logs"]))
        return job

    def test_studio_catalog_and_job_history_are_bound_to_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first, second = workspace / "first", workspace / "second"
            first_state = StateManager(first)
            first_state.save_script_state("EG01", json.loads(FIXTURE.read_text(encoding="utf-8")))
            with TestClient(create_app(first)) as left, TestClient(create_app(second)) as right:
                self.assertEqual(left.get("/api/scripts/EG01").status_code, 200)
                self.assertEqual(right.get("/api/scripts/EG01").status_code, 404)
                self.assertEqual(left.get("/api/sheets/status").json()["status"], "idle")
                with patch("webui.jobs.adapters.assembly.Transcriber", TranscriptDouble):
                    self.queue(left, "assembly", expected="failed")
                self.assertEqual(len(left.get("/api/jobs").json()), 1)
                self.assertEqual(right.get("/api/jobs").json(), [])

    def test_approved_game_to_playable_short_and_safe_replacement(self):
        ffmpeg = find_binary("ffmpeg")
        ffprobe = find_binary("ffprobe")
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            workspace = Path(tmp)
            state_manager = StateManager(workspace)
            state = json.loads(FIXTURE.read_text(encoding="utf-8"))
            state_manager.save_script_state("EG01", state)
            revised = dict(state["content_metadata"]["script"], hook="Which phrase helps an actor before a show?")
            google_row = {
                "ID": "EG01", "expression": "Break a leg", "script_ready": True,
                "SCRIPT_CHANGED": "\n".join(revised[key].replace("\\n", " ") for key in ("hook", "challenge", "pressure", "answer", "explanation")),
            }
            stack.enter_context(patch.object(fetcher, "ENDPOINT_REGISTRY", {("english", "game"): "https://sheets.invalid"}))
            stack.enter_context(patch.object(fetcher, "get_endpoint", return_value=("english", "game", "https://sheets.invalid")))
            stack.enter_context(patch.object(fetcher, "fetch_raw_sheet_rows", return_value=[google_row]))

            images = workspace / "input/images"
            write_png(images / "game_images/empty_chalkboard.png", "#16483e")
            write_png(images / "game_images/english/english_waiting.png", "#313d4e")
            write_png(images / "thumbnail_models/english/english_thumbnail_model.png", "#234f41")
            voices = workspace / "voices"
            _build_synthetic_open_swara(voices)
            stack.enter_context(patch("video_creation._A_video_scripts.script_modifier.is_llm_online", return_value=False))
            for target in (
                "webui.jobs.adapters.voice.ensure_llama_stopped",
                "webui.jobs.adapters.images.ensure_llama_running",
                "webui.jobs.adapters.images.ensure_llama_stopped",
                "video_creation._C_image_generation.service.ensure_llama_running",
                "video_creation._C_image_generation.service.ensure_llama_stopped",
            ):
                stack.enter_context(patch(target))
            stack.enter_context(patch("webui.jobs.adapters.voice.OPEN_SWARA_DIR", voices))
            stack.enter_context(patch("webui.jobs.adapters.voice.COMFY_INPUT_DIR", workspace / "comfy-input"))
            stack.enter_context(patch("webui.jobs.adapters.voice.ComfyClient", return_value=RecordingFakeComfyClient()))
            image_service = ComfyImageResponses()
            stack.enter_context(patch("webui.jobs.adapters.images.ImageComfyClient._http_post", side_effect=image_service.post))
            stack.enter_context(patch("webui.jobs.adapters.images.ImageComfyClient._http_get", side_effect=image_service.get))
            stack.enter_context(patch(
                "webui.jobs.adapters.images.VisualPromptBuilder.build_general_prompt",
                return_value="An actor rehearses backstage in a hand-drawn theater scene.",
            ))
            stack.enter_context(patch(
                "webui.jobs.adapters.images.VisualPromptBuilder.build_storyboard_prompts",
                side_effect=lambda **kwargs: {name.lower(): f"Theater rehearsal scene: {text}" for name, text in kwargs["sections"].items()},
            ))
            stack.enter_context(patch("webui.jobs.adapters.assembly.Transcriber", TranscriptDouble))

            client = stack.enter_context(TestClient(create_app(workspace)))
            response = client.post("/api/sheets/sync", json={"apply_changes": True})
            self.assertEqual(response.status_code, 200, response.text)
            sync = self.wait_for(lambda: client.get("/api/sheets/status"), {"completed", "failed", "success", "done"})
            self.assertEqual(sync["result"]["updated_count"], 1, sync)
            revised_state = state_manager.get_script_state("EG01")
            self.assertIn(revised["hook"], revised_state["script_text"])
            self.assertTrue(all(revised_state["status"][stage] == "pending" for stage in DOWNSTREAM_STAGES))

            for stage in ("voice", "images", "thumbnails", "assembly"):
                with self.subTest(stage=stage):
                    self.queue(client, stage)

            updated = state_manager.get_script_state("EG01")
            for stage in ("voice_generation", "image_generation", "thumbnail_generation", "video_assembly"):
                self.assertEqual(updated["status"][stage], "done")
            self.assertGreaterEqual(len(image_service.images), 2)
            out_dir = get_script_output_dir("EG01", base_dir=workspace)
            video = Path(updated["assets"]["final_video"])
            thumbnail = Path(updated["assets"]["thumbnail_path"])
            self.assertTrue((out_dir / "images/script_EG01_challenge.png").is_file())
            self.assertTrue((out_dir / "script_EG01_subtitles.ass").is_file())
            with Image.open(thumbnail) as image:
                self.assertEqual(image.format, "PNG")
                image.verify()
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                check=True, capture_output=True, text=True, timeout=30,
            )
            metadata = json.loads(probe.stdout)
            streams = {stream["codec_type"]: stream for stream in metadata["streams"]}
            self.assertIn("audio", streams)
            self.assertEqual((streams["video"]["width"], streams["video"]["height"]), (VIDEO_WIDTH, VIDEO_HEIGHT))
            self.assertGreater(float(metadata["format"]["duration"]), 1)
            subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-f", "null", "-"], check=True, timeout=60)

            detail = client.get("/api/scripts/EG01")
            self.assertEqual(detail.status_code, 200, detail.text)
            media_path = detail.json()["assets"]["video"]
            preview = client.get("/api/media", params={"file": media_path}, headers={"Range": "bytes=0-255"})
            self.assertEqual(preview.status_code, 206, preview.text[:120])
            self.assertIn(b"ftyp", preview.content)

            previous_video = video.read_bytes()
            with patch("webui.jobs.adapters.assembly.VideoAssembler.assemble", return_value=False):
                self.queue(client, "assembly", expected="failed")
            self.assertEqual(video.read_bytes(), previous_video)
            self.assertEqual(state_manager.get_script_state("EG01")["assets"]["final_video"], str(video))
            self.queue(client, "assembly")
