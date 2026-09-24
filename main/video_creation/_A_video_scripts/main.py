from typing import Optional
import argparse
import os
import sys
import time
import random
import json
import re
from pathlib import Path

# Add project root, video_creation, and module directory to path for robust imports
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from config import (
        BASE_DIR,
        LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME,
        STATIC_NARRATOR_PERSONALITY, require_services
    )
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from shorts_automation.config import (
        BASE_DIR,
        LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME,
        STATIC_NARRATOR_PERSONALITY, require_services
    )

try:
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from state_manager import StateManager, resolve_lang_and_type

try:
    from video_creation._A_video_scripts.core.metadata_builder import build_metadata
    from video_creation._A_video_scripts.core.llm import generate_response, check_connection
    from video_creation._A_video_scripts.prompts.prompt_builder import build_prompt, validate_params, load_call_to_actions, build_fun_facts_formatting_prompt
    from video_creation._A_video_scripts.id_generator import generate_script_id, parse_script_id
    from video_creation._A_video_scripts.script_modifier import modify_video_script
except (ImportError, ModuleNotFoundError):
    try:
        # pyrefly: ignore [missing-import]
        from core.metadata_builder import build_metadata
        # pyrefly: ignore [missing-import]
        from core.llm import generate_response, check_connection
        from prompts.prompt_builder import build_prompt, validate_params, load_call_to_actions, build_fun_facts_formatting_prompt
        from id_generator import generate_script_id, parse_script_id
        from script_modifier import modify_video_script
    except (ImportError, ModuleNotFoundError):
        try:
            from _A_video_scripts.core.metadata_builder import build_metadata
            from _A_video_scripts.core.llm import generate_response, check_connection
            from _A_video_scripts.prompts.prompt_builder import build_prompt, validate_params, load_call_to_actions, build_fun_facts_formatting_prompt
            from _A_video_scripts.id_generator import generate_script_id, parse_script_id
            from _A_video_scripts.script_modifier import modify_video_script
        except (ImportError, ModuleNotFoundError):
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._A_video_scripts.core.metadata_builder import build_metadata
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._A_video_scripts.core.llm import generate_response, check_connection
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._A_video_scripts.prompts.prompt_builder import build_prompt, validate_params, load_call_to_actions, build_fun_facts_formatting_prompt
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._A_video_scripts.id_generator import generate_script_id, parse_script_id
            # pyrefly: ignore [missing-import]
            from shorts_automation.video_creation._A_video_scripts.script_modifier import modify_video_script

DEFAULT_PAUSE_SECONDS = float(os.getenv("LLM_PAUSE_SECONDS", "5"))

def timed_input(prompt: str, timeout: float = 8.0, default: str = "1") -> str:
    """
    Prompts for interactive console input with a countdown timer.
    Automatically defaults to `default` (e.g. '1') when timeout expires without input.
    """
    if not sys.stdin.isatty():
        return default

    # Windows implementation using msvcrt
    if sys.platform == "win32":
        import msvcrt
        start_time = time.time()
        user_chars = []
        last_shown_sec = -1

        while True:
            elapsed = time.time() - start_time
            remaining = max(0, int(timeout - elapsed) + 1)

            if not user_chars and remaining != last_shown_sec:
                last_shown_sec = remaining
                sys.stdout.write(f"\r{prompt} (auto in {remaining}s): ")
                sys.stdout.flush()

            if elapsed >= timeout:
                if not user_chars:
                    print(f"\n[Timer: {int(timeout)}s elapsed] Automatically selecting [{default}] (Local LLM).")
                    return default
                break

            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    print()
                    break
                elif ch == "\b":  # Backspace
                    if user_chars:
                        user_chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    user_chars.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                    # Quick select on single digit
                    if len(user_chars) == 1 and user_chars[0] in ("1", "2"):
                        print()
                        return user_chars[0]

            time.sleep(0.04)

        val = "".join(user_chars).strip()
        return val if val else default

    # Unix fallback using select
    import select
    print(f"{prompt} (auto in {int(timeout)}s): ", end="", flush=True)
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        val = sys.stdin.readline().strip()
        return val if val else default
    else:
        print(f"\n[Timer: {int(timeout)}s elapsed] Automatically selecting [{default}].")
        return default

def extract_json_from_llm(raw_text: str) -> dict:
    """
    Robustly extracts and parses the JSON object from raw LLM output.
    Handles markdown code fences, surrounding commentary, and extra trailing data.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response from LLM")

    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()

    # 1. Direct parse attempt
    try:
        data = json.loads(cleaned, strict=False)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Extract first valid JSON object using JSONDecoder.raw_decode
    start_idx = cleaned.find("{")
    if start_idx != -1:
        try:
            obj, _ = json.JSONDecoder(strict=False).raw_decode(cleaned[start_idx:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # 3. Balanced bracket scan
    depth = 0
    start = -1
    for i, c in enumerate(cleaned):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start != -1:
                candidate = cleaned[start : i + 1]
                try:
                    obj = json.loads(candidate, strict=False)
                    if isinstance(obj, dict) and ("script" in obj or "video_type" in obj or "title" in obj):
                        return obj
                except Exception:
                    pass

    # 4. Fallback to regex search
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(), strict=False)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from LLM response. Raw output preview:\n{cleaned[:200]}")


def validate_idiomatic_roleplay(script: dict, params: dict) -> list[str]:
    """
    Validate an idiomatic ROLEPLAY script for the two Error #4 quality gates.

    Called when SPECIAL_TREATMENT == 'idiomatic'. Returns a list of violation
    strings; an empty list means the script is valid.

    Gates enforced:
    1. Full idiom form must appear verbatim in DIALOGUE_PART_1 (specifically
       in PERSON_TWO's turn, since P2 introduces the idiom per the arc rules).
    2. PERSON_ONE must actively USE the idiom in DIALOGUE_PART_4 — not just
       react, confirm, or ask about it. Detected by checking that the idiom
       string appears in P1's turn of DIALOGUE_PART_4.

    Args:
        script:  The parsed 'script' dict from the LLM response (7 keys).
        params:  The original prompt params dict (must contain ROLEPLAY_SCENARIO).

    Returns:
        List[str]: Validation error descriptions. Empty list = valid.
    """
    errors = []

    # --- Extract the target idiom from ROLEPLAY_SCENARIO ---
    # The scenario typically quotes both a full scene-setting sentence and the core idiom.
    # We want the CORE IDIOM: the shortest quoted string that is at least 4 chars and
    # no more than 8 words (a multi-word fixed phrase, not an entire sentence).
    # Example scenario quote: '¡Pero tío, déjalas ahí, que te van a costar un ojo de la cara!'
    # → We pick 'costar un ojo de la cara' which is the fixed idiom at the heart of it.
    scenario = str(params.get("ROLEPLAY_SCENARIO", ""))
    quoted_candidates = re.findall(r"'([^']{4,})'", scenario)
    # Filter to phrase-length candidates (≤ 8 words) to avoid capturing full sentences
    phrase_candidates = [c.strip() for c in quoted_candidates if len(c.split()) <= 8]
    # Also consider the full list as fallback if no phrase-length candidates exist
    target_idiom = ""
    if phrase_candidates:
        # Among phrase-length candidates, prefer the one most likely to be the idiom:
        # the shortest one that still contains a meaningful chunk (avoids single-word captures)
        multi_word = [c for c in phrase_candidates if len(c.split()) >= 2]
        if multi_word:
            target_idiom = min(multi_word, key=len).strip().lower()
        else:
            target_idiom = min(phrase_candidates, key=len).strip().lower()
    elif quoted_candidates:
        # Fallback: use the shortest overall candidate
        target_idiom = min(quoted_candidates, key=len).strip().lower()

    part1_text = str(script.get("DIALOGUE_PART_1", "")).lower()
    part4_text = str(script.get("DIALOGUE_PART_4", ""))

    # --- Gate 1: Full idiom form in DIALOGUE_PART_1 ---
    if target_idiom and target_idiom not in part1_text:
        errors.append(
            f"IDIOMATIC GATE 1: Full idiom form '{target_idiom}' not found in "
            f"DIALOGUE_PART_1. PERSON_TWO must drop the complete idiomatic form "
            f"(never truncated) when introducing the expression."
        )

    # --- Gate 2: PERSON_ONE uses the idiom in DIALOGUE_PART_4 ---
    # Parse P1's turn: it appears before the first \nPERSON_TWO line.
    # P1's line begins with "PERSON_ONE" tag.
    part4_lines = part4_text.split("\n")
    p1_line_in_part4 = ""
    for line in part4_lines:
        if line.strip().upper().startswith("PERSON_ONE"):
            p1_line_in_part4 = line.lower()
            break

    if target_idiom and target_idiom not in p1_line_in_part4:
        errors.append(
            f"IDIOMATIC GATE 2 (Error #4 \u2014 No Usage Modeling): PERSON_ONE does not "
            f"use the idiom '{target_idiom}' in an original sentence in DIALOGUE_PART_4. "
            f"P1's breakthrough MUST be an active, natural use of the full idiom \u2014 "
            f"not a question, not a confirmation, not a meta-comment about its meaning."
        )

    return errors



def handle_prompt(
    state_manager: StateManager,
    script_id: str,
    params: dict,
    script_number: int,
    total: int,
    auto: bool = False,
    script_input: str = None,
    force: bool = False,
) -> int:
    # 1. Master DB Gate: Skip if marked DONE in expressions database
    from core.expression_db import is_expression_done
    if not force and is_expression_done(script_id):
        expr_name = params.get("EXPRESSION") or params.get("ROLEPLAY_SCENARIO") or params.get("TOPIC") or ""
        print(f"[{script_number}/{total}] [DB: SKIPPED] Script {script_id} ('{expr_name}') is marked as DONE in database.")
        return 0

    state = state_manager.get_script_state(script_id)
    
    # 2. Stage-level granularity: Skip if script already generated
    if not force and state["status"]["script_generation"] == "done":
        print(f"[{script_number}/{total}] Script {script_id} already generated — skipping.")
        return 0

    try:
        validate_params(params)
    except ValueError as exc:
        print(f"[{script_number}/{total}] Invalid input: {exc}", file=sys.stderr)
        return 1

    video_type = params.get("VIDEO_TYPE", "EXPRESSION").upper()
    user_provided_script = None

    # Interactive or file-based script input for FUN_FACTS
    if video_type in ["FUN_FACTS", "FUNFACTS"]:
        if script_input and Path(script_input).is_file():
            try:
                user_provided_script = Path(script_input).read_text(encoding="utf-8").strip()
                print(f"[{script_number}/{total}] Loaded external script from file: {script_input}")
            except Exception as e:
                print(f"Warning: Could not read script_input file: {e}")
        elif not auto and sys.stdin.isatty():
            topic_desc = params.get("TOPIC") or params.get("EXPRESSION") or params.get("SUBJECT") or script_id
            print("\n" + "=" * 64)
            print(f"🎬 FUN_FACTS SCRIPT WORKFLOW: {script_id} ({params.get('TARGET_LANGUAGE')})")
            print(f"Topic: {topic_desc}")
            print("=" * 64)
            print("Choose how to provide the script:")
            print("  [1] Generate automatically using local LLM (Default)")
            print("  [2] Pass / paste external script (e.g. from ChatGPT/Claude)")
            print("-" * 64)
            try:
                choice = timed_input("Enter choice [1/2] (default: 1)", timeout=8.0, default="1").strip()
            except (EOFError, KeyboardInterrupt):
                choice = "1"

            if choice == "2":
                print("\nPaste your raw script below (or provide a .txt filepath).")
                print("When finished, enter an empty line and then type 'DONE' or 'EOF':")
                print("-" * 40)
                lines = []
                while True:
                    try:
                        line = input()
                    except (EOFError, KeyboardInterrupt):
                        break
                    if line.strip().upper() in ("DONE", "EOF"):
                        break
                    lines.append(line)
                pasted_text = "\n".join(lines).strip()

                # If the user pasted a single path to an existing text file, read from it
                if pasted_text and "\n" not in pasted_text and Path(pasted_text).is_file():
                    try:
                        pasted_text = Path(pasted_text).read_text(encoding="utf-8").strip()
                        print(f"Loaded script from file: {pasted_text[:60]}...")
                    except Exception as fe:
                        print(f"Error reading file '{pasted_text}': {fe}")

                if pasted_text:
                    user_provided_script = pasted_text
                    print(f"✓ External script received ({len(pasted_text.split())} words).")
                else:
                    print("No script text provided — defaulting to automatic generation.")

    if user_provided_script:
        prompt = build_fun_facts_formatting_prompt(user_provided_script, params)
        print(
            f"[{script_number}/{total}] Adapting & formatting external script with local LLM — "
            f"{params.get('TARGET_LANGUAGE')} / {params.get('TOPIC', params.get('EXPRESSION', ''))}"
        )
    else:
        prompt = build_prompt(params)
        print(
            f"[{script_number}/{total}] Generating script — "
            f"{params.get('TARGET_LANGUAGE')} / {params.get('SUBJECT')} / {params.get('EXPRESSION', params.get('TOPIC', ''))}"
        )

    try:
        parsed_json = None
        script_field = None
        raw_response = ""
        last_parse_err = None

        for parse_attempt in range(1, 4):
            try:
                raw_response = generate_response(prompt)
                if not raw_response:
                    raise ValueError("Empty response from LLM")
                    
                # Extract JSON from raw response
                parsed_json = extract_json_from_llm(raw_response)
                script_field = parsed_json.get("script", "")
                if not script_field:
                    raise ValueError("Missing 'script' field in LLM JSON response")
                break
            except Exception as pe:
                last_parse_err = pe
                if parse_attempt < 3:
                    print(
                        f"[{script_number}/{total}] Attempt {parse_attempt} failed ({pe}). "
                        f"Retrying generation in 2s..."
                    )
                    time.sleep(2)
                else:
                    raise last_parse_err
            
        # Automated pipeline guardrail: validate spoken word counts and speaker isolation
        video_type = params.get("VIDEO_TYPE", "EXPRESSION").upper()
        if isinstance(script_field, dict):
            spoken_words = sum(len(v.split()) for k, v in script_field.items() if k.lower() != "title" and isinstance(v, str))
            if video_type == "ROLEPLAY":
                min_limit = 145
                max_limit = 180
            elif video_type == "GAME":
                min_limit = 95
                max_limit = 125
            elif video_type in ["FUN_FACTS", "FUNFACTS"]:
                min_limit = 95
                max_limit = 135
            else:  # EXPRESSION
                min_limit = 85
                max_limit = 110
            keys_lower = {k.lower(): k for k in script_field.keys()}

            if video_type == "ROLEPLAY":
                has_narrator_in_dialogue = any(
                    "narrator" in str(v).lower()
                    for k, v in script_field.items()
                    if "dialogue" in k.lower()
                )
                part_4_text = str(script_field.get("DIALOGUE_PART_4", "")).strip()
                ends_with_unresolved_question = part_4_text.endswith("?")
                missing_payoff = "payoff" not in keys_lower
                missing_hook = "hook" not in keys_lower
                missing_parts = [
                    p for p in ["dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4"]
                    if p not in keys_lower
                ]
                illegal_keys = [
                    k for k in script_field.keys()
                    if k.lower() not in [
                        "title", "hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff"
                    ]
                ]

                # Idiomatic expression quality gates (Error #4: usage modeling)
                idiomatic_errors = []
                if str(params.get("SPECIAL_TREATMENT", "")).strip().lower() == "idiomatic":
                    idiomatic_errors = validate_idiomatic_roleplay(script_field, params)

                needs_retry = (
                    (spoken_words > max_limit or spoken_words < min_limit)
                    or has_narrator_in_dialogue
                    or ends_with_unresolved_question
                    or missing_payoff
                    or missing_hook
                    or bool(missing_parts)
                    or bool(illegal_keys)
                    or bool(idiomatic_errors)
                )
                if needs_retry:
                    reasons = []
                    if spoken_words > max_limit or spoken_words < min_limit:
                        reasons.append(f"word count is {spoken_words} (target {min_limit}-{max_limit})")
                    if missing_payoff:
                        reasons.append("Missing mandatory 'PAYOFF' section")
                    if missing_hook:
                        reasons.append("Missing mandatory 'hook' section")
                    if missing_parts:
                        reasons.append(f"Missing dialogue sections: {', '.join(missing_parts)}")
                    if illegal_keys:
                        reasons.append(f"Illegal invented keys: {', '.join(illegal_keys)}")
                    if has_narrator_in_dialogue:
                        reasons.append("NARRATOR placed inside dialogue")
                    if ends_with_unresolved_question:
                        reasons.append("DIALOGUE_PART_4 ended with unresolved question")
                    if idiomatic_errors:
                        reasons.extend(idiomatic_errors)

                    print(f"[{script_number}/{total}] Validation check failed: {'; '.join(reasons)}. Retrying generation...")
                    retry_prompt = prompt + (
                        f"\n\nCRITICAL RETRY REQUIREMENT: Your previous draft had errors: {'; '.join(reasons)}. "
                        f"1. The 'script' object MUST contain EXACTLY these 7 keys: 'title', 'hook', 'DIALOGUE_PART_1', 'DIALOGUE_PART_2', 'DIALOGUE_PART_3', 'DIALOGUE_PART_4', 'PAYOFF'.\n"
                        f"2. Total spoken words across all sections (excluding title) MUST be STRICTLY between {min_limit} and {max_limit} words for a 60-80s max runtime.\n"
                        f"3. Strict alternating speaker turns: PERSON_ONE then PERSON_TWO in every dialogue part.\n"
                        f"4. The target expression / phonetic word MUST be explicitly spoken in DIALOGUE_PART_1."
                        + (
                            f"\n5. IDIOMATIC ARC FIX REQUIRED: {'; '.join(idiomatic_errors)}"
                            if idiomatic_errors else ""
                        )
                    )
                    try:
                        retry_raw = generate_response(retry_prompt)
                        retry_parsed = extract_json_from_llm(retry_raw)
                        if retry_parsed and retry_parsed.get("script"):
                            parsed_json = retry_parsed
                            script_field = retry_parsed["script"]
                            new_words = sum(len(v.split()) for k, v in script_field.items() if k.lower() != "title" and isinstance(v, str))
                            print(f"[{script_number}/{total}] Retry successful! Calibrated word count: {new_words} words.")
                    except Exception as retry_exc:
                        print(f"[{script_number}/{total}] Retry failed: {retry_exc}")

            elif video_type == "GAME":
                missing_game_keys = [
                    k for k in ["hook", "challenge", "pressure", "answer", "explanation"]
                    if k not in keys_lower
                ]
                illegal_game_keys = [
                    k for k in script_field.keys()
                    if k.lower() not in [
                        "title", "hook", "challenge", "pressure", "answer", "explanation"
                    ]
                ]
                # Check word limits
                word_limit_failed = (spoken_words > max_limit or spoken_words < min_limit)

                # Extract and validate options
                ch_text = str(script_field.get("challenge", ""))
                board_text = str(parsed_json.get("chalkboard_exercise", "") or script_field.get("chalkboard_exercise", ""))

                def _extract_opts(text):
                    return re.findall(r"(?:^|\s)([A-E])[\)\.:\-]\s*([^\n\rA-E\)\.:\-]+)", text)

                ch_opts = _extract_opts(ch_text)
                board_opts = _extract_opts(board_text)

                # Check for duplicate options
                duplicate_reasons = []
                for label, opt_list in [("challenge", ch_opts), ("chalkboard", board_opts)]:
                    if opt_list:
                        seen = {}
                        for let, txt in opt_list:
                            clean_t = txt.strip().rstrip(".,!? ").lower()
                            raw_t = txt.strip().rstrip(".,!? ")
                            if len(clean_t) > 1:
                                if clean_t in seen:
                                    prev_let, prev_raw = seen[clean_t]
                                    if raw_t == prev_raw:
                                        duplicate_reasons.append(f"identical option '{raw_t}' at {prev_let} and {let}")
                                else:
                                    seen[clean_t] = (let, raw_t)

                # Check option count
                opts_to_count = board_opts if board_opts else ch_opts
                too_few_options = len(opts_to_count) < 2
                too_few_spoken_options = not (
                    re.search(r"(?:^|[\s\n])A\s*[:\)\.\-]", ch_text, re.IGNORECASE)
                    and re.search(r"(?:^|[\s\n])B\s*[:\)\.\-]", ch_text, re.IGNORECASE)
                )

                # Check for spoken blank (___ in spoken challenge)
                spoken_blank = bool(re.search(r"_{2,}", ch_text))

                # Check for prompt leakage in spoken challenge
                prompt_leak_reasons = []
                if re.search(r"\(.*=.*(?:vs|ou|o|-).*\)", ch_text) or re.search(r"\((?:noun|verb|sens):", ch_text, re.IGNORECASE):
                    prompt_leak_reasons.append("Prompt definition/notes leaked into spoken challenge")

                # Check for banned formulas
                hook_text = str(script_field.get("hook", "")).lower()
                ans_text = str(script_field.get("answer", "")).lower()
                ch_text_lower = ch_text.lower()
                banned_podcast_hook = "podcast" in hook_text
                banned_crown_reveal = "takes the crown" in ans_text

                # Check for abstract/contextless questions
                abstract_reasons = []
                abstract_patterns = [
                    r"which one is the correct word\b",
                    r"which one has the correct stress\b",
                    r"which is the correct pronunciation\b",
                    r"quel est le mot correct\b",
                    r"cu[aá]l es la palabra correcta\b",
                    r"qual [eè] la parola corretta\b",
                ]
                for pat in abstract_patterns:
                    if re.search(pat, ch_text_lower):
                        if "___" not in ch_text and "___" not in board_text and '"' not in ch_text and "'" not in ch_text:
                            abstract_reasons.append("Abstract question without a concrete test sentence or blank (___)")
                            break

                # Check language purity for French, Spanish, Italian
                target_lang_str = str(params.get("TARGET_LANGUAGE", "")).lower()
                lang_leak_reasons = []
                if target_lang_str in ["french", "spanish", "italian"]:
                    full_script_str = " ".join(str(v) for v in script_field.values()) + " " + board_text
                    en_leaks = re.findall(
                        r"\b(you agree to|never show up|meet your friend|which sentence|totally natural|"
                        r"three seconds on the clock|what does it really mean|can you spot|spot this easy phrase|"
                        r"the correct answer is|choose the most native|native speaker trap|this year|money|blessed)\b",
                        full_script_str,
                        re.IGNORECASE
                    )
                    if en_leaks:
                        lang_leak_reasons.append(f"English leak into {target_lang_str.title()}: {', '.join(set(en_leaks))}")

                missing_board = not board_text.strip()

                needs_retry = (
                    word_limit_failed
                    or bool(missing_game_keys)
                    or bool(illegal_game_keys)
                    or bool(duplicate_reasons)
                    or too_few_options
                    or too_few_spoken_options
                    or spoken_blank
                    or bool(prompt_leak_reasons)
                    or banned_podcast_hook
                    or banned_crown_reveal
                    or bool(abstract_reasons)
                    or bool(lang_leak_reasons)
                    or missing_board
                )
                if needs_retry:
                    reasons = []
                    if word_limit_failed:
                        reasons.append(f"word count is {spoken_words} (target {min_limit}-{max_limit})")
                    if missing_game_keys:
                        reasons.append(f"Missing mandatory sections: {', '.join(missing_game_keys)}")
                    if illegal_game_keys:
                        reasons.append(f"Illegal sections: {', '.join(illegal_game_keys)}")
                    if duplicate_reasons:
                        reasons.append(f"DUPLICATE OPTIONS: {'; '.join(duplicate_reasons)}. All options must be 100% distinct!")
                    if too_few_options:
                        reasons.append("Chalkboard must offer at least 2 distinct labeled options (A and B)")
                    if too_few_spoken_options:
                        reasons.append("Spoken challenge MUST voice all options clearly (e.g. 'A: [Option A], or B: [Option B]')")
                    if spoken_blank:
                        reasons.append("SPOKEN BLANK DETECTED: Do NOT put '___' in spoken challenge audio! Deliver the test sentence with the target word/rhythm spoken naturally and ask which option was heard/used (Option A).")
                    if prompt_leak_reasons:
                        reasons.append(f"PROMPT LEAKAGE: {'; '.join(prompt_leak_reasons)}. Never copy parenthetical notes or glosses into the script!")
                    if banned_podcast_hook:
                        reasons.append("BANNED HOOK: Do NOT use the podcast setup formula! Use the assigned situational archetype.")
                    if banned_crown_reveal:
                        reasons.append("BANNED PHRASE: Do NOT say 'takes the crown' in answer! Reveal the winning answer naturally.")
                    if abstract_reasons:
                        reasons.append(f"ABSTRACT QUESTION: {'; '.join(abstract_reasons)}. You MUST provide a concrete test sentence with a blank (___)!")
                    if lang_leak_reasons:
                        reasons.append(f"LANGUAGE PURITY VIOLATION: {'; '.join(lang_leak_reasons)}. Script must be 100% in {target_lang_str.title()}!")
                    if missing_board:
                        reasons.append("Missing 'chalkboard_exercise' field")

                    print(f"[{script_number}/{total}] Validation check failed: {'; '.join(reasons)}. Retrying generation...")
                    retry_prompt = prompt + (
                        f"\n\nCRITICAL RETRY REQUIREMENT: Your previous draft had errors: {'; '.join(reasons)}. "
                        f"1. The 'script' object MUST contain EXACTLY these 5 sections (plus 'title'): 'title', 'hook', 'challenge', 'pressure', 'answer', 'explanation'.\n"
                        f"2. Total spoken words across all sections (excluding title) MUST be STRICTLY between {min_limit} and {max_limit} words for a 40-55s runtime.\n"
                        f"3. ZERO raw underscores ('___') in the spoken 'challenge'! Deliver the test sentence with the target word/rhythm spoken out loud (Option A), and speak all options clearly (e.g. 'A: [Option A], or B: [Option B]').\n"
                        f"4. All options MUST be completely distinct. ZERO duplicate options allowed.\n"
                        f"5. DO NOT copy parenthetical notes or translations from the prompt into the script.\n"
                        f"6. DO NOT use the word 'podcast' in hook, and DO NOT say 'takes the crown' in answer.\n"
                        f"7. 100% in {target_lang_str.upper()}. No English words, sentences, or translation prompts.\n"
                        f"8. Include 'chalkboard_exercise' formatted with the test sentence with blank (___) on line 1, then each option on a new line: \\n[Test sentence with ___]\\nA) [Option A]\\nB) [Option B]."
                    )
                    try:
                        retry_raw = generate_response(retry_prompt)
                        retry_parsed = extract_json_from_llm(retry_raw)
                        if retry_parsed and retry_parsed.get("script"):
                            parsed_json = retry_parsed
                            script_field = retry_parsed["script"]
                            new_words = sum(len(v.split()) for k, v in script_field.items() if k.lower() != "title" and isinstance(v, str))
                            print(f"[{script_number}/{total}] Retry successful! Calibrated word count: {new_words} words.")
                    except Exception as retry_exc:
                        print(f"[{script_number}/{total}] Retry failed: {retry_exc}")

            elif video_type in ["FUN_FACTS", "FUNFACTS"]:
                missing_hook = "hook" not in keys_lower
                missing_payoff = "payoff" not in keys_lower
                authorized_fun_facts_keys = {
                    "title", "hook", "payoff",
                    # Format A (Facts)
                    "fact_1", "fact_2", "fact_3", "fact_4", "fact_5", "fact",
                    # Format B (One Big Curiosity / Story)
                    "setup", "discovery", "story", "context", "details", "explanation",
                    # Format C (Challenge)
                    "challenge", "thinking_time", "answer", "pressure", "question",
                    # Format D (Mystery)
                    "mystery", "clues", "reveal", "clue_1", "clue_2", "clue_3",
                    # Format E (Comparison)
                    "comparison_a", "comparison_b", "surprise",
                    # Format F (Ranking/List)
                    "item_3", "item_2", "item_1", "item_4", "item_5",
                    # Common optional
                    "cta", "curiosity", "example"
                }
                illegal_keys = [k for k in script_field.keys() if k.lower() not in authorized_fun_facts_keys]
                needs_retry = (
                    (spoken_words > max_limit or spoken_words < min_limit)
                    or missing_hook
                    or missing_payoff
                    or bool(illegal_keys)
                )
                if needs_retry:
                    reasons = []
                    if spoken_words > max_limit or spoken_words < min_limit:
                        reasons.append(f"word count is {spoken_words} (target {min_limit}-{max_limit} words for 40-60s runtime)")
                    if missing_hook:
                        reasons.append("Missing mandatory 'hook' section")
                    if missing_payoff:
                        reasons.append("Missing mandatory 'payoff' section")
                    if illegal_keys:
                        reasons.append(f"Illegal invented keys: {', '.join(illegal_keys)}")

                    print(f"[{script_number}/{total}] Validation check failed: {'; '.join(reasons)}. Retrying generation...")
                    retry_prompt = prompt + (
                        f"\n\nCRITICAL RETRY REQUIREMENT: Your previous draft had errors: {'; '.join(reasons)}. "
                        f"1. Total spoken words across all sections (excluding title) MUST be STRICTLY between {min_limit} and {max_limit} words for a 40-60s runtime.\n"
                        f"2. Follow the FUN_FACTS format with mandatory 'title', 'hook', body discovery sections, and 'payoff'."
                    )
                    try:
                        retry_raw = generate_response(retry_prompt)
                        retry_parsed = extract_json_from_llm(retry_raw)
                        if retry_parsed and retry_parsed.get("script"):
                            parsed_json = retry_parsed
                            script_field = retry_parsed["script"]
                            new_words = sum(len(v.split()) for k, v in script_field.items() if k.lower() != "title" and isinstance(v, str))
                            print(f"[{script_number}/{total}] Retry successful! Calibrated word count: {new_words} words.")
                    except Exception as retry_exc:
                        print(f"[{script_number}/{total}] Retry failed: {retry_exc}")

            elif video_type == "EXPRESSION":
                missing_hook = "hook" not in keys_lower
                missing_setup = "setup" not in keys_lower
                missing_discovery = "discovery" not in keys_lower
                missing_example = "example" not in keys_lower
                missing_payoff = "payoff" not in keys_lower
                word_limit_failed = spoken_words > max_limit or spoken_words < min_limit
                illegal_keys = [
                    k for k in script_field.keys()
                    if k.lower() not in ["title", "hook", "setup", "discovery", "example", "payoff"]
                ]
                needs_retry = (
                    word_limit_failed
                    or missing_hook
                    or missing_setup
                    or missing_discovery
                    or missing_example
                    or missing_payoff
                    or bool(illegal_keys)
                )
                if needs_retry:
                    reasons = []
                    if word_limit_failed:
                        reasons.append(f"word count is {spoken_words} (target {min_limit}-{max_limit} for 38-48s duration)")
                    if missing_hook:
                        reasons.append("missing mandatory 'hook' section")
                    if missing_setup:
                        reasons.append("missing mandatory 'setup' section")
                    if missing_discovery:
                        reasons.append("missing mandatory 'discovery' section")
                    if missing_example:
                        reasons.append("missing mandatory 'example' section (in-context real-world usage phrase)")
                    if missing_payoff:
                        reasons.append("missing mandatory 'payoff' section")
                    if illegal_keys:
                        reasons.append(f"illegal keys: {', '.join(illegal_keys)}")
                    print(f"[{script_number}/{total}] Validation check failed: {'; '.join(reasons)}. Retrying generation...")
                    retry_prompt = prompt + (
                        f"\n\nCRITICAL RETRY REQUIREMENT: Your previous draft had errors: {'; '.join(reasons)}. "
                        f"Total spoken words across all sections (excluding title) MUST be STRICTLY between {min_limit} and {max_limit} words for a 38-48s runtime. "
                        f"Follow the EXPRESSION format with mandatory keys: 'title', 'hook', 'setup', 'discovery', 'example', 'payoff'."
                    )
                    try:
                        retry_raw = generate_response(retry_prompt)
                        retry_parsed = extract_json_from_llm(retry_raw)
                        if retry_parsed and retry_parsed.get("script"):
                            parsed_json = retry_parsed
                            script_field = retry_parsed["script"]
                            new_words = sum(len(v.split()) for k, v in script_field.items() if k.lower() != "title" and isinstance(v, str))
                            print(f"[{script_number}/{total}] Retry successful! Calibrated word count: {new_words} words.")
                    except Exception as retry_exc:
                        print(f"[{script_number}/{total}] Retry failed: {retry_exc}")

        # Ensure PAYOFF does not contain robotic filler like "Follow for more idioms and comments below!"
        if isinstance(script_field, dict):
            payoff_key = next((k for k in script_field if k.lower() == "payoff"), None)
            if payoff_key:
                payoff_val = script_field[payoff_key]
                if isinstance(payoff_val, str):
                    for bad_phr in [
                        "Follow for more essential idioms and comments below!",
                        "Follow for more essential idioms and comments below.",
                        "follow for more essential idioms and comments below!",
                        "follow for more essential idioms and comments below.",
                        "Follow for more idioms and comments below!",
                        "Follow for more essential idioms and comment below!",
                        "comments below!",
                        "comments below."
                    ]:
                        if bad_phr in payoff_val:
                            ctas = load_call_to_actions(params.get("TARGET_LANGUAGE"))
                            replacement = random.choice(ctas) if ctas else "Your turn — use it in a sentence!"
                            payoff_val = payoff_val.replace(bad_phr, replacement).strip()
                            script_field[payoff_key] = payoff_val

            parsed_json["script"] = script_field

        if isinstance(script_field, dict):
            script_text = json.dumps(script_field, indent=2)
        else:
            script_text = str(script_field)
            
    except Exception as exc:
        print(f"[{script_number}/{total}] LLM error: {exc}", file=sys.stderr)
        return 1

    print(f"[{script_number}/{total}] Generating metadata…")
    metadata = build_metadata(script_text, params)

    # Ensure character_personalities exists and includes the static charismatic narrator personality
    if "character_personalities" not in parsed_json or not isinstance(parsed_json["character_personalities"], dict):
        parsed_json["character_personalities"] = {}
    parsed_json["character_personalities"]["Narrator"] = STATIC_NARRATOR_PERSONALITY

    if video_type == "GAME":
        board = parsed_json.get("chalkboard_exercise") or (script_field.get("chalkboard_exercise") if isinstance(script_field, dict) else "")
        expr_val = str(params.get("EXPRESSION", "")).strip()
        context_str = str(params.get("CONTEXT", "")).strip()

        # If board is empty or malformed, build a robust fallback
        if not board or not str(board).strip() or ("A)" not in str(board) and "A." not in str(board)):
            if " vs " in expr_val.lower():
                parts = re.split(r"\s+vs\.?\s+", expr_val, flags=re.IGNORECASE)
                if len(parts) >= 2:
                    p1, p2 = parts[0].strip(), parts[1].strip()
                    first_line = expr_val + "?"
                    if "___" in context_str:
                        clean_sentence = re.split(r"\(", context_str)[0].strip()
                        if clean_sentence:
                            first_line = clean_sentence
                    board = f"{first_line}\nA) {p1}\nB) {p2}"
            elif ch_opts and len(ch_opts) >= 2:
                q_text = ch_text.split("A)")[0].strip() if "A)" in ch_text else expr_val
                board = q_text + "\n" + "\n".join([f"{let}) {txt.strip()}" for let, txt in ch_opts])
            else:
                board = f"{expr_val}\nA) {expr_val}\nB) Option B"

        # If context has a sentence with ___, ensure it is line 1 of the chalkboard
        if "___" in context_str:
            clean_sentence = re.split(r"\(", context_str)[0].strip()
            if clean_sentence and "___" in clean_sentence:
                board_lines = str(board).strip().split("\n")
                if len(board_lines) >= 2 and "___" not in board_lines[0]:
                    board_lines[0] = clean_sentence
                    board = "\n".join(board_lines)

        # Check for duplicate options in board; if duplicate or lost uppercase, fix from clean contrast
        b_opts = re.findall(r"(?:^|\s)([A-E])[\)\.:\-]\s*([^\n\rA-E\)\.:\-]+)", str(board))
        if " vs " in expr_val.lower():
            parts = re.split(r"\s+vs\.?\s+", expr_val, flags=re.IGNORECASE)
            if len(parts) >= 2:
                p1, p2 = parts[0].strip(), parts[1].strip()
                b_lines = str(board).strip().split("\n")
                prompt_line = b_lines[0] if b_lines else expr_val
                # If uppercase stress notation was lost or duplicate options occurred
                has_upper = any(c.isupper() for c in expr_val if c.isalpha())
                if has_upper or len(b_opts) < 2 or b_opts[0][1].strip().lower() == b_opts[1][1].strip().lower():
                    board = f"{prompt_line}\nA) {p1}\nB) {p2}"

        parsed_json["chalkboard_exercise"] = board
        metadata["chalkboard_exercise"] = board

        # Option A Enforcement on Finalized Chalkboard:
        # Guarantee that spoken challenge never contains '___' and voices all options
        if isinstance(script_field, dict):
            ch_val = str(script_field.get("challenge", ""))

            # Strip prompt parentheticals
            ch_val = re.sub(r"\s*\(.*=.*(?:vs|ou|o|-).*\)", "", ch_val)
            ch_val = re.sub(r"\s*\((?:noun|verb|sens):[^\)]*\)", "", ch_val, flags=re.IGNORECASE)

            # Extract final options from finalized board
            b_lines = [l.strip() for l in str(board).splitlines() if l.strip()]
            opt_a, opt_b = None, None
            for l in b_lines:
                ma = re.match(r"^A\s*[:\)\.\-]\s*(.+)$", l, re.IGNORECASE)
                if ma:
                    opt_a = ma.group(1).strip()
                mb = re.match(r"^B\s*[:\)\.\-]\s*(.+)$", l, re.IGNORECASE)
                if mb:
                    opt_b = mb.group(1).strip()

            # Replace ___ in spoken challenge with opt_a
            if re.search(r"_{2,}", ch_val) and opt_a:
                ch_val = re.sub(r"\s*_{2,}\s*", f" {opt_a} ", ch_val)
                ch_val = re.sub(r"\s+", " ", ch_val).strip()

            # Ensure options are voiced in spoken challenge
            has_spoken_opts = bool(
                re.search(r"(?:^|[\s\n])A\s*[:\)\.\-]", ch_val, re.IGNORECASE)
                and re.search(r"(?:^|[\s\n])B\s*[:\)\.\-]", ch_val, re.IGNORECASE)
            )
            if not has_spoken_opts and opt_a and opt_b:
                target_l = str(params.get("TARGET_LANGUAGE", "")).lower()
                sep = {"english": "or", "french": "ou", "italian": "oppure", "spanish": "o"}.get(target_l, "or")
                ch_val = ch_val.rstrip(":., ") + f". A: {opt_a}, {sep} B: {opt_b}?"

            script_field["challenge"] = ch_val
            parsed_json["script"] = script_field
            script_text = json.dumps(script_field, indent=2, ensure_ascii=False)

    # Save to JSON State
    state["prompt_params"] = params
    state["script_text"] = script_text
    state["content_metadata"] = parsed_json
    state["metadata"] = metadata
    state["status"]["script_generation"] = "done"
    state_manager.save_script_state(script_id, state)

    return 0

def load_ready_prompts_from_csv(base_dir: Path) -> list:
    import csv
    input_dir = base_dir / "input"
    
    csv_files = []
    
    # 1. Primary: Unified input/csv/<language>/expressions_list/*_READY_PROMPTS_*.csv
    input_csv_dir = input_dir / "csv"
    if input_csv_dir.exists():
        for lang_dir in sorted(input_csv_dir.iterdir()):
            if lang_dir.is_dir():
                expr_dir = lang_dir / "expressions_list"
                if expr_dir.exists():
                    csv_files.extend(sorted(expr_dir.glob("*READY_PROMPTS_*.csv")))

    # 2. Fallback: input/<language>/expressions_list/*_READY_PROMPTS_*.csv
    if not csv_files and input_dir.exists():
        for lang_dir in sorted(input_dir.iterdir()):
            if lang_dir.is_dir() and lang_dir.name not in ("csv", "images"):
                expr_dir = lang_dir / "expressions_list"
                if expr_dir.exists():
                    csv_files.extend(sorted(expr_dir.glob("*READY_PROMPTS_*.csv")))
                    
        # 3. Fallback: flat files directly inside input/
        if not csv_files:
            csv_files.extend(sorted(input_dir.glob("*READY_PROMPTS_*.csv")))

    # 4. Fallback: legacy data/ directory
    if not csv_files:
        fallback_dir = Path(__file__).parent / "data"
        if fallback_dir.exists():
            csv_files.extend(sorted(fallback_dir.glob("*READY_PROMPTS_*.csv")))

    queued = []
    max_indices = {}

    # Pre-scan existing valid IDs to prevent any collisions
    state_dir = base_dir / "state"
    if state_dir.exists():
        for sf in state_dir.rglob("script_*.json"):
            parsed = parse_script_id(sf.stem.replace("script_", ""))
            if parsed:
                k = (parsed["lang_code"], parsed["type_code"])
                max_indices[k] = max(max_indices.get(k, 0), parsed["index"])

    for ready_csv in csv_files:
        with ready_csv.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = str(row.get("ID", "")).strip().upper()
                parsed = parse_script_id(cid)
                if parsed:
                    k = (parsed["lang_code"], parsed["type_code"])
                    max_indices[k] = max(max_indices.get(k, 0), parsed["index"])

    for ready_csv in csv_files:
        path_parts = [p.lower() for p in ready_csv.parts]
        inferred_lang = "English"
        for lk in ["french", "spanish", "italian", "english"]:
            if lk in path_parts:
                inferred_lang = lk.capitalize()
                break

        fname_upper = ready_csv.name.upper()
        inferred_type = "EXPRESSION"
        if "GAME" in fname_upper:
            inferred_type = "GAME"
        elif "ROLEPLAY" in fname_upper:
            inferred_type = "ROLEPLAY"
        elif "FUN_FACTS" in fname_upper or "FUNFACTS" in fname_upper or "FACTS" in fname_upper:
            inferred_type = "FUN_FACTS"
        elif "EXPRESSION" in fname_upper:
            inferred_type = "EXPRESSION"

        with ready_csv.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if any(row.values()):
                    # Auto-infer TARGET_LANGUAGE and VIDEO_TYPE if not explicitly in CSV
                    if not row.get("TARGET_LANGUAGE"):
                        row["TARGET_LANGUAGE"] = inferred_lang
                    if not row.get("VIDEO_TYPE"):
                        row["VIDEO_TYPE"] = inferred_type

                    # Strip deprecated static fields so they don't pollute state or LLM prompt
                    row.pop("STATUS", None)
                    if inferred_type not in ("FUN_FACTS", "FUNFACTS"):
                        row.pop("FORMAT", None)

                    lang = row.get("TARGET_LANGUAGE", inferred_lang)
                    vtype = row.get("VIDEO_TYPE", inferred_type)

                    if not row.get("ID"):
                        from id_generator import get_language_code, get_type_code
                        lang_c = get_language_code(lang)
                        type_c = get_type_code(vtype)
                        k = (lang_c, type_c)
                        max_indices[k] = max_indices.get(k, 0) + 1
                        row["ID"] = generate_script_id(lang, vtype, max_indices[k])
                    queued.append(row)
                    
    return queued

def process_scripts_to_change_from_csv(
    base_dir: Path,
    csv_path: Optional[str] = None,
    auto: bool = False,
) -> int:
    """
    Processes script updates from CSV file(s) containing columns 'ID' and 'NEW_SCRIPT'.
    Target directory: input/csv/script_to_change/
    
    Before generating and saving the new script, the script's state in state JSON is
    explicitly set from "script_generation": "done" to "pending".
    """
    import csv

    state_manager = StateManager(base_dir)
    script_to_change_dir = base_dir / "input" / "csv" / "script_to_change"
    script_to_change_dir.mkdir(parents=True, exist_ok=True)

    target_csvs: list[Path] = []

    if csv_path:
        p = Path(csv_path)
        if not p.is_file():
            alt_p = script_to_change_dir / csv_path
            if alt_p.is_file():
                p = alt_p
        if not p.is_file():
            print(f"[Error] Specified CSV file '{csv_path}' was not found.", file=sys.stderr)
            return 1
        target_csvs = [p]
    else:
        found_csvs = sorted(script_to_change_dir.glob("*.csv"))
        # Exclude sample templates
        found_csvs = [f for f in found_csvs if not f.name.endswith(".sample.csv")]
        if not found_csvs:
            print(f"\n[Warning] No CSV files found in '{script_to_change_dir}'.")
            print("Please place a CSV file containing columns 'ID' and 'NEW_SCRIPT' in that directory.")
            return 0

        if len(found_csvs) == 1:
            target_csvs = found_csvs
        else:
            if not auto and sys.stdin.isatty():
                print("\n" + "-" * 60)
                print(f"Multiple CSV files found in {script_to_change_dir.name}:")
                for idx, cf in enumerate(found_csvs, start=1):
                    print(f"  [{idx}] {cf.name}")
                print("  [A] Process all CSV files [Default]")
                print("-" * 60)
                try:
                    c_input = input("Select choice (default: A): ").strip().upper()
                except (KeyboardInterrupt, EOFError):
                    print("\nOperation cancelled by user.")
                    return 0

                if c_input in ("A", "", "ALL"):
                    target_csvs = found_csvs
                elif c_input.isdigit() and 1 <= int(c_input) <= len(found_csvs):
                    target_csvs = [found_csvs[int(c_input) - 1]]
                else:
                    target_csvs = found_csvs
            else:
                target_csvs = found_csvs

    queued_prompts = load_ready_prompts_from_csv(base_dir)

    total_processed = 0
    total_successful = 0
    total_failed = 0

    for csv_file in target_csvs:
        print(f"\n📄 Loading script changes from: {csv_file.name}")
        
        rows = []
        raw_text = ""
        try:
            raw_text = csv_file.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            try:
                raw_text = csv_file.read_text(encoding="latin-1", errors="replace")
            except Exception as read_err:
                print(f"❌ Error reading '{csv_file.name}': {read_err}", file=sys.stderr)
                total_failed += 1
                continue

        # Clean manual CSV formatting quirks:
        # 1. Trailing comma after closing quote: '",\n' -> '"\n'
        cleaned_text = re.sub(r'"[ \t]*,[ \t]*\r?\n', '"\n', raw_text)
        # 2. Spaces after comma before opening quote: ', "' -> ',"'
        cleaned_text = re.sub(r',[ \t]+"', ',"', cleaned_text)

        import io
        reader = csv.DictReader(io.StringIO(cleaned_text), skipinitialspace=True)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

        # Detect ID and NEW_SCRIPT columns (case-insensitive)
        id_col = next((c for c in fieldnames if c.strip().upper() == "ID"), None)
        script_col = next(
            (c for c in fieldnames if c.strip().upper() in ("NEW_SCRIPT", "SCRIPT", "NEW_SCRIPT_TEXT", "SCRIPT_CHANGE", "SCRIPT_CHANGED")),
            None
        )

        if not id_col or not script_col:
            print(
                f"❌ Error: '{csv_file.name}' is missing required columns ('ID', 'NEW_SCRIPT'/'SCRIPT_CHANGE'). "
                f"Found headers: {fieldnames}",
                file=sys.stderr
            )
            total_failed += 1
            continue

        if not rows:
            print(f"⚠️ Warning: '{csv_file.name}' is empty (no data rows).")
            continue

        print(f"Found {len(rows)} script modification request(s) in {csv_file.name}.")

        for r_idx, row in enumerate(rows, start=1):
            script_id = str(row.get(id_col, "")).strip().upper()
            raw_new_script = str(row.get(script_col, "")).strip()

            if not script_id:
                continue
            if not raw_new_script:
                print(f"⚠️ Warning: Row {r_idx} for Script ID '{script_id}' has empty NEW_SCRIPT. Skipping.")
                continue

            # Check if raw_new_script points to an existing text file
            if "\n" not in raw_new_script:
                potential_file = Path(raw_new_script)
                if not potential_file.is_file():
                    potential_file = script_to_change_dir / raw_new_script
                if potential_file.is_file():
                    try:
                        raw_new_script = potential_file.read_text(encoding="utf-8").strip()
                        print(f"  Loaded script text from file: {potential_file.name}")
                    except Exception as fe:
                        print(f"  Warning: Could not read script file '{potential_file}': {fe}")

            total_processed += 1
            lang, vtype = resolve_lang_and_type(script_id)
            print("\n" + "=" * 65)
            print(f"[{total_processed}] TARGET SCRIPT: {script_id} ({lang.capitalize()} | {vtype.upper()})")
            print("=" * 65)

            # Step 1: Access state JSON and set "script_generation": "pending" BEFORE doing the new script
            state = state_manager.get_script_state(script_id)
            if "status" not in state or not isinstance(state["status"], dict):
                state["status"] = {}

            previous_status = state["status"].get("script_generation", "pending")
            state["status"]["script_generation"] = "pending"

            # Reset downstream stages since the script content is changing
            for downstream in ["voice_generation", "image_generation", "thumbnail_generation", "video_assembly"]:
                state["status"][downstream] = "pending"

            # Ensure prompt_params exist
            if not state.get("prompt_params"):
                matching_prompt = next((p for p in queued_prompts if p.get("ID", "").upper() == script_id), None)
                if matching_prompt:
                    state["prompt_params"] = dict(matching_prompt)
                else:
                    state["prompt_params"] = {
                        "ID": script_id,
                        "TARGET_LANGUAGE": lang.capitalize(),
                        "VIDEO_TYPE": vtype.upper(),
                    }

            # Save state to disk FIRST with status "pending"
            state_manager.save_script_state(script_id, state)
            print(f"  ✓ Set status in state JSON: 'script_generation' = 'pending' (was '{previous_status}').")

            # Update status tracker manifest
            try:
                from core.status_tracker import get_status_tracker
                tracker = get_status_tracker(base_dir)
                tracker.update_script_stage_status(script_id, "script_generation", "pending")
                for downstream in ["voice_generation", "image_generation", "thumbnail_generation", "video_assembly"]:
                    tracker.update_script_stage_status(script_id, downstream, "pending")
            except Exception:
                pass

            # Step 2: Now do the new script using modify_video_script
            print(f"  🚀 Applying new script to {script_id}...")
            try:
                success = modify_video_script(
                    script_id=script_id,
                    raw_script_text=raw_new_script,
                    reset_downstream=True,
                    base_dir=base_dir,
                )
            except Exception as me:
                print(f"  ❌ Error applying script to {script_id}: {me}", file=sys.stderr)
                success = False

            if success:
                total_successful += 1
                try:
                    from core.status_tracker import get_status_tracker
                    tracker = get_status_tracker(base_dir)
                    tracker.update_script_stage_status(script_id, "script_generation", "done")
                except Exception:
                    pass
                print(f"  ✅ Script {script_id} successfully updated to new script!")
            else:
                total_failed += 1
                print(f"  ❌ Failed to update script {script_id}.", file=sys.stderr)

    print("\n" + "=" * 65)
    print(f"  SCRIPT CHANGE RUN COMPLETED: {total_successful}/{total_processed} succeeded, {total_failed} failed.")
    print("=" * 65 + "\n")

    return 0 if total_failed == 0 else 1

def main() -> int:
    parser = argparse.ArgumentParser(description="LingoVerse Shorts Script Generator")
    parser.add_argument("--script-id", type=str, default=None, help="Target specific script ID (e.g. EE01, FG02)")
    parser.add_argument("--pause-seconds", type=float, default=DEFAULT_PAUSE_SECONDS, help="Pause seconds between scripts")
    parser.add_argument("--auto", action="store_true", help="Auto-generate scripts without interactive terminal prompts")
    parser.add_argument("--script-input", type=str, default=None, help="Path to text file containing raw script to format")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if script is already generated")
    parser.add_argument(
        "--fun-facts",
        "--fun-facts-only",
        dest="fun_facts_only",
        action="store_true",
        help="Only generate scripts for Fun Facts videos (e.g. EF01, FF01, SF01, IF01)"
    )
    parser.add_argument(
        "--video-type",
        type=str,
        default=None,
        choices=["expression", "game", "roleplay", "fun_facts", "all"],
        help="Filter generation to specific video type (e.g. fun_facts)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=["all", "english", "french", "spanish", "italian"],
        help="Filter generation to specific language (default: all)"
    )
    parser.add_argument(
        "--change-from-csv",
        "--script-to-change",
        dest="change_from_csv",
        nargs="?",
        const="",
        default=None,
        help="Change script(s) from CSV containing 'ID' and 'NEW_SCRIPT' columns (optionally specify CSV path, otherwise checks input/csv/script_to_change/)"
    )
    args = parser.parse_args()

    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)
    
    try:
        print("Checking local LLM server connection...")
        require_services(llm=True)
        print("LLM server connection verified.")
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # CLI Direct Option: Change script(s) from CSV
    if args.change_from_csv is not None:
        print("\n[CLI Option] Change script(s) from CSV mode active.")
        csv_p = args.change_from_csv if args.change_from_csv.strip() else None
        return process_scripts_to_change_from_csv(base_dir=base_dir, csv_path=csv_p, auto=args.auto)

    # Production Mode Selection: Mass-produce, Specific Script ID, Number Range Group, Fun Facts, or Change from CSV
    from core.cli_prompt import prompt_production_mode, prompt_group_range, prompt_fun_facts_mode

    is_cli_fun_facts = args.fun_facts_only or (args.video_type and args.video_type.lower() == "fun_facts")

    if is_cli_fun_facts and not args.script_id:
        print("\n[CLI Option] Fun Facts mode active: targeting Fun Facts scripts only.")
        target_script_ids = None
        selected_mode = "fun_facts"
    else:
        target_script_ids, selected_mode = prompt_production_mode(
            stage_title="Part A: Video Scripts",
            asset_name="scripts",
            timeout=20.0,
            script_id_arg=args.script_id,
            auto=args.auto,
            require_existing_state=False,
            base_dir=base_dir,
            return_mode=True,
            allow_fun_facts_mode=True,
            allow_script_to_change_mode=True,
        )
        if is_cli_fun_facts:
            selected_mode = "fun_facts"

    if selected_mode == "script_to_change":
        return process_scripts_to_change_from_csv(base_dir=base_dir, csv_path=None, auto=args.auto)

    while True:
        # Load prompts from CSV and filter using Pipeline Status Tracker
        queued_prompts = load_ready_prompts_from_csv(base_dir)
        if not queued_prompts:
            print("No prompts found in input CSV queues.")
            return 0

        # Determine target video type filter
        target_video_type = None
        if selected_mode == "fun_facts" or args.fun_facts_only:
            target_video_type = "fun_facts"
        elif args.video_type and args.video_type.lower() != "all":
            target_video_type = args.video_type.lower()

        if target_video_type:
            if target_video_type == "fun_facts":
                queued_prompts = [
                    p for p in queued_prompts
                    if p.get("VIDEO_TYPE", "").upper() in ("FUN_FACTS", "FUNFACTS")
                    or (len(p.get("ID", "")) >= 2 and p["ID"][1].upper() == "F")
                ]
            else:
                queued_prompts = [
                    p for p in queued_prompts
                    if p.get("VIDEO_TYPE", "").upper() == target_video_type.upper()
                ]

        # Filter by language if specified via CLI
        if args.language and args.language.lower() != "all":
            queued_prompts = [
                p for p in queued_prompts
                if p.get("TARGET_LANGUAGE", "").lower() == args.language.lower()
            ]

        if target_script_ids:
            target_set = set(target_script_ids)
            prompts_to_process = [p for p in queued_prompts if p["ID"] in target_set]
            prompts_to_process.sort(key=lambda p: target_script_ids.index(p["ID"]) if p["ID"] in target_script_ids else 9999)
            if not prompts_to_process:
                print(f"Error: None of the specified script IDs {target_script_ids} were found in any input CSV queue.", file=sys.stderr)
                if selected_mode == "group_range" and not args.auto:
                    try:
                        retry_more = input("\nWould you like to try another number range? [y/N]: ").strip().lower()
                    except (KeyboardInterrupt, EOFError):
                        return 0
                    if retry_more in ("y", "yes"):
                        target_script_ids = prompt_group_range(require_existing_state=False, base_dir=base_dir)
                        if target_script_ids:
                            continue
                    return 0
                elif selected_mode == "fun_facts" and not args.auto:
                    try:
                        retry_more = input("\nWould you like to try another Fun Facts selection? [y/N]: ").strip().lower()
                    except (KeyboardInterrupt, EOFError):
                        return 0
                    if retry_more in ("y", "yes"):
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=False, base_dir=base_dir)
                        if target_script_ids:
                            continue
                    return 0
                return 1
        else:
            try:
                from core.status_tracker import get_status_tracker
                tracker = get_status_tracker(base_dir)
                pending_rows = tracker.get_pending_scripts(
                    "script_generation",
                    video_type=target_video_type,
                    language=args.language if args.language and args.language.lower() != "all" else None,
                    force=args.force
                )
                pending_ids = {r["ID"] for r in pending_rows}
                prompts_to_process = [p for p in queued_prompts if p["ID"] in pending_ids]
            except Exception:
                prompts_to_process = queued_prompts

        if not prompts_to_process:
            type_label = f" ({target_video_type.upper()})" if target_video_type else ""
            print(f"All {len(queued_prompts)} video scripts{type_label} across all queues have already been generated! (0 pending)")
            if selected_mode in ("group_range", "fun_facts") and not args.auto:
                try:
                    create_more = input("\nDo you want to select another group or scope of scripts? [y/N]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return 0
                if create_more in ("y", "yes"):
                    if selected_mode == "fun_facts":
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=False, base_dir=base_dir)
                    else:
                        target_script_ids = prompt_group_range(require_existing_state=False, base_dir=base_dir)
                    if target_script_ids:
                        continue
            return 0

        total = len(prompts_to_process)
        if target_script_ids:
            print(f"Processing {len(prompts_to_process)} target script(s): {', '.join([p['ID'] for p in prompts_to_process])}")
        else:
            print(f"Found {total} pending prompt(s) to generate out of {len(queued_prompts)} total library prompts.")

        for i, params in enumerate(prompts_to_process, start=1):
            script_id = params["ID"]
            if handle_prompt(state_manager, script_id, params, i, total, auto=args.auto, script_input=args.script_input, force=args.force) != 0:
                return 1
            if i < total:
                time.sleep(args.pause_seconds)

        print(f"\n[Completed] Finished generating {total} script(s)!")

        # If in group_range or fun_facts mode, ask if the user wants to create more scripts
        if selected_mode in ("group_range", "fun_facts") and not args.auto:
            try:
                create_more = input("\nDo you want to create more scripts? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nFinished script generation session.")
                break

            if create_more in ("y", "yes"):
                if selected_mode == "fun_facts":
                    target_script_ids = prompt_fun_facts_mode(require_existing_state=False, base_dir=base_dir)
                else:
                    target_script_ids = prompt_group_range(require_existing_state=False, base_dir=base_dir)
                if target_script_ids:
                    continue
                else:
                    break
            else:
                print("\nFinished script generation session.")
                break
        else:
            break

    return 0

if __name__ == "__main__":
    sys.exit(main())