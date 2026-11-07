"""Unit tests for stress_enhancer.py.

Validates:
1. Directional phonetic respelling mapping for noun vs verb heteronyms.
2. Contextual noun/verb detection without false positives.
3. Preservation of Roman numerals and standard casing.
4. Voice system instruction and IPA directives generation.
"""

import unittest
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.stress_enhancer import (
    enhance_stress_text_for_tts,
    build_stress_style_directive,
    detect_intentional_stress_errors,
)


class TestStressEnhancer(unittest.TestCase):
    """Test suite for stress_enhancer module."""

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

    def test_ipa_slashes_sanitized_for_tts(self):
        """Verify raw IPA phonetics in slashes (e.g. /ˈrek.ɚd/ vs /rɪˈkɔːrd/) normalize safely to clean words."""
        text = "Speakers confuse the noun /ˈrek.ɚd/ with the verb /rɪˈkɔːrd/."
        enhanced, detected = enhance_stress_text_for_tts(text, language="english")
        self.assertIn("record", enhanced)
        self.assertIn("the noun a record", enhanced)
        self.assertIn("the verb to record", enhanced)
        self.assertNotIn("/ˈrek.ɚd/", enhanced)
        self.assertNotIn("/rɪˈkɔːrd/", enhanced)

    def test_detect_intentional_stress_errors_verb_in_noun_slot(self):
        """Verify deliberate error (reCORD or perMIT in noun context) is accurately flagged."""
        text = "Did you hear that our favorite band just released a new reCORD?"
        errs = detect_intentional_stress_errors(text, ["record"])
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0]["word"], "record")
        self.assertEqual(errs[0]["token"], "reCORD")
        self.assertEqual(errs[0]["visual_role"], "verb")
        self.assertEqual(errs[0]["syntactic_role"], "noun")

        text_permit = "I finally received the official perMIT from the city."
        errs_permit = detect_intentional_stress_errors(text_permit, ["permit"])
        self.assertEqual(len(errs_permit), 1)
        self.assertEqual(errs_permit[0]["visual_role"], "verb")
        self.assertEqual(errs_permit[0]["syntactic_role"], "noun")

    def test_detect_intentional_stress_errors_noun_in_verb_slot(self):
        """Verify deliberate error (REcord in verb context) is flagged."""
        text = "Tomorrow they will REcord a new track."
        errs = detect_intentional_stress_errors(text, ["record"])
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0]["visual_role"], "noun")
        self.assertEqual(errs[0]["syntactic_role"], "verb")

    def test_detect_intentional_stress_errors_correct_matching(self):
        """Verify that correctly matched casing has zero intentional errors flagged."""
        text = "Bro, they released a REcord! And tomorrow they will reCORD a new track!"
        errs = detect_intentional_stress_errors(text, ["record"])
        self.assertEqual(len(errs), 0)

    def test_build_stress_style_directive_with_intentional_error(self):
        """Verify style directive injects explicit learner mistake acting instruction."""
        text = "Did you hear that our favorite band just released a new reCORD?"
        directive = build_stress_style_directive(["record"], language="english", raw_text=text)
        self.assertIn("intentionally makes a pronunciation mistake", directive)
        self.assertIn("verb /ri-KORD/", directive)


if __name__ == "__main__":
    unittest.main()
