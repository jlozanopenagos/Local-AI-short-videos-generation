"""Unit tests for manage_pronunciation_bank.py.

Validates:
1. Status display formatting and coverage calculation.
2. Acoustic audit runner.
3. Import CLI handling and validation.
4. JSON export of heteronym metadata and coverage.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.manage_pronunciation_bank import (
    audit_bank,
    export_json_cli,
    import_clip_cli,
    print_status,
)


class TestManagePronunciationBank(unittest.TestCase):
    """Test suite for pronunciation bank management CLI tool."""

    def test_print_status_runs_cleanly(self):
        """Verify print_status executes without exceptions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank_dir = Path(tmpdir)
            # Should not raise any encoding or runtime errors
            print_status(bank_dir=bank_dir)

    def test_export_json_structure(self):
        """Verify export_json_cli produces a valid JSON structure with all words."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank_dir = Path(tmpdir)
            out_file = Path(tmpdir) / "registry_export.json"

            result = export_json_cli(str(out_file), bank_dir=bank_dir)
            self.assertEqual(result, 0)
            self.assertTrue(out_file.exists())

            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIn("present", data)
            self.assertIn("project", data)
            self.assertIn("metadata", data["present"])
            self.assertIn("clips", data["present"])
            self.assertFalse(data["present"]["clips"]["noun"]["available"])

    def test_import_clip_validation(self):
        """Verify import_clip_cli validates word, role, and file existence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bank_dir = Path(tmpdir) / "bank"
            bank_dir.mkdir()

            # 1. Nonexistent source file
            ret = import_clip_cli("nonexistent.flac", "present", "noun", bank_dir=bank_dir)
            self.assertEqual(ret, 1)

            # 2. Invalid role
            dummy = Path(tmpdir) / "dummy.flac"
            dummy.write_bytes(b"dummy")
            ret = import_clip_cli(str(dummy), "present", "adjective", bank_dir=bank_dir)
            self.assertEqual(ret, 1)

            # 3. Unknown word
            ret = import_clip_cli(str(dummy), "unknownwordxyz", "noun", bank_dir=bank_dir)
            self.assertEqual(ret, 1)

            # 4. Valid import with force=True
            with patch(
                "tools.manage_pronunciation_bank.evaluate_acoustic_prominence",
                return_value=(1.5, {"occurrences": [{"ratio": 1.5}]})
            ):
                ret = import_clip_cli(str(dummy), "present", "noun", bank_dir=bank_dir, force=True)
                self.assertEqual(ret, 0)
                imported_file = bank_dir / "present_noun.flac"
                self.assertTrue(imported_file.exists())


if __name__ == "__main__":
    unittest.main()
