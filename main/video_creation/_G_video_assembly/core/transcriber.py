from __future__ import annotations

import ctypes
import os
from pathlib import Path


def _cuda_available() -> bool:
    try:
        # pyrefly: ignore [missing-import]
        import ctranslate2

        if ctranslate2.get_cuda_device_count() <= 0:
            return False
        if os.name == "nt":
            ctypes.WinDLL("cublas64_12.dll")
        return True
    except Exception:
        return False


class Transcriber:
    def __init__(self, model_size: str = "base", device: str = "auto"):
        try:
            # pyrefly: ignore [missing-import]
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "faster-whisper is required for audio transcription. "
                "Please install it using: pip install faster-whisper"
            ) from exc

        self._whisper_model_cls = WhisperModel
        self.model_size = model_size
        requested = os.getenv("WHISPER_DEVICE", device).strip().lower() or "auto"

        if requested in ("auto", "cuda") and _cuda_available():
            try:
                self.model = WhisperModel(model_size, device="cuda", compute_type="float16")
                self.device = "cuda"
                return
            except Exception as exc:
                print(f"Notice: CUDA Whisper unavailable ({exc}); falling back to CPU int8.")

        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.device = "cpu"

    def transcribe(self, audio_path: Path, language: str = None, initial_prompt: str = None):
        print(f"Transcribing {audio_path.name}...")
        kwargs = {"word_timestamps": True}
        if language:
            kwargs["language"] = language
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt

        def _collect_words() -> list[dict]:
            segments, _info = self.model.transcribe(str(audio_path), **kwargs)
            collected = []
            for segment in segments:
                for word in segment.words:
                    collected.append({
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end,
                    })
            return collected

        try:
            return _collect_words()
        except Exception as exc:
            if self.device != "cuda":
                raise
            print(f"Notice: CUDA Whisper transcription failed ({exc}); reloading on CPU int8...")
            self.model = self._whisper_model_cls(self.model_size, device="cpu", compute_type="int8")
            self.device = "cpu"
            return _collect_words()
