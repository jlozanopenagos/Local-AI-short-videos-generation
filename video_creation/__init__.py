"""
video_creation package — Contains all modular workflow stages for automated short video generation:
  - _A_video_scripts: LLM script & metadata generation
  - _B_voice_generation: Multi-speaker TTS generation via ComfyUI Qwen3-TTS
  - _C_image_generation: Scene imagery (ComfyUI Z-Image SD/Flux & native chalkboard renderer)
  - _D_music_generation: Local background music generation via Transformers MusicGen
  - _F_thumbnail_image_generation: Vertical thumbnail generation via ComfyUI Flux img2img
  - _G_video_assembly: Word-level Whisper subtitles & FFmpeg video assembly
  - workflows: Centralized ComfyUI JSON API workflow templates
"""
