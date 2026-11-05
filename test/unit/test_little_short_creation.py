"""
test_little_short_creation.py — Senior QA Unit Tests for Little Short / Teaser Generator.

Verifies:
1. Timestamp and seconds lapse parsing across formats (integers, floats, MM:SS, separators).
2. Validation rules (negative times, inverted ranges, too-short clips).
3. Script ID lookup and state handling.
4. Video assembly graph orchestration with Opening card integration and strict exclusion of closure card.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure paths are set
TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
CORE_DIR = MAIN_DIR / "core"
ASSEMBLY_DIR = MAIN_DIR / "video_creation" / "_G_video_assembly"

for p in [str(MAIN_DIR), str(CORE_DIR), str(ASSEMBLY_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore[missing-import]
from _G_video_assembly.little_short_creation import (
    parse_timestamp_value,
    parse_lapse,
    format_seconds_tag,
    create_little_short,
)


class TestLittleShortCreation(unittest.TestCase):
    def test_parse_timestamp_value_valid(self):
        """Verify numeric and MM:SS timestamp strings parse accurately."""
        self.assertEqual(parse_timestamp_value("10"), 10.0)
        self.assertEqual(parse_timestamp_value("10.5"), 10.5)
        self.assertEqual(parse_timestamp_value("0:10"), 10.0)
        self.assertEqual(parse_timestamp_value("1:30"), 90.0)
        self.assertEqual(parse_timestamp_value("01:00:10"), 3610.0)

    def test_parse_timestamp_value_invalid(self):
        """Verify malformed timestamps raise ValueError."""
        with self.assertRaises(ValueError):
            parse_timestamp_value("abc")
        with self.assertRaises(ValueError):
            parse_timestamp_value("1:2:3:4")

    def test_parse_lapse_various_formats(self):
        """Verify parse_lapse parses standard, spaced, colon, and verbal lapse strings."""
        self.assertEqual(parse_lapse("10-16"), (10.0, 16.0))
        self.assertEqual(parse_lapse(" 10 - 16 "), (10.0, 16.0))
        self.assertEqual(parse_lapse("4.5-10.2"), (4.5, 10.2))
        self.assertEqual(parse_lapse("0:04-0:10"), (4.0, 10.0))
        self.assertEqual(parse_lapse("10 to 16"), (10.0, 16.0))
        self.assertEqual(parse_lapse("10, 16"), (10.0, 16.0))
        self.assertEqual(parse_lapse("4:10"), (4.0, 10.0))

    def test_parse_lapse_validation_errors(self):
        """Verify parse_lapse catches invalid or inverted lapse inputs."""
        # Empty input
        with self.assertRaises(ValueError):
            parse_lapse("")

        # Start equals end
        with self.assertRaises(ValueError):
            parse_lapse("10-10")

        # Start greater than end
        with self.assertRaises(ValueError):
            parse_lapse("16-10")

        # Negative start time
        with self.assertRaises(ValueError):
            parse_lapse("-5-10")

    def test_format_seconds_tag(self):
        """Verify seconds formatting creates clean, filename-friendly strings."""
        self.assertEqual(format_seconds_tag(10.0), "10")
        self.assertEqual(format_seconds_tag(4.0), "4")
        self.assertEqual(format_seconds_tag(10.5), "10.5")
        self.assertEqual(format_seconds_tag(10.25), "10.25")

    def test_create_little_short_missing_state(self):
        """Verify create_little_short returns None when script ID does not exist."""
        mock_sm = MagicMock()
        mock_sm.get_script_state.return_value = None

        res = create_little_short(
            script_id="NONEXISTENT99",
            start_sec=10.0,
            end_sec=16.0,
            state_manager=mock_sm,
        )
        self.assertIsNone(res)

    def test_create_little_short_missing_final_video(self):
        """Verify create_little_short returns None when final master video is absent."""
        mock_sm = MagicMock()
        mock_sm.get_script_state.return_value = {
            "id": "EE99",
            "metadata": {"LABEL": "english"},
            "assets": {"final_video": "/nonexistent/video.mp4"},
        }

        with patch("pathlib.Path.exists", return_value=False):
            res = create_little_short(
                script_id="EE99",
                start_sec=10.0,
                end_sec=16.0,
                state_manager=mock_sm,
            )
            self.assertIsNone(res)

    def test_create_little_short_start_beyond_duration(self):
        """Verify create_little_short returns None when start time exceeds video duration."""
        mock_sm = MagicMock()
        mock_sm.get_script_state.return_value = {
            "id": "EE99",
            "metadata": {"LABEL": "english"},
            "assets": {"final_video": "test_video.mp4"},
        }

        with patch("pathlib.Path.exists", return_value=True), \
             patch("_G_video_assembly.little_short_creation.get_video_duration", return_value=30.0):
            res = create_little_short(
                script_id="EE99",
                start_sec=35.0,
                end_sec=40.0,
                state_manager=mock_sm,
            )
            self.assertIsNone(res)

    @patch("ffmpeg.output")
    @patch("ffmpeg.concat")
    @patch("ffmpeg.input")
    def test_create_little_short_orchestration_success(self, mock_input, mock_concat, mock_output):
        """Verify end-to-end little short assembly builds FFmpeg graph without closure card."""
        mock_sm = MagicMock()
        mock_sm.get_script_state.return_value = {
            "id": "EE01",
            "metadata": {"LABEL": "english"},
            "assets": {
                "final_video": "dummy_final.mp4",
                "opening_card": "dummy_open.png",
                "closure_card": "dummy_close.png",  # Should be ignored for little shorts
            },
        }

        mock_output.return_value.overwrite_output.return_value.run.return_value = (b"", b"")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("_G_video_assembly.little_short_creation.get_video_duration", return_value=41.0), \
             patch("pathlib.Path.mkdir"):
            res = create_little_short(
                script_id="EE01",
                start_sec=10.0,
                end_sec=16.0,
                state_manager=mock_sm,
            )
            self.assertIsNotNone(res)
            self.assertTrue(str(res).endswith("script_EE01_little_10-16.mp4"))
            mock_sm.save_script_state.assert_called_once()

            # Ensure concat was called with exactly 2 inputs (Opening card + Clip) and NO closure card
            video_concat_call = mock_concat.call_args_list[0]
            # args before kwargs
            video_inputs = [a for a in video_concat_call.args]
            self.assertEqual(len(video_inputs), 2, "Expected exactly 2 video streams (Opening + Clip, no closure)")


if __name__ == "__main__":
    unittest.main()
