import json
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional

def trim_trailing_silence(data: np.ndarray, sr: int, threshold: float = 0.01, pad_seconds: float = 0.15) -> np.ndarray:
    """Trims trailing dead silence from generated TTS segments to keep pacing tight."""
    if len(data) == 0:
        return data
    abs_data = np.abs(data)
    if len(abs_data.shape) > 1:
        abs_data = np.max(abs_data, axis=1)
    non_silent = np.where(abs_data > threshold)[0]
    if len(non_silent) > 0:
        pad_samples = int(pad_seconds * sr)
        end_idx = min(len(data), non_silent[-1] + pad_samples)
        return data[:end_idx]
    return data

def concatenate_audios(
    segments_metadata: List[Dict],
    output_path: Path,
    pauses: Optional[Dict[str, float]] = None
) -> Optional[Path]:
    """Concatenates multiple audio segment files into a single master audio file.
    Inserts silent pauses based on transition types (section changes, speaker changes, or paragraph breaks).
    
    segments_metadata format:
    [
        {"path": Path, "section": str, "speaker": str},
        ...
    ]
    """
    if not segments_metadata:
        print("No segments provided for audio concatenation.")
        return None

    if not pauses:
        pauses = {
            "section_gap": 0.40,   # Snappy transition between sections for YouTube Shorts
            "dialogue_gap": 0.20,  # Natural, quick conversational turn
            "paragraph_gap": 0.30, # Crisp paragraph pause
            "pressure_gap": 2.20   # Suspenseful thinking/countdown pause for quiz games
        }

    combined_data = []
    master_samplerate = None
    num_channels = 1

    current_sample = 0
    section_timings = {}

    for i, seg in enumerate(segments_metadata):
        path = Path(seg["path"])
        if not path.exists():
            print(f"Warning: Audio file {path} not found. Skipping.")
            continue

        data, sr = sf.read(str(path))
        data = trim_trailing_silence(data, sr)
        
        if master_samplerate is None:
            master_samplerate = sr
            if len(data.shape) > 1:
                num_channels = data.shape[1]
            else:
                num_channels = 1

        if sr != master_samplerate:
            print(f"Warning: Samplerate mismatch for {path.name} ({sr} vs master {master_samplerate}).")

        # Insert pause if this is not the first segment
        if i > 0 and combined_data:
            prev_seg = segments_metadata[i - 1]
            pause_duration = 0.0

            if prev_seg["section"] == "pressure" and seg["section"] == "answer":
                pause_duration = pauses.get("pressure_gap", 2.20)
            elif prev_seg["section"] != seg["section"]:
                pause_duration = pauses.get("section_gap", 0.40)
            elif prev_seg["speaker"] != seg["speaker"]:
                pause_duration = pauses.get("dialogue_gap", 0.20)
            else:
                pause_duration = pauses.get("paragraph_gap", 0.30)

            if pause_duration > 0:
                num_pause_samples = int(pause_duration * master_samplerate)
                if num_channels > 1:
                    silence = np.zeros((num_pause_samples, num_channels), dtype=data.dtype)
                else:
                    silence = np.zeros(num_pause_samples, dtype=data.dtype)
                combined_data.append(silence)
                current_sample += num_pause_samples

        section = seg["section"]
        if section not in section_timings:
            section_timings[section] = {"start": current_sample / master_samplerate, "end": 0.0}

        combined_data.append(data)
        current_sample += len(data)
        section_timings[section]["end"] = current_sample / master_samplerate

    if combined_data:
        merged = np.concatenate(combined_data, axis=0)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), merged, master_samplerate)
        print(f"Merged audio successfully saved to: {output_path}")
        
        # Save timings map
        timings_path = output_path.parent / "timings.json"
        with timings_path.open("w", encoding="utf-8") as f:
            json.dump(section_timings, f, indent=2)
            
        return output_path
    
    return None
