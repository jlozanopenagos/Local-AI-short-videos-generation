"""
test_post_scripts.py — Unit Tests for Posting Scripts to Google Sheets.

Verifies:
1. Loading source CSVs with UTF-8 BOM handling.
2. Range spec parsing (10-20, 01-50, FE10-FE20).
3. Filtering by all, range, and specific IDs.
4. HTTP POST client payload building, redirect handling, and error diagnostics.
5. Service functions: post_single_sheet and post_all_sheets with mocked client.
"""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure main project is on sys.path
TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
if str(MAIN_DIR) in sys.path:
    sys.path.remove(str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# pyrefly: ignore [missing-import]
from connectivity.core.client import post_sheet_rows
# pyrefly: ignore [missing-import]
from connectivity.post_scripts.poster import (
    filter_scripts,
    get_source_csv_path,
    load_source_scripts_csv,
    parse_operation_input,
    parse_range_spec,
    post_all_sheets,
    post_single_sheet,
    prompt_column_option,
)


class TestPostScripts(unittest.TestCase):
    """Test suite for post_scripts functionality."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Create sample CSV with UTF-8 BOM
        self.sample_csv_path = self.base_path / "french" / "expression" / "french_expression_scripts.csv"
        self.sample_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with self.sample_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "expression", "script"])
            writer.writeheader()
            for i in range(1, 26):
                writer.writerow({
                    "ID": f"FE{i:02d}",
                    "expression": f"Expression {i}",
                    "script": f"Script content for item {i}",
                })

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_source_scripts_csv_with_utf8_bom(self):
        """Verify load_source_scripts_csv strips BOM and returns clean records."""
        rows = load_source_scripts_csv(self.sample_csv_path)
        self.assertEqual(len(rows), 25)
        self.assertEqual(rows[0]["ID"], "FE01")
        self.assertEqual(rows[0]["expression"], "Expression 1")
        self.assertEqual(rows[0]["script"], "Script content for item 1")
        self.assertEqual(rows[24]["ID"], "FE25")

    def test_parse_range_spec_valid(self):
        """Verify parse_range_spec handles multiple range formats."""
        self.assertEqual(parse_range_spec("10-20"), (10, 20))
        self.assertEqual(parse_range_spec("01-50"), (1, 50))
        self.assertEqual(parse_range_spec("FE10-FE20"), (10, 20))
        self.assertEqual(parse_range_spec("20-10"), (10, 20))  # Auto-swap inverted range

    def test_parse_range_spec_invalid(self):
        """Verify parse_range_spec raises ValueError on invalid syntax."""
        with self.assertRaises(ValueError):
            parse_range_spec("invalid_range")
        with self.assertRaises(ValueError):
            parse_range_spec("10-")

    def test_filter_scripts_all(self):
        """Verify mode='all' returns all rows unchanged."""
        rows = load_source_scripts_csv(self.sample_csv_path)
        filtered = filter_scripts(rows, mode="all")
        self.assertEqual(len(filtered), 25)

    def test_filter_scripts_range(self):
        """Verify mode='range' filters correctly between start and end numbers."""
        rows = load_source_scripts_csv(self.sample_csv_path)
        filtered = filter_scripts(rows, mode="range", range_spec="05-10")
        self.assertEqual(len(filtered), 6)
        expected_ids = [f"FE{i:02d}" for i in range(5, 11)]
        self.assertEqual([r["ID"] for r in filtered], expected_ids)

    def test_filter_scripts_ids(self):
        """Verify mode='ids' filters by exact ID string or numeric equivalence."""
        rows = load_source_scripts_csv(self.sample_csv_path)
        filtered = filter_scripts(rows, mode="ids", ids=["FE02", "FE07", "FE19"])
        self.assertEqual(len(filtered), 3)
        self.assertEqual([r["ID"] for r in filtered], ["FE02", "FE07", "FE19"])

    def test_filter_scripts_ids_comma_separated(self):
        """Verify mode='ids' handles comma-separated strings inside list."""
        rows = load_source_scripts_csv(self.sample_csv_path)
        filtered = filter_scripts(rows, mode="ids", ids=["FE01, FE03", "FE05"])
        self.assertEqual(len(filtered), 3)
        self.assertEqual([r["ID"] for r in filtered], ["FE01", "FE03", "FE05"])

    @patch("requests.post")
    def test_post_sheet_rows_success(self, mock_post):
        """Verify post_sheet_rows builds correct payload and parses response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "status": "success",
            "updated_count": 10,
            "appended_count": 0,
            "total_affected": 10,
        })
        mock_response.json.return_value = {
            "status": "success",
            "updated_count": 10,
            "appended_count": 0,
            "total_affected": 10,
        }
        mock_post.return_value = mock_response

        rows = [{"ID": "FE01", "expression": "Test", "script": "Script"}]
        res = post_sheet_rows(
            endpoint_url="https://script.google.com/test",
            rows=rows,
            spreadsheet_id="test_sheet_id_123",
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["updated_count"], 10)

        # Check posted payload
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["json"]["spreadsheet_id"], "test_sheet_id_123")
        self.assertEqual(call_kwargs["json"]["rows"], rows)

    @patch("requests.post")
    def test_post_sheet_rows_html_error_page(self, mock_post):
        """Verify post_sheet_rows raises clear diagnostic error if Apps Script returned HTML error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>No se encontró la función: doPost</body></html>"
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as ctx:
            post_sheet_rows(
                endpoint_url="https://script.google.com/test",
                rows=[{"ID": "FE01", "expression": "E", "script": "S"}],
            )
        self.assertIn("Google Apps Script returned an error page", str(ctx.exception))
        self.assertIn("doPost", str(ctx.exception))

    @patch("time.sleep")
    @patch("requests.post")
    def test_post_sheet_rows_transient_drive_lock_retries_and_succeeds(self, mock_post, mock_sleep):
        """Verify post_sheet_rows detects transient Drive lock, retries, and succeeds."""
        resp_lock = MagicMock()
        resp_lock.status_code = 200
        resp_lock.text = "<html><body>Drive No se pudo abrir el archivo en este momento. Verifica la dirección e inténtalo de nuevo.</body></html>"

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.text = '{"status": "success", "updated_count": 1, "appended_count": 0, "total_affected": 1}'
        resp_ok.json.return_value = {"status": "success", "updated_count": 1, "appended_count": 0, "total_affected": 1}

        mock_post.side_effect = [resp_lock, resp_ok]

        res = post_sheet_rows(
            endpoint_url="https://script.google.com/test",
            rows=[{"ID": "FE01", "expression": "E", "script": "S"}],
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_affected"], 1)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    @patch("requests.post")
    def test_post_sheet_rows_transient_drive_lock_fallback_on_final_attempt(self, mock_post, mock_sleep):
        """Verify post_sheet_rows provides resilient success result if Drive lock persists on final attempt."""
        resp_lock = MagicMock()
        resp_lock.status_code = 200
        resp_lock.text = "<html><body>Drive No se pudo abrir el archivo en este momento.</body></html>"

        mock_post.return_value = resp_lock

        res = post_sheet_rows(
            endpoint_url="https://script.google.com/test",
            rows=[{"ID": "FE01", "expression": "E", "script": "S"}],
        )

        self.assertEqual(res["status"], "success")
        self.assertTrue(res.get("transient_notice"))
        self.assertIn("No se pudo abrir el archivo", res.get("warning", ""))
        self.assertEqual(res["total_affected"], 1)
        self.assertEqual(mock_post.call_count, 3)

    @patch("connectivity.post_scripts.poster.post_sheet_rows")
    def test_post_single_sheet_service(self, mock_post_rows):
        """Verify post_single_sheet ties reading, filtering, and posting together."""
        mock_post_rows.return_value = {
            "status": "success",
            "updated_count": 5,
            "appended_count": 0,
            "total_affected": 5,
        }

        res = post_single_sheet(
            language="french",
            video_type="expression",
            mode="range",
            range_spec="01-05",
            source_dir=self.base_path,
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["filtered_count"], 5)
        self.assertEqual(res["total_in_csv"], 25)
        self.assertEqual(res["updated_count"], 5)
        mock_post_rows.assert_called_once()

    def test_load_source_scripts_csv_with_four_columns(self):
        """Verify load_source_scripts_csv parses SCRIPT_CHANGED when include_script_changed=True."""
        four_col_csv = self.base_path / "french_expression_4cols.csv"
        with four_col_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "expression", "script", "SCRIPT_CHANGED"])
            writer.writeheader()
            writer.writerow({
                "ID": "FE01",
                "expression": "Bonjour",
                "script": "Script 1",
                "SCRIPT_CHANGED": "Script 1 Changed",
            })

        # When include_script_changed is True
        rows_4 = load_source_scripts_csv(four_col_csv, include_script_changed=True)
        self.assertEqual(len(rows_4), 1)
        self.assertEqual(rows_4[0]["ID"], "FE01")
        self.assertEqual(rows_4[0]["expression"], "Bonjour")
        self.assertEqual(rows_4[0]["script"], "Script 1")
        self.assertEqual(rows_4[0]["SCRIPT_CHANGED"], "Script 1 Changed")

        # When include_script_changed is False
        rows_3 = load_source_scripts_csv(four_col_csv, include_script_changed=False)
        self.assertEqual(len(rows_3), 1)
        self.assertNotIn("SCRIPT_CHANGED", rows_3[0])

    @patch("requests.post")
    def test_post_sheet_rows_with_include_script_changed(self, mock_post):
        """Verify post_sheet_rows passes include_script_changed=True in POST payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"status": "success", "updated_count": 1, "appended_count": 0, "total_affected": 1})
        mock_response.json.return_value = {"status": "success", "updated_count": 1, "appended_count": 0, "total_affected": 1}
        mock_post.return_value = mock_response

        rows = [{"ID": "FE01", "expression": "Test", "script": "Script", "SCRIPT_CHANGED": "Changed"}]
        res = post_sheet_rows(
            endpoint_url="https://script.google.com/test",
            rows=rows,
            include_script_changed=True,
        )
        self.assertEqual(res["status"], "success")
        call_kwargs = mock_post.call_args[1]
        self.assertTrue(call_kwargs["json"]["include_script_changed"])

    @patch("connectivity.post_scripts.poster.post_sheet_rows")
    def test_post_single_sheet_with_include_script_changed(self, mock_post_rows):
        """Verify post_single_sheet forwards include_script_changed to post_sheet_rows."""
        mock_post_rows.return_value = {
            "status": "success",
            "updated_count": 1,
            "appended_count": 0,
            "total_affected": 1,
        }

        # Create a sample 4-column CSV
        sample_4col = self.base_path / "french" / "expression" / "french_expression_scripts.csv"
        with sample_4col.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "expression", "script", "SCRIPT_CHANGED"])
            writer.writeheader()
            writer.writerow({
                "ID": "FE01",
                "expression": "Test",
                "script": "Script",
                "SCRIPT_CHANGED": "Changed",
            })

        res = post_single_sheet(
            language="french",
            video_type="expression",
            mode="all",
            source_dir=self.base_path,
            include_script_changed=True,
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["include_script_changed"])
        mock_post_rows.assert_called_once()
        self.assertTrue(mock_post_rows.call_args[1]["include_script_changed"])

    def test_parse_operation_input(self):
        """Verify parse_operation_input handles single and compound operation inputs."""
        self.assertEqual(parse_operation_input(""), ("1", None))
        self.assertEqual(parse_operation_input("1"), ("1", None))
        self.assertEqual(parse_operation_input("2"), ("2", None))
        self.assertEqual(parse_operation_input("3"), ("3", None))
        self.assertEqual(parse_operation_input("4"), ("4", None))
        self.assertEqual(parse_operation_input("0"), ("0", None))

        # Compound inputs (choice 1 -> False (3 cols), choice 2 -> True (4 cols))
        self.assertEqual(parse_operation_input("1.1"), ("1", False))
        self.assertEqual(parse_operation_input("1.2"), ("1", True))
        self.assertEqual(parse_operation_input("1 1"), ("1", False))
        self.assertEqual(parse_operation_input("1 2"), ("1", True))
        self.assertEqual(parse_operation_input("2-1"), ("2", False))
        self.assertEqual(parse_operation_input("2-2"), ("2", True))
        self.assertEqual(parse_operation_input("3,2"), ("3", True))
        self.assertEqual(parse_operation_input("4:2"), ("4", True))

        # Invalid inputs
        self.assertIsNone(parse_operation_input("5"))
        self.assertIsNone(parse_operation_input("invalid"))
        self.assertIsNone(parse_operation_input("1.3"))

    def test_prompt_column_option(self):
        """Verify prompt_column_option correctly handles user input."""
        with patch("builtins.input", return_value=""), patch("builtins.print"):
            self.assertFalse(prompt_column_option())

        with patch("builtins.input", return_value="1"), patch("builtins.print"):
            self.assertFalse(prompt_column_option())

        with patch("builtins.input", return_value="2"), patch("builtins.print"):
            self.assertTrue(prompt_column_option())

        # Invalid then valid
        with patch("builtins.input", side_effect=["invalid", "2"]), patch("builtins.print"):
            self.assertTrue(prompt_column_option())


if __name__ == "__main__":
    unittest.main()
