import re
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
    clean = token.replace("-", "")
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


class SubtitleBuilder:
    def build_ass(
        self,
        words: List[Dict],
        output_path: Path,
        video_width: int = 576,
        video_height: int = 1024,
        suppress_windows: Optional[List[Tuple[float, float]]] = None,
        script_data: Optional[Dict] = None,
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

        # Extract special heteronym stress words from script_data if available
        stress_queue = []
        if script_data:
            script_text = script_data.get("script_text", "")
            if not script_text and "content_metadata" in script_data:
                script_dict = script_data.get("content_metadata", {}).get("script", {})
                if isinstance(script_dict, dict):
                    script_text = " ".join(str(v) for v in script_dict.values())
            stress_queue = extract_stress_words(script_text)

        # Merge hyphenated subwords (e.g. 'REC' and '-ORD' -> 'REC-ORD', or 'RE-' and 'CORD' -> 'RE-CORD')
        merged_words = []
        for w in words:
            word_str = w.get("word", "").strip()
            if not word_str:
                continue
            if word_str.startswith("-") and merged_words:
                merged_words[-1]["word"] = f"{merged_words[-1]['word']}{word_str}"
                merged_words[-1]["end"] = max(merged_words[-1]["end"], w.get("end", merged_words[-1]["end"]))
            elif merged_words and merged_words[-1]["word"].endswith("-"):
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

            # Check if this word matches a special heteronym stress word from the script
            clean_w = re.sub(r"[^\w]", "", w.get("word", "")).lower()
            replacement = None
            if stress_queue and len(clean_w) >= 3:
                for idx, spec in enumerate(stress_queue):
                    clean_spec = spec.replace("-", "").lower()
                    if clean_w == clean_spec:
                        replacement = stress_queue.pop(idx)
                        break

            # If matched, preserve educational syllable stress casing; otherwise Hormozi all-caps
            text = replacement if replacement else w["word"].upper()

            # 5 is center-center alignment
            line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n"
            lines.append(line)
            
        with output_path.open("w", encoding="utf-8") as f:
            f.writelines(lines)
        return output_path

