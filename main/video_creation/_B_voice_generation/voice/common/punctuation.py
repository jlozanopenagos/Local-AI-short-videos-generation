"""
voice/common/punctuation.py — Non-destructive TTS punctuation & quiz-option micro-pause shaping.

Operates strictly on text sent to TTS so visual captions / script JSON stay unchanged.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


_ABBREV_END_RE = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Sr|Sra|Srta|M|Mme|Mlle|Sig|St|vs|etc)\.\s*$", re.IGNORECASE)


def ensure_spanish_inverted_punctuation(text: str) -> str:
    """Prepends missing opening `¿` or `¡` before Spanish clauses ending with `?` or `!`.

    Helps Qwen3-TTS commit early to authentic Spanish interrogative or exclamatory pitch contours
    without mutating displayed screen captions. Preserves existing inverted punctuation cleanly.
    """
    if not text or ("?" not in text and "!" not in text):
        return text

    # Split preserving delimiters (including pause tags or sentence punctuation)
    tokens = re.split(r"(\[pause:\d+(?:\.\d+)?\]|[?!]+|\.)", text)
    out = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i]
        delim = tokens[i + 1] if (i + 1) < len(tokens) else ""
        if delim and ("?" in delim or "!" in delim):
            # Combine clause up to punctuation, keeping any pause tags intact before the spoken clause
            leading_ws = chunk[: len(chunk) - len(chunk.lstrip())]
            clause = chunk.lstrip()
            opener = "¿" if delim.startswith("?") else "¡"
            # Preserve any opening quote before adding ¿ or ¡
            quote_prefix = ""
            if clause.startswith(('"', "'")):
                quote_prefix = clause[0]
                clause = clause[1:].lstrip()
            if clause and not clause.startswith(("¿", "¡")):
                # Also strip any inner unmatched opener only at clause start; prepend clean opener
                clause = f"{opener}{clause}"
            out.append(f"{leading_ws}{quote_prefix}{clause}{delim}")
            i += 2
        else:
            out.append(chunk)
            i += 1
    return "".join(out)


def inject_game_option_micro_pauses(text: str, pause_seconds: float = 0.26) -> str:
    """Inserts clean `[pause:Xs]` before Option B / C / D markers inside GAME challenge segments."""
    if not text or pause_seconds <= 0:
        return text
    opt_pattern = re.compile(
        r"(?<!\[pause:)\s+\b((?:Option|Opción|Opcion|Opzione)\s+[BCD]\s*:)",
        flags=re.IGNORECASE,
    )
    tag = f"[pause:{pause_seconds:.2f}]"
    shaped = opt_pattern.sub(rf" {tag} \1", text)
    return re.sub(r"\s+", " ", shaped).strip()


def inject_learner_sentence_pauses(text: str, video_type: str, pause_seconds: float = 0.28) -> str:
    """Inserts `[pause:Xs]` between sentences in multi-sentence pedagogical segments
    for EXPRESSION, FUN_FACTS, and ROLEPLAY (never GAME) so Qwen3-TTS inserts clean
    learner-friendly breathing pauses without altering captions.
    """
    vtype = (video_type or "").strip().lower()
    if not text or vtype == "game" or pause_seconds <= 0:
        return text
    if len(re.sub(r"\[.*?\]", " ", text).split()) < 12:
        return text
    # Avoid duplicating existing pause tags or breaking ellipses/abbreviations
    tag = f"[pause:{pause_seconds:.2f}]"
    sentence_break_re = re.compile(r"([.?!])(\s+)(?=[A-ZÀ-Ÿ¿¡\"'«])")

    def _repl(match: re.Match) -> str:
        punct = match.group(1)
        start_idx = match.start()
        prefix = text[: start_idx + 1]
        if _ABBREV_END_RE.search(prefix):
            return match.group(0)
        # Skip ellipses (`...`)
        if punct == "." and start_idx >= 1 and text[start_idx - 1] == ".":
            return match.group(0)
        after = text[match.end() :]
        if after.startswith("[pause:"):
            return match.group(0)
        return f"{punct} {tag} "

    shaped = sentence_break_re.sub(_repl, text)
    return re.sub(r"\s+", " ", shaped).strip()


def _restore_controlled_interrobang_and_ellipsis(cleaned: str, raw_text: Optional[str]) -> str:
    """Restores safe expressive cues (`?!` / crisp `...`) from raw script text when flattened."""
    if not raw_text:
        return cleaned
    # Only restore trailing `?!` / `!?` if cleaned ended with single `?` and raw had explicit `?!` or `!?`
    if re.search(r"[?!]{2}\s*$", raw_text.strip()) and re.search(r"\?\s*$", cleaned.strip()):
        cleaned = re.sub(r"\?\s*$", "?!", cleaned.strip())
    # Allow at most one rhythmic ellipsis before a punchline if raw used explicit `...` before `?` or short pause word
    if "..." in raw_text and ", " in cleaned and cleaned.count("...") == 0:
        # Recover up to 1 mid-clause dramatic beat when raw text explicitly placed `...` before a short pivot word
        pivot_match = re.search(r"([A-Za-zÀ-ÿ0-9']+)\s*\.\.\.\s*([A-Za-zÀ-ÿ]+)", raw_text)
        if pivot_match:
            w1, w2 = pivot_match.group(1), pivot_match.group(2)
            pattern = re.compile(rf"\b{re.escape(w1)}\s*,\s+{re.escape(w2)}\b")
            if pattern.search(cleaned):
                cleaned = pattern.sub(f"{w1}... {w2}", cleaned, count=1)
    return cleaned


def prepare_tts_prosody_text(
    text: str,
    raw_text: Optional[str] = None,
    language: str = "english",
    video_type: str = "expression",
    section: str = "",
    is_stress_vital: bool = False,
    use_option_micro_pauses: bool = False,
    option_micro_pause_sec: float = 0.26,
    enforce_inverted_punctuation: bool = False,
    continuous_turn: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Prepares spoken text for Qwen3-TTS with language/type prosody cues without mutating captions.

    Returns `(shaped_text, prosody_flags)`.
    """
    shaped = text or ""
    if not shaped:
        return shaped, {
            "has_question": False,
            "has_exclamation": False,
            "has_interrobang": False,
            "has_ellipsis": False,
            "is_cliffhanger": False,
        }

    # Skip ellipsis restoration on stress-vital English segments so heteronym carrier fluency stays intact
    if raw_text and not (is_stress_vital and (language or "").lower() == "english"):
        shaped = _restore_controlled_interrobang_and_ellipsis(shaped, raw_text)

    if enforce_inverted_punctuation and (language or "").lower() == "spanish":
        shaped = ensure_spanish_inverted_punctuation(shaped)

    sec_low = (section or "").strip().lower()
    if (video_type or "").lower() == "game" and "challenge" in sec_low and use_option_micro_pauses:
        shaped = inject_game_option_micro_pauses(shaped, pause_seconds=option_micro_pause_sec)
    elif not continuous_turn and (video_type or "").lower() in ("expression", "fun_facts", "roleplay"):
        shaped = inject_learner_sentence_pauses(shaped, video_type=video_type, pause_seconds=0.28)

    stripped = shaped.strip()
    flags = {
        "has_question": "?" in stripped,
        "has_exclamation": "!" in stripped,
        "has_interrobang": "?!" in stripped or "!?" in stripped,
        "has_ellipsis": "..." in stripped,
        "is_cliffhanger": stripped.endswith(("?", "!", "?!", "!?", "...")),
    }
    return shaped, flags
