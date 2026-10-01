import unittest
from pathlib import Path
import tempfile

from video_creation._B_voice_generation.core.kokoro_engine import (
    KokoroEngine,
    get_kokoro_engine,
    KOKORO_AVAILABLE,
)


class TestKokoroEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_kokoro_singleton(self):
        engine1 = get_kokoro_engine()
        engine2 = get_kokoro_engine()
        self.assertIs(engine1, engine2)

    def test_kokoro_ready_status(self):
        engine = get_kokoro_engine()
        if KOKORO_AVAILABLE:
            self.assertTrue(engine.is_ready)
            voices = engine.get_available_voices()
            self.assertGreater(len(voices), 0)
            self.assertIn("af_bella", voices)

    def test_kokoro_generate_ipa_phonemes(self):
        engine = get_kokoro_engine()
        if not engine.is_ready:
            self.skipTest("Kokoro model not initialized on this host")

        out_file = self.temp_path / "test_noun.wav"
        res = engine.generate_phonemes("ˈprɛzənt", out_file, voice="af_bella")
        self.assertIsNotNone(res)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 1000)

    def test_kokoro_generate_heteronym_demonstration(self):
        engine = get_kokoro_engine()
        if not engine.is_ready:
            self.skipTest("Kokoro model not initialized on this host")

        out_noun = self.temp_path / "project_noun.wav"
        res_noun = engine.generate_heteronym_demonstration("project", "noun", out_noun)
        self.assertIsNotNone(res_noun)
        self.assertTrue(out_noun.exists())

        out_verb = self.temp_path / "project_verb.wav"
        res_verb = engine.generate_heteronym_demonstration("project", "verb", out_verb)
        self.assertIsNotNone(res_verb)
        self.assertTrue(out_verb.exists())


if __name__ == "__main__":
    unittest.main()
