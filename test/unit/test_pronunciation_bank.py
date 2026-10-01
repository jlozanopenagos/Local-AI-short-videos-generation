"""Unit tests for pronunciation_bank.py.

Validates:
1. Heteronym registry completeness (coverage of core 25+ English heteronyms).
2. Phonetic metadata integrity (IPA, casing, carrier, stress syllable).
3. Retrieval and storage of verified studio clips.
4. Fallback handling when clips do not exist.
"""

import tempfile
import unittest
from pathlib import Path

from video_creation._B_voice_generation.core.pronunciation_bank import (
    HETERONYM_REGISTRY,
    get_heteronym_data,
    get_pronunciation_clip,
    has_pronunciation_clip,
    list_available_clips,
    save_pronunciation_clip,
)


class TestPronunciationBank(unittest.TestCase):
    """Test suite for pronunciation bank and heteronym registry."""

    def test_registry_completeness(self):
        """Verify core English heteronyms are registered with complete metadata."""
        expected_words = [
            "present", "project", "record", "permit", "object",
            "contract", "increase", "decrease", "import", "export",
            "protest", "contest", "conduct", "conflict", "defect"
        ]
        self.assertGreaterEqual(len(HETERONYM_REGISTRY), 25)

        for word in expected_words:
            self.assertIn(word, HETERONYM_REGISTRY)
            entry = HETERONYM_REGISTRY[word]
            self.assertIn("noun", entry)
            self.assertIn("verb", entry)

            # Validate noun metadata
            self.assertEqual(entry["noun"]["stress_syllable"], 1)
            self.assertTrue(entry["noun"]["cased"][:2].isupper())
            self.assertTrue(entry["noun"]["ipa"].startswith("/"))
            self.assertIn(word, entry["noun"]["carrier"])

            # Validate verb metadata
            self.assertEqual(entry["verb"]["stress_syllable"], 2)
            self.assertTrue(entry["verb"]["cased"][-2:].isupper())
            self.assertTrue(entry["verb"]["ipa"].startswith("/"))
            self.assertIn(word, entry["verb"]["carrier"])

    def test_get_heteronym_data_casing_and_whitespace(self):
        """Verify get_heteronym_data is case and whitespace insensitive."""
        data_upper = get_heteronym_data("PROJECT")
        data_spaced = get_heteronym_data("  project  ")
        self.assertIsNotNone(data_upper)
        self.assertEqual(data_upper, data_spaced)
        self.assertEqual(data_upper["noun"]["cased"], "PROject")

        # Unknown word returns None
        self.assertIsNone(get_heteronym_data("nonexistentword123"))

    def test_clip_storage_and_retrieval(self):
        """Verify saving and retrieving clips from bank storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank_dir = Path(tmpdir) / "bank"
            bank_dir.mkdir()

            dummy_src = Path(tmpdir) / "source.flac"
            dummy_src.write_bytes(b"dummy_audio_bytes")

            # Initially not present
            self.assertFalse(has_pronunciation_clip("permit", "noun", bank_dir=bank_dir))
            self.assertIsNone(get_pronunciation_clip("permit", "noun", bank_dir=bank_dir))

            # Save clip
            saved = save_pronunciation_clip("permit", "noun", dummy_src, bank_dir=bank_dir)
            self.assertTrue(saved.exists())
            self.assertEqual(saved.name, "permit_noun.flac")

            # Now present
            self.assertTrue(has_pronunciation_clip("permit", "noun", bank_dir=bank_dir))
            retrieved = get_pronunciation_clip("permit", "noun", bank_dir=bank_dir)
            self.assertEqual(retrieved, saved)

    def test_list_available_clips(self):
        """Verify list_available_clips returns full dictionary mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank_dir = Path(tmpdir) / "bank"
            bank_dir.mkdir()

            coverage = list_available_clips(bank_dir=bank_dir)
            self.assertIn("present", coverage)
            self.assertFalse(coverage["present"]["noun"])
            self.assertFalse(coverage["present"]["verb"])


if __name__ == "__main__":
    unittest.main()
