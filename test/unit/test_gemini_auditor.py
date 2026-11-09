"""
test/unit/test_gemini_auditor.py — Unit tests for Gemini prompt auditor.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# pyrefly: ignore[missing-import]
from core.gemini_auditor import audit_general_prompt, _clean_gemini_output


class TestGeminiAuditor(unittest.TestCase):
    def test_clean_gemini_output_strips_markdown_fences(self):
        """Verify markdown code fences and conversational preambles are stripped."""
        raw = "```markdown\nInside a vintage record shop, two teens discuss music...\n```"
        self.assertEqual(_clean_gemini_output(raw), "Inside a vintage record shop, two teens discuss music...")

        raw_text_fence = "```text\nInside an art studio with easel...\n```"
        self.assertEqual(_clean_gemini_output(raw_text_fence), "Inside an art studio with easel...")

        raw_prefix = "Here is the new general prompt:\nInside a botanical garden..."
        self.assertEqual(_clean_gemini_output(raw_prefix), "Inside a botanical garden...")

        raw_quoted = '"A bustling night market with lanterns and two students"'
        self.assertEqual(_clean_gemini_output(raw_quoted), "A bustling night market with lanterns and two students")

    def test_audit_general_prompt_requires_api_key(self):
        """Verify ValueError is raised if GEMINI_API_KEY is not configured."""
        script_data = {"id": "SR01", "script_text": "Hello"}
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True):
            with patch("config.GEMINI_API_KEY", ""):
                with self.assertRaises(ValueError) as ctx:
                    audit_general_prompt(script_data, api_key="")
                self.assertIn("GEMINI_API_KEY is not configured", str(ctx.exception))

    @patch("core.gemini_auditor.requests.post")
    def test_audit_general_prompt_successful_generation(self, mock_post):
        """Verify successful Gemini prompt generation and payload construction."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "```\nMedium wide shot. Inside a sunny vintage city park skate plaza by a concrete bowl, two students laugh... (thematic setting visible, NO 3D)\n```"
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        script_data = {
            "id": "SR02",
            "content_metadata": {
                "language": "Spanish",
                "video_type": "ROLEPLAY",
                "topic": "Tomar el pelo",
                "speakers_gender": {"PERSON_ONE": "female", "PERSON_TWO": "male"},
            },
            "script_text": '{"hook": "Anoche vi a un gato..."}',
            "assets": {"general_prompt": "Old generic kitchen prompt"},
        }

        result = audit_general_prompt(script_data, api_key="TEST_FAKE_KEY")
        self.assertTrue(mock_post.called)
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["params"], {"key": "TEST_FAKE_KEY"})
        payload = call_kwargs["json"]
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 350)
        self.assertIn("Tomar el pelo", payload["contents"][0]["parts"][0]["text"])

        # Check cleaned result
        self.assertTrue(result.startswith("Medium wide shot. Inside a sunny vintage city park"))
        self.assertFalse(result.startswith("```"))


if __name__ == "__main__":
    unittest.main()

