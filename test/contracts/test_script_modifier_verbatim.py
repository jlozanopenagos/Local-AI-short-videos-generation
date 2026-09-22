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
)


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

if __name__ == "__main__":
    unittest.main()
