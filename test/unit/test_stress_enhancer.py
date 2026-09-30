"""Unit tests for stress_enhancer.py.

Validates:
1. Directional phonetic respelling mapping for noun vs verb heteronyms.
2. Contextual noun/verb detection without false positives.
3. Preservation of Roman numerals and standard casing.
4. Voice system instruction and IPA directives generation.
"""

import unittest
from video_creation._B_voice_generation.core.stress_enhancer import (
    enhance_stress_text_for_tts,
    build_stress_style_directive,
    HETERONYM_TTS_PHONETIC_REPLACEMENTS,
    HETERONYM_IPA_GUIDE,
)


class TestStressEnhancer(unittest.TestCase):
    """Test suite for stress_enhancer module."""

    def test_heteronym_replacements_coverage(self):
        """Verify core English heteronyms are mapped with clean word keys."""
        core_heteronyms = [
            "record", "present", "project", "permit", "object",
            "contract", "increase", "decrease", "import", "export",
            "protest", "contest"
        ]
        for word in core_heteronyms:
            self.assertIn(word, HETERONYM_TTS_PHONETIC_REPLACEMENTS)
            self.assertIn("noun", HETERONYM_TTS_PHONETIC_REPLACEMENTS[word])
            self.assertIn("verb", HETERONYM_TTS_PHONETIC_REPLACEMENTS[word])
            # Under Option B, standard orthography is preserved to avoid BPE token fragmentation
            self.assertEqual(HETERONYM_TTS_PHONETIC_REPLACEMENTS[word]["noun"], word)
            self.assertEqual(HETERONYM_TTS_PHONETIC_REPLACEMENTS[word]["verb"], word)

    def test_record_stress_enhancement(self):
        """Verify 'REcord' (noun) and 'reCORD' (verb) normalize to clean words without BPE fragmentation."""
        text = "Confuse the noun 'REcord' with the verb 'reCORD'. Say 're-CORD' now."
        enhanced, detected = enhance_stress_text_for_tts(text, language="english")
        self.assertIn("record", enhanced)
        self.assertIn("record", detected)
        # Ensure no BPE-breaking hyphenated pseudo-spellings
        self.assertNotIn("RECK-ord", enhanced)
        self.assertNotIn("re-KORD", enhanced)

    def test_present_stress_enhancement(self):
        """Verify 'PREsent' and 'preSENT' convert cleanly to standard English words for TTS."""
        text = "A: PREsent, or B: preSENT? Use PREsent for the gift!"
        enhanced, detected = enhance_stress_text_for_tts(text, language="english")
        self.assertEqual(
            enhanced,
            "A: present, or B: present? Use present for the gift!"
        )
        self.assertIn("present", detected)
        self.assertNotIn("PREZ-ent", enhanced)
        self.assertNotIn("pri-ZENT", enhanced)

    def test_contextual_noun_verb_markers(self):
        """Verify contextual 'the noun record' and 'the verb record' have syntactic carriers injected."""
        text = "Remember, the noun record is a vinyl album, but the verb record is an action."
        enhanced, detected = enhance_stress_text_for_tts(text, language="english")
        self.assertIn("the noun a record", enhanced)
        self.assertIn("the verb to record", enhanced)

    def test_roman_numerals_ignored(self):
        """Verify Roman numerals with ordinals (e.g. XIXe in French) are not mutilated."""
        text = "Son fanatisme aveugle a inspiré des comédies au XIXe siècle."
        enhanced, detected = enhance_stress_text_for_tts(text, language="french")
        self.assertEqual(enhanced, text)
        self.assertEqual(detected, [])

    def test_no_stress_text_unaltered(self):
        """Verify standard everyday text is returned unchanged."""
        text = "Hello world, this is a normal sentence without stress notation."
        enhanced, detected = enhance_stress_text_for_tts(text, language="english")
        self.assertEqual(enhanced, text)
        self.assertEqual(detected, [])

    def test_directives_and_style(self):
        """Verify style directive generates natural prosodic acting guidance without raw IPA jargon."""
        directive = build_stress_style_directive(["record"], language="english")
        self.assertIn("record", directive)
        self.assertIn("first syllable for noun", directive.lower())
        self.assertIn("second syllable for verb", directive.lower())
        # Ensure raw unparsed IPA is not dumped into instruction conditioning
        self.assertNotIn("/ˈrɛk.ərd/", directive)

        it_directive = build_stress_style_directive([], language="italian")
        self.assertIn("dizione italiana", it_directive)


if __name__ == "__main__":
    unittest.main()
