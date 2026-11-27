"""
webui/jobs/adapters/voice.py — Stage B (Voice Generation) adapter.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    COMFY_API_URL,
    COMFY_INPUT_DIR,
    COMFY_OUTPUT_DIR,
    OPEN_SWARA_DIR,
    VOICE_WORKFLOW_PATH,
)
from core.llama_manager import ensure_llama_stopped, get_llama_manager
from core.state_manager import StateManager
from video_creation._B_voice_generation.core.comfy_client import ComfyClient
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
from video_creation._B_voice_generation.voice.common.orchestrator import synthesize_script_voice
from webui.jobs.adapters.base import BaseStageAdapter


class VoiceAdapter(BaseStageAdapter):
    """Executes Stage B multi-character voice generation."""

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
        explicit_accent = options.get("accent") or None
        engine_mode = options.get("voice_engine") or None
        recast = bool(options.get("recast", False))
        requested_provider = options.get("voice_provider") or "auto"
        elevenlabs_model = options.get("elevenlabs_model") or None

        from config import resolve_script_video_type
        from video_creation._B_voice_generation.elevenlabs.tags import resolve_voice_provider

        total = len(script_ids)
        success_count = 0
        failed_ids = []

        # Determine per-script provider upfront so ElevenLabs-only batches never stop Llama or require ComfyUI
        provider_by_id: Dict[str, str] = {}
        for sid in script_ids:
            if sm.script_exists(sid):
                vtype = resolve_script_video_type(sm.get_script_state(sid))
                provider_by_id[sid] = resolve_voice_provider(vtype, requested_provider=requested_provider)
            else:
                provider_by_id[sid] = "local"

        needs_local = any(p == "local" for p in provider_by_id.values())
        needs_elevenlabs = any(p == "elevenlabs" for p in provider_by_id.values())

        voice_manager = None
        comfy_client = None
        if needs_local:
            emit_log("Ensuring LLM server is stopped to release VRAM for local Qwen3-TTS synthesis...")
            ensure_llama_stopped()
            emit_log(f"Initializing local Qwen3-TTS voice clients for batch ({total} script(s))...")
            voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)
            comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
            comfy_client.check_cancelled = check_cancelled
        if needs_elevenlabs:
            emit_log(
                f"ElevenLabs provider active ({elevenlabs_model or 'eleven_v3'}) for "
                f"{sum(1 for p in provider_by_id.values() if p == 'elevenlabs')}/{total} script(s) — zero GPU VRAM required."
            )

        # In mass-production queues, stably group local scripts by saved primary voice so consecutive scripts
        # sharing a narrator reuse ComfyUI's cached LoadAudio + VoiceClonePrompt in VRAM.
        ordered_ids = list(script_ids)
        if len(ordered_ids) > 1 and not recast:
            def _voice_cache_key(sid: str) -> tuple:
                prov = provider_by_id.get(sid, "local")
                if prov != "local" or not sm.script_exists(sid):
                    return (0 if prov == "elevenlabs" else 1, "")
                st = sm.get_script_state(sid) or {}
                sv = (st.get("content_metadata") or {}).get("speakers_voice") or {}
                return (1, str(sv.get("Narrator") or next(iter(sv.values()), "") or ""))

            ordered_ids.sort(key=_voice_cache_key)

        for idx, script_id in enumerate(ordered_ids, start=1):
            if check_cancelled():
                emit_log(f"Job cancelled by user at script {script_id}.")
                break

            emit_progress(idx - 1, total, script_id)

            if not sm.script_exists(script_id):
                emit_log(f"[{script_id}] ERROR: Script state does not exist.")
                failed_ids.append(script_id)
                continue

            script_data = sm.get_script_state(script_id)
            status = script_data.get("status", {})
            if not force and status.get("voice_generation") == "done":
                emit_log(f"[{script_id}] Voice already generated — skipping.")
                success_count += 1
                continue

            script_force = force or (status.get("voice_generation") == "pending")
            script_provider = provider_by_id.get(script_id, "local")
            max_attempts = int(options.get("max_attempts", 2 if script_provider == "elevenlabs" else 3))
            voice_succeeded = False
            last_err = ""

            for attempt in range(1, max_attempts + 1):
                if check_cancelled():
                    emit_log(f"Job cancelled by user at script {script_id}.")
                    break

                try:
                    provider_tag = f"ElevenLabs ({elevenlabs_model or 'eleven_v3'})" if script_provider == "elevenlabs" else "Local Qwen3-TTS"
                    emit_log(f"[{script_id}] Synthesizing audio via {provider_tag} (attempt {attempt}/{max_attempts})...")
                    t0 = time.time()
                    existing_v = script_data.get("content_metadata", {}).get("speakers_voice", {}) or {}
                    exclude_set = {str(v) for v in existing_v.values() if v} if recast else None
                    ok = synthesize_script_voice(
                        script_data=script_data,
                        state_manager=sm,
                        comfy_client=comfy_client,
                        voice_manager=voice_manager,
                        force=script_force,
                        base_dir=self.base_dir,
                        candidates=options.get("candidates"),
                        exclude_voices=exclude_set,
                        force_fresh_cast=recast,
                        explicit_accent=explicit_accent,
                        engine_mode=engine_mode,
                        mark_video_assembly_pending=recast,
                        voice_provider=script_provider,
                        elevenlabs_model=elevenlabs_model,
                        check_cancelled=check_cancelled,
                    )
                    dur = time.time() - t0
                    if ok:
                        refreshed_meta = (script_data.get("content_metadata") or {}).get("voice_profile_meta") or {}
                        cr_note = f" | {refreshed_meta['credits_used']} credits" if refreshed_meta.get("credits_used") else ""
                        emit_log(f"[{script_id}] ✓ Voice synthesis ({provider_tag}) completed in {dur:.1f}s{cr_note}.")
                        success_count += 1
                        voice_succeeded = True
                        break
                    else:
                        last_err = f"Process returned false after {dur:.1f}s"
                        emit_log(f"[{script_id}] Voice attempt {attempt}/{max_attempts} failed.")
                        if attempt < max_attempts and not check_cancelled():
                            time.sleep(2.0)
                except Exception as exc:
                    last_err = str(exc)
                    emit_log(f"[{script_id}] Voice attempt {attempt}/{max_attempts} exception: {last_err}")
                    if attempt < max_attempts:
                        time.sleep(2.0)

            if not voice_succeeded and not check_cancelled():
                emit_log(f"[{script_id}] ERROR: Voice synthesis failed after {max_attempts} attempts: {last_err}")
                failed_ids.append(script_id)

        emit_progress(total, total, None)
        emit_log(f"Voice job finished: {success_count}/{total} successful.")
        return {
            "success_count": success_count,
            "failed_ids": failed_ids,
            "total": total,
        }

