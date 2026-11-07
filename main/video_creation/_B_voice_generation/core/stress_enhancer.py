"""
Module for detecting and enhancing word stress pronunciation for Text-to-Speech (TTS).

In English educational scripts (especially heteronyms / noun-verb pairs), capital letters
denote syllable stress (e.g. 'REcord' vs 'reCORD', 'PERmit' vs 'perMIT').
If mid-word capitalization or hyphens like 're-CORD' are passed directly to TTS models,
tokenizers isolate prefixes like 're' and pronounce them with an unnatural /re/ or /reɪ/
sound, instead of the authentic reduced vowel /rɪ/ in /rɪˈkɔːrd/.

This module:
1. Normalizes capitalized stress notation to natural English words for the TTS model.
2. Injects precise phonetic and IPA style directives instructing the model on authentic
   syllable stress and vowel reduction without artificial /re/ sounds.
"""

import re
from typing import Dict, List, Tuple

# Common English heteronyms and pronunciation-contrast words with comprehensive IPA guidance
# Includes explicit negative constraints to prevent TTS models from pronouncing reduced prefixes
# with tense vowels (e.g. preventing /re/ for 'record', /pre/ for 'present', /proʊ/ for 'project', /diː/ for 'decrease').
# Supported English heteronyms and pronunciation contrast words
ENGLISH_HETERONYMS: List[str] = [
    "record", "present", "project", "permit", "object",
    "contract", "increase", "decrease", "import", "export",
    "protest", "contest", "advise", "advice", "discuss", "argue"
]


def enhance_stress_text_for_tts(text: str, language: str = "english") -> Tuple[str, List[str]]:
    """Transforms written text containing stress capitalization into clean, fluent text for TTS.
    
    Under Option B (Continuous Syntactic Carrier Architecture):
    1. Replaces capitalized syllable notation (e.g. 'PREsent', 'preSENT', 'PROject', 'proJECT')
       with clean standard English words to eliminate Byte-Pair Encoding (BPE) subword
       fragmentation and stuttering artifacts ("pro ejct").
    2. Ensures grammatical carrier particles ('the noun a [word]', 'the verb to [word]') are
       present so the neural TTS model naturally synthesizes authentic syllable stress and vowel reduction.
    3. Retains full visual capitalization in script JSON for on-screen animated captions.
    
    Returns:
        Tuple of (enhanced_text_for_tts, list_of_detected_base_words)
    """
    if not text:
        return text, []

    detected_words: List[str] = []

    # Pre-pass: Sanitize any raw IPA slashes (e.g. /ˈrek.ɚd/ or /rɪˈkɔːrd/) that would break TTS tokenizers
    ipa_heteronym_replacements = [
        (r"/[^/\s]*rek[^/\s]*/", "record"),
        (r"/[^/\s]*k[ɔo]ː?[^/\s]*/", "record"),
        (r"/[^/\s]*pr[ɛe]z[^/\s]*/", "present"),
        (r"/[^/\s]*dʒ[ɛe]kt[^/\s]*/", "project"),
        (r"/[^/\s]*m[ɪi]t[^/\s]*/", "permit"),
        (r"/[^/\s]*tr[æa]kt[^/\s]*/", "contract"),
        (r"/[^/\s]*kriːs[^/\s]*/", "increase"),
    ]
    for pattern, rep_word in ipa_heteronym_replacements:
        if re.search(pattern, text):
            text = re.sub(pattern, rep_word, text)
            if rep_word not in detected_words:
                detected_words.append(rep_word)

    # General catch-all: strip remaining phonetic slashes containing IPA symbols
    text = re.sub(r"/[ˈˌɚɪɔːɛæʊəθðʃʒŋa-zA-Z.'-]{2,}/", "", text)

    # Pattern matches words with capitalized syllables or hyphenated stress notation:
    # e.g. REcord, reCORD, re-CORD, RE-cord, PERmit, perMIT, PROject, proJECT, PREsent, preSENT
    stress_pattern = r'\b([a-z]+[A-Z]{2,}|[A-Z]{2,}[a-z]+|[a-zA-Z]+-[A-Z]{2,}|[A-Z]{2,}-[a-zA-Z]+)\b'
    
    matches = re.findall(stress_pattern, text)
    for m in matches:
        if re.match(r'^(?:[IVXLCDM]+)(?:e|er|ème|ère|th|st|nd|rd)$', m, re.IGNORECASE):
            continue
        base = m.replace("-", "").lower()
        if base not in detected_words:
            detected_words.append(base)

    if (language or "english").lower() != "english":
        # For non-English languages, return cleaned text without altering words
        return text, detected_words

    def repl_clean(m):
        raw = m.group(0)
        # Preserve Roman numerals with ordinal suffixes (e.g. XIXe, XXe, Ier)
        if re.match(r'^(?:[IVXLCDM]+)(?:e|er|ème|ère|th|st|nd|rd)$', raw, re.IGNORECASE):
            return raw
        
        # Check if this token is an intentional learner error (e.g. reCORD in noun slot)
        # We rewrite it to its phonetic counterpart so the neural TTS produces the exact intended vowels.
        base = raw.replace("-", "").lower()
        if base in INTENTIONAL_ERROR_PHONETIC_REWRITES:
            raw_no_dash = raw.replace("-", "")
            vis_role = None
            if len(raw_no_dash) >= 4:
                if re.search(r'^[A-Z]{2,}[a-z]+', raw_no_dash) or (raw_no_dash[:2].isupper() and raw_no_dash[-2:].islower()):
                    vis_role = "noun"
                elif re.search(r'^[a-z]+[A-Z]{2,}', raw_no_dash) or (raw_no_dash[:2].islower() and raw_no_dash[-2:].isupper()):
                    vis_role = "verb"
            
            tok_errors = detect_intentional_stress_errors(text, [base])
            for err in tok_errors:
                if err["token"].strip("'-").replace("-", "") == raw_no_dash and err["visual_role"] == vis_role:
                    rewrite = INTENTIONAL_ERROR_PHONETIC_REWRITES[base].get(vis_role)
                    if rewrite:
                        return rewrite

        return base

    result = re.sub(stress_pattern, repl_clean, text)

    # Contextual carrier normalization: ensure "the noun [word]" has "a", and "the verb [word]" has "to"
    for base in ENGLISH_HETERONYMS:
        # Check for "the noun {base}" or "is a noun {base}" without an article:
        result = re.sub(
            rf"\b(the\s+noun|as\s+a\s+noun|is\s+a\s+noun)\s+['\"]?{base}['\"]?",
            rf"\1 a {base}",
            result,
            flags=re.IGNORECASE
        )
        # Check for "the verb {base}" or "as a verb {base}" without infinitive:
        result = re.sub(
            rf"\b(the\s+verb|to\s+use\s+the\s+verb|as\s+a\s+verb)\s+['\"]?{base}['\"]?",
            rf"\1 to {base}",
            result,
            flags=re.IGNORECASE
        )
        # Clean up any accidental double carriers
        result = re.sub(rf"\b(the\s+noun)\s+a\s+a\b", r"\1 a", result, flags=re.IGNORECASE)
        result = re.sub(rf"\b(the\s+verb)\s+to\s+to\b", r"\1 to", result, flags=re.IGNORECASE)

    # Clean whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    return result, detected_words


NOUN_DETERMINERS = {
    "a", "an", "the", "this", "that", "these", "those",
    "my", "your", "his", "her", "its", "our", "their",
    "noun", "lovely", "big", "new", "great", "whole", "good", "official", "valid"
}

VERB_MARKERS = {
    "to", "will", "would", "shall", "should", "can", "could",
    "may", "might", "must", "did", "do", "does", "verb",
    "i", "you", "he", "she", "it", "we", "they"
}

# Explicit phonetic respellings for intentional learner error simulation
# When a speaker intentionally mispronounces a word (e.g. pronouncing the verb form in a noun syntactic slot),
# neural TTS language-model priors will stubbornly force the noun pronunciation unless the phonetic respelling is fed.
# These respellings are calibrated to produce authentic English phonemes while preserving flawless Whisper transcription.
INTENTIONAL_ERROR_PHONETIC_REWRITES: Dict[str, Dict[str, str]] = {
    "record": {"verb": "ri-cord", "noun": "REK-erd"},
    "permit": {"verb": "per-mit", "noun": "PUR-mit"},
    "present": {"verb": "pri-zent", "noun": "PREZ-ent"},
    "project": {"verb": "pruh-jekt", "noun": "PRAH-jekt"},
    "object": {"verb": "ub-jekt", "noun": "AHB-jekt"},
    "contract": {"verb": "kuhn-trakt", "noun": "KAHN-trakt"},
    "contest": {"verb": "kuhn-test", "noun": "KAHN-test"},
    "conduct": {"verb": "kuhn-dukt", "noun": "KAHN-dukt"},
    "conflict": {"verb": "kuhn-flikt", "noun": "KAHN-flikt"},
    "desert": {"verb": "di-zert", "noun": "DEZ-ert"},
    "rebel": {"verb": "ri-bel", "noun": "REB-el"},
    "suspect": {"verb": "suh-spekt", "noun": "SUHS-pekt"},
    "increase": {"verb": "in-krees", "noun": "IN-krees"},
    "decrease": {"verb": "di-krees", "noun": "DEE-krees"}
}

HETERONYM_PHONETIC_HINTS: Dict[str, Dict[str, Dict[str, str]]] = {
    "record": {
        "verb": {"respell": "/ri-KORD/", "stress": "second", "desc": "second-syllable stress as a verb /ri-KORD/ (stressing the final syllable)"},
        "noun": {"respell": "/REK-erd/", "stress": "first", "desc": "first-syllable stress as a noun /REK-erd/ (stressing the first syllable)"}
    },
    "permit": {
        "verb": {"respell": "/per-MIT/", "stress": "second", "desc": "second-syllable stress as a verb /per-MIT/ (stressing the final syllable)"},
        "noun": {"respell": "/PER-mit/", "stress": "first", "desc": "first-syllable stress as a noun /PER-mit/ (stressing the first syllable)"}
    },
    "present": {
        "verb": {"respell": "/pri-ZENT/", "stress": "second", "desc": "second-syllable stress as a verb /pri-ZENT/ (stressing the final syllable)"},
        "noun": {"respell": "/PREZ-ent/", "stress": "first", "desc": "first-syllable stress as a noun /PREZ-ent/ (stressing the first syllable)"}
    },
    "project": {
        "verb": {"respell": "/pruh-JEKT/", "stress": "second", "desc": "second-syllable stress as a verb /pruh-JEKT/ (stressing the final syllable)"},
        "noun": {"respell": "/PRAH-jekt/", "stress": "first", "desc": "first-syllable stress as a noun /PRAH-jekt/ (stressing the first syllable)"}
    },
    "object": {
        "verb": {"respell": "/ub-JEKT/", "stress": "second", "desc": "second-syllable stress as a verb /ub-JEKT/ (stressing the final syllable)"},
        "noun": {"respell": "/AHB-jekt/", "stress": "first", "desc": "first-syllable stress as a noun /AHB-jekt/ (stressing the first syllable)"}
    },
    "contest": {
        "verb": {"respell": "/kuhn-TEST/", "stress": "second", "desc": "second-syllable stress as a verb /kuhn-TEST/ (stressing the final syllable)"},
        "noun": {"respell": "/KAHN-test/", "stress": "first", "desc": "first-syllable stress as a noun /KAHN-test/ (stressing the first syllable)"}
    },
    "conduct": {
        "verb": {"respell": "/kuhn-DUKT/", "stress": "second", "desc": "second-syllable stress as a verb /kuhn-DUKT/ (stressing the final syllable)"},
        "noun": {"respell": "/KAHN-dukt/", "stress": "first", "desc": "first-syllable stress as a noun /KAHN-dukt/ (stressing the first syllable)"}
    },
    "contract": {
        "verb": {"respell": "/kuhn-TRAKT/", "stress": "second", "desc": "second-syllable stress as a verb /kuhn-TRAKT/ (stressing the final syllable)"},
        "noun": {"respell": "/KAHN-trakt/", "stress": "first", "desc": "first-syllable stress as a noun /KAHN-trakt/ (stressing the first syllable)"}
    },
    "conflict": {
        "verb": {"respell": "/kuhn-FLIKT/", "stress": "second", "desc": "second-syllable stress as a verb /kuhn-FLIKT/ (stressing the final syllable)"},
        "noun": {"respell": "/KAHN-flikt/", "stress": "first", "desc": "first-syllable stress as a noun /KAHN-flikt/ (stressing the first syllable)"}
    },
    "desert": {
        "verb": {"respell": "/di-ZERT/", "stress": "second", "desc": "second-syllable stress as a verb /di-ZERT/ (stressing the final syllable)"},
        "noun": {"respell": "/DEZ-ert/", "stress": "first", "desc": "first-syllable stress as a noun /DEZ-ert/ (stressing the first syllable)"}
    },
    "rebel": {
        "verb": {"respell": "/ri-BEL/", "stress": "second", "desc": "second-syllable stress as a verb /ri-BEL/ (stressing the final syllable)"},
        "noun": {"respell": "/REB-el/", "stress": "first", "desc": "first-syllable stress as a noun /REB-el/ (stressing the first syllable)"}
    },
    "suspect": {
        "verb": {"respell": "/suh-SPEKT/", "stress": "second", "desc": "second-syllable stress as a verb /suh-SPEKT/ (stressing the final syllable)"},
        "noun": {"respell": "/SUHS-pekt/", "stress": "first", "desc": "first-syllable stress as a noun /SUHS-pekt/ (stressing the first syllable)"}
    },
    "increase": {
        "verb": {"respell": "/in-KREES/", "stress": "second", "desc": "second-syllable stress as a verb /in-KREES/ (stressing the final syllable)"},
        "noun": {"respell": "/IN-krees/", "stress": "first", "desc": "first-syllable stress as a noun /IN-krees/ (stressing the first syllable)"}
    },
    "decrease": {
        "verb": {"respell": "/di-KREES/", "stress": "second", "desc": "second-syllable stress as a verb /di-KREES/ (stressing the final syllable)"},
        "noun": {"respell": "/DEE-krees/", "stress": "first", "desc": "first-syllable stress as a noun /DEE-krees/ (stressing the first syllable)"}
    }
}


def detect_intentional_stress_errors(text: str, target_words: List[str]) -> List[Dict[str, str]]:
    """Detects deliberate learner pronunciation errors in educational dialogues.
    
    Identifies occurrences where the visual casing (e.g. 'reCORD' or 'perMIT') represents
    a phonetic role (verb) that intentionally conflicts with surrounding syntax (noun determiner).
    """
    if not text or not target_words:
        return []

    tokens = re.findall(r"[\w'-]+", text)
    stems = {w.lower()[:4]: w.lower() for w in target_words}
    errors = []

    for i, token in enumerate(tokens):
        clean_tok = token.strip("'-").lower()
        matched = None
        for stem in stems:
            if stem in clean_tok:
                matched = stem
                break
        if not matched:
            continue

        raw = token.strip("'-")
        raw_no_dash = raw.replace("-", "")

        visual_role = None
        if len(raw_no_dash) >= 4:
            if re.search(r'^[A-Z]{2,}[a-z]+', raw_no_dash) or (raw_no_dash[:2].isupper() and raw_no_dash[-2:].islower()):
                visual_role = "noun"
            elif re.search(r'^[a-z]+[A-Z]{2,}', raw_no_dash) or (raw_no_dash[:2].islower() and raw_no_dash[-2:].isupper()):
                visual_role = "verb"

        if not visual_role:
            continue

        syntactic_role = None
        # Check immediately preceding word for speech/citation verbs (e.g. "say PERmit", "is PERmit")
        # In citation context ("you must say PERmit"), the word is cited, NOT acting as an intentional verb error.
        citation_markers = {"say", "says", "said", "pronounce", "pronounced", "pronouncing", "word", "is", "called"}
        prev_1 = tokens[i - 1].lower() if i > 0 else ""
        if prev_1 in citation_markers:
            # Citation context: not an intentional grammatical error
            continue

        for j in range(i - 1, max(-1, i - 4), -1):
            prev = tokens[j].lower()
            if prev in citation_markers:
                break
            if prev in VERB_MARKERS:
                syntactic_role = "verb"
                break
            elif prev in NOUN_DETERMINERS:
                syntactic_role = "noun"
                break

        if syntactic_role and visual_role != syntactic_role:
            base_word = stems[matched]
            hint_info = HETERONYM_PHONETIC_HINTS.get(base_word, {}).get(visual_role, {})
            desc = hint_info.get("desc", f"{visual_role} stress")
            respell = hint_info.get("respell", "")
            errors.append({
                "word": base_word,
                "token": token,
                "visual_role": visual_role,
                "syntactic_role": syntactic_role,
                "desc": desc,
                "respell": respell
            })

    return errors


def build_stress_style_directive(
    detected_words: List[str],
    language: str = "english",
    base_style: str = "",
    raw_text: str = ""
) -> str:
    """Builds a natural prosodic and theatrical style directive for the TTS model.
    
    Instructs the voice model on authentic syllable stress and vowel reduction through clear
    prosodic acting directives without unparsed IPA strings that dilute model conditioning.
    """
    lang_lower = (language or "english").lower()

    # 1. Non-English language directives
    if lang_lower == "italian":
        return (
            "dizione italiana chiara, impeccabile e ben articolata, ritmo vocale naturale e cadenza pedagogica misurata. "
            "Pronuncia con precisione chirurgica le singole e le doppie consonanti (es. 't' vs 'tt', 'n' vs 'nn') e i contrasti fonetici."
        )
    elif lang_lower == "spanish":
        return (
            "dicción española clara, limpia y precisa, articulación impecable de cada fonema "
            "(especialmente la vibrante múltiple 'rr' y vocales nítidas), cadencia rítmica natural y ritmo pedagógico medido."
        )
    elif lang_lower == "french":
        return (
            "diction française soignée et limpide, phonèmes articulés avec une clarté irréprochable, "
            "respect naturel de la prosodie, des liaisons et du rythme mélodique de la langue."
        )

    # 2. English heteronym and stress directives
    words_clean = list(set([w.lower().replace("-", "") for w in detected_words]))
    
    # Check for intentional learner errors in raw_text
    intentional_errors = detect_intentional_stress_errors(raw_text, words_clean) if raw_text else []
    error_directive = ""
    if intentional_errors:
        clauses = []
        for err in intentional_errors:
            clauses.append(
                f"The character intentionally makes a pronunciation mistake: "
                f"pronounce '{err['word']}' with {err['desc']} instead of the expected {err['syntactic_role']}."
            )
        error_directive = " Crucial acting instruction: " + " ".join(clauses)

    if words_clean:
        words_str = ", ".join(f"'{w}'" for w in words_clean)
        return (
            "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing. "
            f"Emphasize the contrast for educational focus words {words_str} with natural English rhythm and fluent delivery: "
            "clearly stress the first syllable for noun forms, and smoothly reduce the first syllable with natural stress on the second syllable for verb forms. "
            f"Do not insert pauses or hesitations inside any word.{error_directive}"
        )
        
    # If no specific stress words detected, preserve base_style if available
    if base_style:
        return f"{base_style}{error_directive}"
        
    return (
        f"deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing.{error_directive}"
    )

def normalize_multiple_choice_options_for_tts(text: str, language: str = "english") -> str:
    """Normalizes multiple-choice options (e.g. 'A: ... B: ... C: ...' or 'A) ... B) ...')
    for TTS models so that single-letter options like 'A' are pronounced unambiguously as
    proper letter names (/eɪ/, /a/, etc.) rather than indefinite articles or hesitant vowel grunts.
    """
    if not text:
        return text

    lang = (language or "english").lower()

    # Multiple-choice detection: must have both A and B as options
    has_mc_colon = bool(re.search(r"(?:^|(?<=[.?!,\s]))A\s*:\s*", text) and re.search(r"(?:^|(?<=[.?!,\s]))B\s*:\s*", text))
    has_mc_paren = bool(re.search(r"(?:^|(?<=[.?!,\s]))A\s*\)\s*", text) and re.search(r"(?:^|(?<=[.?!,\s]))B\s*\)\s*", text))

    if not (has_mc_colon or has_mc_paren):
        return text

    prefix_map = {
        "english": "Option",
        "spanish": "Opción",
        "french": "Option",
        "italian": "Opzione",
    }
    opt = prefix_map.get(lang, "Option")

    if has_mc_colon:
        text = re.sub(r"(^|(?<=[.?!,\s]))A\s*:\s*", rf"\g<1>{opt} A: ", text)
        text = re.sub(r"(^|(?<=[.?!,\s]))B\s*:\s*", rf"\g<1>{opt} B: ", text)
        text = re.sub(r"(^|(?<=[.?!,\s]))C\s*:\s*", rf"\g<1>{opt} C: ", text)
        text = re.sub(r"(^|(?<=[.?!,\s]))D\s*:\s*", rf"\g<1>{opt} D: ", text)
    elif has_mc_paren:
        text = re.sub(r"(^|(?<=[.?!,\s]))A\s*\)\s*", rf"\g<1>{opt} A: ", text)
        text = re.sub(r"(^|(?<=[.?!,\s]))B\s*\)\s*", rf"\g<1>{opt} B: ", text)
        text = re.sub(r"(^|(?<=[.?!,\s]))C\s*\)\s*", rf"\g<1>{opt} C: ", text)
        text = re.sub(r"(^|(?<=[.?!,\s]))D\s*\)\s*", rf"\g<1>{opt} D: ", text)

    return text

