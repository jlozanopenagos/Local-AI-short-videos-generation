"""
test/unit/test_voice_manager.py — Unit tests for VoiceManager language normalization, voice allocation,
ComfyClient ICL / localized instruct generation, and voice_modifier helpers.
"""
import unittest
import tempfile
from pathlib import Path

# Add main to sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_DIR = PROJECT_ROOT / "main"
for p in [str(PROJECT_ROOT), str(MAIN_DIR), str(MAIN_DIR / "core")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.comfy_client import ComfyClient
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice_modifier import (
    is_stress_pronunciation_vital,
    infer_dialogue_emotion,
    map_emotion_to_energy,
)
# pyrefly: ignore[missing-import]
import config


class TestVoiceManager(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_root = Path(self._tmp_dir.name)
        comfy_input = tmp_root / "comfy_input"
        comfy_input.mkdir(parents=True, exist_ok=True)

        open_swara = config.OPEN_SWARA_DIR
        if not open_swara.exists():
            open_swara = tmp_root / "open_swara"
            for (_lang, _gend), rel_paths in getattr(config, "NARRATOR_VOICES", {}).items():
                for rel in rel_paths:
                    p = open_swara / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")

        self.vm = VoiceManager(open_swara, comfy_input)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_normalize_language_compound_labels(self):
        cases = [
            ("French | Culture | Fun Facts | Pronunciation", "french"),
            ("Spanish | Slang | Expressions", "spanish"),
            ("Italian | Food & Culture | Travel", "italian"),
            ("English | Idioms | Business", "english"),
            ("French | Français", "french"),
            ("Español | Slang", "spanish"),
            ("Italiano | Grammatica", "italian"),
            ("fr", "french"),
            ("es", "spanish"),
            ("it", "italian"),
            ("en", "english"),
            ("", "english"),
            (None, "english"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                result = VoiceManager.normalize_language(raw)
                self.assertEqual(result, expected)

    def test_assign_voices_for_french_script_with_compound_label(self):
        """Verifies that passing a compound French label assigns a French voice, NEVER English."""
        compound_label = "French | Culture | Fun Facts | Pronunciation"
        self.vm.assign_voices_for_script(["Narrator"], compound_label)
        gender, voice_path, seed = self.vm.get_speaker_voice("Narrator", compound_label)
        
        self.assertIsNotNone(voice_path, "Voice path should not be None")
        self.assertTrue(voice_path.exists(), f"Assigned voice file must exist: {voice_path}")
        self.assertTrue(
            voice_path.name.startswith("french_"),
            f"Assigned voice must be a French voice, but got: {voice_path.name}"
        )
        self.assertNotIn("english", voice_path.name.lower())

    def test_assign_voices_for_spanish_script(self):
        """Verifies that Spanish scripts receive Spanish reference voices."""
        compound_label = "Spanish | Slang | Street Talk"
        self.vm.assign_voices_for_script(["Narrator"], compound_label)
        gender, voice_path, seed = self.vm.get_speaker_voice("Narrator", compound_label)

        self.assertIsNotNone(voice_path)
        self.assertTrue(voice_path.exists())
        self.assertTrue(
            voice_path.name.startswith("spanish_"),
            f"Expected Spanish voice, got {voice_path.name}"
        )

    def test_assign_voices_for_italian_script(self):
        """Verifies that Italian scripts receive Italian reference voices."""
        compound_label = "Italian | Food & Idioms"
        self.vm.assign_voices_for_script(["Narrator"], compound_label)
        gender, voice_path, seed = self.vm.get_speaker_voice("Narrator", compound_label)

        self.assertIsNotNone(voice_path)
        self.assertTrue(voice_path.exists())
        self.assertTrue(
            voice_path.name.startswith("italian_"),
            f"Expected Italian voice, got {voice_path.name}"
        )

    def test_get_available_voices_for_language_and_gender(self):
        """Verifies that get_available_voices returns valid, existing paths for target language."""
        french_female = self.vm.get_available_voices("french", "female")
        self.assertGreater(len(french_female), 0)
        for p in french_female:
            self.assertTrue(p.exists())
            self.assertTrue(p.name.startswith("french_female_"))

    def test_manual_voice_paths_override(self):
        """Verifies that supplying manual_voice_paths overrides default pool selection."""
        french_pool = self.vm.get_available_voices("french", "male")
        if french_pool:
            chosen_manual = french_pool[0]
            self.vm.assign_voices_for_script(
                ["Narrator"],
                "french",
                manual_genders={"Narrator": "male"},
                manual_voice_paths={"Narrator": chosen_manual}
            )
            gender, voice_path, _ = self.vm.get_speaker_voice("Narrator", "french")
            self.assertEqual(gender, "male")
            self.assertEqual(voice_path, chosen_manual)

    def test_voice_manager_excludes_english_tagged_italian_refs(self):
        self.assertFalse(
            VoiceManager._is_acceptable_ref(Path("italian_male_english_open_swara_001.wav"), "italian")
        )
        self.assertTrue(
            VoiceManager._is_acceptable_ref(Path("italian_male_open_swara_001.wav"), "italian")
        )
        self.assertFalse(
            VoiceManager._is_acceptable_ref(Path("french_male_open_swara_001.wav"), "french")
        )

    def test_resolve_speaker_gender(self):
        self.assertEqual(self.vm.resolve_speaker_gender("Narrator"), "male")
        self.assertEqual(self.vm.resolve_speaker_gender("Person One"), "unknown")
        self.assertEqual(self.vm.resolve_speaker_gender("Father"), "male")
        self.assertEqual(self.vm.resolve_speaker_gender("Marie"), "female")

    def test_assign_voices_for_multi_speaker_roleplay_without_manual_genders(self):
        """Verifies multi-speaker roleplay voice assignment succeeds without manual_genders."""
        self.vm.assign_voices_for_script(
            ["Narrator", "Person One", "Person Two"],
            "english",
            video_type="ROLEPLAY",
        )
        g_narr, v_narr, _ = self.vm.get_speaker_voice("Narrator", "english")
        g_p1, v_p1, _ = self.vm.get_speaker_voice("Person One", "english")
        g_p2, v_p2, _ = self.vm.get_speaker_voice("Person Two", "english")
        self.assertIn(g_narr, ("male", "female"))
        self.assertIn(g_p1, ("male", "female"))
        self.assertIn(g_p2, ("male", "female"))
        self.assertIsNotNone(v_narr)
        self.assertIsNotNone(v_p1)
        self.assertIsNotNone(v_p2)

    def test_comfy_client_icl_and_localized_instruct(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wf_path = Path(tmpdir) / "wf.json"
            wf_path.write_text(
                '{"6":{"inputs":{}},"8":{"inputs":{}},"35":{"inputs":{"x_vector_only":true,"ref_text":["40",0]}},"39":{"inputs":{}}}',
                encoding="utf-8",
            )
            client = ComfyClient("http://127.0.0.1:8188", wf_path)
            wf = client._prepare_workflow(
                ref_audio_name="spanish_female_open_swara_009.wav",
                target_text="Hola a todos.",
                language="spanish",
                gender="female",
                context="Narrator",
                emotion="warm",
                energy="high",
                style="lively",
                output_prefix="audio/test",
                seed=42,
                use_icl=True,
                ref_text="Hola, soy una voz de referencia.",
                localize_instruct=True,
            )
            self.assertFalse(wf["35"]["inputs"]["x_vector_only"])
            self.assertEqual(wf["35"]["inputs"]["ref_text"], "Hola, soy una voz de referencia.")
            self.assertIn("Un narrador nativo de español", wf["39"]["inputs"]["instruct"])


class TestVoiceModifier(unittest.TestCase):
    def test_is_stress_pronunciation_vital_with_cased_notation(self):
        script_data = {
            "metadata": {"LABEL": "english"},
            "prompt_params": {"SUBJECT": "Grammar"},
            "content_metadata": {},
        }
        self.assertTrue(is_stress_pronunciation_vital(script_data, "Say a PREsent now"))
        self.assertTrue(is_stress_pronunciation_vital(script_data, "You need to preSENT today"))
        self.assertFalse(is_stress_pronunciation_vital(script_data, "Hello world, how are you?"))

    def test_is_stress_pronunciation_vital_from_metadata(self):
        script_data = {
            "metadata": {"LABEL": "english"},
            "prompt_params": {"SUBJECT": "Word stress and heteronyms"},
            "content_metadata": {"learning_objective": "Syllable stress contrast"},
        }
        self.assertTrue(is_stress_pronunciation_vital(script_data, "Normal sentence text"))

    def test_map_emotion_to_energy(self):
        self.assertEqual(map_emotion_to_energy("electrifying trivia host"), "very high")
        self.assertEqual(map_emotion_to_energy("whisper sad"), "medium")
        self.assertEqual(map_emotion_to_energy("warm confident"), "high")

    def test_infer_dialogue_emotion_narrator(self):
        emo = infer_dialogue_emotion("Narrator", "Check this secret out!", section="hook")
        self.assertIn("dramatic", emo)


if __name__ == "__main__":
    unittest.main()

