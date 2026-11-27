"""
video_creation package — Contains all modular workflow stages for automated short video generation:
  - _A_video_scripts: LLM script & metadata generation
  - _B_voice_generation: Hybrid ElevenLabs (eleven_v3) + local ComfyUI Qwen3-TTS voice generation
  - _C_image_generation: Scene imagery (ComfyUI Z-Image-Turbo & CPU FreeType chalkboard renderer)
  - _D_music_generation: Standing local background music bank via Transformers MusicGen
  - _F_thumbnail_image_generation: CPU Pillow/FreeType vertical category thumbnail renderer
  - _G_video_assembly: Script-aligned Whisper subtitles & FFmpeg video assembly
  - workflows: Centralized ComfyUI JSON API workflow templates
"""
