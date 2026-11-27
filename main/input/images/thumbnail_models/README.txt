================================================================================
THUMBNAIL CATEGORY TEMPLATES GUIDE (STAGE F — CPU PILLOW / FREETYPE)
================================================================================

Folder Layout (20 category-specific master templates):
  - English / French / Italian:
      input/images/thumbnail_models/<language>/<category>/template.png
      where <language> is {english, french, italian}
      and   <category> is {expression, fun_facts, game, roleplay}
  - Spanish (dual regional variants):
      input/images/thumbnail_models/spanish/<category>/latam.png
      input/images/thumbnail_models/spanish/<category>/spain.png

PURPOSE:
Stage F (_F_thumbnail_image_generation/service.py) renders vertical thumbnails
purely on CPU via Pillow + FreeType (zero ComfyUI / zero GPU VRAM) using
category-specific typography, colors, and safe regions defined in
_F_thumbnail_image_generation/core/thumbnail_renderer.py.

TITLE RESOLUTION:
- Prioritizes content_metadata.thumbnail_title verbatim (strip_prefix=False),
  editable in WebUI ScriptDetailModal or batch-synced from Google Sheets
  Column J (POST /api/sheets/sync-thumbnails).
- Falls back to content_metadata.script.title -> target_expression -> EXPRESSION.

SPECIFICATIONS:
- Resolution: 576 x 1024 px (IMAGE_DEFAULT_WIDTH x IMAGE_DEFAULT_HEIGHT)
- Format: PNG (.png) -> output thumbnail.png (or thumbnail_latam.png &
  thumbnail_spain.png for Spanish scripts)
