"""
elevenlabs/client.py — Standalone REST client for ElevenLabs TTS & account subscription status.

Strictly isolated from ComfyUI / Qwen3-TTS code. Never logs or exposes the API key.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from .tags import DEFAULT_ELEVENLABS_MODEL_ID, SUPPORTED_ELEVENLABS_MODELS, normalize_elevenlabs_model

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


def resolve_elevenlabs_api_key(explicit_key: Optional[str] = None) -> str:
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    env_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        from config import settings
        return str(getattr(settings, "ELEVENLABS_API_KEY", "") or "").strip()
    except Exception:
        return ""


def _decode_mp3_bytes_to_wav(audio_bytes: bytes, dest_wav_path: Path) -> Path:
    """Writes MP3 response bytes to a temporary file and converts cleanly to 44.1kHz mono/stereo WAV."""
    dest_wav_path = Path(dest_wav_path)
    dest_wav_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp3 = dest_wav_path.with_suffix(".tmp.mp3")
    tmp_mp3.write_bytes(audio_bytes)
    try:
        # Try soundfile directly first (libsndfile >= 1.1 supports MP3 natively)
        try:
            # pyrefly: ignore[missing-import]
            import soundfile as sf
            data, sr = sf.read(str(tmp_mp3), dtype="float32")
            sf.write(str(dest_wav_path), data, sr, subtype="PCM_16")
            return dest_wav_path
        except Exception:
            pass

        # Fallback: ffmpeg (already present in workspace or PATH)
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            cand = Path(__file__).resolve().parents[2] / "_G_video_assembly" / "ffmpeg.exe"
            if cand.exists():
                ffmpeg_bin = str(cand)
        if not ffmpeg_bin:
            raise RuntimeError("Neither soundfile MP3 decoding nor ffmpeg is available to decode ElevenLabs audio.")

        proc = subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(tmp_mp3), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dest_wav_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not dest_wav_path.exists():
            raise RuntimeError(f"ffmpeg failed decoding ElevenLabs audio: {proc.stderr[-300:]}")
        return dest_wav_path
    finally:
        try:
            tmp_mp3.unlink(missing_ok=True)
        except Exception:
            pass


class ElevenLabsClient:
    """Lightweight REST client for ElevenLabs Text-to-Speech and subscription credit queries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = ELEVENLABS_API_BASE,
        timeout_seconds: int = 90,
    ):
        self._api_key = resolve_elevenlabs_api_key(api_key)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.check_cancelled: Optional[Callable[[], bool]] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self, accept: str = "application/json") -> Dict[str, str]:
        if not self._api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is not configured. Please enter your ElevenLabs API key in the WebUI or main/.env."
            )
        return {
            "xi-api-key": self._api_key,
            "Accept": accept,
            "Content-Type": "application/json",
        }

    def _check_job_cancelled(self) -> None:
        if self.check_cancelled is not None and self.check_cancelled():
            raise InterruptedError("ElevenLabs voice generation cancelled.")

    def get_subscription_info(self) -> Dict[str, Any]:
        """Queries live subscription tier and remaining character/credit quota."""
        resp = requests.get(
            f"{self.base_url}/user/subscription",
            headers=self._headers("application/json"),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        char_count = int(data.get("character_count") or 0)
        char_limit = int(data.get("character_limit") or 0)
        return {
            "tier": str(data.get("tier") or "unknown"),
            "status": str(data.get("status") or "active"),
            "character_count": char_count,
            "character_limit": char_limit,
            "remaining_credits": max(0, char_limit - char_count),
            "next_reset_unix": data.get("next_character_count_reset_unix"),
        }

    def list_voices(self) -> List[Dict[str, Any]]:
        """Lists voices available in the authenticated ElevenLabs account."""
        resp = requests.get(
            f"{self.base_url}/voices",
            headers=self._headers("application/json"),
            timeout=20,
        )
        resp.raise_for_status()
        return list((resp.json() or {}).get("voices") or [])

    def synthesize_segment(
        self,
        *,
        voice_id: str,
        text: str,
        dest_path: Path,
        model_id: str = DEFAULT_ELEVENLABS_MODEL_ID,
        language_code: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
        output_format: str = "mp3_44100_128",
        max_retries: int = 3,
    ) -> Tuple[Path, int]:
        """Synthesizes one speech segment via `POST /v1/text-to-speech/{voice_id}` and saves as WAV.

        Returns `(saved_wav_path, credits_used)`.
        """
        self._check_job_cancelled()
        norm_model = normalize_elevenlabs_model(model_id)
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        params = {"output_format": output_format}

        body: Dict[str, Any] = {
            "text": text,
            "model_id": norm_model,
        }
        if voice_settings:
            body["voice_settings"] = voice_settings
        if language_code and norm_model != "eleven_multilingual_v2":
            # language_code is supported by eleven_v3 and eleven_flash_v2_5 (Multilingual v2 auto-detects)
            body["language_code"] = language_code
        if previous_text and norm_model != "eleven_v3":
            body["previous_text"] = previous_text[-300:]
        if next_text and norm_model != "eleven_v3":
            body["next_text"] = next_text[:300]

        last_exc: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            self._check_job_cancelled()
            try:
                resp = requests.post(
                    url,
                    params=params,
                    headers=self._headers("audio/mpeg"),
                    json=body,
                    timeout=self.timeout_seconds,
                )
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    wait_sec = min(10.0, 1.5 * attempt)
                    time.sleep(wait_sec)
                    continue
                if resp.status_code >= 400:
                    detail = ""
                    try:
                        err_json = resp.json()
                        detail = str(err_json.get("detail") or err_json)
                    except Exception:
                        detail = resp.text[:300]
                    raise RuntimeError(f"ElevenLabs API error HTTP {resp.status_code}: {detail}")

                audio_bytes = resp.content
                if not audio_bytes:
                    raise RuntimeError("ElevenLabs returned empty audio payload.")

                saved_path = _decode_mp3_bytes_to_wav(audio_bytes, Path(dest_path))

                header_cost = resp.headers.get("character-cost")
                if header_cost and str(header_cost).isdigit():
                    credits_used = int(header_cost)
                else:
                    mult = float(SUPPORTED_ELEVENLABS_MODELS[norm_model]["credits_per_char"])
                    credits_used = int(round(len(text) * mult))

                return saved_path, credits_used
            except InterruptedError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)

        raise RuntimeError(f"ElevenLabs synthesis failed after {max_retries} attempts: {last_exc}")
