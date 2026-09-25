import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# pyrefly: ignore [missing-import]
if "faster_whisper" not in sys.modules:
    sys.modules["faster_whisper"] = MagicMock()

# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.main import resolve_bank_music


class TestMusicJamMatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bank_dir = Path(self.temp_dir.name) / "bank_music"
        self.cat_dir = self.bank_dir / "english" / "expression"
        self.cat_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy track files
        self.track1_file = self.cat_dir / "track_01_neo_soul.wav"
        self.track1_file.write_text("dummy audio", encoding="utf-8")
        self.track2_file = self.cat_dir / "track_02_suspense.wav"
        self.track2_file.write_text("dummy audio", encoding="utf-8")

        # Create catalog JSON
        self.catalog = {
            "category": "english/expression",
            "tracks": [
                {
                    "name": "Smooth Neo Soul",
                    "filename": "track_01_neo_soul.wav",
                    "emotion_slug": "relaxed, smooth, warm",
                    "matching_emotions": ["chill", "warm", "casual"],
                },
                {
                    "name": "Clock Ticking Tension",
                    "filename": "track_02_suspense.wav",
                    "emotion_slug": "tense, suspenseful, urgent",
                    "matching_emotions": ["urgency", "panic", "suspense"],
                },
            ]
        }
        (self.cat_dir / "bank_catalog.json").write_text(json.dumps(self.catalog), encoding="utf-8")
        self.script_output_dir = Path(self.temp_dir.name) / "output" / "EE01"
        self.script_output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resolve_bank_music_matches_emotion_trigger(self):
        """Verify resolve_bank_music accurately matches track with trigger keywords."""
        script_data = {
            "id": "EE01",
            "prompt_params": {
                "TARGET_LANGUAGE": "english",
                "EMOTIONAL_TRIGGER": "intense urgency and panic",
            },
            "content_metadata": {
                "video_type": "expression",
            }
        }

        with patch("video_creation._G_video_assembly.main.BANK_MUSIC_DIR", str(self.bank_dir)), \
             patch("builtins.print"):
            result = resolve_bank_music(script_data, self.script_output_dir)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "track_02_suspense.wav")

    def test_resolve_bank_music_deterministic_fallback(self):
        """Verify fallback selects deterministically when no emotion keyword matches."""
        script_data = {
            "id": "EE02",
            "prompt_params": {
                "TARGET_LANGUAGE": "english",
                "EMOTIONAL_TRIGGER": "neutral everyday scenario",
            },
            "content_metadata": {
                "video_type": "expression",
            }
        }

        with patch("video_creation._G_video_assembly.main.BANK_MUSIC_DIR", str(self.bank_dir)), \
             patch("builtins.print"):
            res1 = resolve_bank_music(script_data, self.script_output_dir)
            res2 = resolve_bank_music(script_data, self.script_output_dir)

        self.assertIsNotNone(res1)
        self.assertEqual(res1, res2)  # Deterministic hash for same script_id

    def test_resolve_bank_music_missing_bank_returns_none(self):
        """Verify returns None cleanly when category directory does not exist."""
        script_data = {
            "id": "IE01",
            "prompt_params": {
                "TARGET_LANGUAGE": "italian",
            },
            "content_metadata": {
                "video_type": "expression",
            }
        }

        with patch("video_creation._G_video_assembly.main.BANK_MUSIC_DIR", str(self.bank_dir)), \
             patch("builtins.print"):
            result = resolve_bank_music(script_data, self.script_output_dir)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
