"""
test_layer/integration/test_status_tracker.py — Integration tests for central pipeline status tracker and manifest.
"""
import unittest
import tempfile
import csv
from pathlib import Path

from core.status_tracker import PipelineStatusTracker, CSV_COLUMNS


class TestStatusTrackerIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)
        self.tracker = PipelineStatusTracker(self.base_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_update_script_stage_status_creates_and_updates_manifest(self):
        # Seed initial row
        initial_rows = [{
            "ID": "EE01",
            "EXPRESSION": "Break a leg",
            "LANGUAGE": "english",
            "VIDEO_TYPE": "expression",
            "script_generation_status": "pending",
            "voice_generation_status": "pending",
            "image_generation_status": "pending",
            "thumbnail_generation_status": "pending",
            "video_assembly_status": "pending",
            "db_status": "PENDING"
        }]
        self.tracker.save_status_csv(initial_rows)

        # Update stage status for EE01
        self.tracker.update_script_stage_status("EE01", "script_generation", "done")
        manifest_path = self.base_dir / "state" / "pipeline_status.csv"
        self.assertTrue(manifest_path.exists())

        # Read back
        with manifest_path.open("r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            row = reader[0]
            self.assertEqual(row["ID"], "EE01")
            self.assertEqual(row["script_generation_status"], "done")

    def test_update_multiple_stages_same_script(self):
        initial_rows = [{
            "ID": "EE01",
            "EXPRESSION": "Break a leg",
            "LANGUAGE": "english",
            "VIDEO_TYPE": "expression",
            "script_generation_status": "pending",
            "voice_generation_status": "pending",
            "image_generation_status": "pending",
            "thumbnail_generation_status": "pending",
            "video_assembly_status": "pending",
            "db_status": "PENDING"
        }]
        self.tracker.save_status_csv(initial_rows)

        self.tracker.update_script_stage_status("EE01", "script_generation", "done")
        self.tracker.update_script_stage_status("EE01", "voice_generation", "done")
        self.tracker.update_script_stage_status("EE01", "image_generation", "done")

        manifest_path = self.base_dir / "state" / "pipeline_status.csv"
        with manifest_path.open("r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            row = reader[0]
            self.assertEqual(row["script_generation_status"], "done")
            self.assertEqual(row["voice_generation_status"], "done")
            self.assertEqual(row["image_generation_status"], "done")


if __name__ == "__main__":
    unittest.main()
