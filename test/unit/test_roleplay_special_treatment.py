"""
test/unit/test_roleplay_special_treatment.py — Unit tests for ROLEPLAY SPECIAL_TREATMENT
classification system.

Tests the 'SPECIAL_TREATMENT' column introduced to READY_PROMPTS_ROLEPLAY.sample.csv, which
classifies each expression under ONE exclusive pedagogical lens:
    - 'idiomatic'     : fixed multi-word figurative phrase (break a leg, costar un ojo de la cara)
    - 'phonetic'      : stress-shift / heteronym / minimal pair (REcord vs reCORD)
    - 'false_friend'  : cross-language false cognate (embarrassed / embarazada)
    - '' (blank)      : default behaviour — LLM decides

Focus: Error #4 (No Usage Modeling) — the primary quality gate.
An idiomatic roleplay MUST show PERSON_ONE using the full idiom in an original sentence
by DIALOGUE_PART_4, not just reacting to an explanation.
"""

from __future__ import annotations

import csv
import io
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path setup — mirrors conftest.py sys.path injection
# ---------------------------------------------------------------------------
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_DIR = PROJECT_ROOT / "main"
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from video_creation._A_video_scripts.prompts.prompt_builder import (
    build_prompt,
    validate_params,
)
from video_creation._A_video_scripts.main import validate_idiomatic_roleplay


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

BASE_ROLEPLAY_PARAMS = {
    "ID": "SR01",
    "TARGET_LANGUAGE": "Spanish",
    "VIDEO_TYPE": "ROLEPLAY",
    "ROLEPLAY_SCENARIO": (
        "En una tienda de zapatillas exclusivas: dos amigos miran una vitrina con "
        "zapatillas de 800 euros. Uno saca la tarjeta y el otro le agarra el brazo: "
        "'Pero tio, dejalas ahi, que te van a costar un ojo de la cara!' "
        "La expresion a ensenhar es 'costar un ojo de la cara'."
    ),
    "SUBJECT": "Modismos populares en español",
    "LEXICAL_FIELD": "Compras y dinero",
    "EMOTIONAL_TRIGGER": "Sorpresa & Curiosidad",
}

# A script where DIALOGUE_PART_4 has PERSON_ONE actively USING the idiom — VALID
VALID_IDIOMATIC_SCRIPT = {
    "title": "El Shock del Precio",
    "hook": "Cuando ves un precio ridiculo en una tienda exclusiva, la cara de tu amigo lo dice todo.",
    "DIALOGUE_PART_1": (
        "PERSON_ONE (Entusiasmado): Mira estas zapatillas, son increibles! Quiero comprarlas ahora.\n"
        "PERSON_TWO (Skeptical): Espera! Eso te va a costar un ojo de la cara, tio."
    ),
    "DIALOGUE_PART_2": (
        "PERSON_ONE (Baffled): Un ojo de la cara? Es que me voy a quedar tuerto?\n"
        "PERSON_TWO (Chuckling): No, significa que es carisimo. Ruinoso. Nada mas."
    ),
    "DIALOGUE_PART_3": (
        "PERSON_ONE (Curious): Ah, como ese restaurante del centro que...\n"
        "PERSON_TWO (Smirking): Exacto. La semana pasada pague el menu y me costo un ojo de la cara."
    ),
    "DIALOGUE_PART_4": (
        "PERSON_ONE (Grinning): Entonces si invito a toda la familia a cenar fuera, me va a costar un ojo de la cara.\n"
        "PERSON_TWO (Hilarious): Y probablemente el otro tambien! Guarda la tarjeta, anda."
    ),
    "PAYOFF": (
        "Cuando el precio te deja sin palabras, al menos tienes las palabras correctas. "
        "Cuentalo abajo!"
    ),
}

# A script where DIALOGUE_PART_4 has PERSON_ONE only reacting/asking — INVALID (Error #4)
INVALID_IDIOMATIC_SCRIPT_NO_USAGE = {
    "title": "El Shock del Precio",
    "hook": "Cuando ves un precio ridículo en una tienda exclusiva, la cara de tu amigo lo dice todo.",
    "DIALOGUE_PART_1": (
        "PERSON_ONE (Entusiasmado): Mira estas zapatillas, ¡son increíbles!\n"
        "PERSON_TWO (Skeptical): ¡Espera! Eso te va a costar un ojo de la cara."
    ),
    "DIALOGUE_PART_2": (
        "PERSON_ONE (Baffled): ¿Un ojo de la cara? ¿Qué significa eso exactamente?\n"
        "PERSON_TWO (Deadpan): Es una expresión. Significa que el producto es increíblemente caro."
    ),
    "DIALOGUE_PART_3": (
        "PERSON_ONE (Relieved): Ah, entiendo. Entonces es para cosas muy caras.\n"
        "PERSON_TWO (Chuckling): Exacto. Es el modo de decir que algo te deja en la ruina."
    ),
    "DIALOGUE_PART_4": (
        # P1 reacts and nods — does NOT use the idiom themselves
        "PERSON_ONE (Relieved): ¡Vale! Ya no me sorprende. Ahora ya sé qué significa.\n"
        "PERSON_TWO (Smirking): Así es. ¡Cuidado con el presupuesto!"
    ),
    "PAYOFF": (
        "Esa frase habla de la realidad de los gastos inesperados. "
        "Momento de reto: escribe una frase con esta expresión ahora mismo!"
    ),
}

# A script where the full idiom form is MISSING from DIALOGUE_PART_1 — INVALID
INVALID_IDIOMATIC_SCRIPT_TRUNCATED_IN_P1 = {
    "title": "El Shock del Precio",
    "hook": "Cuando ves un precio ridículo, la cara de tu amigo lo dice todo.",
    "DIALOGUE_PART_1": (
        "PERSON_ONE (Entusiasmado): Mira estas zapatillas.\n"
        # Only partial form "costar un ojo" — missing "de la cara"
        "PERSON_TWO (Skeptical): ¡Eso te va a costar un ojo, tío!"
    ),
    "DIALOGUE_PART_2": (
        "PERSON_ONE (Baffled): ¿Un ojo?\n"
        "PERSON_TWO (Deadpan): Significa que es carísimo."
    ),
    "DIALOGUE_PART_3": (
        "PERSON_ONE (Curious): Ya veo.\n"
        "PERSON_TWO (Smirking): La semana pasada me costó un ojo de la cara."
    ),
    "DIALOGUE_PART_4": (
        "PERSON_ONE (Grinning): Si invito a todos me va a costar un ojo de la cara.\n"
        "PERSON_TWO (Hilarious): ¡Y el otro también!"
    ),
    "PAYOFF": "Cuéntalo abajo!",
}

SAMPLE_CSV_PATH = (
    PROJECT_ROOT / "main" / "input" / "csv" / "sample_templates"
    / "READY_PROMPTS_ROLEPLAY.sample.csv"
)


# ---------------------------------------------------------------------------
# Test Class
# ---------------------------------------------------------------------------

class TestRoleplaySpecialTreatment(unittest.TestCase):
    """Tests for the SPECIAL_TREATMENT classification in ROLEPLAY prompt pipeline."""

    # ------------------------------------------------------------------
    # Test 1 — SPECIAL_TREATMENT is an optional field in validate_params
    # ------------------------------------------------------------------
    def test_special_treatment_passed_through_validate_params(self):
        """SPECIAL_TREATMENT must not cause validate_params to raise."""
        params_with_idiomatic = {**BASE_ROLEPLAY_PARAMS, "SPECIAL_TREATMENT": "idiomatic"}
        params_with_phonetic  = {**BASE_ROLEPLAY_PARAMS, "SPECIAL_TREATMENT": "phonetic"}
        params_with_blank     = {**BASE_ROLEPLAY_PARAMS, "SPECIAL_TREATMENT": ""}
        params_without_field  = {**BASE_ROLEPLAY_PARAMS}

        for params in [
            params_with_idiomatic,
            params_with_phonetic,
            params_with_blank,
            params_without_field,
        ]:
            with self.subTest(SPECIAL_TREATMENT=params.get("SPECIAL_TREATMENT", "<absent>")):
                result = validate_params(params)
                self.assertIsNotNone(result)

    # ------------------------------------------------------------------
    # Test 2 — idiomatic prompt contains the arc instructions
    # ------------------------------------------------------------------
    def test_idiomatic_prompt_contains_arc_instructions(self):
        """build_prompt() with SPECIAL_TREATMENT=idiomatic must inject the idiomatic arc block."""
        params = {**BASE_ROLEPLAY_PARAMS, "SPECIAL_TREATMENT": "idiomatic"}
        with patch("video_creation._A_video_scripts.prompts.prompt_builder.load_call_to_actions",
                   return_value=[]):
            prompt = build_prompt(params)

        # Must contain keywords specific to the idiomatic arc instruction block
        self.assertIn("IDIOMATIC", prompt.upper(),
                      "Idiomatic arc block header must appear in prompt")
        # The core Error #4 fix: P1 must use the idiom in DIALOGUE_PART_4
        self.assertIn("DIALOGUE_PART_4", prompt,
                      "Prompt must reference DIALOGUE_PART_4 usage requirement")
        # Must emphasize full-form usage
        self.assertIn("full", prompt.lower(),
                      "Prompt must instruct on using the FULL idiomatic form")

    # ------------------------------------------------------------------
    # Test 3 — phonetic type still gets stress-pair instructions, NOT idiomatic arc
    # ------------------------------------------------------------------
    def test_phonetic_prompt_unchanged_by_idiomatic_flag(self):
        """SPECIAL_TREATMENT=phonetic must trigger stress-pair instructions, not idiomatic arc."""
        phonetic_params = {
            **BASE_ROLEPLAY_PARAMS,
            "ROLEPLAY_SCENARIO": (
                "Inside a vinyl store: PERSON_ONE holds up an old LP asking 'Did you hear that "
                "band's new reCORD?', and PERSON_TWO laughs: 'Bro, they released a REcord! "
                "But tomorrow we have to reCORD our own track!' Mandatory: keep uppercase "
                "stress REcord and reCORD in dialogue."
            ),
            "SPECIAL_TREATMENT": "phonetic",
        }
        with patch("video_creation._A_video_scripts.prompts.prompt_builder.load_call_to_actions",
                   return_value=[]):
            prompt = build_prompt(phonetic_params)

        # Stress-pair instructions must be present (already handled by is_stress_pair detection)
        self.assertIn("UPPERCASE", prompt,
                      "Phonetic scripts must contain stress capitalization instructions")
        # Idiomatic arc must NOT be injected for phonetic scripts
        self.assertNotIn("SPECIAL TREATMENT: IDIOMATIC", prompt,
                         "Phonetic scripts must NOT receive idiomatic arc instructions")

    # ------------------------------------------------------------------
    # Test 4 — false_friend type gets false-friend guard, not idiomatic arc
    # ------------------------------------------------------------------
    def test_false_friend_prompt_does_not_inject_idiomatic_arc(self):
        """SPECIAL_TREATMENT=false_friend must not inject idiomatic arc instructions."""
        ff_params = {
            **BASE_ROLEPLAY_PARAMS,
            "TARGET_LANGUAGE": "French",
            "ROLEPLAY_SCENARIO": (
                "Au bureau: PERSON_ONE dit 'Je suis embarrassée' en pensant à 'embarrassed' "
                "en anglais, mais PERSON_TWO réagit avec surprise car 'embarrassée' en "
                "français veut dire 'encombrée / dans l\\'embarras'."
            ),
            "SPECIAL_TREATMENT": "false_friend",
        }
        with patch("video_creation._A_video_scripts.prompts.prompt_builder.load_call_to_actions",
                   return_value=[]):
            prompt = build_prompt(ff_params)

        # The false-friend guard should be present
        self.assertIn("FALSE FRIEND", prompt.upper(),
                      "False friend scripts must contain the false-friend guard block")
        # Idiomatic arc must NOT be injected
        self.assertNotIn("SPECIAL TREATMENT: IDIOMATIC", prompt,
                         "False friend scripts must NOT receive idiomatic arc instructions")

    # ------------------------------------------------------------------
    # Test 5 — blank SPECIAL_TREATMENT produces identical output to absent field
    # ------------------------------------------------------------------
    def test_blank_special_treatment_is_default_behavior(self):
        """Empty SPECIAL_TREATMENT must not change the prompt vs. absent field."""
        params_blank   = {**BASE_ROLEPLAY_PARAMS, "SPECIAL_TREATMENT": ""}
        params_absent  = {**BASE_ROLEPLAY_PARAMS}

        with patch("video_creation._A_video_scripts.prompts.prompt_builder.load_call_to_actions",
                   return_value=[]):
            prompt_blank  = build_prompt(params_blank)
            prompt_absent = build_prompt(params_absent)

        self.assertEqual(
            prompt_blank, prompt_absent,
            "An empty SPECIAL_TREATMENT must produce the same prompt as a missing field"
        )

    # ------------------------------------------------------------------
    # Test 6 — validate_idiomatic_roleplay: PASSES when P1 uses the idiom in DIALOGUE_PART_4
    # ------------------------------------------------------------------
    def test_idiomatic_validation_passes_when_p1_uses_idiom_in_part4(self):
        """Validator must return no errors when P1 correctly uses the idiom in DIALOGUE_PART_4."""
        errors = validate_idiomatic_roleplay(
            script=VALID_IDIOMATIC_SCRIPT,
            params=BASE_ROLEPLAY_PARAMS,
        )
        self.assertEqual(
            errors, [],
            f"Expected no validation errors but got: {errors}"
        )

    # ------------------------------------------------------------------
    # Test 7 — validate_idiomatic_roleplay: FAILS when P1 only reacts in DIALOGUE_PART_4
    # ------------------------------------------------------------------
    def test_idiomatic_validation_fails_when_p1_only_reacts_in_part4(self):
        """Validator must flag Error #4: P1 does not use the idiom in DIALOGUE_PART_4."""
        errors = validate_idiomatic_roleplay(
            script=INVALID_IDIOMATIC_SCRIPT_NO_USAGE,
            params=BASE_ROLEPLAY_PARAMS,
        )
        self.assertGreater(
            len(errors), 0,
            "Expected at least one validation error when P1 never uses the idiom in DIALOGUE_PART_4"
        )
        # The error message must point to the usage modeling problem
        combined = " ".join(errors).lower()
        self.assertTrue(
            "usage" in combined or "dialogue_part_4" in combined or "person_one" in combined,
            f"Error message must reference the usage modeling failure. Got: {errors}"
        )

    # ------------------------------------------------------------------
    # Test 8 — READY_PROMPTS_ROLEPLAY.sample.csv has SPECIAL_TREATMENT column
    # ------------------------------------------------------------------
    def test_roleplay_sample_csv_has_special_treatment_column(self):
        """Contract test: the sample ROLEPLAY CSV must include the SPECIAL_TREATMENT column."""
        self.assertTrue(
            SAMPLE_CSV_PATH.exists(),
            f"Sample CSV not found at {SAMPLE_CSV_PATH}"
        )
        with SAMPLE_CSV_PATH.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

        self.assertIn(
            "SPECIAL_TREATMENT",
            fieldnames,
            f"READY_PROMPTS_ROLEPLAY.sample.csv must have a SPECIAL_TREATMENT column. "
            f"Found columns: {fieldnames}"
        )


if __name__ == "__main__":
    unittest.main()
