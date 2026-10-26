"""
test_layer/unit/test_reset_stage_status.py — Unit tests for the pipeline stage status reset tool.
"""
import json
import tempfile
import unittest
from pathlib import Path

# Add main directory to sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_DIR = PROJECT_ROOT / "main"
for p in [str(PROJECT_ROOT), str(MAIN_DIR), str(MAIN_DIR / "core")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.database.reset_stage_status import reset_stage_status, VALID_STAGES


class TestResetStageStatus(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.state_dir = self.base_dir / "state"

        # Create structured sample state files
        self._create_sample_state("english", "expression", "EE01", "done", "done")
        self._create_sample_state("english", "expression", "EE02", "pending", "done")
        self._create_sample_state("french", "game", "FG01", "done", "pending")
        self._create_sample_state("spanish", "roleplay", "SR01", "done", "done")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_state(self, lang: str, vtype: str, sid: str, voice_status: str, img_status: str):
        target_dir = self.state_dir / lang / vtype
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"script_{sid}.json"
        data = {
            "id": sid,
            "status": {
                "script_generation": "done",
                "voice_generation": voice_status,
                "image_generation": img_status,
                "thumbnail_generation": "pending",
                "video_assembly": "pending",
            },
            "assets": {
                "audio_path": f"/path/to/{sid}.wav",
                "image_dir": f"/path/to/{sid}/images",
            },
            "prompt_params": {
                "TARGET_LANGUAGE": lang.capitalize(),
                "VIDEO_TYPE": vtype.upper(),
            }
        }
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def test_dry_run_does_not_modify_files(self):
        result = reset_stage_status(
            stage="voice_generation",
            target_status="pending",
            base_dir=self.base_dir,
            dry_run=True,
            sync_manifest=False,
        )
        self.assertEqual(result["total_scanned"], 4)
        self.assertEqual(result["total_matched"], 4)
        # EE01, FG01, SR01 have voice_generation == 'done', so 3 would be modified
        self.assertEqual(result["total_modified"], 3)

        # Verify on-disk file was NOT modified
        ee01_path = self.state_dir / "english" / "expression" / "script_EE01.json"
        with ee01_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["status"]["voice_generation"], "done")

    def test_reset_voice_generation_all_scripts(self):
        result = reset_stage_status(
            stage="voice_generation",
            target_status="pending",
            base_dir=self.base_dir,
            dry_run=False,
            sync_manifest=False,
        )
        self.assertEqual(result["total_modified"], 3)
        self.assertIn("EE01", result["modified_ids"])
        self.assertIn("FG01", result["modified_ids"])
        self.assertIn("SR01", result["modified_ids"])
        self.assertNotIn("EE02", result["modified_ids"])  # Already pending

        # Verify on disk
        for sid, lang, vtype in [
            ("EE01", "english", "expression"),
            ("EE02", "english", "expression"),
            ("FG01", "french", "game"),
            ("SR01", "spanish", "roleplay"),
        ]:
            fpath = self.state_dir / lang / vtype / f"script_{sid}.json"
            with fpath.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["status"]["voice_generation"], "pending")

    def test_filter_by_language_and_type(self):
        result = reset_stage_status(
            stage="voice_generation",
            target_status="pending",
            language="french",
            video_type="game",
            base_dir=self.base_dir,
            dry_run=False,
            sync_manifest=False,
        )
        self.assertEqual(result["total_matched"], 1)
        self.assertEqual(result["total_modified"], 1)
        self.assertEqual(result["modified_ids"], ["FG01"])

        # Check that English was untouched
        ee01_path = self.state_dir / "english" / "expression" / "script_EE01.json"
        with ee01_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["status"]["voice_generation"], "done")

    def test_filter_by_script_id(self):
        result = reset_stage_status(
            stage="voice_generation",
            target_status="pending",
            script_ids=["SR01"],
            base_dir=self.base_dir,
            dry_run=False,
            sync_manifest=False,
        )
        self.assertEqual(result["total_matched"], 1)
        self.assertEqual(result["total_modified"], 1)
        self.assertEqual(result["modified_ids"], ["SR01"])

    def test_clear_assets_flag(self):
        result = reset_stage_status(
            stage="voice_generation",
            target_status="pending",
            script_ids=["EE01"],
            base_dir=self.base_dir,
            clear_assets=True,
            dry_run=False,
            sync_manifest=False,
        )
        ee01_path = self.state_dir / "english" / "expression" / "script_EE01.json"
        with ee01_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("audio_path", data["assets"])
        self.assertIn("image_dir", data["assets"])  # other assets untouched

    def test_invalid_stage_raises_value_error(self):
        with self.assertRaises(ValueError):
            reset_stage_status(stage="non_existent_stage", base_dir=self.base_dir)


if __name__ == "__main__":
    unittest.main()
