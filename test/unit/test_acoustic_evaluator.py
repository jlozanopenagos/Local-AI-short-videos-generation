"""Unit tests for acoustic_evaluator.py.

Validates:
1. Heteronym role detection in text (noun vs verb via casing and carriers).
2. Missing or corrupted audio error handling.
3. Syllable energy ratio calculation and geometric scoring.
4. Multi-candidate selection and rejected file cleanup.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.acoustic_evaluator import (
    detect_roles_in_text,
    evaluate_acoustic_prominence,
    select_best_voice_candidate,
    compute_pitch_metrics,
    evaluate_voice_take,
    select_best_general_candidate,
)


class TestAcousticEvaluator(unittest.TestCase):
    """Test suite for acoustic prominence evaluator."""

    def test_detect_roles_in_text_casing(self):
        """Verify role detection handles uppercase syllable casing correctly."""
        text = "Are you talking about a PREsent, or do you need to preSENT?"
        roles = detect_roles_in_text(text, ["present"])
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0], ("PREsent", "noun"))
        self.assertEqual(roles[1], ("preSENT", "verb"))

    def test_detect_roles_in_text_carriers(self):
        """Verify role detection handles carrier phrases with standard lowercase words."""
        text = "Say the noun a project clearly, then practice the verb to project."
        roles = detect_roles_in_text(text, ["project"])
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0][1], "noun")
        self.assertEqual(roles[1][1], "verb")

    def test_detect_roles_empty(self):
        """Verify role detection handles empty or unrelated inputs."""
        self.assertEqual(detect_roles_in_text("", ["present"]), [])
        self.assertEqual(detect_roles_in_text("Hello world", ["present"]), [])

    def test_evaluate_missing_file(self):
        """Verify missing audio file returns negative error score."""
        score, details = evaluate_acoustic_prominence("non_existent_audio.flac", ["present"])
        self.assertEqual(score, -100.0)
        self.assertIn("error", details)

    def test_evaluate_synthetic_audio_with_mock_whisper(self):
        """Verify syllable energy calculation and scoring with synthetic audio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test_synth.wav"
            sr = 16000
            duration = 1.0  # 1 second
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)
            
            # First half loud (amplitude 0.8), second half quiet (amplitude 0.1) -> strong noun
            samples = np.sin(2 * np.pi * 440 * t)
            mid_sample = len(samples) // 2
            samples[:mid_sample] *= 0.8
            samples[mid_sample:] *= 0.1
            sf.write(str(audio_path), samples, sr)

            # Mock WhisperModel transcribe
            mock_word = MagicMock()
            mock_word.word = "present"
            mock_word.start = 0.0
            mock_word.end = 1.0

            mock_seg = MagicMock()
            mock_seg.text = "a PREsent"
            mock_seg.words = [mock_word]

            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = ([mock_seg], None)

            with patch(
                "video_creation._B_voice_generation.core.acoustic_evaluator.get_whisper_model",
                return_value=mock_whisper
            ):
                score, details = evaluate_acoustic_prominence(
                    audio_path=audio_path,
                    target_words=["present"],
                    text_context="I have a PREsent."
                )

                self.assertGreater(score, 1.5)  # E1 / E2 should be ~8.0
                self.assertEqual(len(details["occurrences"]), 1)
                self.assertEqual(details["occurrences"][0]["role"], "noun")
                self.assertGreater(details["occurrences"][0]["ratio"], 5.0)

    def test_select_best_voice_candidate_single(self):
        """Verify single candidate is promoted directly without multi-take evaluation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cand1 = Path(tmpdir) / "cand1.flac"
            dest = Path(tmpdir) / "final.flac"
            cand1.write_text("audio_content")

            result = select_best_voice_candidate([cand1], ["present"], "text", dest)
            self.assertEqual(result, dest)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.read_text(), "audio_content")

    def test_select_best_voice_candidate_multi_winner_and_cleanup(self):
        """Verify highest scoring candidate is selected and rejected candidates are deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cand1 = Path(tmpdir) / "cand1.flac"
            cand2 = Path(tmpdir) / "cand2.flac"
            dest = Path(tmpdir) / "final.flac"
            cand1.write_text("cand1_take")
            cand2.write_text("cand2_winner_take")

            # Mock evaluate_acoustic_prominence so cand1 scores 0.6, cand2 scores 2.8
            def mock_eval(path, targets, text):
                if "cand1" in str(path):
                    return 0.6, {"transcript": "cand1", "occurrences": []}
                return 2.8, {"transcript": "cand2", "occurrences": []}

            with patch(
                "video_creation._B_voice_generation.core.acoustic_evaluator.evaluate_acoustic_prominence",
                side_effect=mock_eval
            ):
                result = select_best_voice_candidate([cand1, cand2], ["present"], "text", dest)
                self.assertEqual(result, dest)
                self.assertTrue(dest.exists())
                self.assertEqual(dest.read_text(), "cand2_winner_take")
                # Cand 1 was rejected and should be deleted
                self.assertFalse(cand1.exists())

    def test_select_best_voice_candidate_pronunciation_bank_fallback(self):
        """Verify that when all candidate takes score below threshold, system falls back to pronunciation bank."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cand1 = Path(tmpdir) / "cand1.flac"
            cand2 = Path(tmpdir) / "cand2.flac"
            bank_clip = Path(tmpdir) / "present_noun.flac"
            dest = Path(tmpdir) / "final.flac"

            cand1.write_text("low_score_1")
            cand2.write_text("low_score_2")
            bank_clip.write_text("studio_verified_clip")

            # Mock both candidates to score below 0.80 (e.g. 0.45 and 0.55)
            def mock_low_eval(path, targets, text):
                return 0.55, {"transcript": "present", "occurrences": []}

            with patch(
                "video_creation._B_voice_generation.core.acoustic_evaluator.evaluate_acoustic_prominence",
                side_effect=mock_low_eval
            ), patch(
                "video_creation._B_voice_generation.core.pronunciation_bank.get_pronunciation_clip",
                return_value=bank_clip
            ):
                result = select_best_voice_candidate([cand1, cand2], ["present"], "a PREsent", dest)
                self.assertEqual(result, dest)
                self.assertTrue(dest.exists())
                self.assertEqual(dest.read_text(), "studio_verified_clip")

    def test_compute_pitch_metrics_constant_vs_modulated(self):
        """Verify pitch metrics accurately distinguish constant monotone from pitch modulated speech."""
        sr = 24000
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # Monotone 180 Hz sine wave
        mono_sig = 0.5 * np.sin(2 * np.pi * 180 * t)
        m_mono, s_mono, v_mono = compute_pitch_metrics(mono_sig, sr)
        self.assertAlmostEqual(m_mono, 180.0, delta=2.0)
        self.assertLess(v_mono, 0.05)  # Pitch variance < 5%

        # Modulated 150 to 220 Hz sine wave
        f_mod = 185 + 35 * np.sin(2 * np.pi * 3 * t)
        phase = 2 * np.pi * np.cumsum(f_mod) / sr
        mod_sig = 0.5 * np.sin(phase)
        m_mod, s_mod, v_mod = compute_pitch_metrics(mod_sig, sr)
        self.assertGreater(v_mod, 0.10)  # Pitch variance > 10%

    def test_evaluate_voice_take_clean_vs_monotone(self):
        """Verify evaluate_voice_take detects monotone takes and validates healthy takes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            clean_path = Path(tmpdir) / "clean.flac"
            mono_path = Path(tmpdir) / "mono.flac"
            sr = 24000
            duration = 2.0
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)

            # Monotone tone
            mono_sig = 0.3 * np.sin(2 * np.pi * 150 * t)
            sf.write(str(mono_path), mono_sig, sr)

            # Modulated tone with realistic speech duration
            f_mod = 180 + 40 * np.sin(2 * np.pi * 4 * t)
            phase = 2 * np.pi * np.cumsum(f_mod) / sr
            clean_sig = 0.3 * np.sin(phase)
            sf.write(str(clean_path), clean_sig, sr)

            # Monotone take should be flagged for robotic variance
            score_m, pass_m, issues_m, met_m = evaluate_voice_take(mono_path, "This is a sample sentence with normal length.", "english")
            self.assertFalse(pass_m)
            self.assertTrue(any("Monotone" in iss for iss in issues_m))

            # Modulated take should pass
            score_c, pass_c, issues_c, met_c = evaluate_voice_take(clean_path, "This is a sample sentence with normal length.", "english")
            self.assertTrue(pass_c)
            self.assertGreater(score_c, 0.50)

    def test_select_best_general_candidate(self):
        """Verify select_best_general_candidate selects higher scoring take and unlinks rejected take."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cand1 = Path(tmpdir) / "cand1.flac"
            cand2 = Path(tmpdir) / "cand2.flac"
            dest = Path(tmpdir) / "dest.flac"
            sr = 24000
            duration = 1.5
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)

            # cand1: flat monotone
            sf.write(str(cand1), 0.3 * np.sin(2 * np.pi * 160 * t), sr)

            # cand2: dynamic pitch modulation
            f_mod = 180 + 45 * np.sin(2 * np.pi * 4 * t)
            phase = 2 * np.pi * np.cumsum(f_mod) / sr
            sf.write(str(cand2), 0.3 * np.sin(phase), sr)

            winner = select_best_general_candidate([cand1, cand2], "Sample sentence for candidate selection test.", "english", dest)
            self.assertEqual(winner, dest)
            self.assertTrue(dest.exists())
            # The losing candidate (cand1) should be unlinked
            self.assertFalse(cand1.exists())


if __name__ == "__main__":
    unittest.main()
