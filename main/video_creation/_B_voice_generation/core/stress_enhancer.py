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

# Clean orthographic mappings for Option B (standard English words, zero BPE fragmentation)
HETERONYM_TTS_PHONETIC_REPLACEMENTS: Dict[str, Dict[str, str]] = {
    word: {"noun": word, "verb": word} for word in ENGLISH_HETERONYMS
}

# Guidance mapping for reference and diagnostics
HETERONYM_IPA_GUIDE: Dict[str, Dict[str, str]] = {
    "record": {
        "noun": "/ˈrɛk.ərd/",
        "verb": "/rɪˈkɔːrd/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "present": {
        "noun": "/ˈprɛz.ənt/",
        "verb": "/prɪˈzɛnt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "project": {
        "noun": "/ˈprɑː.dʒɛkt/",
        "verb": "/prəˈdʒɛkt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "permit": {
        "noun": "/ˈpɜːr.mɪt/",
        "verb": "/pərˈmɪt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "object": {
        "noun": "/ˈɑːb.dʒɛkt/",
        "verb": "/əbˈdʒɛkt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "contract": {
        "noun": "/ˈkɑːn.trækt/",
        "verb": "/kənˈtrækt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "increase": {
        "noun": "/ˈɪn.kriːs/",
        "verb": "/ɪnˈkriːs/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "decrease": {
        "noun": "/ˈdiː.kriːs/",
        "verb": "/dɪˈkriːs/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "import": {
        "noun": "/ˈɪm.pɔːrt/",
        "verb": "/ɪmˈpɔːrt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "export": {
        "noun": "/ˈɛk.spɔːrt/",
        "verb": "/ɪkˈspɔːrt/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "protest": {
        "noun": "/ˈproʊ.tɛst/",
        "verb": "/prəˈtɛst/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    },
    "contest": {
        "noun": "/ˈkɑːn.tɛst/",
        "verb": "/kənˈtɛst/",
        "directive": "Clearly stress the first syllable for the noun form, and smoothly reduce the first syllable with natural stress on the second syllable for the verb form."
    }
}


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
        base = raw.replace("-", "").lower()
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


def build_stress_style_directive(detected_words: List[str], language: str = "english", base_style: str = "") -> str:
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
    
    if words_clean:
        words_str = ", ".join(f"'{w}'" for w in words_clean)
        return (
            "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing. "
            f"Emphasize the contrast for educational focus words {words_str} with natural English rhythm and fluent delivery: "
            "clearly stress the first syllable for noun forms, and smoothly reduce the first syllable with natural stress on the second syllable for verb forms. "
            "Do not insert pauses or hesitations inside any word."
        )
        
    # If no specific stress words detected, preserve base_style if available
    if base_style:
        return base_style
        
    return (
        "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing."
    )


