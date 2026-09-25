"""
test_layer/unit/test_watchdog.py — Unit tests for LLM & ComfyUI keep-alive and watchdog recovery.
"""
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
# pyrefly: ignore [missing-import]
import httpx

# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.core.llm import generate_response
# pyrefly: ignore [missing-import]
from video_creation._B_voice_generation.core.comfy_client import ComfyClient
# pyrefly: ignore [missing-import]
from video_creation._C_image_generation.core.comfy_client import ImageComfyClient


class TestWatchdog(unittest.TestCase):

    # ── LLM Watchdog Tests ────────────────────────────────────────────────────

    @patch("video_creation._A_video_scripts.core.llm.client")
    def test_llm_streaming_success(self, mock_client):
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=" World"))]

        mock_client.chat.completions.create.return_value = [chunk1, chunk2]

        result = generate_response("Test prompt", show_progress=False)
        self.assertEqual(result, "Hello World")
        mock_client.chat.completions.create.assert_called_once()

    @patch("video_creation._A_video_scripts.core.llm.time.sleep")
    @patch("video_creation._A_video_scripts.core.llm.client")
    def test_llm_streaming_recovers_after_stall(self, mock_client, mock_sleep):
        chunk_ok = MagicMock()
        chunk_ok.choices = [MagicMock(delta=MagicMock(content="Recovered after stall"))]

        mock_client.chat.completions.create.side_effect = [
            httpx.ReadTimeout("Socket stall detected"),
            [chunk_ok]
        ]

        result = generate_response("Test prompt", max_retries=2, show_progress=False)
        self.assertEqual(result, "Recovered after stall")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        mock_sleep.assert_called()

    # ── ComfyUI Voice Client Watchdog Tests ───────────────────────────────────

    @patch.object(ComfyClient, "_load_template", return_value={})
    @patch("video_creation._B_voice_generation.core.comfy_client.requests.get")
    @patch("video_creation._B_voice_generation.core.comfy_client.requests.post")
    def test_comfy_voice_ensure_clean_slate_when_queue_stuck(self, mock_post, mock_get, mock_load):
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "queue_running": [["prompt-123"]],
            "queue_pending": [["prompt-456"]],
        }
        mock_get.return_value = mock_get_resp

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post.return_value = mock_post_resp

        client = ComfyClient("http://127.0.0.1:8188", Path("dummy_workflow.json"))

        with patch("video_creation._B_voice_generation.core.comfy_client.time.sleep"):
            client.ensure_clean_slate()

        called_urls = [call.args[0] for call in mock_post.call_args_list]
        self.assertTrue(any("interrupt" in u for u in called_urls))
        self.assertTrue(any("queue" in u for u in called_urls))

    @patch.object(ComfyClient, "_load_template", return_value={})
    @patch("video_creation._B_voice_generation.core.comfy_client.time.sleep")
    def test_comfy_voice_auto_interrupt_on_stall(self, mock_sleep, mock_load):
        client = ComfyClient("http://127.0.0.1:8188", Path("dummy_workflow.json"))
        client.ensure_clean_slate = MagicMock()
        client._prepare_workflow = MagicMock(return_value={})
        client.queue_prompt = MagicMock(return_value="prompt-test")
        client.interrupt = MagicMock(return_value=True)
        client.download_file = MagicMock()

        success_history = {
            "outputs": {
                "8": {"audio": [{"filename": "out.flac", "subfolder": "audio", "type": "output"}]}
            }
        }
        client.poll_for_completion = MagicMock(side_effect=[
            TimeoutError("Execution stalled"),
            success_history
        ])

        dest_path = Path("fake_segment.flac")
        res = client.generate_voice_segment(
            ref_audio_name="ref.wav",
            target_text="Test dialogue text",
            language="English",
            gender="Female",
            context="",
            emotion="Calm",
            energy="MEDIUM",
            style="Conversational",
            output_prefix="audio/test",
            dest_path=dest_path,
            max_retries=2,
            stall_timeout=10,
        )

        self.assertEqual(res, dest_path)
        client.interrupt.assert_called_once()
        self.assertEqual(client.queue_prompt.call_count, 2)

    # ── ComfyUI Image Client Watchdog Tests ───────────────────────────────────

    @patch.object(ImageComfyClient, "_load_and_convert_workflow", return_value={})
    @patch("video_creation._C_image_generation.core.comfy_client.time.sleep")
    def test_comfy_image_auto_interrupt_on_stall(self, mock_sleep, mock_load):
        client = ImageComfyClient("http://127.0.0.1:8188", Path("dummy_workflow.json"))
        client.ensure_clean_slate = MagicMock()
        client._prepare_workflow = MagicMock(return_value={})
        client._queue_prompt = MagicMock(return_value="prompt-img")
        client.interrupt = MagicMock(return_value=True)
        client._download_image = MagicMock()

        success_history = {
            "outputs": {
                "9": {"images": [{"filename": "out.png", "subfolder": "images", "type": "output"}]}
            }
        }
        client._poll_for_completion = MagicMock(side_effect=[
            TimeoutError("Execution stalled"),
            success_history
        ])

        dest_path = Path("fake_image.png")
        res = client.generate_image(
            prompt_text="Detailed visual scene description",
            filename_prefix="Z-Image/test",
            dest_path=dest_path,
            max_retries=2,
            stall_timeout=10,
        )

        self.assertEqual(res, dest_path)
        client.interrupt.assert_called_once()
        self.assertEqual(client._queue_prompt.call_count, 2)


if __name__ == "__main__":
    unittest.main()
