"""
test_layer/integration/test_health_checks.py — Integration tests for AI services health assertions (ComfyUI & LLM).
"""
import unittest
from unittest.mock import patch, MagicMock

from config.health import (
    check_comfy_connection,
    check_llm_connection,
    check_all_services,
    require_services,
)


class TestHealthChecksIntegration(unittest.TestCase):
    @patch("config.health.requests.get")
    def test_comfy_connection_online(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        is_online, msg = check_comfy_connection(api_url="http://127.0.0.1:8188", timeout=1.0)
        self.assertTrue(is_online)
        self.assertIn("Reachable", msg)

    @patch("config.health.requests.get")
    def test_comfy_connection_offline_returns_false(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        is_online, msg = check_comfy_connection(api_url="http://127.0.0.1:8188", timeout=1.0)
        self.assertFalse(is_online)
        self.assertIn("Cannot connect", msg)

    @patch("config.health.requests.get")
    def test_comfy_connection_raise_on_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        with self.assertRaises(ConnectionError):
            check_comfy_connection(api_url="http://127.0.0.1:8188", timeout=1.0, raise_on_error=True)

    @patch("config.health.OpenAI")
    def test_llm_connection_online(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_client.models.list.return_value = ["model1"]
        mock_openai_cls.return_value = mock_client

        is_online, msg = check_llm_connection(base_url="http://127.0.0.1:8080/v1", timeout=1.0)
        self.assertTrue(is_online)
        self.assertIn("Reachable", msg)

    @patch("config.health.OpenAI")
    def test_llm_connection_offline_returns_false(self, mock_openai_cls):
        mock_openai_cls.side_effect = Exception("Timeout connecting to LLM")
        is_online, msg = check_llm_connection(base_url="http://127.0.0.1:8080/v1", timeout=1.0)
        self.assertFalse(is_online)
        self.assertIn("Cannot connect", msg)

    @patch("config.health.check_comfy_connection")
    @patch("config.health.check_llm_connection")
    def test_check_all_services_structure(self, mock_llm, mock_comfy):
        mock_comfy.return_value = (True, "Comfy reachable")
        mock_llm.return_value = (True, "LLM reachable")

        res = check_all_services(timeout=1.0)
        self.assertIn("ComfyUI", res)
        self.assertIn("LLM", res)
        self.assertTrue(res["ComfyUI"]["online"])
        self.assertTrue(res["LLM"]["online"])


if __name__ == "__main__":
    unittest.main()
