================================================================================
INPUT IMAGES ASSET SPECIFICATION & MODEL GUIDE
================================================================================

This directory contains static visual assets used across the video generation pipeline.
You can replace any of these assets with your own brand assets:

1. thumbnail_models/
   - Purpose: Reference character portrait models for Part F (_F_thumbnail_image_generation).
   - Usage: ComfyUI Flux image-to-image uses these portraits to generate styled YouTube thumbnails.
   - Files: <language>/<language>_thumbnail_model.png (576x1024 vertical portrait).

2. watermark/
   - Purpose: Channel watermark / brand logo overlaid on video in Part G (_G_video_assembly).
   - Usage: Automatically faded (60% opacity) and placed at bottom-right corner.
   - Files: watermark.png (transparent PNG, ~120px recommended).

3. openning_closure_images/
   - Purpose: Channel bumper cards (opening hook and closing call-to-action).
   - Usage: Prepend 2.0s opening card and append 3.0s closing card during video assembly.
   - Structure:
     - normal_videos/: opening/ and closure/ per language for EXPRESSION, GAME, ROLEPLAY.
     - fun_facts/: opening/ and closure/ per language and dialect for FUN_FACTS.

4. game_images/
   - Purpose: Visual assets for interactive GAME quiz videos.
   - Files:
     - empty_chalkboard.png: Blank green chalkboard template (576x1024) onto which
       the Python chalkboard renderer writes quiz questions and options with zero VRAM.
     - <language>/<language>_waiting.png: Static thinking/waiting illustration displayed
       during the 2.2-second suspense countdown pause between challenge and answer.
