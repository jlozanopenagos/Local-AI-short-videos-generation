"""
test_script_to_change.py — Senior QA Unit Tests for:
1. 20-second default timeout in _A_video_scripts main.py.
2. CLI and interactive option for changing scripts from CSV in input/csv/script_to_change/.
3. Requirement that state JSON property "script_generation" is set to "pending" BEFORE the new script is generated.
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# pyrefly: ignore [missing-import]
from core.cli_prompt import prompt_production_mode
# pyrefly: ignore [missing-import]
from core.state_manager import StateManager, resolve_lang_and_type
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.main import process_scripts_to_change_from_csv


class TestScriptToChange(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.state_dir = self.base_dir / "state"
        self.csv_dir = self.base_dir / "input" / "csv" / "script_to_change"
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.state_manager = StateManager(self.base_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_prompt_production_mode_offers_script_to_change_choice(self):
        """Verify prompt_production_mode accepts choice 5 when allow_script_to_change_mode is True."""
        with patch("core.cli_prompt.sys.stdin.isatty", return_value=True), \
             patch("core.cli_prompt._timed_choice", return_value="5"):
            result, mode = prompt_production_mode(
                stage_title="Part A: Video Scripts",
                asset_name="scripts",
                timeout=20.0,
                allow_fun_facts_mode=True,
                allow_script_to_change_mode=True,
                return_mode=True,
            )
            self.assertEqual(mode, "script_to_change")
            self.assertIsNone(result)

    def test_prompt_production_mode_20s_timeout_display(self):
        """Verify prompt_production_mode passes 20s timeout to _timed_choice."""
        with patch("core.cli_prompt.sys.stdin.isatty", return_value=True), \
             patch("core.cli_prompt._timed_choice", return_value="1") as mock_choice:
            prompt_production_mode(
                stage_title="Part A: Video Scripts",
                asset_name="scripts",
                timeout=20.0,
                allow_fun_facts_mode=True,
                allow_script_to_change_mode=True,
            )
            mock_choice.assert_called_once()
            _, kwargs = mock_choice.call_args
            self.assertEqual(kwargs.get("timeout"), 20.0)

    def test_resolve_lang_and_type_from_id(self):
        """Verify language and video type are accurately inferred from canonical script ID."""
        self.assertEqual(resolve_lang_and_type("EE01"), ("english", "expression"))
        self.assertEqual(resolve_lang_and_type("EG05"), ("english", "game"))
        self.assertEqual(resolve_lang_and_type("ER03"), ("english", "roleplay"))
        self.assertEqual(resolve_lang_and_type("EF12"), ("english", "fun_facts"))
        self.assertEqual(resolve_lang_and_type("FE02"), ("french", "expression"))
        self.assertEqual(resolve_lang_and_type("SR01"), ("spanish", "roleplay"))
        self.assertEqual(resolve_lang_and_type("IG04"), ("italian", "game"))

    def test_state_json_set_to_pending_before_doing_new_script(self):
        """
        Critical Test: Ensure that when changing a script from CSV, the state JSON
        has 'script_generation': 'pending' BEFORE the new script formatting is executed.
        """
        script_id = "EE01"
        # 1. Initialize existing state with script_generation = "done"
        initial_state = {
            "id": script_id,
            "status": {
                "script_generation": "done",
                "voice_generation": "done",
                "image_generation": "done",
                "thumbnail_generation": "done",
                "video_assembly": "done",
            },
            "prompt_params": {
                "ID": script_id,
                "EXPRESSION": "Break a leg",
                "TARGET_LANGUAGE": "English",
                "VIDEO_TYPE": "EXPRESSION",
            },
            "script_text": '{"title": "Old Script", "hook": "Old"}',
        }
        self.state_manager.save_script_state(script_id, initial_state)

        # 2. Create CSV in input/csv/script_to_change/
        csv_file = self.csv_dir / "update_ee01.csv"
        new_script_text = (
            "Title: New Break A Leg\n"
            "Hook: Stop saying good luck!\n"
            "Setup: Theater people consider it bad luck.\n"
            "Discovery: Say break a leg instead.\n"
            "Example: Tell your co-star to break a leg tonight.\n"
            "Payoff: Share this tip with friends!"
        )
        with csv_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "NEW_SCRIPT"])
            writer.writeheader()
            writer.writerow({"ID": script_id, "NEW_SCRIPT": new_script_text})

        # 3. Mock modify_video_script to inspect disk state AT THE TIME it is called
        observed_status_before_generation = []

        def mock_modify(script_id, raw_script_text, reset_downstream=True, base_dir=None):
            # Read state directly from disk to verify it was set to pending
            disk_state = self.state_manager.get_script_state(script_id)
            observed_status_before_generation.append(disk_state["status"]["script_generation"])
            # Now simulate successful completion
            disk_state["status"]["script_generation"] = "done"
            self.state_manager.save_script_state(script_id, disk_state)
            return True

        with patch("video_creation._A_video_scripts.main.modify_video_script", side_effect=mock_modify):
            res = process_scripts_to_change_from_csv(
                base_dir=self.base_dir,
                csv_path=str(csv_file),
                auto=True,
            )

        self.assertEqual(res, 0)
        self.assertEqual(len(observed_status_before_generation), 1)
        # Verify it was 'pending' before modify_video_script ran
        self.assertEqual(observed_status_before_generation[0], "pending")

        # Verify final state after completion is done
        final_state = self.state_manager.get_script_state(script_id)
        self.assertEqual(final_state["status"]["script_generation"], "done")

    def test_process_scripts_to_change_missing_columns_logs_error(self):
        """Verify invalid CSV without required columns is rejected cleanly without crashing."""
        csv_file = self.csv_dir / "invalid.csv"
        with csv_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["WRONG_1", "WRONG_2"])
            writer.writeheader()
            writer.writerow({"WRONG_1": "123", "WRONG_2": "abc"})

        res = process_scripts_to_change_from_csv(
            base_dir=self.base_dir,
            csv_path=str(csv_file),
            auto=True,
        )
        self.assertEqual(res, 1)


if __name__ == "__main__":
    unittest.main()
