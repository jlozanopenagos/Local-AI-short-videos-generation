"""
test_layer/integration/test_expression_db.py — Integration tests for SQLite + CSV hybrid expression database.
"""
import unittest
import tempfile
import csv
from pathlib import Path

from core.expression_db import ExpressionDB


class TestExpressionDBIntegration(unittest.TestCase):
    def setUp(self):
        try:
            self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        except TypeError:
            self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.db_path = self.base_dir / "database" / "expressions.db"
        self.database_dir = self.base_dir / "database"
        self.db = ExpressionDB(
            db_path=self.db_path,
            database_dir=self.database_dir,
            auto_sync=False
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_db_initialization_creates_sqlite_file_and_tables(self):
        self.assertTrue(self.db_path.exists())
        with self.db._get_connection() as conn:
            tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            self.assertIn("expressions", tables)
            self.assertIn("meta", tables)

    def test_add_and_query_expression_defaults_to_pending(self):
        with self.db._get_connection() as conn:
            conn.execute(
                "INSERT INTO expressions (id, expression, context, language, video_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                ("EE01", "Break a leg", "Stage luck", "english", "EXPRESSION", "PENDING")
            )
            conn.commit()

        row = self.db.get_expression("EE01")
        self.assertIsNotNone(row)
        self.assertEqual(row["expression"], "Break a leg")
        self.assertEqual(row["status"].upper(), "PENDING")
        self.assertFalse(self.db.is_done("EE01"))

    def test_master_gate_rule_is_done(self):
        # By default, not done
        with self.db._get_connection() as conn:
            conn.execute(
                "INSERT INTO expressions (id, expression, context, language, video_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                ("EE01", "Break a leg", "Stage luck", "english", "EXPRESSION", "PENDING")
            )
            conn.commit()
        self.assertFalse(self.db.is_done("EE01"))

        # User marks DONE
        with self.db._get_connection() as conn:
            conn.execute("UPDATE expressions SET status = 'DONE' WHERE id = 'EE01'")
            conn.commit()

        self.assertTrue(self.db.is_done("EE01"))

    def test_csv_export_sync(self):
        with self.db._get_connection() as conn:
            conn.execute(
                "INSERT INTO expressions (id, expression, context, language, video_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                ("EE01", "Break a leg", "Stage luck", "english", "EXPRESSION", "PENDING")
            )
            conn.commit()

        # Trigger sync to export english_expressions.csv
        self.db.sync()
        csv_path = self.db.get_csv_path("english")
        self.assertTrue(csv_path.exists())

        with csv_path.open("r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            self.assertEqual(reader[0]["ID"], "EE01")
            self.assertEqual(reader[0]["EXPRESSION"], "Break a leg")
            self.assertEqual(reader[0]["STATUS"], "PENDING")


if __name__ == "__main__":
    unittest.main()
