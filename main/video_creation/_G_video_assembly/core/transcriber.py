from pathlib import Path


class Transcriber:
    def __init__(self, model_size="base"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "faster-whisper is required for audio transcription. "
                "Please install it using: pip install faster-whisper"
            ) from exc
        # Run on CPU with int8 if CUDA is not available
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: Path, language: str = None, initial_prompt: str = None):
        print(f"Transcribing {audio_path.name}...")
        kwargs = {"word_timestamps": True}
        if language:
            kwargs["language"] = language
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt
        segments, info = self.model.transcribe(str(audio_path), **kwargs)
        
        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })
        return words
