"""
test_sheets_fetcher.py — Senior QA Unit Tests for Google Sheets Connectivity.

Verifies:
1. Endpoint resolution and modular registry.
2. HTTP GET fetching, redirect handling, and JSON parsing.
3. Column extraction and normalization for 'ID', 'expression', 'script'.
4. CSV and JSON disk persistence in the connectivity output directory.
"""

import csv
import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure main project is at index 0 of sys.path
TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
if str(MAIN_DIR) in sys.path:
    sys.path.remove(str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

try:
    # pyrefly: ignore [missing-import]
    from connectivity.core.endpoints import (
        get_endpoint,
        register_endpoint,
        list_registered_endpoints,
        DEFAULT_FRENCH_EXPRESSION_URL,
    )
    # pyrefly: ignore [missing-import]
    from connectivity.sheet_sync.sync_service import (
        fetch_sheet_data,
        save_connectivity_data,
        resolve_connectivity_output_dir,
        TARGET_COLUMNS,
        FOUR_COLUMNS,
    )
except (ImportError, ModuleNotFoundError):
    from main.connectivity.core.endpoints import (
        get_endpoint,
        register_endpoint,
        list_registered_endpoints,
        DEFAULT_FRENCH_EXPRESSION_URL,
    )
    from main.connectivity.sheet_sync.sync_service import (
        fetch_sheet_data,
        save_connectivity_data,
        resolve_connectivity_output_dir,
        TARGET_COLUMNS,
        FOUR_COLUMNS,
    )


class TestSheetsFetcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_endpoint_resolution_defaults_to_french_expression(self):
        """Verify default resolution points to French Expression target."""
        # pyrefly: ignore [missing-import]
        from connectivity.core.endpoints import build_fetch_url
        lang, vtype, url = get_endpoint()
        self.assertEqual(lang, "french")
        self.assertEqual(vtype, "expression")
        self.assertEqual(url, build_fetch_url(DEFAULT_FRENCH_EXPRESSION_URL))

    def test_endpoint_custom_url_override(self):
        """Verify custom URL override bypasses registry."""
        custom = "https://script.google.com/macros/s/CUSTOM_URL/exec"
        lang, vtype, url = get_endpoint(language="spanish", video_type="roleplay", custom_url=custom)
        self.assertEqual(lang, "spanish")
        self.assertEqual(vtype, "roleplay")
        self.assertEqual(url, custom)

    def test_endpoint_register_and_switch(self):
        """Verify dynamic registration allows switching endpoints modularly."""
        new_url = "https://script.google.com/macros/s/SPANISH_EXPRESSION/exec"
        register_endpoint("spanish", "expression", new_url)

        lang, vtype, url = get_endpoint("spanish", "expression")
        self.assertEqual(lang, "spanish")
        self.assertEqual(vtype, "expression")
        self.assertEqual(url, new_url)

    def test_option_a_extract_spreadsheet_id_from_url_and_id(self):
        """Verify extract_spreadsheet_id correctly parses Google Sheet URLs and raw IDs."""
        # pyrefly: ignore [missing-import]
        from connectivity.core.endpoints import extract_spreadsheet_id
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0"
        self.assertEqual(extract_spreadsheet_id(url), "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")

        raw_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        self.assertEqual(extract_spreadsheet_id(raw_id), "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")

        # Web App URLs should not be treated as spreadsheet IDs
        webapp = "https://script.google.com/macros/s/AKfycbx.../exec"
        self.assertIsNone(extract_spreadsheet_id(webapp))

    def test_option_a_build_fetch_url_routes_through_master(self):
        """Verify Option A: Sheet ID routes through MASTER_WEBAPP_URL with ?id= and &sheet=."""
        # pyrefly: ignore [missing-import]
        from connectivity.core.endpoints import build_fetch_url, MASTER_WEBAPP_URL
        sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        resolved = build_fetch_url(sheet_id, tab="English_Scripts")
        self.assertIn(f"id={sheet_id}", resolved)
        self.assertIn("sheet=English_Scripts", resolved)
        self.assertTrue(resolved.startswith(MASTER_WEBAPP_URL))

    def test_option_a_get_endpoint_with_sheet_id(self):
        """Verify get_endpoint supports passing sheet_id directly."""
        lang, vtype, url = get_endpoint(language="english", video_type="expression", sheet_id="1MyTestSheetId12345")
        self.assertEqual(lang, "english")
        self.assertEqual(vtype, "expression")
        self.assertIn("id=1MyTestSheetId12345", url)

    def test_fetch_sheet_data_parses_json_payload(self):
        """Verify fetching extracts and normalizes the 3 target columns (ID, expression, script)."""
        mock_payload = {
            "status": "success",
            "count": 2,
            "data": [
                {
                    "ID": "FE01",
                    "expression": "Poser un lapin",
                    "script": "New script for Poser un lapin",
                },
                {
                    "id": "fe02",
                    "EXPRESSION": "Avoir le cafard",
                    "script_changed": "New script for Avoir le cafard",
                },
                {
                    # Empty row - should be filtered out
                    "ID": "",
                    "expression": "",
                    "script": "",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            records = fetch_sheet_data("https://fake-url.com")

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["ID"], "FE01")
        self.assertEqual(records[0]["expression"], "Poser un lapin")
        self.assertEqual(records[0]["script"], "New script for Poser un lapin")

        # Check normalization of lowercase keys and legacy script_changed alias
        self.assertEqual(records[1]["ID"], "FE02")
        self.assertEqual(records[1]["expression"], "Avoir le cafard")
        self.assertEqual(records[1]["script"], "New script for Avoir le cafard")

    def test_fetch_sheet_data_handles_error_status(self):
        """Verify RuntimeError is raised when Google Apps Script returns error status."""
        mock_payload = {
            "status": "error",
            "message": "Required column 'ID' was not found in sheet headers."
        }

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            with self.assertRaises(RuntimeError) as ctx:
                fetch_sheet_data("https://fake-url.com")
            self.assertIn("Required column 'ID'", str(ctx.exception))

    def test_save_connectivity_data_writes_csv(self):
        """Verify records are persisted to CSV in the language/type subfolder."""
        records = [
            {"ID": "FE01", "expression": "Poser un lapin", "script": "Script 1"},
            {"ID": "FE02", "expression": "Avoir le cafard", "script": "Script 2"},
        ]

        csv_path = save_connectivity_data(
            records=records,
            language="french",
            video_type="expression",
            output_dir=self.test_output_dir,
        )

        self.assertTrue(csv_path.exists())
        self.assertEqual(csv_path.name, "french_expression_connectivity.csv")
        self.assertEqual(csv_path.parent, self.test_output_dir / "_3_columns" / "french" / "expression")

        # Verify CSV content
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, TARGET_COLUMNS)
            self.assertEqual(reader.fieldnames, ["ID", "expression", "script"])
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["ID"], "FE01")
            self.assertEqual(rows[0]["expression"], "Poser un lapin")
            self.assertEqual(rows[0]["script"], "Script 1")

    def test_save_connectivity_data_writes_four_columns(self):
        """Verify records are persisted with 4 columns in the _4_columns subfolder."""
        records = [
            {"ID": "FE01", "expression": "Poser un lapin", "script": "Script 1", "SCRIPT_CHANGED": "Fixed Script 1"},
            {"ID": "FE02", "expression": "Avoir le cafard", "script": "Script 2", "SCRIPT_CHANGED": ""},
        ]

        csv_path = save_connectivity_data(
            records=records,
            language="french",
            video_type="expression",
            output_dir=self.test_output_dir,
            include_script_changed=True,
        )

        self.assertTrue(csv_path.exists())
        self.assertEqual(csv_path.name, "french_expression_connectivity.csv")
        self.assertEqual(csv_path.parent, self.test_output_dir / "_4_columns" / "french" / "expression")

        # Verify 4 columns CSV content
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, FOUR_COLUMNS)
            self.assertEqual(reader.fieldnames, ["ID", "expression", "script", "SCRIPT_CHANGED"])
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["ID"], "FE01")
            self.assertEqual(rows[0]["expression"], "Poser un lapin")
            self.assertEqual(rows[0]["script"], "Script 1")
            self.assertEqual(rows[0]["SCRIPT_CHANGED"], "Fixed Script 1")
            self.assertEqual(rows[1]["SCRIPT_CHANGED"], "")

    def test_sync_sheet_with_four_columns(self):
        """Verify sync_sheet passes include_script_changed through and saves 4 columns."""
        # pyrefly: ignore [missing-import]
        from connectivity.sheet_sync.sync_service import sync_sheet

        mock_payload = {
            "status": "success",
            "count": 1,
            "data": [
                {
                    "ID": "EE01",
                    "expression": "Break a leg",
                    "script": "Original script",
                    "SCRIPT_CHANGED": "Polished script",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = sync_sheet(
                language="english",
                video_type="expression",
                output_dir=self.test_output_dir,
                include_script_changed=True,
            )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["include_script_changed"])
        self.assertEqual(result["columns"], FOUR_COLUMNS)
        self.assertIn("_4_columns", result["csv_path"])

    def test_prompt_include_script_changed_choices(self):
        """Verify prompt_include_script_changed in cli.py handles user responses correctly."""
        # pyrefly: ignore [missing-import]
        from connectivity.cli import prompt_include_script_changed

        # Test affirmative choices
        for aff in ["y", "yes", "2", "4", "Y", "YES"]:
            with patch("builtins.input", return_value=aff):
                self.assertTrue(prompt_include_script_changed())

        # Test negative or default choices
        for neg in ["", "n", "no", "1", "3", "N", "NO"]:
            with patch("builtins.input", return_value=neg):
                self.assertFalse(prompt_include_script_changed())

    def test_legacy_backward_compatibility_imports(self):
        """Verify legacy module import paths (connectivity.endpoints and connectivity.sheets_fetcher) continue to resolve."""
        import connectivity
        # pyrefly: ignore [missing-import]
        from connectivity.endpoints import get_endpoint as legacy_get_endpoint
        # pyrefly: ignore [missing-import]
        from connectivity.sheets_fetcher import sync_sheet as legacy_sync_sheet

        self.assertTrue(callable(legacy_get_endpoint))
        self.assertTrue(callable(legacy_sync_sheet))


if __name__ == "__main__":
    unittest.main()

