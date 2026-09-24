"""
test_reconcile_scripts.py — Unit tests for the Reconcile & Reorganize scripts service.

Verifies:
1. Reconciling exact matches in Google Sheets order.
2. Reordering local scripts that appear out of order.
3. Keeping the Google Sheets canonical expression name when local has variants.
4. Appending new local entries (e.g. FF06-FF15) to the end of the file.
5. Preserving sheet-only entries in place.
6. Writing clean CSVs with UTF-8 BOM.
7. Priority resolution in poster.py to pick scripts_to_post before scripts_to_see.
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

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
from connectivity.reconcile.service import (
    load_csv_records,
    normalize_text,
    reconcile_all_sheets,
    reconcile_sheet_data,
    reconcile_single_sheet,
    save_reconciled_csv,
)
# pyrefly: ignore [missing-import]
from connectivity.post_scripts.poster import get_source_csv_path


class TestReconcileScripts(unittest.TestCase):
    """Test suite for script reconciliation and reorganization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_normalize_text(self):
        """Verify normalize_text handles whitespace, quotes, and case."""
        self.assertEqual(normalize_text("  Avoir Le Cafard  "), "avoir le cafard")
        self.assertEqual(normalize_text("L’accent"), "l'accent")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    def test_reconcile_exact_matches_in_sheet_order(self):
        """Verify matching entries follow Google Sheet order with local scripts."""
        sheet_rows = [
            {"ID": "FE01", "expression": "Poser un lapin", "script": "old script 1"},
            {"ID": "FE02", "expression": "Tomber dans les pommes", "script": "old script 2"},
            {"ID": "FE03", "expression": "Avoir le cafard", "script": "old script 3"},
        ]
        # Local has different scripts and reverse order
        local_rows = [
            {"ID": "FE03", "expression": "Avoir le cafard", "script": "new local script 3"},
            {"ID": "FE01", "expression": "Poser un lapin", "script": "new local script 1"},
            {"ID": "FE02", "expression": "Tomber dans les pommes", "script": "new local script 2"},
        ]

        res = reconcile_sheet_data(local_rows, sheet_rows, "french", "expression")
        rows = res["reconciled_rows"]

        self.assertEqual(len(rows), 3)
        self.assertEqual([r["ID"] for r in rows], ["FE01", "FE02", "FE03"])
        self.assertEqual(rows[0]["script"], "new local script 1")
        self.assertEqual(rows[1]["script"], "new local script 2")
        self.assertEqual(rows[2]["script"], "new local script 3")
        self.assertEqual(res["exact_matches"], 3)
        self.assertEqual(res["new_local_appended"], 0)

    def test_reconcile_keeps_google_sheet_name_on_variant(self):
        """Verify Google Sheet expression is preserved when local has long scenario or notes."""
        sheet_rows = [
            {"ID": "FR01", "expression": "poser un lapin", "script": "old sheet script"},
            {"ID": "FE06", "expression": "blessé", "script": "old sheet script"},
        ]
        local_rows = [
            {"ID": "FR01", "expression": "Devant une terrasse de brasserie: un jeune homme...", "script": "latest roleplay script"},
            {"ID": "FE06", "expression": "Blessé (Injury/Hit)", "script": "latest expression script"},
        ]

        res = reconcile_sheet_data(local_rows, sheet_rows)
        rows = res["reconciled_rows"]

        self.assertEqual(len(rows), 2)
        # Keeps Google Sheet names
        self.assertEqual(rows[0]["ID"], "FR01")
        self.assertEqual(rows[0]["expression"], "poser un lapin")
        self.assertEqual(rows[0]["script"], "latest roleplay script")

        self.assertEqual(rows[1]["ID"], "FE06")
        self.assertEqual(rows[1]["expression"], "blessé")
        self.assertEqual(rows[1]["script"], "latest expression script")

        self.assertEqual(res["canonical_updates"], 2)

    def test_reconcile_appends_new_local_entries_to_end(self):
        """Verify new entries present in local but not in Google Sheets go to the end."""
        sheet_rows = [
            {"ID": "FF01", "expression": "Quatre-vingts", "script": "sheet 1"},
            {"ID": "FF02", "expression": "Oiseau", "script": "sheet 2"},
        ]
        local_rows = [
            {"ID": "FF01", "expression": "Quatre-vingts", "script": "local 1"},
            {"ID": "FF02", "expression": "Oiseau", "script": "local 2"},
            {"ID": "FF03", "expression": "crée", "script": "local 3"},
            {"ID": "FF04", "expression": "4 mots", "script": "local 4"},
        ]

        res = reconcile_sheet_data(local_rows, sheet_rows)
        rows = res["reconciled_rows"]

        self.assertEqual(len(rows), 4)
        self.assertEqual([r["ID"] for r in rows], ["FF01", "FF02", "FF03", "FF04"])
        self.assertEqual(rows[2]["ID"], "FF03")
        self.assertEqual(rows[2]["script"], "local 3")
        self.assertEqual(rows[3]["ID"], "FF04")
        self.assertEqual(rows[3]["script"], "local 4")
        self.assertEqual(res["new_local_appended"], 2)

    def test_reconcile_preserves_sheet_only_entries(self):
        """Verify entries in Google Sheets not found in local are preserved."""
        sheet_rows = [
            {"ID": "SR01", "expression": "Pedir ayuda", "script": "sheet script 1"},
            {"ID": "CODIGO CONFIRMAR", "expression": "Confirmacion", "script": "sheet code"},
        ]
        local_rows = [
            {"ID": "SR01", "expression": "Pedir ayuda", "script": "new local script 1"},
        ]

        res = reconcile_sheet_data(local_rows, sheet_rows)
        rows = res["reconciled_rows"]

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ID"], "SR01")
        self.assertEqual(rows[0]["script"], "new local script 1")
        self.assertEqual(rows[1]["ID"], "CODIGO CONFIRMAR")
        self.assertEqual(rows[1]["script"], "sheet code")
        self.assertEqual(res["sheet_only_preserved"], 1)

    def test_save_and_load_reconciled_csv(self):
        """Verify saving and reading reconciled CSV preserves UTF-8 characters."""
        csv_path = self.base_path / "test_reconciled.csv"
        rows = [
            {"ID": "FE01", "expression": "À l'improviste", "script": "Script français avec caractères: été, garçon"},
            {"ID": "FE02", "expression": "Tomber dans les pommes", "script": "Script 2"},
        ]

        save_reconciled_csv(csv_path, rows)
        self.assertTrue(csv_path.exists())

        loaded = load_csv_records(csv_path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["ID"], "FE01")
        self.assertEqual(loaded[0]["expression"], "À l'improviste")
        self.assertEqual(loaded[0]["script"], "Script français avec caractères: été, garçon")

    def test_reconcile_single_sheet_end_to_end(self):
        """Verify reconcile_single_sheet reads, reconciles, and saves to output directory."""
        s_dir = self.base_path / "scripts_to_see"
        c_dir = self.base_path / "connectivity" / "synced_sheets" / "_3_columns"
        o_dir = self.base_path / "connectivity" / "scripts_to_post"

        local_file = s_dir / "french" / "expression" / "french_expression_scripts.csv"
        sheet_file = c_dir / "french" / "expression" / "french_expression_connectivity.csv"
        local_file.parent.mkdir(parents=True, exist_ok=True)
        sheet_file.parent.mkdir(parents=True, exist_ok=True)

        save_reconciled_csv(sheet_file, [
            {"ID": "FE01", "expression": "poser un lapin", "script": "sheet 1"},
            {"ID": "FE02", "expression": "tomber dans les pommes", "script": "sheet 2"},
        ])
        save_reconciled_csv(local_file, [
            {"ID": "FE02", "expression": "Tomber dans les pommes", "script": "local 2"},
            {"ID": "FE01", "expression": "Poser un lapin", "script": "local 1"},
            {"ID": "FE03", "expression": "avoir le cafard", "script": "local 3"},
        ])

        res = reconcile_single_sheet(
            language="french",
            video_type="expression",
            scripts_dir=s_dir,
            connectivity_dir=c_dir,
            output_dir=o_dir,
            dry_run=False,
        )

        self.assertEqual(res["total_reconciled"], 3)
        self.assertEqual(res["new_local_appended"], 1)
        self.assertTrue(res["saved"])

        # Check saved CSV
        expected_output = o_dir / "french" / "expression" / "french_expression_scripts.csv"
        self.assertTrue(expected_output.exists())
        saved_rows = load_csv_records(expected_output)
        self.assertEqual([r["ID"] for r in saved_rows], ["FE01", "FE02", "FE03"])
        self.assertEqual(saved_rows[0]["expression"], "poser un lapin")  # Sheet name kept
        self.assertEqual(saved_rows[0]["script"], "local 1")

    def test_poster_get_source_csv_path_prioritizes_scripts_to_post(self):
        """Verify poster.get_source_csv_path picks scripts_to_post if present."""
        post_dir = self.base_path / "scripts_to_post" / "french" / "expression"
        see_dir = self.base_path / "scripts_to_see" / "french" / "expression"
        post_dir.mkdir(parents=True, exist_ok=True)
        see_dir.mkdir(parents=True, exist_ok=True)

        post_csv = post_dir / "french_expression_scripts.csv"
        see_csv = see_dir / "french_expression_scripts.csv"
        post_csv.write_text("ID,expression,script\nFE01,A,S\n", encoding="utf-8")
        see_csv.write_text("ID,expression,script\nFE01,A,S_old\n", encoding="utf-8")

        # Mock DEFAULT_SCRIPTS_TO_POST_DIR in poster
        from unittest.mock import patch
        with patch("connectivity.post_scripts.poster.DEFAULT_SCRIPTS_TO_POST_DIR", self.base_path / "scripts_to_post"), \
             patch("connectivity.post_scripts.poster.DEFAULT_SCRIPTS_TO_SEE_DIR", self.base_path / "scripts_to_see"):
            resolved = get_source_csv_path(language="french", video_type="expression")
            self.assertEqual(resolved, post_csv)


if __name__ == "__main__":
    unittest.main()
