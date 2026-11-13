"""
test/unit/test_gemini_auditor.py — Unit tests for Gemini prompt auditor with Result Checker.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# pyrefly: ignore[missing-import]
from core.gemini_auditor import (
    audit_general_prompt,
    _clean_gemini_output,
    _clean_gemini_output_with_anchors,
    _strip_redundant_tails,
    validate_gemini_core_prompt,
    detect_script_domain,
    get_video_type_directive,
    extract_character_anchors_from_output,
    POSITIVE_STYLE_PILLAR,
    NEGATIVE_PROMPT_SHIELD,
)


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

    def test_strip_redundant_tails(self):
        """Verify duplicate style tags or negative shields are cleanly stripped."""
        text = "Medium wide eye-level shot. Inside a workshop. Clean modern 2D cartoon narrative illustration, stylized 2D animation art style (thematic setting visible, NO 3D)"
        stripped = _strip_redundant_tails(text)
        self.assertEqual(stripped, "Medium wide eye-level shot. Inside a workshop")

    def test_validate_gemini_core_prompt(self):
        """Verify the Result Checker catches truncation, short responses, and missing pillars."""
        # 1. Truncation flag
        ok, reason = validate_gemini_core_prompt("Some text...", finish_reason="MAX_TOKENS")
        self.assertFalse(ok)
        self.assertIn("truncated", reason)

        # 2. Too short
        ok, reason = validate_gemini_core_prompt("Medium wide shot. Two students talk.")
        self.assertFalse(ok)
        self.assertIn("too short", reason)

        # 3. Cut off mid-sentence
        incomplete_text = (
            "Medium wide eye-level shot. Inside a chic retro Italian designer sneaker boutique and luxury leather footwear workshop, "
            "a 15-year-old female high-school student narrator with a sleek vibrant turquoise bob haircut stands on the left in a tailored "
            "mustard-yellow tweed waistcoat over an ivory collared silk blouse, high-waisted navy pleated trousers, and polished dark brown leather penny loafers. "
            "On the right her peer stands by the counter while golden afternoon sunbeams stream across the polished floor casting"
        )
        ok, reason = validate_gemini_core_prompt(incomplete_text)
        self.assertFalse(ok)
        self.assertIn("mid-sentence", reason)

        # 4. Valid rich core prompt
        valid_core = (
            "Medium wide eye-level shot. Inside a chic retro Italian designer sneaker boutique and luxury leather footwear workshop, "
            "a 15-year-old female high-school student narrator with a sleek vibrant turquoise bob haircut stands on the left in a tailored "
            "mustard-yellow tweed waistcoat over an ivory collared silk blouse, high-waisted navy pleated trousers, and polished dark brown leather penny loafers. "
            "On the right, her 15-year-old male friend with messy copper curls stands at the sleek glass counter dressed in an olive-green knit cardigan over an off-white henley shirt. "
            "Between them, the counter displays three towering designer shoe boxes and a vintage brass lever cash register. "
            "In the background, illuminated warm-wood shelving shows sneakers under amber afternoon sunlight, casting rich slate-blue directional cast shadows across the herringbone floor."
        )
        ok, reason = validate_gemini_core_prompt(valid_core)
        self.assertTrue(ok)
        self.assertEqual(reason, "Valid")

    def test_audit_general_prompt_requires_api_key(self):
        """Verify ValueError is raised if GEMINI_API_KEY is not configured."""
        script_data = {"id": "SR01", "script_text": "Hello"}
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True):
            with patch("config.GEMINI_API_KEY", ""):
                with self.assertRaises(ValueError) as ctx:
                    audit_general_prompt(script_data, api_key="")
                self.assertIn("GEMINI_API_KEY is not configured", str(ctx.exception))

    @patch("core.gemini_auditor.requests.post")
    def test_audit_general_prompt_successful_generation_and_stitching(self, mock_post):
        """Verify successful Gemini prompt generation, 800 token budget, and seamless 9-part stitching."""
        valid_core = (
            "Medium wide eye-level shot. Inside a sunny vintage city park skate plaza by a concrete bowl, "
            "a 16-year-old high-school student boy in a forest-green corduroy jacket laughs with expressive cartoon eyes. "
            "On the right, his 15-year-old female peer in a coral-pink pinafore vest smiles while holding a skateboard. "
            "Between them, a vintage bicycle leans against a lamppost free of floating icons. "
            "In the background, pastel facades glow under warm amber sunlight casting teal directional cast shadows."
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {
                                "text": f"```\n{valid_core}\n```"
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

        # Token budget is 800
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 800)
        self.assertIn("Tomar el pelo", payload["contents"][0]["parts"][0]["text"])

        # Check result has core + Part 8 + Part 9
        self.assertTrue(result.startswith("Medium wide eye-level shot. Inside a sunny vintage city park"))
        self.assertIn(POSITIVE_STYLE_PILLAR, result)
        self.assertIn(NEGATIVE_PROMPT_SHIELD, result)
        self.assertFalse(result.startswith("```"))

    def test_detect_script_domain_and_guidance(self):
        """Verify semantic domain is detected from topic/script keywords."""
        # 1. Family / Holiday dinner
        doc_family = {
            "content_metadata": {"language": "italian", "topic": "parenti vs genitori"},
            "script_text": "A Natale ci riuniamo a cena con i parenti a casa mia."
        }
        domain, guidance = detect_script_domain(doc_family)
        self.assertEqual(domain, "Family, Home & Holiday Gatherings")
        self.assertIn("dining room", guidance)

        # 2. Food / Dining
        doc_food = {
            "content_metadata": {"language": "spanish", "topic": "Pedir la cuenta"},
            "script_text": "En el restaurante comemos pasta y pizza deliciosa."
        }
        domain, guidance = detect_script_domain(doc_food)
        self.assertEqual(domain, "Food, Culinary & Dining")
        self.assertIn("culinary", guidance)

        # 3. Travel / Transit
        doc_travel = {
            "content_metadata": {"language": "french", "topic": "Prendre le train"},
            "script_text": "A la gare de Lyon, nous prenons le train avec nos valises."
        }
        domain, guidance = detect_script_domain(doc_travel)
        self.assertEqual(domain, "Travel, Transit & Commute")
        self.assertIn("transit", guidance)

    def test_get_video_type_directive(self):
        """Verify distinct video type directives for Expression vs Game vs Roleplay."""
        dir_game = get_video_type_directive("GAME")
        self.assertIn("Interactive Challenge Arena", dir_game)
        self.assertIn("timer", dir_game.lower())

        dir_roleplay = get_video_type_directive("ROLEPLAY")
        self.assertIn("Character Drama", dir_roleplay)
        self.assertIn("interpersonal", dir_roleplay.lower())

        dir_expr = get_video_type_directive("EXPRESSION")
        self.assertIn("Everyday Cultural Observation", dir_expr)
        self.assertIn("relatable", dir_expr.lower())

    def test_extract_character_anchors_from_output(self):
        """Verify [CHARACTER_ANCHORS] block is cleanly extracted into structured dictionary."""
        sample = (
            "[CHARACTER_ANCHORS]\n"
            "CHAR_1: 15-16yo high-school student boy | hair: messy dark-brown curls | attire: burgundy wool cardigan over jersey | shoes: leather work boots\n"
            "CHAR_2: 15-16yo high-school student girl | hair: copper-tinted bob | attire: indigo denim chore jacket | shoes: canvas sneakers\n"
            "[/CHARACTER_ANCHORS]\n\n"
            "Medium wide eye-level shot. Inside a dining room..."
        )
        cleaned, anchors = extract_character_anchors_from_output(sample)
        self.assertEqual(cleaned, "Medium wide eye-level shot. Inside a dining room...")
        self.assertEqual(anchors["char1_hair"], "messy dark-brown curls")
        self.assertEqual(anchors["char1_attire"], "burgundy wool cardigan over jersey")
        self.assertEqual(anchors["char1_shoes"], "leather work boots")
        self.assertEqual(anchors["char2_hair"], "copper-tinted bob")
        self.assertIn("Character appearance continuity", anchors["continuity_summary"])


if __name__ == "__main__":
    unittest.main()
