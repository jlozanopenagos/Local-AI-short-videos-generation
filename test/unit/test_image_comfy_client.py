"""
test/unit/test_image_comfy_client.py — Unit tests for ImageComfyClient HTTP & pool methods.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
from video_creation._C_image_generation.core.comfy_client import ImageComfyClient


class TestImageComfyClient(unittest.TestCase):
    @patch("video_creation._C_image_generation.core.comfy_client.ImageComfyClient._load_and_convert_workflow")
    def setUp(self, mock_load):
        mock_load.return_value = {
            "6": {"inputs": {"text": ""}},
            "7": {"inputs": {"text": ""}},
            "3": {"inputs": {"seed": 0, "steps": 6}},
            "9": {"inputs": {"filename_prefix": ""}},
            "13": {"inputs": {"width": 576, "height": 1024}},
        }
        self.client = ImageComfyClient(
            api_url="http://127.0.0.1:8188",
            workflow_path=Path("dummy_workflow.json"),
        )

    def test_http_methods_exist(self):
        """Verify _http_get and _http_post exist and are callable on ImageComfyClient."""
        self.assertTrue(hasattr(self.client, "_http_get"))
        self.assertTrue(hasattr(self.client, "_http_post"))
        self.assertTrue(callable(self.client._http_get))
        self.assertTrue(callable(self.client._http_post))

    @patch("requests.post")
    def test_http_post_fallback_requests(self, mock_post):
        """Verify _http_post delegates to requests.post when mocked."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = self.client._http_post("http://127.0.0.1:8188/prompt", json={"test": True})
        self.assertEqual(res.status_code, 200)
        mock_post.assert_called_once()

    @patch("requests.get")
    def test_http_get_fallback_requests(self, mock_get):
        """Verify _http_get delegates to requests.get when mocked."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        res = self.client._http_get("http://127.0.0.1:8188/queue")
        self.assertEqual(res.status_code, 200)
        mock_get.assert_called_once()

    @patch("video_creation._C_image_generation.core.comfy_client.ImageComfyClient._http_post")
    def test_queue_prompt_calls_http_post(self, mock_post):
        """Verify _queue_prompt calls self._http_post."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"prompt_id": "test-prompt-id-123"}
        mock_post.return_value = mock_resp

        pid = self.client._queue_prompt({"test": "workflow"})
        self.assertEqual(pid, "test-prompt-id-123")
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()

