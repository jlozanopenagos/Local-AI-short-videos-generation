import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from ..assembly.common.subtitles import format_ass_dialogue_line, render_ass_header
    from ..assembly.languages import get_assembly_language_profile
    from ..assembly.types import get_assembly_profile
except (ImportError, ValueError):
    from assembly.common.subtitles import format_ass_dialogue_line, render_ass_header  # type: ignore[no-redef]
    from assembly.languages import get_assembly_language_profile  # type: ignore[no-redef]
    from assembly.types import get_assembly_profile  # type: ignore[no-redef]

KNOWN_HETERONYMS = {
    "record", "present", "project", "permit", "object",
    "contract", "conduct", "desert", "increase", "decrease",
    "import", "export", "protest", "contest", "refuse",
    "rebel", "address", "combat", "conflict", "defect",
    "digest", "escort", "impact", "insult", "produce",
    "progress", "refund", "reject", "subject", "suspect",
    "transfer", "transport", "update", "upgrade", "upset",
}


def is_stress_heteronym_word(token: str) -> bool:
    """Checks if a token represents an educational syllable-stress heteronym (e.g. PREsent, preSENT)."""
    clean = re.sub(r"[^\w]", "", token).replace("-", "")
    if len(clean) < 4:
        return False
    # Check registered heteronyms
    if clean.lower() in KNOWN_HETERONYMS:
        if any(c.isupper() for c in clean) and any(c.islower() for c in clean):
            return True
    # General multi-uppercase syllable pattern (e.g. PROject, proJECT)
    upper_count = sum(1 for c in clean if c.isupper())
    lower_count = sum(1 for c in clean if c.islower())
    return upper_count >= 2 and lower_count >= 1


def extract_stress_words(text: str) -> List[str]:
    """Extracts sequential mixed-case heteronym stress words from script text."""
    if not text:
        return []
    tokens = re.findall(r"\b[A-Za-z]+(?:-[A-Za-z]+)?\b", text)
    return [tok for tok in tokens if is_stress_heteronym_word(tok)]


def clean_token(token: str) -> str:
    """Normalizes token for alignment comparison by removing punctuation and lowercasing."""
    return re.sub(r"[^\w]", "", token).lower()


def premerge_whisper_words(whisper_words: List[Dict]) -> List[Dict]:
    """
    Pre-merges Whisper's split contraction tokens, elisions, and hyphenated fragments.
    E.g.:
      ['n', "'arrive"] -> ["n'arrive"]
      ['l', "'expression"] -> ["l'expression"]
      ['c', "'est"] -> ["c'est"]
      ['rendez', '-vous'] -> ["rendez-vous"]
      ['don', "'t"] -> ["don't"]
      ['it', "'s"] -> ["it's"]
      ['l', "'amico"] -> ["l'amico"]
    Also filters out standalone punctuation marks emitted as words by Whisper (e.g. '?').
    """
    if not whisper_words:
        return []

    merged = []
    contraction_prefixes = {
        "l", "d", "c", "j", "m", "t", "s", "n", "qu",
        "l'", "d'", "c'", "j'", "m'", "t'", "s'", "n'", "qu'",
        "un'", "all'", "dell'", "dall'", "nell'", "sull'",
        "don", "doesn", "didn", "won", "can", "couldn", "shouldn", "wouldn", "isn", "aren", "wasn", "weren", "haven", "hasn", "hadn"
    }

    for w in whisper_words:
        w_text = w.get("word", "").strip()
        if not w_text:
            continue
        # Drop standalone punctuation emitted as words by Whisper
        if w_text in {".", ",", "!", "?", ";", ":", "...", "…", "-", "–", "—", "--"}:
            continue

        # Case 1: Previous token was a contraction prefix
        if merged and (
            merged[-1]["word"].lower() in contraction_prefixes
            or (len(merged[-1]["word"]) <= 2 and merged[-1]["word"].isalpha() and (w_text.startswith("'") or w_text.isalpha()))
        ):
            prev = merged[-1]["word"]
            if not prev.endswith("'") and (w_text.startswith("'") or len(prev) <= 2):
                if not w_text.startswith("'"):
                    prev += "'"
            clean_curr = w_text.lstrip("'")
            merged[-1]["word"] = prev + clean_curr
            merged[-1]["end"] = max(merged[-1]["end"], w.get("end", merged[-1]["end"]))

        # Case 2: Current word starts with hyphen (e.g. '-vous')
        elif w_text.startswith("-") and merged:
            merged[-1]["word"] += w_text
            merged[-1]["end"] = max(merged[-1]["end"], w.get("end", merged[-1]["end"]))

        # Case 3: Previous word ended with hyphen (e.g. 'rendez-')
        elif merged and merged[-1]["word"].endswith("-"):
            merged[-1]["word"] += w_text
            merged[-1]["end"] = max(merged[-1]["end"], w.get("end", merged[-1]["end"]))

        # Case 4: Current word starts with apostrophe suffix (e.g. "'t", "'s", "'ve", "'ll", "'re", "'d")
        elif w_text.startswith("'") and merged and not (w_text.endswith("'") and len(w_text) > 1):
            merged[-1]["word"] += w_text
            merged[-1]["end"] = max(merged[-1]["end"], w.get("end", merged[-1]["end"]))

        else:
            merged.append(dict(w))

    return merged


_IPA_WORD_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"/[^/\s]*rek[^/\s]*/", "record"),
    (r"/[^/\s]*k[ɔoƆ]ː?[^/\s]*/", "record"),
    (r"/[^/\s]*pr[ɛe]z[^/\s]*/", "present"),
    (r"/[^/\s]*dʒ[ɛe]kt[^/\s]*/", "project"),
    (r"/[^/\s]*m[ɪiꞮ]t[^/\s]*/", "permit"),
    (r"/[^/\s]*tr[æa]kt[^/\s]*/", "contract"),
    (r"/[^/\s]*kriːs[^/\s]*/", "increase"),
]

_PHONETIC_RESPELLING_MAP: Dict[str, str] = {
    "rek-erd": "record",
    "ri-kord": "record",
    "ri-cord": "record",
    "re-cord": "record",
    "prez-ent": "present",
    "pri-zent": "present",
    "pre-sent": "present",
    "prah-jekt": "project",
    "pruh-jekt": "project",
    "pro-ject": "project",
    "pur-mit": "permit",
    "per-mit": "permit",
    "ahb-jekt": "object",
    "ub-jekt": "object",
    "ob-ject": "object",
    "kahn-trakt": "contract",
    "kuhn-trakt": "contract",
    "con-tract": "contract",
    "kahn-test": "contest",
    "kuhn-test": "contest",
    "con-test": "contest",
    "kahn-dukt": "conduct",
    "kuhn-dukt": "conduct",
    "con-duct": "conduct",
    "kahn-flikt": "conflict",
    "kuhn-flikt": "conflict",
    "con-flict": "conflict",
    "dez-ert": "desert",
    "di-zert": "desert",
    "de-sert": "desert",
    "des-sert": "dessert",
    "reb-el": "rebel",
    "ri-bel": "rebel",
    "re-bel": "rebel",
    "suhs-pekt": "suspect",
    "suh-spekt": "suspect",
    "sus-pect": "suspect",
    "in-krees": "increase",
    "in-crease": "increase",
    "dee-krees": "decrease",
    "di-krees": "decrease",
    "de-crease": "decrease",
    "im-port": "import",
    "ex-port": "export",
    "pro-test": "protest",
    "ac-cept": "accept",
    "ex-cept": "except",
    "uh-fect": "affect",
    "af-fect": "affect",
    "ef-fect": "effect",
    "lay-ter": "later",
    "lat-ter": "latter",
    "prin-ci-pul": "principal",
    "prin-ci-pal": "principal",
    "com-pluh-ment": "compliment",
    "weh-ther": "weather",
    "ad-vice": "advice",
    "ad-vise": "advise",
    "a-nnée": "année",
    "an-née": "année",
}

_PHONETIC_RESPELLING_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_PHONETIC_RESPELLING_MAP, key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)


def normalize_pronunciation_for_subtitles(text: str) -> str:
    """
    Replaces raw IPA transcriptions (e.g. /ˈrek.ɚd/, /rɪˈkɔːrd/), phonetic respellings
    (e.g. uh-FECT, COM-pluh-ment, WEH-ther, LAY-ter), and syllable-hyphenated stress words
    (e.g. PRO-ject, DE-crease, des-SERT) with clean standard dictionary spelling for subtitles.
    """
    if not text:
        return text

    for pattern, replacement in _IPA_WORD_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Strip any remaining raw IPA slash notation
    text = re.sub(r"/[ˈˌɚɪɔːɛæʊəθðʃʒŋꞮƆa-zA-Z.'-]{2,}/", "", text)

    # Replace explicit phonetic respellings and syllable-hyphenated stress words
    text = _PHONETIC_RESPELLING_RE.sub(
        lambda m: _PHONETIC_RESPELLING_MAP[m.group(0).lower()],
        text,
    )

    # Collapse any hyphenated stress-capitalized heteronym (e.g. RE-cord -> record)
    def _dehyphenate_stress_word(m: re.Match) -> str:
        word = m.group(0)
        collapsed = word.replace("-", "")
        if collapsed.lower() in KNOWN_HETERONYMS:
            return collapsed.lower()
        return word

    text = re.sub(r"\b[A-Za-z]+-[A-Za-z]+\b", _dehyphenate_stress_word, text)
    return text


def clean_spoken_text(text: str) -> str:
    """
    Strips parentheticals, explicit speaker labels (PERSON_ONE, Narrator, etc.), formatting asterisks,
    and normalizes IPA / phonetic respellings into clean standard words while carefully preserving
    spoken conversational cues that contain colons (e.g. 'Dis juste :', 'Por ejemplo :').
    """
    text = normalize_pronunciation_for_subtitles(text)
    # Strip parentheticals like (smiling), (Panicked), or (Agent)
    text = re.sub(r"\([^)]+\)", "", text)
    # Strip bold speaker tags (e.g. **PERSON_ONE:** or **Narrator:**)
    text = re.sub(r"\*\*([^*:]+)\s*:\*\*\s*", "", text)
    # Strip bracketed speaker tags (e.g. [PERSON_ONE] or [Narrator])
    text = re.sub(r"\[[A-Za-z0-9_\s-]+\]\s*", "", text)
    # Strip explicit roleplay speaker labels anywhere (e.g. PERSON_ONE:, PERSON_TWO:, Narrator:)
    text = re.sub(
        r"\b(PERSON_ONE|PERSON_TWO|PERSON_1|PERSON_2|Narrator|Host|Speaker)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Strip standalone uppercase speaker tags on lines (e.g. "ALICE: Hello" or "BOB:"), ignoring quiz choices A:, B:, C:, D:
    text = re.sub(r"(?m)^\s*(?![A-D]\b)[A-Z0-9_]{2,20}\s*:\s*", "", text)
    # Strip formatting markdown
    text = text.replace("**", "").replace("*", "")
    # Normalize unicode quotes and dashes
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return text.strip()


def tokenize_script_text(text: str) -> List[str]:
    """
    Splits spoken script text into subtitle tokens.
    Attaches trailing and leading punctuation appropriately and discards orphan non-spoken dash separators.
    """
    text = clean_spoken_text(text)
    raw_tokens = text.split()
    tokens = []
    
    trailing_punct = {".", ",", "!", "?", ";", ":", "...", "…"}
    dash_punct = {"-", "–", "—", "--"}
    leading_punct = {"¿", "¡"}

    for tok in raw_tokens:
        tok = tok.strip()
        if not tok:
            continue
        # Standalone dash separators (e.g. "À ton tour  -  utilise") are pause markers, not spoken words
        if tok in dash_punct:
            continue
        if tok in trailing_punct and tokens:
            tokens[-1] = tokens[-1] + tok
        elif tok in leading_punct:
            tokens.append(tok)
        else:
            if tokens and tokens[-1] in leading_punct:
                tokens[-1] = tokens[-1] + tok
            else:
                tokens.append(tok)

    # Discard any remaining orphan tokens that contain no word characters
    return [t for t in tokens if re.search(r"[\w]", t)]


_SPEAKER_MARKER_RE = re.compile(
    r"(?:"
    r"(?:\*\*\s*)?\b(PERSON_ONE|PERSON_1|PERSON_TWO|PERSON_2|Narrator|Host|Speaker)\b(?:\s*\([^)]*\))?\s*(?:\*\*\s*)?:"
    r"|\[\s*(PERSON_ONE|PERSON_1|PERSON_TWO|PERSON_2|Narrator)\s*\](?:\s*\([^)]*\))?\s*:?"
    r")",
    flags=re.IGNORECASE,
)


def _canonical_speaker_name(raw_tag: str) -> str:
    low = (raw_tag or "").strip().lower()
    if low in ("person_one", "person_1"):
        return "PERSON_ONE"
    if low in ("person_two", "person_2"):
        return "PERSON_TWO"
    return "NARRATOR"


def tokenize_script_with_speakers(
    text: str,
    default_speaker: str = "NARRATOR",
) -> List[Tuple[str, str]]:
    """
    Splits spoken script text into `(token, canonical_speaker)` pairs so multi-speaker
    ROLEPLAY dialogue beats retain per-word speaker attribution (`PERSON_ONE`, `PERSON_TWO`, `NARRATOR`).
    """
    if not text:
        return []

    matches = list(_SPEAKER_MARKER_RE.finditer(text))
    if not matches:
        return [(tok, default_speaker) for tok in tokenize_script_text(text)]

    result: List[Tuple[str, str]] = []
    current_speaker = default_speaker
    cursor = 0
    for m in matches:
        segment = text[cursor:m.start()]
        if segment.strip():
            for tok in tokenize_script_text(segment):
                result.append((tok, current_speaker))
        raw_tag = m.group(1) or m.group(2) or ""
        current_speaker = _canonical_speaker_name(raw_tag)
        cursor = m.end()

    tail = text[cursor:]
    if tail.strip():
        for tok in tokenize_script_text(tail):
            result.append((tok, current_speaker))

    return result


def align_tokens_to_whisper(
    script_tokens: List[str],
    whisper_words: List[Dict],
    default_start: float = 0.0,
    default_end: float = 30.0,
    token_speakers: Optional[List[str]] = None,
    section_name: str = "",
    token_sections: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Aligns ground-truth script tokens against Whisper detected word timestamps using SequenceMatcher.
    Guarantees script spelling and homophone fidelity while preserving Whisper's acoustic timestamps,
    and attaches optional speaker/section metadata for typed ASS styling.
    """
    if not script_tokens:
        return []

    def _make_entry(s_idx: int, word: str, start: float, end: float) -> Dict:
        entry: Dict = {"word": word, "start": start, "end": end}
        if token_speakers and 0 <= s_idx < len(token_speakers):
            entry["speaker"] = token_speakers[s_idx]
        if token_sections and 0 <= s_idx < len(token_sections):
            if token_sections[s_idx]:
                entry["section"] = token_sections[s_idx]
        elif section_name:
            entry["section"] = section_name
        return entry

    # Pre-merge Whisper contractions, elisions, and hyphens for robust 1:1 token correspondence
    whisper_words = premerge_whisper_words(whisper_words)

    if not whisper_words:
        duration = max(1.0, default_end - default_start)
        step = duration / max(1, len(script_tokens))
        return [
            _make_entry(
                i,
                tok,
                round(default_start + i * step, 2),
                round(default_start + (i + 1) * step, 2),
            )
            for i, tok in enumerate(script_tokens)
        ]

    s_keys = [clean_token(tok) for tok in script_tokens]
    w_keys = [clean_token(w.get("word", "")) for w in whisper_words]

    matcher = SequenceMatcher(None, s_keys, w_keys)
    aligned = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for s_idx, w_idx in zip(range(i1, i2), range(j1, j2)):
                aligned.append(
                    _make_entry(
                        s_idx,
                        script_tokens[s_idx],
                        whisper_words[w_idx]["start"],
                        whisper_words[w_idx]["end"],
                    )
                )
        elif tag == "replace":
            s_slice = script_tokens[i1:i2]
            w_slice = whisper_words[j1:j2]
            if not w_slice:
                continue
            t_start = w_slice[0]["start"]
            t_end = w_slice[-1]["end"]
            duration = max(0.08 * len(s_slice), t_end - t_start)
            step = duration / max(1, len(s_slice))
            for idx, sw in enumerate(s_slice):
                w_s = t_start + idx * step
                w_e = t_start + (idx + 1) * step
                aligned.append(
                    _make_entry(i1 + idx, sw, round(w_s, 2), round(w_e, 2))
                )
        elif tag == "delete":
            prev_end = aligned[-1]["end"] if aligned else (whisper_words[0]["start"] if whisper_words else default_start)
            remaining_tokens = script_tokens[i1:i2]
            available_time = max(0.1, default_end - prev_end) if default_end > prev_end else 0.25 * len(remaining_tokens)
            step = min(0.25, available_time / max(1, len(remaining_tokens)))
            for idx, sw in enumerate(remaining_tokens):
                aligned.append(
                    _make_entry(
                        i1 + idx,
                        sw,
                        round(prev_end, 2),
                        round(prev_end + step, 2),
                    )
                )
                prev_end += step
        elif tag == "insert":
            # Extra hallucinations in Whisper are skipped
            pass

    # Ensure strictly monotonic timestamps
    for i in range(1, len(aligned)):
        if aligned[i]["start"] < aligned[i - 1]["start"]:
            aligned[i]["start"] = aligned[i - 1]["end"]
        if aligned[i]["end"] <= aligned[i]["start"]:
            aligned[i]["end"] = round(aligned[i]["start"] + 0.15, 2)

    # Prevent section subtitle spillover into adjacent sections
    if default_end > default_start and aligned:
        if aligned[-1]["end"] > default_end:
            allowed_span = default_end - aligned[0]["start"]
            current_span = aligned[-1]["end"] - aligned[0]["start"]
            if allowed_span > 0.2 and current_span > 0:
                scale = allowed_span / current_span
                base_s = aligned[0]["start"]
                for w in aligned:
                    w["start"] = round(base_s + (w["start"] - base_s) * scale, 2)
                    w["end"] = round(base_s + (w["end"] - base_s) * scale, 2)
            else:
                for w in aligned:
                    if w["end"] > default_end:
                        w["end"] = round(default_end, 2)
                    if w["start"] >= w["end"]:
                        w["start"] = round(max(default_start, w["end"] - 0.1), 2)

    return aligned


def align_script_data_to_whisper(
    script_data: Dict,
    whisper_words: List[Dict],
    timings_data: Optional[Dict] = None
) -> List[Dict]:
    """
    Extracts ground-truth text from script_data and aligns it to Whisper word timestamps.
    Leverages section-level boundaries from timings_data when available, while preserving
    per-token speaker and section attribution.
    """
    if not script_data:
        return whisper_words

    script_dict = script_data.get("content_metadata", {}).get("script", {})
    if not script_dict and "script_text" in script_data:
        raw = script_data["script_text"]
        if isinstance(raw, str):
            raw_s = raw.strip()
            if raw_s.startswith("{") and raw_s.endswith("}"):
                try:
                    script_dict = json.loads(raw_s)
                except Exception:
                    script_dict = None
            if not script_dict:
                pairs = tokenize_script_with_speakers(raw_s)
                tokens = [t for t, _ in pairs]
                speakers = [s for _, s in pairs]
                return align_tokens_to_whisper(tokens, whisper_words, token_speakers=speakers)

    if not isinstance(script_dict, dict) or not script_dict:
        return whisper_words

    # Filter out title (titles are not spoken)
    script_sections = {k.lower(): str(v) for k, v in script_dict.items() if k.lower() != "title"}

    # Use section timings if available to isolate each narrative beat
    if timings_data and any(k in timings_data for k in script_sections):
        all_aligned = []
        for sec_name, sec_text in script_sections.items():
            pairs = tokenize_script_with_speakers(sec_text)
            sec_tokens = [t for t, _ in pairs]
            sec_speakers = [s for _, s in pairs]
            if not sec_tokens:
                continue

            timing_info = timings_data.get(sec_name, {})
            t_start = timing_info.get("start", 0.0)
            t_end = timing_info.get("end", 0.0)

            if t_end > t_start:
                sec_w_words = [
                    w for w in whisper_words
                    if w["start"] >= (t_start - 0.35) and w["end"] <= (t_end + 0.45)
                ]
            else:
                sec_w_words = whisper_words

            aligned_sec = align_tokens_to_whisper(
                sec_tokens,
                sec_w_words,
                default_start=t_start,
                default_end=t_end if t_end > t_start else t_start + len(sec_tokens) * 0.3,
                token_speakers=sec_speakers,
                section_name=sec_name,
            )
            all_aligned.extend(aligned_sec)
        return all_aligned
    else:
        tokens: List[str] = []
        speakers: List[str] = []
        sections: List[str] = []
        for sec_name, sec_text in script_sections.items():
            for tok, spk in tokenize_script_with_speakers(sec_text):
                tokens.append(tok)
                speakers.append(spk)
                sections.append(sec_name)
        return align_tokens_to_whisper(
            tokens,
            whisper_words,
            token_speakers=speakers,
            token_sections=sections,
        )


def _infer_video_type(script_data: Optional[Dict], explicit: str = "") -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    if isinstance(script_data, dict):
        cm = script_data.get("content_metadata") or {}
        pp = script_data.get("prompt_params") or {}
        md = script_data.get("metadata") or {}
        for cand in (
            cm.get("video_type"),
            pp.get("VIDEO_TYPE"),
            pp.get("type"),
            md.get("VIDEO_TYPE"),
        ):
            if cand and str(cand).strip():
                return str(cand).strip()
        sid = str(script_data.get("id") or "").strip().upper()
        if re.match(r"^[EFSI]_?[EGRF]\d{2,}$", sid):
            return sid
        script_obj = cm.get("script")
        if isinstance(script_obj, dict):
            keys = {str(k).strip().lower() for k in script_obj}
            if any(k.startswith("dialogue_part") for k in keys):
                return "roleplay"
            if "challenge" in keys or "pressure" in keys:
                return "game"
            if "explanation" in keys and "example" not in keys:
                return "fun_facts"
    return "expression"


def _infer_language(script_data: Optional[Dict], explicit: str = "") -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    if isinstance(script_data, dict):
        cm = script_data.get("content_metadata") or {}
        pp = script_data.get("prompt_params") or {}
        md = script_data.get("metadata") or {}
        for cand in (
            cm.get("language"),
            pp.get("TARGET_LANGUAGE"),
            pp.get("language"),
            md.get("LABEL"),
            script_data.get("id"),
        ):
            if cand and str(cand).strip():
                return str(cand).strip()
    return "english"


class SubtitleBuilder:
    def build_ass(
        self,
        words: List[Dict],
        output_path: Path,
        video_width: int = 576,
        video_height: int = 1024,
        suppress_windows: Optional[List[Tuple[float, float]]] = None,
        script_data: Optional[Dict] = None,
        timings_data: Optional[Dict] = None,
        video_type: str = "",
        language: str = "",
    ) -> Path:
        """Builds an ASS animated word-by-word subtitle file driven by the active `AssemblyProfile`."""
        resolved_vtype = _infer_video_type(script_data, video_type)
        resolved_lang = _infer_language(script_data, language)
        profile = get_assembly_profile(resolved_vtype)
        lang_profile = get_assembly_language_profile(resolved_lang)

        if profile is not None:
            style_spec = profile.get_subtitle_style()
            ass_header = render_ass_header(
                style_spec,
                video_width=video_width,
                video_height=video_height,
                margin_v_offset=lang_profile.margin_v_offset,
                font_override=lang_profile.font_override,
            )
        else:
            style_spec = None
            ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,60,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,5,10,10,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = [ass_header]

        def format_time(seconds: float) -> str:
            # ASS format: H:MM:SS.cs
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds - int(seconds)) * 100)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

        # If script_data is available, perform forced alignment against the golden script
        if script_data:
            if timings_data is None:
                candidate_timings = output_path.parent / "timings.json"
                if candidate_timings.exists():
                    try:
                        with candidate_timings.open("r", encoding="utf-8") as tf:
                            timings_data = json.load(tf)
                    except Exception:
                        timings_data = None
            words = align_script_data_to_whisper(script_data, words, timings_data=timings_data)

        # Merge hyphenated subwords (e.g. 'REC' and '-ORD' -> 'REC-ORD', or 'RE-' and 'CORD' -> 'RE-CORD')
        merged_words = []
        for w in words:
            word_str = w.get("word", "").strip()
            if not word_str or word_str in ["-", "–", "—", "--"]:
                continue
            clean_hw = re.sub(r"[^\w-]", "", word_str)
            if not clean_hw:
                continue

            # Only merge if it's an actual syllable affix (starts with '-' with characters after it)
            if word_str.startswith("-") and len(word_str) > 1 and merged_words:
                merged_words[-1]["word"] = f"{merged_words[-1]['word']}{word_str}"
                merged_words[-1]["end"] = max(merged_words[-1]["end"], w.get("end", merged_words[-1]["end"]))
            elif merged_words and merged_words[-1]["word"].endswith("-") and len(merged_words[-1]["word"]) > 1:
                merged_words[-1]["word"] = f"{merged_words[-1]['word']}{word_str}"
                merged_words[-1]["end"] = max(merged_words[-1]["end"], w.get("end", merged_words[-1]["end"]))
            else:
                merged_words.append(dict(w))

        for w in merged_words:
            # If word start falls into any suppressed window (e.g. GAME challenge scene), omit it
            if suppress_windows:
                if any(start <= w["start"] < end for start, end in suppress_windows):
                    continue

            start_str = format_time(w["start"])
            end_str = format_time(w["end"])

            raw_word = normalize_pronunciation_for_subtitles(w.get("word", "")).strip()
            if not raw_word:
                continue

            # Always render clean, uniform all-caps dictionary words (never IPA symbols, phonetic respellings, or mixed-case stress caps)
            text = raw_word.upper()

            if profile is not None and style_spec is not None:
                style_name = profile.select_subtitle_style_name(
                    text,
                    section=w.get("section", ""),
                    speaker=w.get("speaker", ""),
                )
                line = format_ass_dialogue_line(start_str, end_str, text, style_name, style_spec)
            else:
                line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n"
            lines.append(line)

        with output_path.open("w", encoding="utf-8") as f:
            f.writelines(lines)
        return output_path


