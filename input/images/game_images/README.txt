================================================================================
GAME QUIZ VISUAL ASSETS GUIDE
================================================================================

Folder: input/images/game_images/

PURPOSE:
Visual assets for the interactive GAME trivia quiz videos:

1. empty_chalkboard.png
   - A clean, high-resolution blank green chalkboard graphic (576 x 1024 px).
   - In Part C (_C_image_generation), the Python FreeType renderer (chalkboard_renderer.py)
     writes the quiz question, yellow option badges (A, B, C, D), and translucent green
     option cards directly onto this template on CPU in milliseconds with zero VRAM.

2. <language>/<language>_waiting.png (e.g. english/english_waiting.png)
   - Static waiting/thinking illustration (576 x 1024 px).
   - Displayed during the 2.2-second suspense countdown pause while the viewer thinks.
