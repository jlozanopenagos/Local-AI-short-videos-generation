"""
test/unit/test_sheets_router.py — Unit tests for the Google Sheets Sync WebUI router.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
sys.path = [p for p in sys.path if not p.rstrip("/\\").endswith("tools")]
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# If tools/webui.py was imported as 'webui', clear it so package 'webui' is resolved
if "webui" in sys.modules and not hasattr(sys.modules["webui"], "__path__"):
    del sys.modules["webui"]

# pyrefly: ignore[missing-import]
from webui.routers.sheets import (
    router,
    _SHEETS_SYNC_STATE,
    _run_sheets_sync_worker,
    _count_existing_csvs,
    reset_sheets_sync_status,
    get_sheets_sync_status,
)


class TestSheetsRouter(unittest.TestCase):
    def setUp(self):
        # Reset state before each test
        reset_sheets_sync_status()

    def test_initial_status(self):
        """Verify initial state of the sheets sync router is idle."""
        status = get_sheets_sync_status()
        self.assertEqual(status["status"], "idle")
        self.assertEqual(status["progress"], 0)
        self.assertIsNone(status["result"])

    @patch("webui.routers.sheets._get_indexed_scripts")
    @patch("webui.routers.sheets.modify_video_script")
    @patch("webui.routers.sheets.audit_script_changes")
    @patch("webui.routers.sheets.fetch_all_sheets_corrected_scripts")
    def test_sync_worker_full_pipeline(self, mock_fetch, mock_audit, mock_modify, mock_index):
        """Verify the complete sync worker execution flow: purge -> fetch -> audit -> apply."""
        # 1. Mock fetcher returning 1 CSV file with 1 script
        csv_file = MagicMock()
        csv_file.name = "spanish_roleplay_script_to_change.csv"
        mock_fetch.return_value = [(csv_file, 1)]

        # 2. Mock audit returning 1 changed record
        mock_audit.return_value = (
            [
                {
                    "id": "SR02",
                    "file": "spanish_roleplay_script_to_change.csv",
                    "new_script": "Person 1: Hola\nPerson 2: Adios",
                    "current_spoken": "Person 1: Hola",
                    "words_current": 3,
                    "words_new": 5,
                    "diff_preview": "+ Adios",
                }
            ],
            [],  # identical
            [],  # missing
        )

        # 3. Mock modify_video_script returning True
        mock_modify.return_value = True

        # Run worker with clean_cache=False to avoid touching local disk during test
        _run_sheets_sync_worker(clean_cache=False, apply_changes=True)

        status = get_sheets_sync_status()
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["progress"], 100)
        self.assertIsNotNone(status["result"])
        self.assertEqual(status["result"]["changed_count"], 1)
        self.assertEqual(status["result"]["updated_count"], 1)
        self.assertEqual(status["result"]["failed_count"], 0)
        self.assertEqual(len(status["result"]["updated_records"]), 1)
        self.assertEqual(status["result"]["updated_records"][0]["id"], "SR02")

        mock_fetch.assert_called_once()
        mock_audit.assert_called_once()
        mock_modify.assert_called_once()
        mock_index.assert_called_once_with(force_refresh=True)

    @patch("webui.routers.sheets.modify_video_script")
    @patch("webui.routers.sheets.audit_script_changes")
    @patch("webui.routers.sheets.fetch_all_sheets_corrected_scripts")
    def test_sync_worker_audit_only_skips_modifications(self, mock_fetch, mock_audit, mock_modify):
        """Verify that apply_changes=False audits without modifying State JSONs."""
        mock_fetch.return_value = []
        mock_audit.return_value = (
            [
                {
                    "id": "SE01",
                    "file": "spanish_expression_script_to_change.csv",
                    "new_script": "New text",
                    "current_spoken": "Old text",
                    "words_current": 2,
                    "words_new": 2,
                    "diff_preview": "Modified",
                }
            ],
            [],
            [],
        )

        _run_sheets_sync_worker(clean_cache=False, apply_changes=False)

        status = get_sheets_sync_status()
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["result"]["updated_count"], 0)
        mock_modify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
