import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from video_creation._B_voice_generation.core.pronunciation_bank import HETERONYM_REGISTRY
except (ImportError, ModuleNotFoundError):
    try:
        # pyrefly: ignore [missing-import]
        from core.pronunciation_bank import HETERONYM_REGISTRY
    except (ImportError, ModuleNotFoundError):
        HETERONYM_REGISTRY = {}


def is_stress_heteronym_word(token: str) -> bool:
    """Checks if a token represents an educational syllable-stress heteronym (e.g. PREsent, preSENT)."""
    clean = re.sub(r"[^\w]", "", token).replace("-", "")
    if len(clean) < 4:
        return False
    # Check registered heteronyms
    if clean.lower() in HETERONYM_REGISTRY:
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


def clean_spoken_text(text: str) -> str:
    """
    Strips parentheticals, explicit speaker labels (PERSON_ONE, Narrator, etc.), formatting asterisks,
    while carefully preserving spoken conversational cues that contain colons (e.g. 'Dis juste :', 'Por ejemplo :').
    """
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


def align_tokens_to_whisper(
    script_tokens: List[str],
    whisper_words: List[Dict],
    default_start: float = 0.0,
    default_end: float = 30.0,
) -> List[Dict]:
    """
    Aligns ground-truth script tokens against Whisper detected word timestamps using SequenceMatcher.
    Guarantees script spelling and homophone fidelity while preserving Whisper's acoustic timestamps.
    """
    if not script_tokens:
        return []

    # Pre-merge Whisper contractions, elisions, and hyphens for robust 1:1 token correspondence
    whisper_words = premerge_whisper_words(whisper_words)

    if not whisper_words:
        duration = max(1.0, default_end - default_start)
        step = duration / max(1, len(script_tokens))
        return [{
            "word": tok,
            "start": round(default_start + i * step, 2),
            "end": round(default_start + (i + 1) * step, 2)
        } for i, tok in enumerate(script_tokens)]

    s_keys = [clean_token(tok) for tok in script_tokens]
    w_keys = [clean_token(w.get("word", "")) for w in whisper_words]

    matcher = SequenceMatcher(None, s_keys, w_keys)
    aligned = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for s_idx, w_idx in zip(range(i1, i2), range(j1, j2)):
                aligned.append({
                    "word": script_tokens[s_idx],
                    "start": whisper_words[w_idx]["start"],
                    "end": whisper_words[w_idx]["end"]
                })
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
                aligned.append({
                    "word": sw,
                    "start": round(w_s, 2),
                    "end": round(w_e, 2)
                })
        elif tag == "delete":
            prev_end = aligned[-1]["end"] if aligned else whisper_words[0]["start"]
            step = 0.25
            for idx, sw in enumerate(script_tokens[i1:i2]):
                aligned.append({
                    "word": sw,
                    "start": round(prev_end, 2),
                    "end": round(prev_end + step, 2)
                })
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

    return aligned


def align_script_data_to_whisper(
    script_data: Dict,
    whisper_words: List[Dict],
    timings_data: Optional[Dict] = None
) -> List[Dict]:
    """
    Extracts ground-truth text from script_data and aligns it to Whisper word timestamps.
    Leverages section-level boundaries from timings_data when available.
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
                tokens = tokenize_script_text(raw_s)
                return align_tokens_to_whisper(tokens, whisper_words)

    if not isinstance(script_dict, dict) or not script_dict:
        return whisper_words

    # Filter out title (titles are not spoken)
    script_sections = {k.lower(): str(v) for k, v in script_dict.items() if k.lower() != "title"}

    # Use section timings if available to isolate each narrative beat
    if timings_data and any(k in timings_data for k in script_sections):
        all_aligned = []
        for sec_name, sec_text in script_sections.items():
            sec_tokens = tokenize_script_text(sec_text)
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
                default_end=t_end if t_end > t_start else t_start + len(sec_tokens) * 0.3
            )
            all_aligned.extend(aligned_sec)
        return all_aligned
    else:
        full_text = " ".join(script_sections.values())
        tokens = tokenize_script_text(full_text)
        return align_tokens_to_whisper(tokens, whisper_words)


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
    ) -> Path:
        # Generate ASS with dynamic word-by-word style
        # Hormozi style: One/two words on screen at a time, large font, center screen.

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

            raw_word = w.get("word", "")
            clean_hw = re.sub(r"[^\w-]", "", raw_word)

            # Preserve educational syllable stress casing if matched; otherwise Hormozi all-caps
            if clean_hw and is_stress_heteronym_word(clean_hw):
                text = clean_hw
            else:
                text = raw_word.upper()

            # 5 is center-center alignment
            line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n"
            lines.append(line)

        with output_path.open("w", encoding="utf-8") as f:
            f.writelines(lines)
        return output_path


