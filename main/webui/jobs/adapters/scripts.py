"""
webui/jobs/adapters/scripts.py — Stage A (Script Generation) adapter.
Integrates the modular domain script engines directly into the WebUI job execution engine.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

MAIN_DIR = Path(__file__).resolve().parents[3]
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from config import BASE_DIR

from core.llama_manager import get_llama_manager
from core.state_manager import StateManager, resolve_lang_and_type
from video_creation._A_video_scripts.api import generate_script_for_payload
from video_creation._A_video_scripts.registry import ScriptEngineRegistry
from webui.jobs.adapters.base import BaseStageAdapter

logger = logging.getLogger("webui.adapters.scripts")


def _lookup_csv_row_for_script(script_id: str, base_dir: Path) -> Dict[str, str]:
    """Finds the source CSV row for a script across all ready prompt CSV files."""
    sid = str(script_id).strip().upper()
    csv_dir = base_dir / "input" / "csv"
    if not csv_dir.exists():
        return {}
    for f in csv_dir.rglob("*READY_PROMPTS_*.csv"):
        try:
            with open(f, mode="r", encoding="utf-8-sig", errors="ignore") as fp:
                for row in csv.DictReader(fp):
                    if (row.get("ID") or "").strip().upper() == sid:
                        return {k.strip(): (v or "").strip() for k, v in row.items() if k}
        except Exception:
            pass
    return {}


class ScriptsAdapter(BaseStageAdapter):
    """Executes Stage A script generation for single or batch scripts via the WebUI."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or BASE_DIR

    def run(
        self,
        script_ids: List[str],
        options: Dict[str, Any],
        emit_log: Callable[[str], None],
        emit_progress: Callable[[int, int, str], None],
        check_cancelled: Callable[[], bool],
    ) -> Dict[str, Any]:
        sm = StateManager(base_dir=self.base_dir)
        force = options.get("force", False)
        max_retries = int(options.get("max_retries", 2))

        total = len(script_ids)
        success_count = 0
        failed_ids = []

        # 1. Ensure LLM server is active and reachable
        emit_log(f"Preparing LLM session for {total} script generation task(s)...")
        lm = get_llama_manager()
        try:
            if not lm.is_reachable():
                emit_log("LLM server is not reachable. Attempting on-demand initialization...")
                lm.start()
                time.sleep(2.0)
        except Exception as exc:
            emit_log(f"Warning checking LLM service: {exc}")

        emit_log(f"Starting script generation across {total} script(s)...")

        for idx, script_id in enumerate(script_ids, start=1):
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            emit_progress(idx, total, script_id)
            emit_log(f"[{idx}/{total}] Processing script '{script_id}'...")

            state = sm.get_script_state(script_id)
            curr_status = state.get("status", {}).get("script_generation")

            if curr_status == "done" and not force:
                emit_log(f"[{script_id}] Script already marked as done. Skipping (use force=True to regenerate).")
                success_count += 1
                continue

            # Resolve Language and Video Type
            lang, vtype = resolve_lang_and_type(script_id, state)
            prompt_params = state.get("prompt_params") or {}
            content_meta = state.get("content_metadata") or {}
            raw_meta = state.get("metadata") or {}

            # Look up source CSV row for full contextual fidelity
            csv_row = _lookup_csv_row_for_script(script_id, self.base_dir)

            # Authoritative Target Expression Resolution:
            # Strictly discard any candidate that equals script_id (e.g. "EE01" or "SG02")
            candidates = [
                options.get("target_expression"),
                options.get("expression"),
                csv_row.get("EXPRESSION"),
                csv_row.get("TOPIC"),
                content_meta.get("target_expression"),
                content_meta.get("topic"),
                prompt_params.get("EXPRESSION"),
                prompt_params.get("expression"),
                prompt_params.get("TARGET_EXPRESSION"),
                prompt_params.get("target_expression"),
                prompt_params.get("TOPIC"),
                prompt_params.get("topic"),
            ]
            target_expression = ""
            for c in candidates:
                if c and isinstance(c, str):
                    c_clean = c.strip()
                    if c_clean and c_clean.upper() != script_id.strip().upper():
                        target_expression = c_clean
                        break

            # If target_expression is empty or accidentally contains a full scenario paragraph (>60 chars) for roleplay/game,
            # resolve the canonical idiom from the matching expression script (e.g. FR01 -> FE01, IG01 -> IE01)
            # strictly for roleplay and game (never overwrite independent fun_facts topics!)
            if vtype in ("roleplay", "game") and (not target_expression or len(target_expression) > 60) and len(script_id) >= 2:
                matching_exp_id = script_id[0] + "E" + script_id[2:]
                exp_row = _lookup_csv_row_for_script(matching_exp_id, self.base_dir)
                if exp_row.get("EXPRESSION"):
                    target_expression = exp_row.get("EXPRESSION").strip()
                elif exp_row.get("TOPIC"):
                    target_expression = exp_row.get("TOPIC").strip()

            # If still empty, check if metadata TITLE has an expression
            if not target_expression and raw_meta.get("TITLE"):
                target_expression = str(raw_meta.get("TITLE", "")).split("|")[0].strip()

            # Rich contextual columns from CSV / prompt_params
            scenario = (
                options.get("scenario")
                or csv_row.get("ROLEPLAY_SCENARIO")
                or csv_row.get("SCENARIO")
                or prompt_params.get("ROLEPLAY_SCENARIO")
                or prompt_params.get("SCENARIO")
                or prompt_params.get("scenario")
                or ""
            )
            context = (
                options.get("context")
                or csv_row.get("CONTEXT")
                or prompt_params.get("CONTEXT")
                or prompt_params.get("context")
                or content_meta.get("base_setting")
                or ""
            )
            angle = (
                options.get("angle")
                or csv_row.get("ANGLE")
                or csv_row.get("HOOK_ANGLE")
                or prompt_params.get("ANGLE")
                or prompt_params.get("angle")
                or prompt_params.get("HOOK_ANGLE")
                or prompt_params.get("hook_angle")
                or ""
            )
            subject = (
                options.get("subject")
                or csv_row.get("SUBJECT")
                or prompt_params.get("SUBJECT")
                or prompt_params.get("subject")
                or content_meta.get("category")
                or ""
            )
            lexical_field = (
                options.get("lexical_field")
                or csv_row.get("LEXICAL_FIELD")
                or prompt_params.get("LEXICAL_FIELD")
                or prompt_params.get("lexical_field")
                or content_meta.get("lexical_field")
                or ""
            )
            emotional_trigger = (
                csv_row.get("EMOTIONAL_TRIGGER")
                or prompt_params.get("EMOTIONAL_TRIGGER")
                or prompt_params.get("emotional_trigger")
                or content_meta.get("emotion")
                or ""
            )
            special_treatment = (
                options.get("special_treatment")
                or csv_row.get("SPECIAL_TREATMENT")
                or prompt_params.get("SPECIAL_TREATMENT")
                or prompt_params.get("special_treatment")
                or ""
            )
            fact_details = (
                options.get("fact_details")
                or csv_row.get("FACT_DETAILS")
                or prompt_params.get("FACT_DETAILS")
                or prompt_params.get("fact_details")
                or ""
            )
            pillar = (
                csv_row.get("PILLAR")
                or prompt_params.get("PILLAR")
                or prompt_params.get("pillar")
                or ""
            )
            format_type = (
                csv_row.get("FORMAT")
                or prompt_params.get("FORMAT")
                or prompt_params.get("format")
                or ""
            )

            # Construct comprehensive input payload
            payload = {
                "SCRIPT_ID": script_id,
                "script_id": script_id,
                "LANGUAGE": lang,
                "language": lang,
                "TYPE": vtype,
                "type": vtype,
                "TARGET_EXPRESSION": target_expression,
                "target_expression": target_expression,
                "EXPRESSION": target_expression,
                "expression": target_expression,
                "SCENARIO": scenario,
                "scenario": scenario,
                "ROLEPLAY_SCENARIO": scenario,
                "roleplay_scenario": scenario,
                "CONTEXT": context,
                "context": context,
                "ANGLE": angle,
                "angle": angle,
                "HOOK_ANGLE": angle,
                "hook_angle": angle,
                "SUBJECT": subject,
                "subject": subject,
                "LEXICAL_FIELD": lexical_field,
                "lexical_field": lexical_field,
                "EMOTIONAL_TRIGGER": emotional_trigger,
                "emotional_trigger": emotional_trigger,
                "SPECIAL_TREATMENT": special_treatment,
                "special_treatment": special_treatment,
                "FACT_DETAILS": fact_details,
                "fact_details": fact_details,
                "PILLAR": pillar,
                "pillar": pillar,
                "FORMAT": format_type,
                "format": format_type,
                "TOPIC": target_expression or prompt_params.get("TOPIC") or "",
                "topic": target_expression or prompt_params.get("topic") or "",
            }

            # Check if domain engine is registered
            engine = ScriptEngineRegistry.get_engine(script_id) or ScriptEngineRegistry.get_engine(vtype)
            if not engine:
                err_msg = f"[{script_id}] No domain engine registered for type='{vtype}'."
                emit_log(f"ERROR: {err_msg}")
                failed_ids.append(script_id)
                continue

            emit_log(f"[{script_id}] Generating using dedicated domain engine: '{engine.script_type}'")

            # Stream token buffer reporter
            token_count = [0]
            last_report = [time.time()]

            def on_token_received(token: str) -> None:
                token_count[0] += 1
                now = time.time()
                if now - last_report[0] >= 3.0:
                    emit_log(f"  [{script_id}] LLM generating... ({token_count[0]} tokens streamed)")
                    last_report[0] = now

            try:
                result = generate_script_for_payload(
                    payload,
                    on_token=on_token_received,
                    max_retries=max_retries,
                )

                if not result.is_valid:
                    err = f"Validation failed after retries: {'; '.join(result.validation_errors)}"
                    emit_log(f"[{script_id}] ERROR: {err}")
                    failed_ids.append(script_id)
                    continue

                # Save generated script and chalkboard into state
                script_body = result.script.get("script") if isinstance(result.script.get("script"), dict) else result.script
                content_meta = state.get("content_metadata") or {}
                content_meta["script"] = script_body
                if target_expression:
                    content_meta["target_expression"] = target_expression
                    content_meta["topic"] = target_expression

                if "chalkboard_exercise" in result.script:
                    content_meta["chalkboard_exercise"] = result.script["chalkboard_exercise"]

                state["prompt_params"] = payload
                state["script_text"] = json.dumps(script_body, indent=2, ensure_ascii=False)
                state["content_metadata"] = content_meta
                state["status"]["script_generation"] = "done"

                # If script was regenerated, invalidate downstream voice so it stays in sync!
                state["status"]["voice_generation"] = "pending"

                sm.save_script_state(script_id, state)
                try:
                    from webui.routers.scripts import _get_indexed_scripts
                    _get_indexed_scripts(force_refresh=True)
                except Exception:
                    pass
                success_count += 1
                emit_log(
                    f"[{script_id}] Successfully generated script ({result.spoken_words} spoken words, "
                    f"{result.retry_count} retries)."
                )

            except Exception as exc:
                emit_log(f"[{script_id}] Generation failed with exception: {exc}")
                logger.error(f"Generation error on {script_id}: {exc}", exc_info=True)
                failed_ids.append(script_id)

        emit_log(f"Script generation finished: {success_count} succeeded, {len(failed_ids)} failed.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }
