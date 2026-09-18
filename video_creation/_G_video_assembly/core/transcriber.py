# pyrefly: ignore [missing-import]
from faster_whisper import WhisperModel
from pathlib import Path

class Transcriber:
    def __init__(self, model_size="base"):
        # Run on CPU with int8 if CUDA is not available
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: Path):
        print(f"Transcribing {audio_path.name}...")
        segments, info = self.model.transcribe(str(audio_path), word_timestamps=True)
        
        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })
        return words
