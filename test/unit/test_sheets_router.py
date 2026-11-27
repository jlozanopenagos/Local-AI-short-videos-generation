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

    def test_modify_video_script_schema_harmonization_and_asset_invalidation(self):
        """Verify that modify_video_script produces canonical lowercase keys, preserves character anchors & voices, and clears stale image prompts."""
        import json
        import tempfile
        # pyrefly: ignore[missing-import]
        from video_creation._A_video_scripts.script_modifier import modify_video_script
        # pyrefly: ignore[missing-import]
        from core.state_manager import StateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            state_mgr = StateManager(base_dir)

            # 1. Setup mock ER01 state
            initial_state = {
                "id": "ER01",
                "status": {
                    "script_generation": "done",
                    "voice_generation": "done",
                    "image_generation": "done",
                    "thumbnail_generation": "done",
                    "video_assembly": "done",
                },
                "prompt_params": {
                    "SCRIPT_ID": "ER01",
                    "TARGET_LANGUAGE": "English",
                    "VIDEO_TYPE": "ROLEPLAY",
                    "TOPIC": "Break a leg",
                },
                "script_text": "{}",
                "content_metadata": {
                    "video_type": "ROLEPLAY",
                    "language": "English",
                    "topic": "Break a leg",
                    "character_anchors": {
                        "has_two_characters": True,
                        "char1_gender": "female",
                        "char1_hair": "dark ponytail",
                    },
                    "speakers_voice": {
                        "Narrator": "golden_narrator.wav",
                        "PERSON_ONE": "voice_1.wav",
                    },
                    "speakers_gender": {
                        "Narrator": "female",
                        "PERSON_ONE": "female",
                    },
                    "anchor_environment": "Dressing room backstage.",
                    "script": {},
                },
                "assets": {
                    "image_prompts": {
                        "hook": "Old hook prompt",
                        "dialogue_part_1": "Old dialogue prompt",
                    },
                    "character_anchors": {
                        "char1_gender": "female",
                    },
                },
                "metadata": {
                    "TITLE": "Old Title",
                    "DESCRIPTION": "Old Desc",
                    "TAGS": "old, tags",
                },
            }

            state_mgr.save_script_state("ER01", initial_state)

            raw_new_script = """Hook: A frantic actor forgets their line backstage before the show starts!
dialogue_part_1: PERSON_ONE (Panicked): I forgot the words!
PERSON_TWO (Calm): Deep breaths, you got this.
dialogue_part_2: PERSON_ONE (Nervous): What if I mess up?
PERSON_TWO (Smirking): Break a leg!
dialogue_part_3: PERSON_ONE (Relieved): Wait, break a leg means good luck?
PERSON_TWO (Chuckling): Exactly, theater folklore!
dialogue_part_4: PERSON_ONE (Smiling): Okay, I'm ready.
PERSON_TWO (Nodding): Go crush it!
payoff: A theatrical superstition turns stage panic into pure energy!"""

            ok = modify_video_script(
                script_id="ER01",
                raw_script_text=raw_new_script,
                reset_downstream=True,
                base_dir=base_dir,
                auto_update_csv=False,
            )
            self.assertTrue(ok)

            updated = state_mgr.get_script_state("ER01")
            content_meta = updated["content_metadata"]
            script_dict = content_meta["script"]

            # Verify lowercase keys
            expected_keys = ["title", "hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff"]
            for k in expected_keys:
                self.assertIn(k, script_dict)

            # Verify uppercase keys are NOT present
            self.assertNotIn("DIALOGUE_PART_1", script_dict)
            self.assertNotIn("PAYOFF", script_dict)

            # Verify continuity metadata was preserved
            self.assertIn("character_anchors", content_meta)
            self.assertEqual(content_meta["character_anchors"]["char1_hair"], "dark ponytail")
            self.assertIn("speakers_voice", content_meta)
            self.assertEqual(content_meta["speakers_voice"]["Narrator"], "golden_narrator.wav")
            self.assertEqual(content_meta["anchor_environment"], "Dressing room backstage.")

            # Verify downstream stages reset to pending
            self.assertEqual(updated["status"]["voice_generation"], "pending")
            self.assertEqual(updated["status"]["image_generation"], "pending")

            # Verify stale image_prompts wiped to force fresh prompt generation
            self.assertEqual(updated["assets"]["image_prompts"], {})
            self.assertEqual(updated["assets"]["character_anchors"]["char1_gender"], "female")

    def test_fun_facts_expression_change_updates_topic_title_and_5_sections(self):
        """Verify audit_script_changes detects Column B EXPRESSION drift and updates FUN_FACTS to 5 sections."""
        import tempfile
        # pyrefly: ignore[missing-import]
        from core.state_manager import StateManager
        # pyrefly: ignore[missing-import]
        from tools.check_script_changes import audit_script_changes
        # pyrefly: ignore[missing-import]
        from video_creation._A_video_scripts.script_modifier import modify_video_script

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "input" / "csv" / "script_to_change").mkdir(parents=True, exist_ok=True)
            state_mgr = StateManager(base_dir)

            script_body = (
                "Have you fought with English words keeping letters you do not pronounce?\n\n"
                "Here is the wild truth. In words like knight and knee, that K was not always silent.\n\n"
                "Centuries ago, English speakers actually pronounced both letters out loud.\n\n"
                "That means silent letters are linguistic fossils trapped in time.\n\n"
                "What silent letter drives you completely crazy?"
            )

            initial_state = {
                "id": "EF01",
                "status": {
                    "script_generation": "done",
                    "voice_generation": "done",
                    "image_generation": "done",
                    "thumbnail_generation": "done",
                    "video_assembly": "done",
                },
                "assets": {
                    "general_prompt": "Old world prompt",
                    "anchor_world_id": "old_world",
                    "image_prompts": {"hook": "old"},
                    "images": {"hook": "old.png"},
                },
                "prompt_params": {
                    "SCRIPT_ID": "EF01",
                    "TARGET_LANGUAGE": "English",
                    "VIDEO_TYPE": "FUN_FACTS",
                    "EXPRESSION": "'I am' is the Shortest Complete Sentence in English",
                    "TOPIC": "'I am' is the Shortest Complete Sentence in English",
                },
                "content_metadata": {
                    "video_type": "FUN_FACTS",
                    "language": "English",
                    "topic": "'I am' is the Shortest Complete Sentence in English",
                    "target_expression": "'I am' is the Shortest Complete Sentence in English",
                    "script": {
                        "title": "I am the shortest sentence ever",
                        "hook": "Old hook about I am.",
                        "setup": "Old setup.",
                        "discovery": "Old discovery.",
                        "payoff": "Old payoff.",
                    },
                },
                "metadata": {"TITLE": "I am the shortest sentence ever"},
            }
            state_mgr.save_script_state("EF01", initial_state)

            csv_path = base_dir / "input" / "csv" / "script_to_change" / "english_fun_facts_script_to_change.csv"
            import csv
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["ID", "NEW_SCRIPT", "EXPRESSION"])
                w.writeheader()
                w.writerow({"ID": "EF01", "NEW_SCRIPT": script_body, "EXPRESSION": "Silent Letters"})

            changed, identical, missing = audit_script_changes(base_dir=base_dir)
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["id"], "EF01")
            self.assertEqual(changed[0]["new_expression"], "Silent Letters")

            with patch("video_creation._A_video_scripts.script_modifier.is_llm_online", return_value=False):
                ok = modify_video_script(
                    script_id="EF01",
                    raw_script_text=changed[0]["new_script"],
                    reset_downstream=True,
                    base_dir=base_dir,
                    auto_update_csv=False,
                    new_expression=changed[0]["new_expression"],
                )
            self.assertTrue(ok)

            updated = state_mgr.get_script_state("EF01")
            self.assertEqual(updated["prompt_params"]["TOPIC"], "Silent Letters")
            self.assertEqual(updated["prompt_params"]["EXPRESSION"], "Silent Letters")
            self.assertEqual(updated["content_metadata"]["topic"], "Silent Letters")
            self.assertEqual(updated["content_metadata"]["script"]["title"], "Silent Letters")
            self.assertEqual(updated["metadata"]["TITLE"], "Silent Letters")
            for k in ("hook", "setup", "discovery", "explanation", "payoff"):
                self.assertIn(k, updated["content_metadata"]["script"])
            self.assertNotIn("general_prompt", updated["assets"])
            self.assertEqual(updated["status"]["image_generation"], "pending")

    def test_normalize_sheet_rows_extracts_column_j_short_title_and_positional_fallback(self):
        """Verify normalize_sheet_rows extracts Column J via short_title/THUMBNAIL_TITLE or positional fallback."""
        # pyrefly: ignore[missing-import]
        from connectivity.core.client import normalize_sheet_rows

        rows = [
            {
                "ID": "ig02",
                "expression": "Avere le mani bucate",
                "script": "body",
                "SCRIPT_CHANGED": "",
                "short_title": "MANI BUCATE?!",
            },
            {
                "ID": "eg03",
                "expression": "reCORD",
                "script": "body",
                "SCRIPT_CHANGED": "",
                "script_ready": "TRUE",
                "script_date": "",
                "video_ready": "",
                "video_date": "",
                "short_description": "",
                "CustomColJHeader": "REcord or reCORD?",
            },
        ]
        norm = normalize_sheet_rows(rows)
        self.assertEqual(len(norm), 2)
        self.assertEqual(norm[0]["THUMBNAIL_TITLE"], "MANI BUCATE?!")
        self.assertEqual(norm[1]["THUMBNAIL_TITLE"], "REcord or reCORD?")

    @patch("webui.routers.sheets._get_indexed_scripts")
    def test_thumbnail_titles_sync_worker_updates_only_thumbnail_title_and_resets_only_thumbnails(self, mock_index):
        """Verify _run_thumbnail_titles_sync_worker writes thumbnail_title without resetting voice/images/assembly."""
        import json
        import tempfile
        # pyrefly: ignore[missing-import]
        from core.state_manager import StateManager
        # pyrefly: ignore[missing-import]
        from webui.routers.sheets import _run_thumbnail_titles_sync_worker

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            sm = StateManager(base_dir)
            sm.save_script_state("IG02", {
                "id": "IG02",
                "status": {
                    "script_generation": "done",
                    "voice_generation": "done",
                    "image_generation": "done",
                    "thumbnail_generation": "done",
                    "video_assembly": "done",
                },
                "prompt_params": {"ID": "IG02", "TARGET_LANGUAGE": "Italian", "VIDEO_TYPE": "GAME"},
                "content_metadata": {
                    "video_type": "GAME",
                    "language": "Italian",
                    "script": {"title": "Old Title"},
                },
            })

            fake_rows = [{
                "ID": "IG02",
                "expression": "Avere le mani bucate",
                "short_title": "MANI BUCATE?!",
            }]
            with patch("connectivity.core.ENDPOINT_REGISTRY", {("italian", "game"): "https://fake"}), \
                 patch("connectivity.core.get_endpoint", return_value=("italian", "game", "https://fake")), \
                 patch("connectivity.core.fetch_raw_sheet_rows", return_value=fake_rows):
                _run_thumbnail_titles_sync_worker(apply_changes=True, base_dir=base_dir)

            status = get_sheets_sync_status()
            self.assertEqual(status["status"], "completed")
            self.assertEqual(status["result"]["sync_mode"], "thumbnails")
            self.assertEqual(status["result"]["updated_count"], 1)

            updated = sm.get_script_state("IG02")
            self.assertEqual(updated["content_metadata"]["thumbnail_title"], "MANI BUCATE?!")
            self.assertEqual(updated["status"]["thumbnail_generation"], "pending")
            self.assertEqual(updated["status"]["voice_generation"], "done")
            self.assertEqual(updated["status"]["image_generation"], "done")
            self.assertEqual(updated["status"]["video_assembly"], "done")
            mock_index.assert_called_once_with(force_refresh=True)


if __name__ == "__main__":
    unittest.main()
