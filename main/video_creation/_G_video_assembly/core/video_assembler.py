# pyrefly: ignore [missing-import]
import ffmpeg
import json
from pathlib import Path

class VideoAssembler:
    def assemble(self, script_id: str, timings_path: Path, image_dir: Path, audio_path: Path, ass_path: Path, output_path: Path, bgm_path: Path = None, watermark_path: Path = None, opening_path: Path = None, closure_path: Path = None):
        if opening_path:
            opening_path = Path(opening_path)
        if closure_path:
            closure_path = Path(closure_path)

        with timings_path.open("r", encoding="utf-8") as f:
            timings = json.load(f)
            
        # Sort sections by start time
        sorted_sections = sorted(timings.items(), key=lambda x: x[1]["start"])
        
        # Collect available images
        available_sections = []
        for section, timing in sorted_sections:
            img_name = f"script_{script_id}_{section}.png"
            img_path = image_dir / img_name
            
            # Fallback for old formatting just in case
            if not img_path.exists():
                img_name_alt = f"script_{script_id}_{section.replace(' ', '_')}.png"
                if (image_dir / img_name_alt).exists():
                    img_path = image_dir / img_name_alt

            if img_path.exists():
                available_sections.append({"path": img_path, "start": timing["start"]})
            else:
                print(f"Warning: Missing image for section '{section}': {img_path}")
                
        if not available_sections:
            print("Error: No images found to assemble video.")
            return False

        print("Building FFMPEG filter graph for Ken Burns effect...")
        video_streams = []
        for i in range(len(available_sections)):
            current = available_sections[i]
            if i < len(available_sections) - 1:
                next_item = available_sections[i+1]
                current_start = current["start"] if i > 0 else 0.0
                duration = next_item["start"] - current_start
            else:
                try:
                    # ffprobe resolution (located in _G_video_assembly/ffprobe.exe or PATH)
                    local_ffprobe = (Path(__file__).parent.parent / "ffprobe.exe").resolve()
                    if local_ffprobe.exists():
                        ffprobe_path = local_ffprobe.as_posix()
                    else:
                        ffprobe_path = "ffprobe"

                    probe = ffmpeg.probe(audio_path.as_posix(), cmd=ffprobe_path)
                    total_dur = float(probe['format']['duration'])
                    current_start = current["start"] if i > 0 else 0.0
                    duration = max(0.5, total_dur - current_start)
                except Exception as e:
                    print(f"Failed to probe audio duration: {e}")
                    duration = 60.0  # Cover remaining audio
                
            # zoompan: d is duration in frames (25 fps)
            frames = int(duration * 25)
            stream = (
                ffmpeg.input(current['path'].resolve().as_posix())
                .filter('scale', '4608x8192', force_original_aspect_ratio='increase')  
                .filter('crop', '4608', '8192') 
                .filter('zoompan', z='min(zoom+0.0015,1.5)', d=frames, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='576x1024')
                .filter('setsar', '1')
                .filter('format', 'yuv420p')   
            )
            video_streams.append(stream)

        # Concatenate all main video streams
        main_video = ffmpeg.concat(*video_streams, v=1, a=0)
        
        # Apply Watermark if provided
        if watermark_path and watermark_path.exists():
            watermark_input = ffmpeg.input(watermark_path.as_posix())
            watermark_scaled = watermark_input.filter('scale', '120', '-1')
            watermark_faded = watermark_scaled.filter('colorchannelmixer', aa=0.6)
            main_video = ffmpeg.overlay(main_video, watermark_faded, x='main_w-overlay_w-36', y='main_h-overlay_h-90')
        
        # Overlay subtitles onto main video if provided and exists
        if ass_path and Path(ass_path).exists():
            main_video = main_video.filter('subtitles', filename=Path(ass_path).as_posix())
        else:
            print("Notice: No subtitle file provided or found. Assembling video without subtitles.")
        
        # Build Final Video and Audio Sequences
        final_video_streams = []
        final_audio_streams = []
        
        # 1. Opening
        if opening_path and opening_path.exists():
            print(f"Adding opening card to video timeline: {opening_path.name}")
            frames_open = int(2.0 * 25) # 2 seconds
            opening_stream = (
                ffmpeg.input(opening_path.as_posix(), loop=1, framerate=25, t=2)
                .filter('scale', '576x1024', force_original_aspect_ratio='decrease')
                .filter('pad', '576', '1024', '(ow-iw)/2', '(oh-ih)/2')
                .filter('setsar', '1')
                .filter('format', 'yuv420p')
            )
            final_video_streams.append(opening_stream)
            final_audio_streams.append(ffmpeg.input('anullsrc', f='lavfi', t=2))
        else:
            print("Notice: No opening card provided or found.")
            
        # 2. Main
        final_video_streams.append(main_video)
        final_audio_streams.append(ffmpeg.input(audio_path.as_posix()))
        
        # 3. Closure
        if closure_path and closure_path.exists():
            print(f"Adding closure card to video timeline: {closure_path.name}")
            frames_close = int(3.0 * 25) # 3 seconds
            closure_stream = (
                ffmpeg.input(closure_path.as_posix(), loop=1, framerate=25, t=3)
                .filter('scale', '576x1024', force_original_aspect_ratio='decrease')
                .filter('pad', '576', '1024', '(ow-iw)/2', '(oh-ih)/2')
                .filter('setsar', '1')
                .filter('format', 'yuv420p')
            )
            final_video_streams.append(closure_stream)
            final_audio_streams.append(ffmpeg.input('anullsrc', f='lavfi', t=3))
        else:
            print("Notice: No closure card provided or found.")
            
        concat_video = ffmpeg.concat(*final_video_streams, v=1, a=0)
        concat_audio = ffmpeg.concat(*final_audio_streams, v=0, a=1)

        # Apply BGM if provided
        final_audio = concat_audio
        if bgm_path and bgm_path.exists():
            bgm_input = ffmpeg.input(bgm_path.as_posix(), stream_loop=-1)
            bgm_low = bgm_input.filter('volume', '0.05')
            # Mix concat_audio and bgm_low. duration='first' stops when concat_audio ends.
            final_audio = ffmpeg.filter([concat_audio, bgm_low], 'amix', inputs=2, duration='first')
            
        ffmpeg_file = (Path(__file__).parent.parent / "ffmpeg.exe").resolve()
        ffmpeg_path = ffmpeg_file.as_posix() if ffmpeg_file.exists() else "ffmpeg"
        
        print("Running FFMPEG to assemble final video...")
        try:
            (
                ffmpeg
                .output(
                    concat_video,
                    final_audio,
                    output_path.as_posix(),
                    vcodec='libx264',
                    pix_fmt='yuv420p',
                    acodec='aac',
                    shortest=None
                )
                .overwrite_output()
                .run(cmd=ffmpeg_path, capture_stdout=True, capture_stderr=True)
            )
            print(f"Video successfully assembled at {output_path}")
            return True
        except ffmpeg.Error as e:
            print("FFMPEG ERROR:")
            print(e.stderr.decode("utf-8"))
            return False
