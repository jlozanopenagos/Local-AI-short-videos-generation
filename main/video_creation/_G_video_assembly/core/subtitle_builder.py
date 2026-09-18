from pathlib import Path
from typing import List, Dict

class SubtitleBuilder:
    def build_ass(self, words: List[Dict], output_path: Path, video_width=576, video_height=1024, suppress_windows=None):
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

        for w in words:
            # If word start falls into any suppressed window (e.g. GAME challenge scene), omit it
            if suppress_windows:
                if any(start <= w["start"] < end for start, end in suppress_windows):
                    continue

            start_str = format_time(w["start"])
            end_str = format_time(w["end"])
            # The text is just the word itself, capitalized
            text = w["word"].upper()
            # 5 is center-center alignment
            line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n"
            lines.append(line)
            
        with output_path.open("w", encoding="utf-8") as f:
            f.writelines(lines)
        return output_path

