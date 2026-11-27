"""
test_layer/unit/test_subtitle_builder.py — Unit tests for ASS dynamic animated subtitle generation.
"""
import os
import re
import unittest
import tempfile
from pathlib import Path
from unittest import mock

# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.core.subtitle_builder import (
    SubtitleBuilder,
    align_tokens_to_whisper,
    premerge_whisper_words,
    tokenize_script_with_speakers,
)


def _extract_dialogue_events(content: str):
    """Returns list of `(style_name, raw_text, plain_text)` from ASS `Dialogue:` lines."""
    events = []
    for line in content.splitlines():
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) == 10:
                style_name = parts[3].strip()
                raw_text = parts[9].rstrip("\r\n")
                plain_text = re.sub(r"\{[^}]*\}", "", raw_text)
                events.append((style_name, raw_text, plain_text))
    return events


def _extract_dialogue_texts(content: str):
    return [plain for _, _, plain in _extract_dialogue_events(content)]


class TestSubtitleBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.builder = SubtitleBuilder()
        self.out_path = Path(self.temp_dir.name) / "test_subtitles.ass"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_ass_basic_structure(self):
        words = [
            {"word": "Hello", "start": 0.50, "end": 0.90},
            {"word": "world", "start": 0.95, "end": 1.40}
        ]
        created = self.builder.build_ass(words, self.out_path)
        self.assertTrue(created.exists())

        content = created.read_text(encoding="utf-8")
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResX: 576", content)
        self.assertIn("PlayResY: 1024", content)
        self.assertIn("&H0000FFFF", content)  # Hormozi Yellow primary color

        # Dialogue events
        self.assertIn("HELLO", content)
        self.assertIn("WORLD", content)

    def test_build_ass_suppression_windows(self):
        # Challenge window between 5.0 and 15.0 seconds
        words = [
            {"word": "Before", "start": 2.0, "end": 2.5},
            {"word": "HiddenInChallenge", "start": 7.0, "end": 8.0},
            {"word": "After", "start": 16.0, "end": 16.5}
        ]
        suppress = [(5.0, 15.0)]
        self.builder.build_ass(words, self.out_path, suppress_windows=suppress)

        content = self.out_path.read_text(encoding="utf-8")
        self.assertIn("BEFORE", content)
        self.assertNotIn("HIDDENINCHALLENGE", content)
        self.assertIn("AFTER", content)

    def test_timestamp_formatting_accuracy(self):
        words = [
            {"word": "MinuteOne", "start": 65.25, "end": 66.50}
        ]
        self.builder.build_ass(words, self.out_path)
        content = self.out_path.read_text(encoding="utf-8")
        # 65.25s -> 0:01:05.25, 66.50s -> 0:01:06.50
        self.assertIn("0:01:05.25", content)
        self.assertIn("0:01:06.50", content)

    def test_build_ass_normalizes_stress_ipa_and_phonetic_respellings_to_clean_subtitles(self):
        """Verify that IPA symbols, phonetic respellings, and stress-capitalized heteronyms render as clean standard all-caps words."""
        words = [
            {"word": "Feel", "start": 0.0, "end": 0.2},
            {"word": "the", "start": 0.2, "end": 0.3},
            {"word": "noun", "start": 0.3, "end": 0.5},
            {"word": "a", "start": 0.5, "end": 0.6},
            {"word": "present", "start": 0.6, "end": 1.0},
            {"word": "versus", "start": 1.0, "end": 1.3},
            {"word": "the", "start": 1.3, "end": 1.4},
            {"word": "verb", "start": 1.4, "end": 1.6},
            {"word": "to", "start": 1.6, "end": 1.7},
            {"word": "present", "start": 1.7, "end": 2.2},
        ]
        script_data = {
            "script_text": "Feel the noun a PREsent versus the verb to preSENT."
        }
        self.builder.build_ass(words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")

        dialogue_lines = [l for l in content.splitlines() if l.startswith("Dialogue:")]
        self.assertEqual(len(dialogue_lines), 10)
        texts = _extract_dialogue_texts(content)
        self.assertEqual(texts[4], "PRESENT")
        self.assertEqual(texts[9], "PRESENT.")

        # Also verify raw IPA (/ˈrek.ɚd/, /rɪˈkɔːrd/) and phonetic respellings (COM-pluh-ment, WEH-ther, uh-FECT, PRO-ject)
        ipa_words = [
            {"word": "record", "start": 0.0, "end": 0.3},
            {"word": "record", "start": 0.3, "end": 0.6},
            {"word": "compliment", "start": 0.6, "end": 0.9},
            {"word": "weather", "start": 0.9, "end": 1.2},
            {"word": "affect", "start": 1.2, "end": 1.5},
            {"word": "project", "start": 1.5, "end": 1.8},
        ]
        ipa_script_data = {
            "script_text": "/ˈrek.ɚd/ /rɪˈkɔːrd/ COM-pluh-ment WEH-ther uh-FECT PRO-ject"
        }
        self.builder.build_ass(ipa_words, self.out_path, script_data=ipa_script_data)
        ipa_content = self.out_path.read_text(encoding="utf-8")
        ipa_texts = _extract_dialogue_texts(ipa_content)
        self.assertEqual(ipa_texts, ["RECORD", "RECORD", "COMPLIMENT", "WEATHER", "AFFECT", "PROJECT"])

    def test_build_ass_homophone_forced_alignment(self):
        """Verify that homophones confused by Whisper (e.g. French ver/verre/vert/vers) are restored to exact script spelling."""
        # Simulated Whisper output where Whisper heard 'VERRE' for all homophones
        whisper_words = [
            {"word": "Un", "start": 0.0, "end": 0.2},
            {"word": "verre", "start": 0.2, "end": 0.5},
            {"word": "verre", "start": 0.5, "end": 0.8},
            {"word": "va", "start": 0.8, "end": 1.0},
            {"word": "verre", "start": 1.0, "end": 1.3},
            {"word": "un", "start": 1.3, "end": 1.5},
            {"word": "verre", "start": 1.5, "end": 1.8},
            {"word": "verre", "start": 1.8, "end": 2.2},
        ]
        script_data = {
            "content_metadata": {
                "script": {
                    "payoff": "Un ver vert va vers un verre vert."
                }
            }
        }
        self.builder.build_ass(whisper_words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")
        texts = _extract_dialogue_texts(content)

        # Verify that all 4 homophones are restored to their distinct script spellings
        self.assertEqual(texts, ["UN", "VER", "VERT", "VA", "VERS", "UN", "VERRE", "VERT."])

    def test_build_ass_italian_loanword_and_split_resolution(self):
        """Verify that Italian split words and phonetic letter names are aligned properly."""
        # Simulated Whisper output where 'alfabeto' was split into 'AL' + 'FABETO' and 'gei' heard as 'J'
        whisper_words = [
            {"word": "Satevi", "start": 0.0, "end": 0.5},
            {"word": "il", "start": 0.5, "end": 0.7},
            {"word": "al", "start": 0.7, "end": 0.9},
            {"word": "fabeto", "start": 0.9, "end": 1.2},
            {"word": "lettera", "start": 1.2, "end": 1.5},
            {"word": "J", "start": 1.5, "end": 1.8},
            {"word": "gins", "start": 1.8, "end": 2.2},
        ]
        script_data = {
            "content_metadata": {
                "script": {
                    "hook": "Sapevi il alfabeto lettera gei jeans"
                }
            }
        }
        self.builder.build_ass(whisper_words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")
        texts = _extract_dialogue_texts(content)

        # Should match golden script words, capitalized for Hormozi style
        self.assertEqual(texts, ["SAPEVI", "IL", "ALFABETO", "LETTERA", "GEI", "JEANS"])

    def test_build_ass_strips_roleplay_speaker_labels_and_color_codes_speakers(self):
        """Verify speaker labels are stripped AND mapped to PersonOne (Gold) vs PersonTwo (Sky-Cyan) styles."""
        whisper_words = [
            {"word": "I", "start": 1.0, "end": 1.2},
            {"word": "forgot", "start": 1.2, "end": 1.5},
            {"word": "Relax", "start": 2.0, "end": 2.3},
        ]
        script_data = {
            "content_metadata": {
                "video_type": "ROLEPLAY",
                "script": {
                    "hook": "Listen now",
                    "dialogue_part_1": "PERSON_ONE (Panicked): I forgot\nPERSON_TWO (Calm): Relax",
                },
            }
        }
        timings_data = {
            "hook": {"start": 0.0, "end": 0.9},
            "dialogue_part_1": {"start": 0.9, "end": 2.5},
        }
        # First check speaker-aware tokenization directly
        pairs = tokenize_script_with_speakers("PERSON_ONE (Panicked): I forgot\nPERSON_TWO (Calm): Relax")
        self.assertEqual(pairs, [("I", "PERSON_ONE"), ("forgot", "PERSON_ONE"), ("Relax", "PERSON_TWO")])

        self.builder.build_ass(whisper_words, self.out_path, script_data=script_data, timings_data=timings_data)
        content = self.out_path.read_text(encoding="utf-8")
        events = _extract_dialogue_events(content)
        texts = [plain for _, _, plain in events]
        self.assertNotIn("PERSON_ONE:", texts)
        self.assertNotIn("PERSON_TWO:", texts)
        self.assertNotIn("PANICKED", texts)
        self.assertNotIn("CALM", texts)
        self.assertEqual(texts, ["LISTEN", "NOW", "I", "FORGOT", "RELAX"])
        self.assertEqual(events[0][0], "Narrator")
        self.assertEqual(events[2][0], "PersonOne")
        self.assertEqual(events[3][0], "PersonOne")
        self.assertEqual(events[4][0], "PersonTwo")

    def test_build_ass_french_conversational_colon_and_elision(self):
        """Verify that conversational colons (e.g. 'Dis juste :') are preserved and French elisions are aligned."""
        whisper_words = [
            {"word": "Dis", "start": 0.0, "end": 0.2},
            {"word": "juste,", "start": 0.2, "end": 0.5},
            {"word": "il", "start": 0.5, "end": 0.7},
            {"word": "a", "start": 0.7, "end": 0.8},
            {"word": "posé", "start": 0.8, "end": 1.1},
            {"word": "un", "start": 1.1, "end": 1.2},
            {"word": "lapin,", "start": 1.2, "end": 1.5},
            {"word": "c", "start": 1.5, "end": 1.6},
            {"word": "'est", "start": 1.6, "end": 1.8},
            {"word": "pas", "start": 1.8, "end": 2.0},
            {"word": "grave,", "start": 2.0, "end": 2.3},
            {"word": "on", "start": 2.3, "end": 2.4},
            {"word": "se", "start": 2.4, "end": 2.5},
            {"word": "calme", "start": 2.5, "end": 2.8},
            {"word": "un", "start": 2.8, "end": 2.9},
            {"word": "autre", "start": 2.9, "end": 3.1},
            {"word": "truc.", "start": 3.1, "end": 3.4},
        ]
        script_data = {
            "content_metadata": {
                "script": {
                    "example": "Dis juste : 'Il a posé un lapin, c'est pas grave, on se cale un autre truc.'"
                }
            }
        }
        self.builder.build_ass(whisper_words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")
        texts = _extract_dialogue_texts(content)

        self.assertIn("DIS", texts)
        self.assertIn("JUSTE:", texts)
        self.assertIn("C'EST", texts)
        self.assertIn("CALE", texts)
        self.assertNotIn("CALME", texts)

    def test_build_ass_dash_separator_never_glues_words(self):
        """Verify that dash separators (e.g. 'À ton tour  -  utilise') are not merged into glued compounds like 'TOUR-UTILISE'."""
        whisper_words = [
            {"word": "À", "start": 0.0, "end": 0.2},
            {"word": "ton", "start": 0.2, "end": 0.4},
            {"word": "tour", "start": 0.4, "end": 0.7},
            {"word": "utilise", "start": 0.8, "end": 1.1},
            {"word": "cette", "start": 1.1, "end": 1.4},
            {"word": "expression", "start": 1.4, "end": 1.8},
        ]
        script_data = {
            "content_metadata": {
                "script": {
                    "payoff": "À ton tour  -  utilise cette expression dans une phrase en commentaire !"
                }
            }
        }
        self.builder.build_ass(whisper_words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")
        texts = _extract_dialogue_texts(content)

        self.assertNotIn("TOUR-UTILISE", texts)
        self.assertIn("TOUR", texts)
        self.assertIn("UTILISE", texts)

    def test_build_ass_multilingual_contractions_and_elisions(self):
        """Verify Italian, English, and Spanish elisions / punctuation marks align faithfully."""
        whisper_words = [
            {"word": "L", "start": 0.0, "end": 0.1},
            {"word": "'amico", "start": 0.1, "end": 0.4},
            {"word": "non", "start": 0.4, "end": 0.6},
            {"word": "e", "start": 0.6, "end": 0.8},
            {"word": "c", "start": 0.8, "end": 0.9},
            {"word": "'è", "start": 0.9, "end": 1.1},
            {"word": "un", "start": 1.1, "end": 1.3},
            {"word": "problema.", "start": 1.3, "end": 1.6},
        ]
        script_data = {
            "content_metadata": {
                "script": {
                    "hook": "L'amico non è c'è un problema."
                }
            }
        }
        self.builder.build_ass(whisper_words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")
        texts = _extract_dialogue_texts(content)

        self.assertIn("L'AMICO", texts)
        self.assertIn("È", texts)
        self.assertIn("C'È", texts)

    def test_build_ass_safe_zone_pop_in_and_type_styles(self):
        """Verify Lower-Middle safe zone Alignment=2, kinetic pop-in tags, FUN_FACTS Highlight, and GAME Explanation style."""
        # 1. FUN_FACTS: crisp white Default + Gold Highlight for numeric tokens
        ff_script = {
            "id": "IF01",
            "content_metadata": {
                "video_type": "FUN_FACTS",
                "script": {"hook": "Solo 21 lettere"},
            },
        }
        self.builder.build_ass(
            [{"word": "Solo", "start": 0.0, "end": 0.3}, {"word": "21", "start": 0.3, "end": 0.6}, {"word": "lettere", "start": 0.6, "end": 1.0}],
            self.out_path,
            script_data=ff_script,
        )
        ff_content = self.out_path.read_text(encoding="utf-8")
        self.assertIn("Style: Default,Arial,60,&H00FFFFFF,", ff_content)
        self.assertIn("Style: Highlight,Arial,60,&H0000FFFF,", ff_content)
        self.assertIn(",2,20,20,250,1", ff_content)
        ff_events = _extract_dialogue_events(ff_content)
        self.assertEqual(ff_events[0][0], "Default")
        self.assertEqual(ff_events[1][0], "Highlight")
        self.assertIn(r"\fscx88\fscy88\t(0,65,\fscx100\fscy100)", ff_events[1][1])

        # 2. GAME: Gold in answer, crisp White Explanation style in explanation section
        game_script = {
            "id": "SG01",
            "content_metadata": {
                "video_type": "GAME",
                "script": {"answer": "Opcion A", "explanation": "Significa caro"},
            },
        }
        game_timings = {
            "answer": {"start": 0.0, "end": 1.0},
            "explanation": {"start": 1.0, "end": 2.0},
        }
        self.builder.build_ass([], self.out_path, script_data=game_script, timings_data=game_timings)
        game_content = self.out_path.read_text(encoding="utf-8")
        game_events = _extract_dialogue_events(game_content)
        self.assertEqual([e[0] for e in game_events], ["Default", "Default", "Explanation", "Explanation"])

        # 3. Legacy rollback toggle restores Alignment=5 and MarginV=150
        with mock.patch.dict(os.environ, {"VIDEO_ASSEMBLY_ENGINE": "legacy"}):
            self.builder.build_ass([{"word": "Legacy", "start": 0.0, "end": 0.5}], self.out_path)
            legacy_content = self.out_path.read_text(encoding="utf-8")
            self.assertIn(",5,10,10,150,1", legacy_content)
            self.assertNotIn(r"\fscx", legacy_content)

    def test_premerge_never_glues_ordinary_two_letter_words_like_le_verre(self):
        """Regression for FF04: 'le' + 'verre' MUST NOT merge into 'le'verre', while real elisions ('l' + \"'ami\") DO merge."""
        raw = [
            {"word": "le", "start": 0.0, "end": 0.2},
            {"word": "verre", "start": 0.2, "end": 0.6},
            {"word": "pour", "start": 0.6, "end": 0.9},
            {"word": "l", "start": 0.9, "end": 1.0},
            {"word": "'ami", "start": 1.0, "end": 1.4},
            {"word": "d'", "start": 1.4, "end": 1.5},
            {"word": "abord", "start": 1.5, "end": 1.9},
        ]
        merged = premerge_whisper_words(raw)
        self.assertEqual([w["word"] for w in merged], ["le", "verre", "pour", "l'ami", "d'abord"])

    def test_collapse_recovery_repairs_frozen_word_and_speed_burst(self):
        """Regression for FF04 / IG87 / SR33: frozen single word + rushed burst recovers to smooth weighted timing."""
        tokens = ["Le", "verre", "pour", "boire.", "La", "couleur", "vert.", "Le", "mot", "vers."]
        # Simulate Whisper dropping 6s and cramming everything into 0.5s at the end
        collapsed_whisper = [
            {"word": "Le", "start": 18.0, "end": 23.0},
            {"word": "vers", "start": 23.5, "end": 23.8},
        ]
        aligned = align_tokens_to_whisper(
            tokens,
            collapsed_whisper,
            default_start=18.0,
            default_end=24.0,
            section_name="discovery",
        )
        self.assertEqual(len(aligned), len(tokens))
        durations = [round(a["end"] - a["start"], 2) for a in aligned]
        # No frozen word > 1.8s and no 0.03s burst
        self.assertLessEqual(max(durations), 1.5)
        self.assertGreaterEqual(min(durations), 0.25)
        self.assertAlmostEqual(aligned[0]["start"], 18.0, places=2)
        self.assertAlmostEqual(aligned[-1]["end"], 24.0, places=2)

    def test_build_ass_never_emits_overlapping_dialogue_cues(self):
        """Regression for IE01 (0:30.87 SENTIRE/QUESTA & 0:34.70 A/USARLA): two words must NEVER overlap in time."""
        raw_overlapping = [
            {"word": "Sentire", "start": 30.87, "end": 31.12},
            {"word": "questa", "start": 30.87, "end": 31.23},
            {"word": "frase", "start": 31.20, "end": 31.64},
            {"word": "a", "start": 34.70, "end": 34.95},
            {"word": "usarla", "start": 34.70, "end": 35.14},
        ]
        self.builder.build_ass(raw_overlapping, self.out_path)
        content = self.out_path.read_text(encoding="utf-8")

        def _parse_t(ts: str) -> float:
            h, m, s = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)

        cues = []
        for line in content.splitlines():
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                cues.append((_parse_t(parts[1].strip()), _parse_t(parts[2].strip()), parts[9].strip()))
        self.assertEqual(len(cues), 5)
        for i in range(1, len(cues)):
            self.assertGreaterEqual(cues[i][0], cues[i - 1][1], f"Overlap between {cues[i-1]} and {cues[i]}")
            self.assertGreater(cues[i][1], cues[i][0])


if __name__ == "__main__":
    unittest.main()

