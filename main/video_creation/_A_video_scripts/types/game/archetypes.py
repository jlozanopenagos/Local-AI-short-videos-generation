"""
types/game/archetypes.py — Multi-archetype domain definitions, automatic detection,
and prompt directives for viral linguistic micro-learning challenges.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class GameArchetype:
    """Canonical game archetype identifiers."""
    FALSE_FRIEND_TRAP = "FALSE_FRIEND_TRAP"
    ODD_ONE_OUT = "ODD_ONE_OUT"
    SPOT_THE_MISTAKE = "SPOT_THE_MISTAKE"
    MINIMAL_PAIR_SHOWDOWN = "MINIMAL_PAIR_SHOWDOWN"
    FILL_IN_THE_BLANK_SPEEDRUN = "FILL_IN_THE_BLANK_SPEEDRUN"

    ALL = [
        FALSE_FRIEND_TRAP,
        ODD_ONE_OUT,
        SPOT_THE_MISTAKE,
        MINIMAL_PAIR_SHOWDOWN,
        FILL_IN_THE_BLANK_SPEEDRUN,
    ]


ARCHETYPE_METADATA: Dict[str, Dict[str, Any]] = {
    GameArchetype.FALSE_FRIEND_TRAP: {
        "display_name": "False Friend Trap",
        "description": "Exposes deceptive cognates and funny translation blunders (e.g. parenti vs parents, embarazada vs embarrassed).",
        "default_options": 4,
        "recommended_options": [3, 4],
    },
    GameArchetype.ODD_ONE_OUT: {
        "display_name": "Odd One Out",
        "description": "Pattern recognition challenge with 3 or 4 options where one breaks a hidden grammar or category rule.",
        "default_options": 4,
        "recommended_options": [3, 4],
    },
    GameArchetype.SPOT_THE_MISTAKE: {
        "display_name": "Spot the Mistake",
        "description": "Ego-challenge targeting common learner errors (wrong prepositions, false agreement).",
        "default_options": 4,
        "recommended_options": [3, 4],
    },
    GameArchetype.MINIMAL_PAIR_SHOWDOWN: {
        "display_name": "Minimal Pair / Stress Showdown",
        "description": "Auditory perception challenge testing word stress (PROject vs proJECT) or minimal phonetic sound contrasts.",
        "default_options": 2,
        "recommended_options": [2, 3],
    },
    GameArchetype.FILL_IN_THE_BLANK_SPEEDRUN: {
        "display_name": "Fill-in-the-Blank Speedrun",
        "description": "High-velocity collocation and idiomatic sprint with 3 or 4 candidate options.",
        "default_options": 4,
        "recommended_options": [3, 4],
    },
}


def detect_game_archetype(input_data: Dict[str, Any]) -> str:
    """
    Detects the best suited game archetype from input metadata.
    Prioritizes explicit user override ('GAME_ARCHETYPE' or 'game_archetype'),
    then analyzes topic, subject, expression, and context keywords.
    """
    # 1. Explicit manual override (e.g. from WebUI dropdown)
    explicit = (
        input_data.get("GAME_ARCHETYPE")
        or input_data.get("game_archetype")
        or ""
    ).strip().upper()

    if explicit in GameArchetype.ALL:
        return explicit

    # 2. Inspect linguistic focus and keywords
    expr = str(
        input_data.get("TARGET_EXPRESSION")
        or input_data.get("target_expression")
        or input_data.get("EXPRESSION")
        or input_data.get("expression")
        or ""
    ).strip()

    subject = str(input_data.get("SUBJECT") or input_data.get("subject") or "").strip()
    special = str(input_data.get("SPECIAL_TREATMENT") or input_data.get("special_treatment") or "").strip()
    context = str(input_data.get("CONTEXT") or input_data.get("context") or "").strip()
    topic = str(input_data.get("TOPIC") or input_data.get("topic") or "").strip()

    combined_text = f"{expr} {subject} {special} {context} {topic}".lower()

    # Minimal Pair / Stress Showdown
    if (
        "stress" in combined_text
        or "heteronym" in combined_text
        or "pronunciation" in combined_text
        or "accent" in combined_text
        or "syllable" in combined_text
        or re.search(r"\b[a-z]+[A-Z]{2,}|\b[A-Z]{2,}[a-z]+", expr)
    ):
        return GameArchetype.MINIMAL_PAIR_SHOWDOWN

    # False Friend Trap
    if (
        "false friend" in combined_text
        or "falso amigo" in combined_text
        or "falsos amigos" in combined_text
        or "faux-ami" in combined_text
        or "faux ami" in combined_text
        or "false cognate" in combined_text
        or "cognado" in combined_text
        or any(w in combined_text for w in ["parenti", "embarazada", "actuellement", "librería", "preservative", "sensible"])
    ):
        return GameArchetype.FALSE_FRIEND_TRAP

    # Odd One Out
    if (
        "odd one" in combined_text
        or "intruso" in combined_text
        or "intrus" in combined_text
        or "intruder" in combined_text
        or "which one does not belong" in combined_text
        or "outlier" in combined_text
    ):
        return GameArchetype.ODD_ONE_OUT

    # Idiom / Figurative Meaning Trap (e.g. Break a leg, Poser un lapin, Costar un ojo de la cara)
    if (
        "idiom" in combined_text
        or "modismo" in combined_text
        or "expression idiomatique" in combined_text
        or "superstition" in combined_text
        or "refrán" in combined_text
        or "proverbe" in combined_text
        or "dicho" in combined_text
    ):
        return GameArchetype.FALSE_FRIEND_TRAP

    # Spot the Mistake
    if (
        "mistake" in combined_text
        or "error" in combined_text
        or "faute" in combined_text
        or "wrong preposition" in combined_text
        or "common error" in combined_text
        or "spot the" in combined_text
        or "find the mistake" in combined_text
    ):
        return GameArchetype.SPOT_THE_MISTAKE

    # Balanced fallback based on script_id hash
    script_id = str(input_data.get("SCRIPT_ID") or input_data.get("script_id") or "GAME01")
    hash_val = sum(ord(c) for c in script_id)
    fallbacks = [
        GameArchetype.FILL_IN_THE_BLANK_SPEEDRUN,
        GameArchetype.FALSE_FRIEND_TRAP,
        GameArchetype.SPOT_THE_MISTAKE,
        GameArchetype.ODD_ONE_OUT,
    ]
    return fallbacks[hash_val % len(fallbacks)]


def get_localized_game_header(archetype: str, language: str) -> str:
    """Returns the culturally authentic, target-language header for chalkboard rendering."""
    lang = (language or "english").strip().lower()
    headers = {
        GameArchetype.ODD_ONE_OUT: {
            "english": "SPOT THE INTRUDER:",
            "french": "TROUVEZ L'INTRUS :",
            "spanish": "¡ENCUENTRA EL INTRUSO!:",
            "italian": "TROVA L'INTRUSO:",
        },
        GameArchetype.SPOT_THE_MISTAKE: {
            "english": "WHERE IS THE MISTAKE? / COMPLETE NATURALLY:",
            "french": "OÙ EST L'ERREUR ? / COMPLÉTEZ :",
            "spanish": "¿DÓNDE ESTÁ EL ERROR? / COMPLETA :",
            "italian": "DOV'È L'ERRORE? / COMPLETA :",
        },
        GameArchetype.FILL_IN_THE_BLANK_SPEEDRUN: {
            "english": "COMPLETE THE EXPRESSION:",
            "french": "COMPLÉTEZ L'EXPRESSION :",
            "spanish": "COMPLETA LA EXPRESIÓN:",
            "italian": "COMPLETA L'ESPRESSIONE:",
        },
        GameArchetype.FALSE_FRIEND_TRAP: {
            "english": "WHAT DOES IT MEAN?",
            "french": "QUE SIGNIFIE CETTE EXPRESSION ?",
            "spanish": "¿QUÉ SIGNIFICA ESTA EXPRESIÓN?",
            "italian": "COSA SIGNIFICA QUESTA ESPRESSIONE?",
        },
        GameArchetype.MINIMAL_PAIR_SHOWDOWN: {
            "english": "WHICH WORD DID YOU HEAR?",
            "french": "QUEL MOT AVEZ-VOUS ENTENDU ?",
            "spanish": "¿QUÉ PALABRA ESCUCHASTE?",
            "italian": "QUALE PAROLA HAI SENTITO?",
        },
    }
    arch_map = headers.get(archetype, {})
    return arch_map.get(lang, arch_map.get("english", "CHALLENGE:"))


def get_archetype_prompt_instructions(archetype: str, target_lang: str, expr: str) -> str:
    """Returns specialized prompt instructions tailored to the specific game archetype."""
    target_lang_upper = target_lang.upper()
    lang_lower = (target_lang or "english").strip().lower()
    header = get_localized_game_header(archetype, lang_lower)

    if archetype == GameArchetype.FALSE_FRIEND_TRAP:
        return f"""
-----------------------------
GAME ARCHETYPE: FALSE FRIEND TRAP / IDIOM TRAP (Falsos Amigos / Faux-amis)
-----------------------------
CORE OBJECTIVE: Break the deceptive translation trap where a learner's brain translates a look-alike literally, or test the native meaning of an idiom!
NUMBER OF OPTIONS: Provide EXACTLY 3 or 4 options (A, B, C, optionally D).
- Option A or B MUST be the deceptive literal trap that sounds like a cognate (e.g. "Poser un lapin" -> "He gave you a pet rabbit", "Break a leg" -> "Break your bone").
- One option MUST be the true authentic native meaning.
- Remaining options MUST be plausible but distinct contextual distractors.

SPOKEN NARRATION RULES (TTS AUDIO):
- Hook: High-energy pattern-interrupt warning about an embarrassing or funny translation mishap (100% in {target_lang_upper}).
- Challenge: Spoken naturally by the Narrator voicing the test scenario with the native phrase in place, then explicitly voicing ALL candidate meanings cleanly:
  e.g.: "If your friend says 'Sono pieno di parenti', what does it mean? A: I have many parents.  B: I have many relatives.  C: I have many partners.  D: I have many debts."
  e.g. French: "Ton ami te dit : 'Hier soir, Thomas m'a posé un lapin !' Que s'est-il passé ? A: Il lui a offert un animal.  B: Il n'est pas venu au rendez-vous.  C: Il a payé l'addition.  D: Il est arrivé en retard."
  (NEVER include raw '___' in spoken audio!)
  (NEVER give away the meaning in the question!)
- Pressure: Fast urgency line (3 seconds countdown, 100% in {target_lang_upper}).
- Answer: Direct reveal (e.g. "It's B!", "¡Es la B!", "C'est la B !") explaining why the deceptive trap is wrong and what the true native meaning is.
- Explanation: Real-life native usage contrast with an engaging loop hook.

VISUAL CHALKBOARD RULES (ON SCREEN):
- 100% IN {target_lang_upper}: The entire 'chalkboard_exercise' MUST be strictly in {target_lang_upper}. ZERO English text or headers!
- The 'chalkboard_exercise' MUST be multiline with the header, challenge phrase, and 3-4 options:
  {header}
  [Clear test sentence or phrase in {target_lang_upper}]
  A) [Option A in {target_lang_upper}]
  B) [Option B in {target_lang_upper}]
  C) [Option C in {target_lang_upper}]
  D) [Option D in {target_lang_upper} (optional)]
"""

    elif archetype == GameArchetype.ODD_ONE_OUT:
        return f"""
-----------------------------
GAME ARCHETYPE: ODD ONE OUT (El Intruso / L'Intrus)
-----------------------------
CORE OBJECTIVE: Pattern recognition! 3 words or forms follow a strict grammatical, phonetic, or semantic rule, and ONE is an intruder.
NUMBER OF OPTIONS: Provide EXACTLY 3 or 4 options (A, B, C, and optionally D).
- Three options share an invisible morphological or linguistic rule (e.g. irregular verbs, feminine endings, subjunctive triggers, formal idioms).
- Exactly ONE option breaks the rule (the intruder).

SPOKEN NARRATION RULES (TTS AUDIO):
- Hook: Challenge the learner's pattern recognition ("Three of these words share an invisible secret, but one is a trap!", 100% in {target_lang_upper}).
- Challenge: Spoken naturally voicing each option clearly without filler:
  e.g.: "Listen to all four verbs: A: Went.  B: Bought.  C: Fixed.  D: Caught. Which one is the odd one out?"
  e.g. French: "Écoute ces quatre verbes : A: Mangé.  B: Chanté.  C: Parlé.  D: Pris. Lequel est l'intrus ?"
- Pressure: Fast urgency line (3 seconds countdown, 100% in {target_lang_upper}).
- Answer: Reveal the winning letter and name the exact linguistic pattern that unifies the others.
- Explanation: Brief native breakdown of the grammar rule and invitation to drop score in the comments.

VISUAL CHALKBOARD RULES (ON SCREEN):
- 100% IN {target_lang_upper}: The entire 'chalkboard_exercise' MUST be strictly in {target_lang_upper}. ZERO English text or headers!
- The 'chalkboard_exercise' MUST display:
  {header}
  A) [Word 1 in {target_lang_upper}]
  B) [Word 2 in {target_lang_upper}]
  C) [Word 3 in {target_lang_upper}]
  D) [Word 4 in {target_lang_upper} (optional)]
"""

    elif archetype == GameArchetype.SPOT_THE_MISTAKE:
        return f"""
-----------------------------
GAME ARCHETYPE: SPOT THE MISTAKE (Encuentra el Error / Trouve la Faute)
-----------------------------
CORE OBJECTIVE: Train the learner to catch the #1 subtle grammatical or prepositional mistake that 90% of intermediate learners make!
NUMBER OF OPTIONS: Provide EXACTLY 3 or 4 options (A, B, C, optionally D).
- Present candidate corrections for the error (e.g. different prepositions, conjugations, or phrasing variants).
- Exactly ONE option is 100% grammatically natural for a native speaker.
- ❌ NEVER put the candidate answer word inside the challenge sentence before asking the question!

SPOKEN NARRATION RULES (TTS AUDIO):
- Hook: High-energy challenge targeting a common learner mistake ("Native speakers use this daily, but 90% of students say it wrong!", 100% in {target_lang_upper}).
- Challenge: Voice the scenario or question sentence naturally and read the candidate options cleanly:
  e.g.: "How do you naturally complete this phrase: 'It depends...' A: on your choice.  B: of your choice.  C: from your choice.  D: with your choice."
  e.g. French: "Comment dit-on naturellement en français : A: Dépendre de toi.  B: Dépendre sur toi.  C: Dépendre à toi.  D: Dépendre pour toi."
- Pressure: Snappy countdown line (100% in {target_lang_upper}).
- Answer: Direct reveal with the grammatical rule and why the common distractor is an error.
- Explanation: Native mnemonic trick to never make that mistake again.

VISUAL CHALKBOARD RULES (ON SCREEN):
- 100% IN {target_lang_upper}: The entire 'chalkboard_exercise' MUST be strictly in {target_lang_upper}. ZERO English text or headers!
- The 'chalkboard_exercise' MUST display the sentence with a blank (___) and options:
  {header}
  "Sentence with ___ in {target_lang_upper}"
  A) [Correction A in {target_lang_upper}]
  B) [Correction B in {target_lang_upper}]
  C) [Correction C in {target_lang_upper}]
  D) [Correction D in {target_lang_upper} (optional)]
"""

    elif archetype == GameArchetype.MINIMAL_PAIR_SHOWDOWN:
        return f"""
-----------------------------
GAME ARCHETYPE: MINIMAL PAIR / STRESS SHOWDOWN
-----------------------------
CORE OBJECTIVE: Auditory and phonetic perception! Differentiate syllable stress (noun vs verb heteronyms) or subtle phonetic contrast.
NUMBER OF OPTIONS: Provide 2 or 3 options (A, B, optionally C).
- Target contrast: '{expr}'
- One option is the noun/adjective form, the other is the verb/alternative form.

SPOKEN NARRATION RULES (TTS AUDIO):
- Hook: Auditory challenge ("Did you know shifting one syllable completely changes this word from an object to an action?", 100% in {target_lang_upper}).
- Challenge: Spoken naturally by the Narrator pronouncing the test sentence with the exact native inflection, followed by:
  "Which word did you hear? A: [Option A].  B: [Option B]."
- Pressure: Fast countdown line (100% in {target_lang_upper}).
- Answer: Reveal the correct option and break down the stress rule (e.g. "Stress on first syllable for nouns, second for verbs!").
- Explanation: Native pronunciation tip.

VISUAL CHALKBOARD RULES (ON SCREEN):
- 100% IN {target_lang_upper}: The entire 'chalkboard_exercise' MUST be strictly in {target_lang_upper}. ZERO English text or headers!
- The 'chalkboard_exercise' MUST display UPPERCASE syllable stress notation:
  {header}
  [Sentence with ___ in {target_lang_upper}]
  A) [e.g. PROject (noun)]
  B) [e.g. proJECT (verb)]
"""

    else:  # FILL_IN_THE_BLANK_SPEEDRUN (default)
        return f"""
-----------------------------
GAME ARCHETYPE: FILL-IN-THE-BLANK SPEEDRUN (Rellena el Hueco)
-----------------------------
CORE OBJECTIVE: Fast-paced idiomatic and collocation challenge under time pressure!
NUMBER OF OPTIONS: Provide EXACTLY 3 or 4 options (A, B, C, and optionally D).
- One option is the authentic native collocation or idiom.
- Other options are plausible contextual distractors (different prepositions, synonyms, or literal translations).
- ❌ NEVER put the answer word into the prompt sentence!

SPOKEN NARRATION RULES (TTS AUDIO):
- Hook: Speedrun dilemma ("Quick test! You have three seconds to finish this native phrase!", 100% in {target_lang_upper}).
- Challenge: Spoken naturally voicing the context up to the missing element or asking which choice completes it:
  e.g.: "Which word completes this common idiom: 'To cost an arm and a...' A: leg.  B: hand.  C: foot.  D: head."
  e.g. French: "Quel mot complète cette expression : 'Hier, il m'a posé un...' A: lapin.  B: lièvre.  C: chat.  D: renard."
- Pressure: Fast urgency countdown line (100% in {target_lang_upper}).
- Answer: Direct reveal with the idiomatic origin and meaning.
- Explanation: How natives use it in daily conversation.

VISUAL CHALKBOARD RULES (ON SCREEN):
- 100% IN {target_lang_upper}: The entire 'chalkboard_exercise' MUST be strictly in {target_lang_upper}. ZERO English text or headers!
- The 'chalkboard_exercise' MUST display:
  {header}
  [Contextual sentence with blank ___ in {target_lang_upper}]
  A) [Option A in {target_lang_upper}]
  B) [Option B in {target_lang_upper}]
  C) [Option C in {target_lang_upper}]
  D) [Option D in {target_lang_upper} (optional)]
"""

