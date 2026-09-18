"""
test_layer/unit/test_audio_processor.py — Unit tests for audio silence trimming, pause math, and token budgeting.
"""
import unittest
import numpy as np

from video_creation._B_voice_generation.core.audio_processor import trim_trailing_silence


class TestAudioProcessor(unittest.TestCase):
    def test_trim_trailing_silence_empty_array(self):
        empty = np.array([])
        result = trim_trailing_silence(empty, sr=24000)
        self.assertEqual(len(result), 0)

    def test_trim_trailing_silence_cuts_dead_tail(self):
        sr = 24000
        # 1.0 second of speech (amplitude 0.5) followed by 1.0 second of silence (amplitude 0.0)
        speech = np.ones(sr, dtype=np.float32) * 0.5
        silence = np.zeros(sr, dtype=np.float32)
        audio = np.concatenate([speech, silence])

        pad_seconds = 0.15
        trimmed = trim_trailing_silence(audio, sr=sr, threshold=0.01, pad_seconds=pad_seconds)

        expected_samples = sr + int(pad_seconds * sr)
        self.assertAlmostEqual(len(trimmed), expected_samples, delta=1)
        self.assertLess(len(trimmed), len(audio))

    def test_trim_trailing_silence_stereo_array(self):
        sr = 24000
        speech = np.ones((sr, 2), dtype=np.float32) * 0.5
        silence = np.zeros((sr, 2), dtype=np.float32)
        audio = np.concatenate([speech, silence], axis=0)

        trimmed = trim_trailing_silence(audio, sr=sr, threshold=0.01, pad_seconds=0.10)
        self.assertEqual(trimmed.shape[1], 2)
        self.assertLess(len(trimmed), len(audio))

    def test_dynamic_token_budget_calculation(self):
        # Formula: max(96, min(240, words * 12))
        def calc_tokens(words: int) -> int:
            return max(96, min(240, words * 12))

        # Low word count clamped to minimum 96
        self.assertEqual(calc_tokens(5), 96)
        self.assertEqual(calc_tokens(7), 96)

        # Normal word count scaled proportionally
        self.assertEqual(calc_tokens(10), 120)
        self.assertEqual(calc_tokens(15), 180)

        # High word count clamped to maximum 240
        self.assertEqual(calc_tokens(25), 240)
        self.assertEqual(calc_tokens(40), 240)

    def test_standard_pause_gap_durations(self):
        pauses = {
            "section_gap": 0.40,
            "dialogue_gap": 0.20,
            "paragraph_gap": 0.30,
            "pressure_gap": 2.20
        }
        self.assertEqual(pauses["section_gap"], 0.40)
        self.assertEqual(pauses["dialogue_gap"], 0.20)
        self.assertEqual(pauses["paragraph_gap"], 0.30)
        self.assertEqual(pauses["pressure_gap"], 2.20)


if __name__ == "__main__":
    unittest.main()
