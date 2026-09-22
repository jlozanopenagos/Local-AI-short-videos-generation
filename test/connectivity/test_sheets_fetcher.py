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

# pyrefly: ignore [missing-import]
try:
    from connectivity.endpoints import (
        get_endpoint,
        register_endpoint,
        list_registered_endpoints,
        DEFAULT_FRENCH_EXPRESSION_URL,
    )
    from connectivity.sheets_fetcher import (
        fetch_sheet_data,
        save_connectivity_data,
        resolve_connectivity_output_dir,
        TARGET_COLUMNS,
    )
except (ImportError, ModuleNotFoundError):
    from main.connectivity.endpoints import (
        get_endpoint,
        register_endpoint,
        list_registered_endpoints,
        DEFAULT_FRENCH_EXPRESSION_URL,
    )
    from main.connectivity.sheets_fetcher import (
        fetch_sheet_data,
        save_connectivity_data,
        resolve_connectivity_output_dir,
        TARGET_COLUMNS,
    )


class TestSheetsFetcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_endpoint_resolution_defaults_to_french_expression(self):
        """Verify default resolution points to French Expression URL."""
        lang, vtype, url = get_endpoint()
        self.assertEqual(lang, "french")
        self.assertEqual(vtype, "expression")
        self.assertEqual(url, DEFAULT_FRENCH_EXPRESSION_URL)

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

    def test_save_connectivity_data_writes_csv_and_json(self):
        """Verify records are persisted to CSV and JSON with correct schemas."""
        records = [
            {"ID": "FE01", "expression": "Poser un lapin", "script": "Script 1"},
            {"ID": "FE02", "expression": "Avoir le cafard", "script": "Script 2"},
        ]

        csv_path, json_path = save_connectivity_data(
            records=records,
            language="french",
            video_type="expression",
            output_dir=self.test_output_dir,
        )

        self.assertTrue(csv_path.exists())
        self.assertTrue(json_path.exists())
        self.assertEqual(csv_path.name, "french_expression_connectivity.csv")
        self.assertEqual(json_path.name, "french_expression_connectivity.json")

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

        # Verify JSON content
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["language"], "french")
            self.assertEqual(data["video_type"], "expression")
            self.assertEqual(data["count"], 2)
            self.assertEqual(len(data["records"]), 2)
            self.assertEqual(data["records"][0]["script"], "Script 1")


if __name__ == "__main__":
    unittest.main()
