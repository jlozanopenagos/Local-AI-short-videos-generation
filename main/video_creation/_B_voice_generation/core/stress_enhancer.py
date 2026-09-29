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
HETERONYM_IPA_GUIDE: Dict[str, Dict[str, str]] = {
    "record": {
        "noun": "/ˈrɛk.ərd/",
        "verb": "/rɪˈkɔːrd/",
        "directive": (
            "Pronounce the noun form of 'record' with clear primary stress on the first syllable /ˈrɛk.ərd/. "
            "Pronounce the verb form of 'record' with authentic vowel reduction on the initial syllable /rɪ/ and natural stress on the second syllable /rɪˈkɔːrd/. "
            "Never pronounce the initial syllable of the verb 'record' with a tense /re/ sound; keep it reduced and natural as /rɪˈkɔːrd/."
        )
    },
    "present": {
        "noun": "/ˈprɛz.ənt/",
        "verb": "/prɪˈzɛnt/",
        "directive": (
            "Pronounce the noun form of 'present' with clear primary stress on the first syllable /ˈprɛz.ənt/. "
            "Pronounce the verb form of 'present' with authentic vowel reduction on the initial syllable /prɪ/ and natural stress on the second syllable /prɪˈzɛnt/. "
            "Never pronounce the initial syllable of the verb 'present' with a tense /pre/ sound; keep it reduced and natural as /prɪˈzɛnt/."
        )
    },
    "project": {
        "noun": "/ˈprɑː.dʒɛkt/",
        "verb": "/prəˈdʒɛkt/",
        "directive": (
            "Pronounce the noun form of 'project' with clear primary stress on the first syllable /ˈprɑː.dʒɛkt/. "
            "Pronounce the verb form of 'project' with authentic vowel reduction on the initial syllable /prə/ and natural stress on the second syllable /prəˈdʒɛkt/. "
            "Never pronounce the initial syllable of the verb 'project' with a tense /proʊ/ sound; keep it reduced and natural as /prəˈdʒɛkt/."
        )
    },
    "permit": {
        "noun": "/ˈpɜːr.mɪt/",
        "verb": "/pərˈmɪt/",
        "directive": (
            "Pronounce the noun form of 'permit' with clear primary stress on the first syllable /ˈpɜːr.mɪt/. "
            "Pronounce the verb form of 'permit' with authentic vowel reduction on the initial syllable /pər/ and natural stress on the second syllable /pərˈmɪt/. "
            "Never pronounce the initial syllable of the verb 'permit' with a tense /pɜːr/ sound; keep it reduced and natural as /pərˈmɪt/."
        )
    },
    "object": {
        "noun": "/ˈɑːb.dʒɛkt/",
        "verb": "/əbˈdʒɛkt/",
        "directive": (
            "Pronounce the noun form of 'object' with clear primary stress on the first syllable /ˈɑːb.dʒɛkt/. "
            "Pronounce the verb form of 'object' with authentic vowel reduction on the initial syllable /əb/ and natural stress on the second syllable /əbˈdʒɛkt/. "
            "Never pronounce the initial syllable of the verb 'object' with a tense /ɑːb/ sound; keep it reduced and natural as /əbˈdʒɛkt/."
        )
    },
    "contract": {
        "noun": "/ˈkɑːn.trækt/",
        "verb": "/kənˈtrækt/",
        "directive": (
            "Pronounce the noun form of 'contract' with clear primary stress on the first syllable /ˈkɑːn.trækt/. "
            "Pronounce the verb form of 'contract' with authentic vowel reduction on the initial syllable /kən/ and natural stress on the second syllable /kənˈtrækt/. "
            "Never pronounce the initial syllable of the verb 'contract' with a tense /kɑːn/ sound; keep it reduced and natural as /kənˈtrækt/."
        )
    },
    "increase": {
        "noun": "/ˈɪn.kriːs/",
        "verb": "/ɪnˈkriːs/",
        "directive": (
            "Pronounce the noun form of 'increase' with clear primary stress on the first syllable /ˈɪn.kriːs/. "
            "Pronounce the verb form of 'increase' with primary stress on the second syllable /ɪnˈkriːs/ and lighter weight on the first syllable."
        )
    },
    "decrease": {
        "noun": "/ˈdiː.kriːs/",
        "verb": "/dɪˈkriːs/",
        "directive": (
            "Pronounce the noun form of 'decrease' with clear primary stress on the first syllable /ˈdiː.kriːs/. "
            "Pronounce the verb form of 'decrease' with authentic vowel reduction on the initial syllable /dɪ/ and natural stress on the second syllable /dɪˈkriːs/. "
            "Never pronounce the initial syllable of the verb 'decrease' with a tense /diː/ sound; keep it reduced and natural as /dɪˈkriːs/."
        )
    },
    "import": {
        "noun": "/ˈɪm.pɔːrt/",
        "verb": "/ɪmˈpɔːrt/",
        "directive": (
            "Pronounce the noun form of 'import' with clear primary stress on the first syllable /ˈɪm.pɔːrt/. "
            "Pronounce the verb form of 'import' with distinct primary stress on the second syllable /ɪmˈpɔːrt/."
        )
    },
    "export": {
        "noun": "/ˈɛk.spɔːrt/",
        "verb": "/ɪkˈspɔːrt/",
        "directive": (
            "Pronounce the noun form of 'export' with clear primary stress on the first syllable /ˈɛk.spɔːrt/. "
            "Pronounce the verb form of 'export' with authentic vowel reduction on the initial syllable /ɪk/ and natural stress on the second syllable /ɪkˈspɔːrt/."
        )
    },
    "protest": {
        "noun": "/ˈproʊ.tɛst/",
        "verb": "/prəˈtɛst/",
        "directive": (
            "Pronounce the noun form of 'protest' with clear primary stress on the first syllable /ˈproʊ.tɛst/. "
            "Pronounce the verb form of 'protest' with authentic vowel reduction on the initial syllable /prə/ and natural stress on the second syllable /prəˈtɛst/. "
            "Never pronounce the initial syllable of the verb 'protest' with a tense /proʊ/ sound; keep it reduced and natural as /prəˈtɛst/."
        )
    },
    "contest": {
        "noun": "/ˈkɑːn.tɛst/",
        "verb": "/kənˈtɛst/",
        "directive": (
            "Pronounce the noun form of 'contest' with clear primary stress on the first syllable /ˈkɑːn.tɛst/. "
            "Pronounce the verb form of 'contest' with authentic vowel reduction on the initial syllable /kən/ and natural stress on the second syllable /kənˈtɛst/. "
            "Never pronounce the initial syllable of the verb 'contest' with a tense /kɑːn/ sound; keep it reduced and natural as /kənˈtɛst/."
        )
    },
    "advise": {
        "noun": "/ədˈvaɪs/",
        "verb": "/ədˈvaɪz/",
        "directive": (
            "Pronounce the noun 'advice' with a clear voiceless /s/ ending /ədˈvaɪs/. "
            "Pronounce the verb 'advise' with a distinct voiced /z/ ending /ədˈvaɪz/. "
            "Ensure clear, crisp phoneme contrast between the noun and verb."
        )
    },
    "advice": {
        "noun": "/ədˈvaɪs/",
        "verb": "/ədˈvaɪz/",
        "directive": (
            "Pronounce the noun 'advice' with a clear voiceless /s/ ending /ədˈvaɪs/. "
            "Pronounce the verb 'advise' with a distinct voiced /z/ ending /ədˈvaɪz/. "
            "Ensure clear, crisp phoneme contrast between the noun and verb."
        )
    },
    "discuss": {
        "word": "/dɪˈskʌs/",
        "directive": (
            "Pronounce 'discuss' with stress on the second syllable /dɪˈskʌs/ and reduced initial vowel /dɪ/. "
            "Pronounce 'argue' with primary stress on the first syllable /ˈɑːr.ɡjuː/."
        )
    },
    "argue": {
  }
}

# Tested syllabic phonetic respellings for Qwen3-TTS
# Designed to force the model to place acoustic stress and energy on the designated syllable
# without causing tokenizer fragmentation or awkward pauses.
HETERONYM_TTS_PHONETIC_REPLACEMENTS: Dict[str, Dict[str, str]] = {
    "record": {
        "noun": "RECK-ord",
        "verb": "re-KORD",
    },
    "present": {
        "noun": "PREZ-ent",
        "verb": "pri-ZENT",
    },
    "project": {
        "noun": "PRAHJ-ekt",
        "verb": "pruh-JEKT",
    },
    "permit": {
        "noun": "PER-mit",
        "verb": "per-MIT",
    },
    "object": {
        "noun": "AHB-jekt",
        "verb": "ub-JEKT",
    },
    "contract": {
        "noun": "KAHN-trakt",
        "verb": "kun-TRAKT",
    },
    "increase": {
        "noun": "IN-crease",
        "verb": "in-CREASE",
    },
    "decrease": {
        "noun": "DEE-crease",
        "verb": "di-CREASE",
    },
    "import": {
        "noun": "IM-port",
        "verb": "im-PORT",
    },
    "export": {
        "noun": "EK-sport",
        "verb": "ik-SPORT",
    },
    "protest": {
        "noun": "PRO-test",
        "verb": "pruh-TEST",
    },
    "contest": {
        "noun": "KAHN-test",
        "verb": "kun-TEST",
    },
    "advise": {
        "noun": "ad-VICE",
        "verb": "ad-VIZE",
    },
    "advice": {
        "noun": "ad-VICE",
        "verb": "ad-VIZE",
    },
    "discuss": {
        "noun": "DIS-kuss",
        "verb": "di-SKUSS",
    },
    "argue": {
        "noun": "AR-gyoo",
        "verb": "ar-GYOO",
    },
}


def enhance_stress_text_for_tts(text: str, language: str = "english") -> Tuple[str, List[str]]:
    """Transforms written text containing stress capitalization into optimized phonetic triggers for TTS.
    
    Replaces capitalized syllables with calibrated phonetic respellings (e.g. 'REcord' -> 'RECK-ord',
    'reCORD' -> 're-KORD') so the model synthesizes distinct, audible stress contrast and authentic
    vowel reduction without pauses or unnatural /re/ sounds.
    
    Returns:
        Tuple of (enhanced_text_for_tts, list_of_detected_base_words)
    """
    if not text:
        return text, []

    detected_words: List[str] = []

    # Pattern matches words with capitalized syllables or hyphenated stress notation:
    # e.g. REcord, reCORD, re-CORD, RE-cord, PERmit, perMIT, PROject, proJECT, Dis-CUSS, AR-gue
    stress_pattern = r'\b([a-z]+[A-Z]{2,}|[A-Z]{2,}[a-z]+|[a-zA-Z]+-[A-Z]{2,}|[A-Z]{2,}-[a-zA-Z]+)\b'
    
    matches = re.findall(stress_pattern, text)
    for m in matches:
        if re.match(r'^(?:[IVXLCDM]+)(?:e|er|ème|ère|th|st|nd|rd)$', m, re.IGNORECASE):
            continue
        base = m.replace("-", "").lower()
        if base not in detected_words:
            detected_words.append(base)

    def repl_phonetic(m):
        raw = m.group(0)
        # Ignore Roman numerals with ordinal suffixes (e.g. XIXe, XXe, Ier in French)
        if re.match(r'^(?:[IVXLCDM]+)(?:e|er|ème|ère|th|st|nd|rd)$', raw, re.IGNORECASE):
            return raw
            
        base = raw.replace("-", "").lower()
        
        # Determine whether first syllable (noun) or second syllable (verb) is stressed
        # Case 1: First syllable stressed (e.g. REcord, RE-cord, PREsent, PROject)
        is_first_stressed = bool(re.match(r'^[A-Z]{2,}', raw))
        # Case 2: Second syllable stressed (e.g. reCORD, re-CORD, preSENT, proJECT)
        is_second_stressed = bool(re.search(r'[a-z]+-?[A-Z]{2,}', raw))
        
        if language.lower() == "english" and base in HETERONYM_TTS_PHONETIC_REPLACEMENTS:
            rep = HETERONYM_TTS_PHONETIC_REPLACEMENTS[base]
            if is_first_stressed:
                return rep["noun"]
            elif is_second_stressed:
                return rep["verb"]
        
        # Fallback if not specifically mapped: standard clean word
        return base

    result = re.sub(stress_pattern, repl_phonetic, text)

    # Contextual replacement for lowercase occurrences following "noun" or "verb" indicators:
    if language.lower() == "english":
        for base, rep in HETERONYM_TTS_PHONETIC_REPLACEMENTS.items():
            # Check for "the noun 'record'" or "the noun record"
            noun_pattern = rf"\b(the\s+noun|as\s+a\s+noun|is\s+a\s+noun)\s+['\"]?{base}['\"]?"
            result = re.sub(noun_pattern, rf"\1 '{rep['noun']}'", result, flags=re.IGNORECASE)
            
            # Check for "the verb 'record'" or "to use the verb 'record'" or "as a verb 'record'"
            verb_pattern = rf"\b(the\s+verb|to\s+use\s+the\s+verb|as\s+a\s+verb)\s+['\"]?{base}['\"]?"
            result = re.sub(verb_pattern, rf"\1 '{rep['verb']}'", result, flags=re.IGNORECASE)

    # Specific phonetic artifact cleanups:
    result = re.sub(r"\b'ad-vice'\b", "'ad-VICE'", result, flags=re.IGNORECASE)
    result = re.sub(r"\bad-vice\b", "ad-VICE", result, flags=re.IGNORECASE)
    result = re.sub(r"\b'in-increase'\b", "'in-CREASE'", result, flags=re.IGNORECASE)
    result = re.sub(r"\bin-increase\b", "in-CREASE", result, flags=re.IGNORECASE)

    # Clean whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    return result, detected_words


def build_stress_style_directive(detected_words: List[str], language: str = "english", base_style: str = "") -> str:
    """Builds an articulate, phonetically accurate style directive for the TTS model.
    
    Instructs the voice model on authentic syllable stress, vowel reduction, and phoneme clarity
    (e.g. /rɪˈkɔːrd/ with reduced initial /rɪ/ for verbs, and /ˈrɛk.ərd/ for nouns),
    explicitly avoiding artificial vowel sounds, and supporting foreign language phonetic targets.
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
    
    # Check if any known heteronym or contrast word is present
    for hw, guide in HETERONYM_IPA_GUIDE.items():
        if hw in words_clean:
            return (
                "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing. "
                f"{guide['directive']} Ensure smooth, natural human articulation."
            )
            
    if words_clean:
        words_str = ", ".join(f"'{w}'" for w in words_clean)
        return (
            f"deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing. "
            f"Natural syllable stress contrast for educational focus words {words_str}: "
            f"Pronounce noun forms with primary stress on the first syllable. "
            f"Pronounce verb forms with authentic vowel reduction on the first syllable and natural stress on the second syllable. "
            f"Ensure smooth, human articulation without artificial vowel shifts or exaggerated pauses."
        )
        
    # If no specific stress words detected, preserve base_style if available
    if base_style:
        return base_style
        
    return (
        "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing."
    )

