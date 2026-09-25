import sys
import unittest
import tempfile
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DIR = REPO_ROOT / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.script_modifier import (
    try_direct_script_parse,
    parse_user_script_into_sections,
    find_available_ready_scripts_csvs,
    load_scripts_from_csv,
)


class MockStateManager:
    def script_exists(self, script_id: str) -> bool:
        return script_id.upper() in ("FE01", "SG02")

    def get_script_state(self, script_id: str) -> dict:
        return {
            "prompt_params": {
                "EXPRESSION": "avoir le cafard",
                "TARGET_LANGUAGE": "French",
                "VIDEO_TYPE": "EXPRESSION",
            },
            "content_metadata": {
                "topic": "avoir le cafard",
                "language": "French",
                "video_type": "EXPRESSION",
            },
        }


class TestScriptModifierVerbatim(unittest.TestCase):
    def test_expression_5_paragraphs(self):
        script = (
            "Stop wishing someone 'good luck'! That phrase is actually bad luck.\n"
            "Most people think wishing someone luck is positive. But in theater, it's considered a total curse.\n"
            "The real expression is 'break a leg.' It's how professionals wish each other success backstage.\n"
            "Before my big show, I told my friend, 'Break a leg tonight, you'll crush it.'\n"
            "So next time you wish good to someone, don't say 'Good luck.' Say 'Break a leg.'"
        )
        parsed = try_direct_script_parse(script, "EXPRESSION")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["hook"], "Stop wishing someone 'good luck'! That phrase is actually bad luck.")
        self.assertEqual(parsed["setup"], "Most people think wishing someone luck is positive. But in theater, it's considered a total curse.")
        self.assertEqual(parsed["discovery"], "The real expression is 'break a leg.' It's how professionals wish each other success backstage.")
        self.assertEqual(parsed["example"], "Before my big show, I told my friend, 'Break a leg tonight, you'll crush it.'")
        self.assertEqual(parsed["payoff"], "So next time you wish good to someone, don't say 'Good luck.' Say 'Break a leg.'")

    def test_game_multi_line_quiz(self):
        script = (
            "Stop guessing! Can you actually understand this common idiom?\n"
            "What does it mean when someone says: The ball is in your court?\n"
            "A: You must make the next move.\n"
            "B: I am ready to play.\n"
            "C: The game is over.\n"
            "Three seconds on the clock! Choose A, B, or C right now!\n"
            "Time is up! The correct answer is A: You must make the next move!\n"
            "This tennis idiom means it is now your turn to take action."
        )
        parsed = try_direct_script_parse(script, "GAME")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["hook"], "Stop guessing! Can you actually understand this common idiom?")
        self.assertIn("What does it mean", parsed["challenge"])
        self.assertIn("A: You must make the next move.", parsed["challenge"])
        self.assertEqual(parsed["pressure"], "Three seconds on the clock! Choose A, B, or C right now!")
        self.assertEqual(parsed["answer"], "Time is up! The correct answer is A: You must make the next move!")
        self.assertEqual(parsed["explanation"], "This tennis idiom means it is now your turn to take action.")

    def test_roleplay_dialogue_pairs(self):
        script = (
            "Backstage chaos! A nervous actor is losing their mind over a forgotten line.\n"
            "PERSON_ONE (Panicked): I totally forgot my line!\n"
            "PERSON_TWO (Calm): Relax. Just remember: Break a leg!\n"
            "PERSON_ONE (Baffled): Break a leg? What is that supposed to mean?\n"
            "PERSON_TWO (Smirking): Nah, it's theater slang.\n"
            "PERSON_ONE (Relieved): So it's a superstition?\n"
            "PERSON_TWO (Chuckling): Exactly.\n"
            "PERSON_ONE (Determined): Okay, I'm going out there.\n"
            "PERSON_TWO (Encouraging): Go crush it!\n"
            "When the lights go up, knowing the right words turns panic into power."
        )
        parsed = try_direct_script_parse(script, "ROLEPLAY")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["hook"], "Backstage chaos! A nervous actor is losing their mind over a forgotten line.")
        self.assertIn("PERSON_ONE (Panicked)", parsed["DIALOGUE_PART_1"])
        self.assertIn("PERSON_TWO (Calm)", parsed["DIALOGUE_PART_1"])
        self.assertIn("PERSON_ONE (Baffled)", parsed["DIALOGUE_PART_2"])
        self.assertIn("PERSON_ONE (Relieved)", parsed["DIALOGUE_PART_3"])
        self.assertIn("PERSON_ONE (Determined)", parsed["DIALOGUE_PART_4"])
        self.assertEqual(parsed["PAYOFF"], "When the lights go up, knowing the right words turns panic into power.")

    def test_roleplay_user_case1_standard_unlabeled_narrator(self):
        script = (
            "Backstage chaos! A nervous actor is losing their mind over a forgotten line just thirty seconds before the show starts.\n\n"
            "PERSON_ONE (Panicked): I totally forgot my line! I'm going to freeze right here and ruin everything!\n"
            "PERSON_TWO (Calm): Relax. Just remember what I told you: Break a leg!\n\n"
            "PERSON_ONE (Baffled): Break a leg? What is that supposed to mean? Are you telling me I should physically hurt myself?\n"
            "PERSON_TWO (Smirking): Nah, it's theater slang. It's the ultimate way to wish someone massive luck.\n\n"
            "PERSON_ONE (Relieved): So it's a superstition? It means good luck, right? I feel a little better now.\n"
            "PERSON_TWO (Chuckling): Exactly. You just need to own the stage and give it everything you've got.\n\n"
            "PERSON_ONE (Determined): Okay, okay. I'm going out there. I won't mess up this final scene.\n"
            "PERSON_TWO (Encouraging): Go crush it! Now get out there and show them how it's done.\n\n"
            "When the lights go up, knowing the right words can turn pure panic into pure performance energy. Speak with confidence and own the moment. What would you say instead? Drop your version below!"
        )
        parsed = try_direct_script_parse(script, "ROLEPLAY")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["hook"], "Backstage chaos! A nervous actor is losing their mind over a forgotten line just thirty seconds before the show starts.")
        self.assertIn("PERSON_ONE (Panicked)", parsed["DIALOGUE_PART_1"])
        self.assertIn("PERSON_TWO (Calm)", parsed["DIALOGUE_PART_1"])
        self.assertIn("PERSON_ONE (Baffled)", parsed["DIALOGUE_PART_2"])
        self.assertIn("PERSON_TWO (Smirking)", parsed["DIALOGUE_PART_2"])
        self.assertIn("PERSON_ONE (Relieved)", parsed["DIALOGUE_PART_3"])
        self.assertIn("PERSON_TWO (Chuckling)", parsed["DIALOGUE_PART_3"])
        self.assertIn("PERSON_ONE (Determined)", parsed["DIALOGUE_PART_4"])
        self.assertIn("PERSON_TWO (Encouraging)", parsed["DIALOGUE_PART_4"])
        self.assertEqual(
            parsed["PAYOFF"],
            "When the lights go up, knowing the right words can turn pure panic into pure performance energy. Speak with confidence and own the moment. What would you say instead? Drop your version below!"
        )

    def test_roleplay_user_case2_explicit_narrator_and_5_turns(self):
        script = (
            "Narrator: Are you making this common pronunciation mistake at work? Let us look at the confusing word permit.\n"
            "PERSON_ONE (Confident): Okay, I finally received the official perMIT from the city to start building our new office.\n"
            "PERSON_TWO (Helpful): Wait a second. You are using the action verb pronunciation. For the official document, you must say PERmit.\n"
            "PERSON_ONE (Confused): Really? Are they not pronounced exactly the same way? I always thought they were just identical words.\n"
            "PERSON_TWO (Calm): They are spelled exactly the same, but the syllable stress changes. The noun is PERmit. The action verb is perMIT.\n"
            "PERSON_ONE (Relieved): Oh, that makes total sense now! I will go show them the PERmit and start the project today.\n"
            "Narrator: Master this syllable stress rule to sound completely natural in your next office meeting. Subscribe for more daily English pronunciation tips!"
        )
        parsed = try_direct_script_parse(script, "ROLEPLAY")
        self.assertIsNotNone(parsed)
        # Narrator prefix must be cleanly stripped so TTS voice does not speak "Narrator:"
        self.assertEqual(
            parsed["hook"],
            "Are you making this common pronunciation mistake at work? Let us look at the confusing word permit."
        )
        self.assertFalse(parsed["hook"].lower().startswith("narrator"))
        self.assertEqual(
            parsed["PAYOFF"],
            "Master this syllable stress rule to sound completely natural in your next office meeting. Subscribe for more daily English pronunciation tips!"
        )
        self.assertFalse(parsed["PAYOFF"].lower().startswith("narrator"))

        # Check turn distribution across 4 dialogue parts (5 turns distributed as 2, 1, 1, 1)
        self.assertIn("PERSON_ONE (Confident)", parsed["DIALOGUE_PART_1"])
        self.assertIn("PERSON_TWO (Helpful)", parsed["DIALOGUE_PART_1"])
        self.assertIn("PERSON_ONE (Confused)", parsed["DIALOGUE_PART_2"])
        self.assertIn("PERSON_TWO (Calm)", parsed["DIALOGUE_PART_3"])
        self.assertIn("PERSON_ONE (Relieved)", parsed["DIALOGUE_PART_4"])

        # Crucial: verify no turn is duplicated between parts
        self.assertNotEqual(parsed["DIALOGUE_PART_3"], parsed["DIALOGUE_PART_4"])
        self.assertNotIn("PERSON_ONE (Relieved)", parsed["DIALOGUE_PART_3"])
        self.assertNotIn("PERSON_TWO (Calm)", parsed["DIALOGUE_PART_4"])

    def test_find_available_ready_scripts_csvs(self):
        """Verify find_available_ready_scripts_csvs finds and prioritizes ready_scripts_to_work_with CSVs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir)
            f1 = p / "2026-09-23_ready_scripts_to_work_with.csv"
            f1.write_text("ID,SCRIPT_CHANGE\n", encoding="utf-8")
            f2 = p / "undated_ready_scripts_to_work_with.csv"
            f2.write_text("ID,SCRIPT_CHANGE\n", encoding="utf-8")
            err_f = p / "error_report.csv"
            err_f.write_text("ID,problem\n", encoding="utf-8")
            other_f = p / "2026-09-23_ready_scripts.csv"
            other_f.write_text("ID,expression\n", encoding="utf-8")

            found = find_available_ready_scripts_csvs(p)
            found_names = [f.name for f in found]

            self.assertIn("2026-09-23_ready_scripts_to_work_with.csv", found_names)
            self.assertIn("undated_ready_scripts_to_work_with.csv", found_names)
            self.assertIn("2026-09-23_ready_scripts.csv", found_names)
            self.assertNotIn("error_report.csv", found_names)
            # work_with files should precede standard files
            self.assertTrue(found_names.index("2026-09-23_ready_scripts_to_work_with.csv") < found_names.index("2026-09-23_ready_scripts.csv"))

    def test_load_scripts_from_csv_valid_and_filtering(self):
        """Verify load_scripts_from_csv validates IDs, skips blanks/duplicates/missing state."""
        mock_sm = MockStateManager()
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "2026-09-23_ready_scripts_to_work_with.csv"
            csv_content = (
                "ID,SCRIPT_CHANGE\n"
                "FE01,\"Voici un nouveau script complet pour FE01.\"\n"
                "FE02,\"\" \n" # blank -> skip
                "ZZ99,\"Script for non-existent ID\"\n" # not in state -> skip
                "FE01,\"Duplicate script for FE01\"\n" # duplicate -> skip
                "SG02,\"Nuevo guion en espanol para SG02.\"\n"
            )
            csv_path.write_text(csv_content, encoding="utf-8-sig")

            results = load_scripts_from_csv(csv_path, mock_sm) # type: ignore
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0][0], "FE01")
            self.assertEqual(results[0][1], "Voici un nouveau script complet pour FE01.")
            self.assertEqual(results[1][0], "SG02")
            self.assertEqual(results[1][1], "Nuevo guion en espanol para SG02.")

    def test_load_scripts_from_csv_alternative_headers(self):
        """Verify load_scripts_from_csv recognizes SCRIPT_CHANGED and NEW_SCRIPT headers."""
        mock_sm = MockStateManager()
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "test_alt.csv"
            csv_content = "ID,SCRIPT_CHANGED\nFE01,\"Script content here\"\n"
            csv_path.write_text(csv_content, encoding="utf-8")

            results = load_scripts_from_csv(csv_path, mock_sm) # type: ignore
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][0], "FE01")
            self.assertEqual(results[0][1], "Script content here")


if __name__ == "__main__":
    unittest.main()
