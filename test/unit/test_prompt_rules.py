"""
test_layer/unit/test_prompt_rules.py — Unit tests for prompt parameter validation and format word budgets.
"""
import unittest

# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.prompts.prompt_builder import validate_params
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.prompts.common_rules import COMMON_CONTENT_RULES
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.prompts.expression_rules import EXPRESSION_RULES
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.prompts.game_rules import GAME_RULES
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.prompts.roleplay_rules import ROLEPLAY_RULES
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.prompts.fun_facts_rules import FUN_FACTS_RULES


class TestPromptRules(unittest.TestCase):
    def test_missing_video_type_raises_value_error(self):
        params = {"TARGET_LANGUAGE": "english"}
        with self.assertRaises(ValueError) as ctx:
            validate_params(params)
        self.assertIn("VIDEO_TYPE", str(ctx.exception))

    def test_missing_target_language_raises_value_error(self):
        params = {"VIDEO_TYPE": "EXPRESSION"}
        with self.assertRaises(ValueError) as ctx:
            validate_params(params)
        self.assertIn("TARGET_LANGUAGE", str(ctx.exception))

    def test_expression_params_validation(self):
        # Valid
        valid_params = {
            "TARGET_LANGUAGE": "english",
            "VIDEO_TYPE": "EXPRESSION",
            "EXPRESSION": "Break a leg",
            "CONTEXT": "Theatrical good luck",
            "ANGLE": "Curious superstition"
        }
        self.assertEqual(validate_params(valid_params), valid_params)

        # Missing CONTEXT
        invalid_params = valid_params.copy()
        del invalid_params["CONTEXT"]
        with self.assertRaises(ValueError):
            validate_params(invalid_params)

    def test_roleplay_params_validation(self):
        valid = {
            "TARGET_LANGUAGE": "french",
            "VIDEO_TYPE": "ROLEPLAY",
            "ROLEPLAY_SCENARIO": "At the train station"
        }
        self.assertEqual(validate_params(valid), valid)

        invalid = {"TARGET_LANGUAGE": "french", "VIDEO_TYPE": "ROLEPLAY"}
        with self.assertRaises(ValueError):
            validate_params(invalid)

    def test_game_params_validation(self):
        valid = {
            "TARGET_LANGUAGE": "spanish",
            "VIDEO_TYPE": "GAME",
            "EXPRESSION": "blessé vs béni"
        }
        self.assertEqual(validate_params(valid), valid)

        invalid = {"TARGET_LANGUAGE": "spanish", "VIDEO_TYPE": "GAME"}
        with self.assertRaises(ValueError):
            validate_params(invalid)

    def test_fun_facts_params_validation(self):
        valid = {
            "TARGET_LANGUAGE": "italian",
            "VIDEO_TYPE": "FUN_FACTS",
            "TOPIC": "Italian Alphabet"
        }
        self.assertEqual(validate_params(valid), valid)

        invalid = {"TARGET_LANGUAGE": "italian", "VIDEO_TYPE": "FUN_FACTS"}
        with self.assertRaises(ValueError):
            validate_params(invalid)

    def test_word_budget_standards(self):
        """Asserts canonical word budget limits are present in actual prompt rule strings and never use legacy ranges."""
        self.assertIn("85-110 words", COMMON_CONTENT_RULES)
        self.assertIn("95-125 words", COMMON_CONTENT_RULES)
        self.assertIn("145-180 words", COMMON_CONTENT_RULES)
        self.assertIn("95-135 words", COMMON_CONTENT_RULES)

        self.assertIn("85", EXPRESSION_RULES)
        self.assertIn("110", EXPRESSION_RULES)
        self.assertIn("95", GAME_RULES)
        self.assertIn("125", GAME_RULES)
        self.assertIn("145", ROLEPLAY_RULES)
        self.assertIn("180", ROLEPLAY_RULES)
        self.assertIn("95", FUN_FACTS_RULES)
        self.assertIn("135", FUN_FACTS_RULES)

        # Ensure legacy outdated word-count bounds never reappear
        for rule_text in (COMMON_CONTENT_RULES, EXPRESSION_RULES, GAME_RULES, ROLEPLAY_RULES, FUN_FACTS_RULES):
            self.assertNotIn("70-90", rule_text)
            self.assertNotIn("120-140", rule_text)
            self.assertNotIn("70 to 90", rule_text)
            self.assertNotIn("120 to 140", rule_text)


if __name__ == "__main__":
    unittest.main()
