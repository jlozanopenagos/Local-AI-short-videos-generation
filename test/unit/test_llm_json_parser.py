"""
test_layer/unit/test_llm_json_parser.py — Unit tests for 4-tier LLM JSON extraction in _A_video_scripts/main.py.
"""
import unittest

# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.main import extract_json_from_llm


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
        # Should parse with strict=False or via regex/bracket fallback
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
