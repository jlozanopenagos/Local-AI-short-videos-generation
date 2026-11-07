"""
test_layer/unit/test_metadata_builder.py — Unit tests for YouTube metadata builder and JSON extraction.
"""
import unittest
from unittest.mock import patch

# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.core.metadata_builder import (
    _extract_json,
    build_metadata,
    _FALLBACK_VALUES,
    _KEY_MAP,
)
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.main import extract_json_from_llm


class TestMetadataBuilder(unittest.TestCase):
    def test_extract_json_clean(self):
        raw = '{"title": "Valid Title", "description": "Valid Description"}'
        parsed = _extract_json(raw)
        self.assertEqual(parsed.get("title"), "Valid Title")
        self.assertEqual(parsed.get("description"), "Valid Description")

    def test_extract_json_with_fences(self):
        raw = """```json
{"title": "Fenced Title", "tags": "shorts, english"}
```"""
        parsed = _extract_json(raw)
        self.assertEqual(parsed.get("title"), "Fenced Title")
        self.assertEqual(parsed.get("tags"), "shorts, english")

    def test_extract_json_fallback_with_chatter(self):
        raw = 'Here is metadata:\n{"title": "Embedded Title"}\nDone!'
        parsed = _extract_json(raw)
        self.assertEqual(parsed.get("title"), "Embedded Title")

    def test_extract_json_invalid_returns_empty_dict(self):
        self.assertEqual(_extract_json("No json here"), {})

    @patch("video_creation._A_video_scripts.core.metadata_builder.generate_response")
    def test_build_metadata_success(self, mock_llm):
        mock_llm.return_value = """{
            "title": "Learn Break a Leg",
            "description": "The true meaning behind the famous idiom.",
            "short_description": "Idiom breakdown",
            "tags": "english, idioms, shorts",
            "hashtags": "#english #shorts",
            "label": "english_idioms",
            "filename": "english_break_a_leg.mp4"
        }"""
        result = build_metadata("Dummy script", {"TARGET_LANGUAGE": "english"})
        self.assertEqual(result["TITLE"], "Learn Break a Leg")
        self.assertEqual(result["DESCRIPTION"], "The true meaning behind the famous idiom.")
        self.assertEqual(result["SHORT_DESCRIPTION"], "Idiom breakdown")
        self.assertEqual(result["TAGS"], "english, idioms, shorts")
        self.assertEqual(result["HASHTAGS"], "#english #shorts")
        self.assertEqual(result["LABEL"], "english_idioms")
        self.assertEqual(result["FILENAME"], "english_break_a_leg.mp4")

    @patch("video_creation._A_video_scripts.core.metadata_builder.generate_response")
    def test_build_metadata_fallbacks_on_partial_response(self, mock_llm):
        mock_llm.return_value = '{"title": "Only Title Provided"}'
        result = build_metadata("Dummy script", {"TARGET_LANGUAGE": "english"})
        self.assertEqual(result["TITLE"], "Only Title Provided")
        self.assertEqual(result["DESCRIPTION"], _FALLBACK_VALUES["description"])
        self.assertEqual(result["FILENAME"], _FALLBACK_VALUES["filename"])


class TestLLMJsonParser(unittest.TestCase):
    def test_direct_json_parse(self):
        raw = '{"script": {"title": "Direct Test", "hook": "Hello world"}}'
        result = extract_json_from_llm(raw)
        self.assertIn("script", result)
        self.assertEqual(result["script"]["title"], "Direct Test")

    def test_markdown_fence_stripping(self):
        raw = """```json
{
    "script": {
        "title": "Fenced Title",
        "hook": "Fenced Hook"
    }
}
```"""
        result = extract_json_from_llm(raw)
        self.assertIn("script", result)
        self.assertEqual(result["script"]["title"], "Fenced Title")

    def test_conversational_chatter_wrapping(self):
        raw = """Sure, here is the viral short script you requested:

{
    "script": {
        "title": "Chatter Wrapped",
        "hook": "Caught in the chatter"
    }
}

Hope this helps! Let me know if you need changes."""
        result = extract_json_from_llm(raw)
        self.assertIn("script", result)
        self.assertEqual(result["script"]["title"], "Chatter Wrapped")

    def test_unescaped_newlines_in_dialogue_recovery(self):
        raw = """{
    "script": {
        "title": "Multi-Line Dialogue",
        "DIALOGUE_PART_1": "PERSON_ONE (Panicked): We only have 4 minutes!
PERSON_TWO (Calm): Take a breath."
    }
}"""
        result = extract_json_from_llm(raw)
        self.assertIn("script", result)
        self.assertIn("DIALOGUE_PART_1", result["script"])

    def test_empty_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            extract_json_from_llm("")
        with self.assertRaises(ValueError):
            extract_json_from_llm("   \n\t  ")

    def test_garbage_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            extract_json_from_llm("This response does not contain any JSON objects at all.")


if __name__ == "__main__":
    unittest.main()
