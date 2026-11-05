"""
test/unit/test_check_script_changes.py — Unit tests for check_script_changes auditor tool.
"""
import unittest
# pyrefly: ignore[missing-import]
from tools.check_script_changes import (
    extract_spoken_text_from_state,
    normalize_text_for_comparison,
    compute_preview_diff,
)


class TestCheckScriptChanges(unittest.TestCase):
    def test_extract_spoken_text_excludes_title(self):
        state = {
            "content_metadata": {
                "script": {
                    "title": "Unspoken Title",
                    "hook": "Spoken hook line.",
                    "setup": "Spoken setup line.",
                    "payoff": "Spoken payoff line.",
                }
            }
        }
        spoken = extract_spoken_text_from_state(state)
        self.assertNotIn("Unspoken Title", spoken)
        self.assertIn("Spoken hook line.", spoken)
        self.assertIn("Spoken setup line.", spoken)
        self.assertIn("Spoken payoff line.", spoken)

    def test_normalize_text_for_comparison(self):
        raw1 = "Here’s a ‘sample’ text   with\nmultiple   spaces."
        raw2 = "Here's a 'sample' text with multiple spaces."
        self.assertEqual(
            normalize_text_for_comparison(raw1),
            normalize_text_for_comparison(raw2),
        )

    def test_compute_preview_diff(self):
        old = "Line 1\nLine 2\nLine 3"
        new = "Line 1\nModified Line 2\nLine 3"
        diff = compute_preview_diff(old, new)
        self.assertIn("-Line 2", diff)
        self.assertIn("+Modified Line 2", diff)


if __name__ == "__main__":
    unittest.main()

