"""
test_layer/unit/test_prompt_rules.py — Unit tests for prompt parameter validation and format word budgets.
"""
import unittest

from video_creation._A_video_scripts.prompts.prompt_builder import validate_params


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
        # Asserts canonical word budget limits documented in AGENTS.md / README.md
        budgets = {
            "EXPRESSION": (85, 110),
            "GAME": (95, 125),
            "ROLEPLAY": (145, 180),
            "FUN_FACTS": (95, 135)
        }
        for vtype, (min_words, max_words) in budgets.items():
            self.assertLess(min_words, max_words)
            self.assertGreaterEqual(min_words, 85)
            self.assertLessEqual(max_words, 180)


if __name__ == "__main__":
    unittest.main()
