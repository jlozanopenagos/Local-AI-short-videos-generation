# Shorts Automation

Shorts Studio produces vertical language-learning videos in English, French, Spanish, and Italian. Each language supports Expression, Game, Roleplay, and Fun Facts.

This repository contains the production studio. The separate `GoogleSheet_UI_auditor` project handles editorial review and release planning in Google Sheets. `ComfyUI_windows_portable` supplies the rendering and speech runtime. The studio also has a Gemini tool for reviewing image prompts.

## Start the studio

Run these commands from the repository root in PowerShell. For a new setup, configure the local llama.cpp and ComfyUI services, their model and voice assets, and FFmpeg and FFprobe. Configure Sheets, Drive, and Gemini for the features you use.

```powershell
Copy-Item main/.env.example main/.env
py -m pip install -r main/requirements.txt
py main/tools/webui.py
```

The launcher serves the studio on `http://127.0.0.1:8190` by default. For an existing setup, keep your configured `main/.env`.

## Production workflow

1. Generate a lesson script from **Script Catalog**, or bring reviewed Google Sheets revisions (**Column D** scripts and **Column J** thumbnail titles) into existing local state JSONs (`main/state/`, `1,224` scripts) via **Sheets Sync**.
2. Queue **Voice**, **Scene Images**, and **Thumbnails** from the catalog or **Mass Creation**. Mass Creation accepts pasted IDs, an ID CSV, or catalog presets (including pending thumbnails), plus image seeds, voice provider/model selection, accent overrides, and recasting.
3. Queue **Video Assembly** after voice and images complete. FFmpeg combines the audio, illustrations, non-overlapping subtitles, music, and branding into a vertical MP4. Enable **"Reuse existing subtitles"** only when you intentionally want to keep existing `.ass` captions.
4. Track execution in **Queue**, inspect media or edit thumbnail/chalkboard text in the script details, and use **Drive Upload** (full bundle, video-only, or thumbnail-only) to deliver the finished assets.

Per-script JSON under `main/state/` records production status and references to assets. Generated media lives under the configured `OUTPUT_DIR`. Use the live catalog or the status tools for inventory.

The WebUI is the production entry point. Operator tools cover service supervision, voice and music bank generation, teaser extraction, and database and Sheets maintenance.

## Verification

Run `py -m pytest test -m "not live"` after completing the [test setup](test/README.md). Offline tests automatically isolate `VOICE_PROVIDER=local` via `test/conftest.py` so no live ElevenLabs credits are spent. The suite includes an isolated Sheets-to-MP4 workflow with real FFmpeg, a browser retry and preview check, and focused engine tests. Windows CI builds the frontend and runs the deterministic and browser checks. The real ComfyUI GPU test is opt-in.

## Project guides

- [Repository agent quickstart](AGENTS.md)
- [Full agent & architecture contract](main/AGENTS.md)
- [Architecture and configuration](main/README.md)
- [Studio and API](main/webui/README.md)
- [Sheets and Drive](main/connectivity/README.md)
- [State schema](main/state/README.md)
- [Operator tools](main/tools/README.md)
- [Test suite guide](test/README.md)

## Voice generation today

Studio uses a **hybrid voice architecture** defined by `ELEVENLABS_HYBRID_TYPES` (`roleplay`, `expression`, `fun_facts`):

- **ElevenLabs (`eleven_v3`)** renders `ROLEPLAY`, `EXPRESSION`, and `FUN_FACTS` using a `227`-voice curated catalog (`EN: 57`, `FR: 70`, `IT: 50`, `ES: 50`) with full-cycle LRU rotation (`max_history=60`), same-speaker-only `previous_text`/`next_text` stitching, native delivery speed (`0.94` Roleplay, `0.92` Expression/Fun Facts), and raised-cosine `10ms`/`20ms` trim fades.
- **Local Qwen3-TTS (`1.7B-Base` / `1.7B-VoiceDesign` via ComfyUI)** renders `GAME` (and any script when `VOICE_PROVIDER=local`). The local curated bank currently contains **52 distinct baseline voices** indexed in `<VOICE_BANK_DIR>/voice_bank_manifest.json` (`roleplay_*` actor baselines are excluded from `GAME` and `FUN_FACTS`, and Spanish local casting follows an exact 60% LatAm / 40% Castilian rotation).

Use Voice with **Force** to rerender and enable **Recast (`Choose new voices`)** only to assign a different cast.

## Thumbnails, subtitles, Sheets & Drive today

- **Thumbnails (Stage F):** Rendered natively on CPU with Pillow + FreeType (`576x1024`, zero VRAM) across **20 category-specific master templates** (single `template.png` per category for EN/FR/IT; paired `latam.png` + `spain.png` variants for Spanish). Custom titles from `content_metadata.thumbnail_title` (editable in the Script Detail modal or synced from Google Sheets **Column J**) render verbatim.
- **Subtitles & Assembly (Stage G):** Word alignment protects 1–2 letter words from false apostrophe gluing, recovers collapsed Whisper timings via character-weighted interpolation, enforces a 2-layer strict non-overlap guard on every `.ass` dialogue event, and strictly respects the **"Reuse existing subtitles"** toggle in Mass Creation.
- **Google Sheets Sync:** Syncs both script edits (**Column D `SCRIPT_CHANGED`** + **Column B `EXPRESSION`**) with blank-line `GAME` option merging and `Counter`-based diffing, and custom **Column J (`THUMBNAIL_TITLE`)** titles directly into local state JSONs (resetting only `thumbnail_generation` to `pending`).
- **Google Drive Upload:** Supports scoped uploads (`all` / `video` / `thumbnail`), dual Spanish regional thumbnails, duplicate folder cleanup, and automatic browser OAuth re-authentication when `token.json` expires (`client_secret.json`).

## Historical release notes

These notes describe earlier releases. Use the workflow and verification instructions above for the current project.

### Previous Release: Stage C Late-Teen Cropped Framing, Preserved General Prompt Redo, Google Sheets Sync & Cultural World Atlas
- **Stage C Late-Teen (`17-year-old`, `1:7`) Proportions, Cropped `hook` Framing & Sanitizer Hardening**:
  - **Proportion & Age Normalization (`sanitizer.py`, `style.py`, `cast.py`, `gemini_auditor.py`)**: Upgraded the purely-positive Z-Image-Turbo (`cfg=1.0`) anchor to `17-year-old high-school senior` (`realistic late-teen 1:7 head-to-body proportions, defined jawline, proportional shoulders, lean athletic teenage build`) and automatically upgrades `8–15`, `fourteen-year-old`, `fifteen-year-old`, `14-16yo`, and `14-16-year-old` tokens to `17-year-old` (preserving `16–18`).
  - **Cropped `hook` Framing & Wearable Footwear Stripping (`prompt_builder.py`, `sanitizer.py`, `visual/types/*`)**: Switched `GAME` `hook` to a waist-up 3/4-angled `50mm` medium shot under directional spotlighting, tightened `EXPRESSION` `hook` (`35mm` waist-up / mid-thigh) and `FUN_FACTS` `hook` (`28mm` low-angle mid-thigh/waist-up), removed footwear mandates from cropped scene prompts (`strip_footwear_clauses`, `CROPPED_FRAMING_RE`, `_CROPPED_SCENES`, and `NEGATIVE_PROMPT_SHIELD`) while preserving venue/prop nouns (`sneaker boutique`, `footwear workshop`, `shoe boxes`), and fixed shortened-tail proportion anchor skipping plus compound-noun false positives (`reading lamp`, `reading alcove`, `reading hall`, `reading boxes`, `calling card`).
- **WebUI Preserved General Prompt on Full Image Redo (`POST /api/scripts/{script_id}/redo-all-images`, `ScriptDetailModal`)**:
  - Added `preserve_general_prompt=True` so single-script **Queue Redo (All Images)** keeps the user-edited or Gemini-audited `general_prompt` intact while regenerating scene prompts and PNGs (while **Mass Assets Creation** keeps `preserve_general_prompt=False` for full rebuilds). Rebuilt frontend static bundle in `main/webui/static/`.
- **Google Sheets Sync Fixes Across All 16 Sheets (`client.py`, `fetcher.py`, `check_script_changes.py`, `sheets.py`, `script_modifier.py`)**:
  - Added `SCRIPT_CHANGE` header alias alongside `SCRIPT_CHANGED`, Column B `EXPRESSION` preservation through CSV/WebUI sync, 5-section `FUN_FACTS` parsing (`hook`, `setup`, `discovery`, `explanation`, `payoff`), and title/anchor invalidation on topic changes.
- **Google Drive Clean Delete-Before-Upload Replacement (`drive_client.py`, `sync_service.py`, `DriveAdapter`, `sync_drive.py`)**:
  - **Safe Atomic Replacement**: Validates that BOTH the local final assembled video and companion thumbnail exist BEFORE making any deletions on Drive.
  - **Clean Deduplication & Pre-Upload Cleanup**: Calls `delete_duplicate_folders()` for `<script_id>` and `clear_folder()` (paginated deletion with `supportsAllDrives=True, includeItemsFromAllDrives=True` and HTTP 400/403 Trash fallback + `_folder_cache` eviction) before uploading fresh `<script_id>.mp4` and `<script_id>_thumbnail.png` files into `<root>/<language>/<expressions|fun_facts|game|role_play>/<script_id>/`. Returns and logs `deleted_existing_count` across both CLI and WebUI `DriveAdapter`.
  - **Unified Credential Resolution**: Auto-resolves credentials from `--credentials`, `GOOGLE_APPLICATION_CREDENTIALS`, or `main/credentials/` (`token.json` -> `service_account.json` -> `client_secret.json`).
- **Cultural World Atlas (124 Culturally Grounded Worlds) & Stage G Modular Video Assembly (`_G_video_assembly/assembly/`)**:
  - **Cultural Worlds & Gemini Auditor Reroll**: Replaced generic studio/workshop/greenhouse/drafting-vest tropes with **124 culturally authentic venues** across 4 languages (36 English, 32 Spanish, 28 French, 28 Italian), Triplet Collision Guard, and automatic Cultural World reroll excluding prior drafts.
  - **Per-Type Editing Grammar & Forced Mass Assembly**: Decoupled `assembly/types/{expression,game,roleplay,fun_facts}/` with cosine-eased Ken Burns motion, **Lower-Middle Safe Zone** subtitles, `ROLEPLAY` speaker color-coding, frame-accurate `xfade` transitions, and staged replacement in `AssemblyAdapter`.
- **QA Test Suite**: Isolated `test_chalkboard_adapter.py` into a temporary sandbox and expanded verified coverage to **436 automated tests across 46 test files** in that release.

### Previous Release: Google Drive Sync Suite, Single Source of Truth Visual Anchors & Prompt Auditor 2.0
- **Google Drive Export & Mass Drive Upload Suite**:
  - **Standalone CLI & Service (`main/connectivity/sync_drive.py` & `drive_sync/`)**: Headless and automated synchronization of finished video assets to Google Drive (`drive_client.py` & `sync_service.py`). Supports OAuth 2.0 Desktop App (`client_secret.json` -> `token.json` in `main/credentials/`) and Service Account (`service_account.json`) credentials.
  - **Hierarchical Drive Folder Structuring**: Routes uploads to `GOOGLE_DRIVE_ROOT_FOLDER_ID` organized into `<language>` (`english`, `french`, `spanish`, `italian`), `<video_type>` (`expressions`, `fun_facts`, `game`, `role_play`), and `<script_id>` subfolders.
  - **Atomic Video & Thumbnail Bundling**: Strictly validates that each script possesses both the final assembled video and companion thumbnail before uploading `<script_id>.mp4` and `<script_id>_thumbnail.png`.
  - **WebUI Single-Script Upload & Mass Drive Upload**:
    - `ScriptDetailModal`: Added instant "upload to google drive" action (`POST /api/drive/scripts/{script_id}/upload`).
    - `MassAssetsCreationView`: Added "google drive upload" mode allowing bulk ID entry, CSV drag-and-drop, and "ready for drive upload (video + thumb)" preset. Validates IDs via `POST /api/scripts/validate-ids`, displays readiness badges, and enqueues batch jobs through `DriveAdapter` via `POST /api/jobs` (`stage="drive_upload"`).
- **Authoritative Visual World Anchor & Single Source of Truth**:
  - **General Prompt Authority**: Completely eliminated disparate prompt generation logic where `_extract_shared_story_context` in `prompt_builder.py` recalculated independent character demographics. Scene prompts now inherit visual world anchors directly from `extract_or_build_character_anchors`, ensuring the General Prompt serves as the sole, authoritative source of truth for character gender, ethnicity/skin tone, hairstyle, and wardrobe across all scenes.
  - **Case-Insensitive Speaker Gender Resolution (`get_speaker_gender_safe`)**: Resolved a pervasive gender inversion bug where TitleCase keys (`"Narrator"`) in `speakers_gender` (present in over 1,038 state files across the database) failed `.get("NARRATOR")` lookups and defaulted female characters to `"male"`. Added case-insensitive key normalization and fuzzy fallback.
  - **Director Gender Anchor Locking**: Storyboard generation tasks for Game, Fun Facts, and Expression explicitly lock `{p1_word}` (`girl`/`boy`) in director tasks based on authoritative anchors, eradicating conflicting double injections.
- **System Prompts Editor & IMAGE_PROMPT_AUDITOR Modernization**:
  - Fully upgraded `IMAGE_PROMPT_AUDITOR` in `main/system_prompts_editor.csv` to incorporate all modern production rules: multi-character gender integrity, ethnicity/complexion lock, gender-accurate hairstyles, video-type specific visual grammar, prop relevance / anti-gift-box ban, and standard production style tail.
  - Normalized line endings across `system_prompts_editor.csv` to RFC-4180 compliant CRLF (`\r\n`), eliminating formatting anomalies and mixed line-ending git warnings.
- **Bingo Matrix View**:
  - Added interactive visual completion grid in WebUI (`BingoMatrixView.tsx`) to track asset readiness across all 16 language/format combinations.

### Previous Release: Anti-Cliché Prop Governance, Expressive Acting & Queued Scene Redo
- **Anti-Cliché Prop Governance & Strict Gift Box Ban**:
  - **Eradication of the Gift Box Cliché**: Eliminated generic ribbon-wrapped gift boxes, mystery parcels, and present boxes used as lazy fallback props across Game, Roleplay, Expression, and Fun Facts. Gift boxes are strictly restricted to the heteronym `present` (PREsent vs preSENT).
  - **Context-Grounded Setting Props**: Enforced domain-authentic props matching the physical environment (travel luggage/tickets for trips, culinary cookware/platters for kitchens, tools/blueprints for studios, tuning forks/phonetics mirrors for pronunciation).
  - **Refined Idiom Discovery**: Purged bare `"expression"` substring from `is_figurative_idiom()`, preventing standard vocabulary/grammar scripts from falsely inheriting idiom visual directives.
  - **Sanitizer Interceptors**: `sanitize_and_style_prompt()` automatically cleans legacy gift box tokens into authentic setting-specific props.
- **Expressive Character Design & Anti-Distortion Shield**:
  - **Purged Deadpan & Bug-Eye Triggers**: Replaced `"Wes Anderson-style central balance"` and `"frozen at a physical crossroads"` with dynamic 3/4 framing and natural animated dilemma acting.
  - **Natural Facial Acting (Bug-Eye Eradication)**: Scrubbed all `"conspiratorial glance"` and `"arched eyebrow"` triggers from prompt templates and storyboard generators to prevent diffusion models from rendering excessively open, rounded, or bulging bug-eyes. Replaced with *"engaging, playful knowing smile and natural animated cartoon eyes with relaxed facial acting"*.
  - **Healthy Athletic Build**: Replaced `"tall slender proportions"` with `"natural balanced teenage proportions, healthy youthful athletic build"`, eradicating gaunt stick-figure silhouettes.
  - **Expanded Negative Shield**: Added `NO bulging eyes, NO bug eyes, NO staring unblinking eyes, NO excessively open rounded eyes, NO unnatural wide eyes, NO deadpan blank face, NO emotionless expression, NO stiff mannequin pose, NO gaunt, NO emaciated, NO stick-figure proportions`.
- **Zero-Copy Static Shared Asset Architecture**:
  - **Elimination of Duplicate Asset Copies**: Static pre-made assets that never vary across scripts of the same language and video type (e.g. Tito waiting image `pressure.png` for GAME shorts, opening branding cards, closure cards, watermark) are NEVER physically copied into individual script output folders (`<OUTPUT_DIR>/video_assets/...`).
  - **On-Demand Dynamic Resolution (`resolve_static_scene_path`)**: `config/settings.py` dynamically resolves the canonical asset from `input/images/game_images/` or `input/images/openning_closure_images/` based on script language, video type, and dialect without hardcoded paths.
  - **Decoupled Creation & Assembly**: `_C_image_generation/main.py` and `image_modifier.py` verify central asset existence and skip file duplication, while `_G_video_assembly/core/video_assembler.py` automatically links the central asset directly into the FFmpeg render timeline. Reclaimed 167.78 MB of disk space by purging 93 duplicate files.
- **Queued Scene Image Redoing & Specific Prompt Editor**:
  - Single scene regeneration (`POST /api/scripts/{id}/scenes/{scene}/redo-image`) enqueues asynchronously into the Job Manager queue instead of blocking the HTTP connection.
  - Dedicated per-scene prompt editing with independent persistence across state JSONs and UI cache.
- **Full Image Set Redo from General Prompt (`POST /api/scripts/{id}/redo-all-images`)**:
  - Updating the general prompt provides a dedicated `queue redo (all images)` button in the Script Detail Modal.
  - Automatically updates the general prompt in the state JSON, invalidates old scene-specific prompts and disk PNGs, marks `image_generation` and `video_assembly` stages as pending, and queues a two-phase background job.
  - **Automated VRAM Handoff**: Starts `llama-server` in Phase 1 to regenerate all scene-specific prompts aligned to the new visual world, saves them to state, and stops Llama to release VRAM before ComfyUI boots in Phase 2 to render the complete set of images.

### Previous Release: Modern WebUI Studio, Mass Assets Creation, Canonical GAME Format & VRAM Arbiter
- **Visual Grammar, Character Continuity & Game Timeline Refinement**:
  - **Fun Facts & Global Text Shielding**: Positive prompts enforce abstract wavy cartoon scribble lines on documents/scrolls/books; automatic quote and phrase stripping blocks diffusion models from painting text onto images.
  - **Game Shorts 5 Distinct Cuts**: Expanded ComfyUI rendering to 3 scenes (`hook`, `answer`, `explanation`), eliminating duplicate images between scenes 4 & 5 (`hook` ComfyUI $\rightarrow$ `challenge` Chalkboard $\rightarrow$ `pressure` Tito $\rightarrow$ `answer` ComfyUI $\rightarrow$ `explanation` ComfyUI).
  - **Character Appearance Continuity & Demographic Lock**: Single source of truth in `content_metadata.character_anchors` with locked gender, skin tone, eye color, hairstyle, and wardrobe. Mandatory complexion anchoring (e.g. *warm tan skin*, *fair peach skin*, *olive skin*) and eye color (*dark brown cartoon eyes*) prevents diffusion drift between 35mm foreground Hook close-ups and medium two-shot scenes. Demographic anchored to *16-year-old high-school teenager with natural balanced teenage proportions (mature teenage features, NOT a child)*. Gender-attire integrity checks prevent male corsets/kirtles, and negative prompt shield blocks young children and childish proportions.
### Latest Release: Scene Calibration, Chalkboard Localization, Zero-Text Prompts & Safe ComfyUI Supervisor
- **Calibrated Scene & Image Timeline Architecture**:
  - **EXPRESSION (5 images)**: `hook`, `setup`, `discovery`, `example`, `payoff` rendered via ComfyUI.
  - **GAME (5 images, 2 ComfyUI renders)**: `hook` and `answer` rendered via ComfyUI; `challenge` rendered natively on CPU via FreeType onto `empty_chalkboard.png` with zero VRAM; `pressure` loaded from static per-language Tito waiting image; `explanation` automatically duplicated from `answer.png`.
  - **ROLEPLAY (6 timeline cuts, 4 ComfyUI renders)**: `hook`, `dialogue_part_2`, `dialogue_part_3`, `payoff` rendered via ComfyUI; dynamic 1.25x punch-in cuts for `dialogue_part_1` and `dialogue_part_4` in video assembly.
  - **FUN_FACT (5 images)**: `hook`, `setup`, `discovery`, `explanation`, `payoff` rendered via ComfyUI.
- **Chalkboard Language Purity & Localization (`get_localized_game_header`)**:
  - Implemented `get_localized_game_header()` in `types/game/archetypes.py`, providing 100% culturally authentic, target-language headers (e.g. French: `QUE SIGNIFIE CETTE EXPRESSION ?`, Spanish: `¿QUÉ SIGNIFICA ESTA EXPRESIÓN?`, Italian: `COSA SIGNIFICA QUESTA ESPRESSIONE?`).
  - Zero English headers or English instruction text allowed on non-English chalkboards.
- **Deep Prompt Text & Quote Scrubbing (`sanitize_and_style_prompt`)**:
  - Completely scrubs all quoted words, idioms, foreign phrases, and speech actions (`whispering the words...`, `saying the words...`) from image prompts to prevent diffusion models from hallucinating or painting pseudo-text onto characters and backgrounds.
  - Enforced strict negative prompt directives: `NO text, NO words, NO letters, NO quotes, NO signs with text, NO subtitles, NO typography`.
- **Game Archetypes & Challenge Logic Integrity**:
  - Categorizes idioms and figurative expressions (e.g. *Poser un lapin*, *Break a leg*) under `FALSE_FRIEND_TRAP` (testing true native meaning vs literal blunder).
  - Enforces that Narrator audio voices the scenario clearly without giving away or spoiling the solution in the question sentence.
- **Port-Based PID Discovery & WebUI Crash Prevention**:
  - Hardened `ComfyManager.stop()` with `_discover_pid_from_port()` to inspect only active TCP `LISTENING` sockets on `:8188`, refusing to kill parent/caller PIDs and preventing accidental WebUI process termination.
- **QA Test Suite**:
  - Expanded and verified test suite to **358 automated tests** passing 100%.

### Previous Release: Streamlined Voice Modifier, Distinct Roleplay Casting & Resilient Parser Architecture
- **Streamlined Voice Modifier & Recaster (`_B_voice_generation/voice_modifier.py`)**:
  - **Immediate Pre-Flight Health Assertions**: Runs backend connection checks (`require_services(comfy=True)` and local Kokoro engine readiness) upfront before asking for Script IDs or user input.
  - **Zero Manual File Selection**: Completely eliminated tedious manual reference file picking and 10-item `.wav` filename lists. Users only specify character/narrator genders (`male`/`female`), and the program automatically randomizes high-quality distinct voices from reference pools matching `main.py`.
  - **Strict Roleplay Voice Distinctness Mandate**: Enforces that in multi-speaker / roleplay scripts, the **Narrator and any character sharing the same gender NEVER share the same reference voice or Kokoro recipe**. Collision avoidance checks guarantee that every speaker in the script receives a distinct reference voice and Kokoro timbre (`_narrator`, `_alt`).
  - **Automatic Downstream State Invalidation**: Automatically flags `video_assembly: "pending"` in the script state JSON whenever a new master voiceover is synthesized, ensuring that final assembly is flagged to re-render with the new audio track.
  - **Intermediate Audio Sanitization**: Cleans up stale `.flac` takes and temporary `.wav` files before synthesis to prevent cross-run pollution.
- **Resilient JSON Section Parsing & Control-Character Tolerance (`script_parser.py`)**:
  - Enhanced `parse_sections` with `json.loads(..., strict=False)` and regex sanitization of unescaped literal newlines/tabs inside multi-line JSON values.
  - Eliminates `JSONDecodeError` (`Invalid control character`) crashes on raw scripts, with automatic state recovery from `content_metadata.script`.
- **5-Section GAME Format Integrity & Pacing**:
  - Canonical 5-spoken-section structure (`hook`, `challenge`, `pressure`, `answer`, `explanation`) with strict 95–125 word budget and dedicated 2.20s suspense pause (`pressure_gap`).
  - Dynamic subtitle suppression strictly during the `challenge` section window to preserve chalkboard legibility.

### Stable Release: Headless ComfyUI Supervisor, Connection Pool & VRAM Arbiter
- **Headless ComfyUI Process Supervisor (`tools/comfy.py` & `core/comfy_manager.py`)**:
  - Eliminates the need for manual bash/cmd terminal windows entirely.
  - Spawns ComfyUI in the background via `pythonw.exe` (`CREATE_NO_WINDOW | DETACHED_PROCESS`), completely immunizing the system against Windows QuickEdit terminal freeze deadlocks.
  - Provides a complete CLI management tool: `start`, `stop`, `restart`, `status`, and `logs -f`.
  - Redirects all runtime logs to `main/logs/comfyui/comfyui.log` with automatic log rotation.
- **Connection Pool & VRAM Arbiter (`core/comfy_pool.py`)**:
  - Replaces per-request socket churn with a persistent `requests.Session` connection pool with keep-alive and retry adapters.
  - Implements thread and file-based VRAM mutex guards (`vram_guard`) preventing concurrent collisions between Flux image generation and Qwen3-TTS voice generation on constrained GPUs (e.g. 6GB RTX 2060).
  - Automatically invokes `/free` memory reclamation between generation cycles.
- **Senior QA Test Suite Expansion**:
  - Expanded test suite to **287 automated tests** passing across all 5 test layers with 100% green status.

### Previous Release: Title & Metadata Singularity, Strict Emoji Ban & Mass Upgrade
- **Title & Metadata Singularity Architecture**:
  - Eliminated repetitive *"Native Secret"* / *"El Secreto de los Nativos"* / *"Il Segreto dei Nativi"* / *"Le Secret des Natifs"* clichés across the entire pipeline.
  - Implemented format-differentiated title archetypes across all 4 formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`), guaranteeing distinct angles even when sharing an underlying expression.
  - Two-tier title model: punchy 3–6 word chalkboard titles for Tito (`content_metadata.script.title`) and curiosity-driven uppercase trigger titles for YouTube Shorts (`metadata.TITLE`).
- **Strict Universal Emoji Purge**:
  - Emojis strictly banned from all YouTube titles, descriptions, and chalkboard titles.
  - Integrated `strip_emojis()` and negative prompting across `prompts_data.py`, `metadata_builder.py`, `script_modifier.py`, and `thumbnail_renderer.py`.
- **Title & Metadata Upgrader Tool (`upgrade_titles.py`)**:
  - Upgraded **1,220 state JSON files** with canonical SQLite expression resolution (preventing 30-word scenario leakage from Roleplay prompts).
  - Contaminated cliché titles dropped from 35.1% (430 state files) down to 0.5% (6 files representing literal historical titles).
  - 100% of titles across all 1,220 state files are confirmed emoji-free.
  - All downstream statuses (`voice_generation`, `image_generation`, `video_assembly`) 100% preserved.

### Previous Release: Script Change Auditor, Zero-Duplication Ingestion & Thumbnail Localization
- **Script Change Auditor (`check_script_changes.py`)**:
  - Automated comparison and synchronization engine between CSV Column D corrections (`input/csv/script_to_change/`) and local runtime state JSONs (`main/state/`).
  - Implements speaker prefix stripping (`Narrator:`), quotation mark normalization, and whitespace cleanup to eliminate false positives.
  - Automatically resets downstream generation stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `'pending'` upon application.
  - Supports `--check-only`, `--apply`, targeting specific CSVs (`--csv <filename>`), or single scripts (`--script-id <ID>`).
  - Available at `main/tools/check_script_changes.py`.
- **Zero-Duplication Parsing Fix (`script_modifier.py`)**:
  - Resolved legacy 4-paragraph duplication bug that previously duplicated `setup` into `discovery` for `EXPRESSION` or `challenge` into `pressure` for `GAME`.
  - Multi-sentence lines are now cleanly partitioned across canonical schema keys or intelligently structured by the LLM with zero duplication.
- **Chalkboard Thumbnail Title Sanitization & Localization (`_F_thumbnail_image_generation`)**:
  - Implemented `sanitize_thumbnail_title()` in `thumbnail_renderer.py` and `script_modifier.py` to eliminate English title leakage on chalkboard thumbnails for Latin languages (Spanish, French, Italian).
  - Automatically translates formulaic English suffixes (`: The Native Secret`, `: The Secret`, `: The Native Sound Trap`) into authentic native equivalents (`: El Secreto de los Nativos`, `: Le Secret des Natifs`, `: Il Segreto dei Nativi`) and restores the native target expression.
- **100% State Synchronization**:
  - All 359 scripts with human modifications across all 16 CSV queues in `input/csv/script_to_change/` audited and 100% synchronized with state JSONs on disk.
- **Senior QA Test Suite Expansion**:
  - Test suite expanded to **275 automated tests** passing across all 5 test layers with 100% success in ~20 seconds.

### Story World Anchor, Hairstyle Sanitization & Visual Director 2.0
- **Master Story World Anchor & Locked General Prompt**:
  - Two-pass visual director engine: Pass 1 generates an overarching `general_prompt` anchoring architectural environment, time of day, cinematic lighting, and character designs into state.
  - Pass 2 (`build_storyboard_prompts`) generates single-pass, fully coordinated scene prompts anchored directly to the locked master story world.
- **Strict Gender-Accurate Hairstyle Sanitization (`sanitize_character_hair`)**:
  - Programmatic regex and token-based enforcement preventing male characters from receiving feminine hairstyles (buns, bobs, ponytails, chignons) and female characters from receiving masculine haircuts (quiffs, buzz cuts, crew cuts).
  - Locks male characters to clean-cut masculine styling (`short textured dark hair with clean tapered sides and a neat side-part`) and female characters to stylish feminine styles (`dark wavy hair tied in an elegant high ponytail`, `textured caramel-brown hair styled in soft shoulder-length waves`).
- **Character Identity Continuity & Locked Anchors (`extract_or_build_character_anchors`)**:
  - Eliminates character identity drift, hair color swapping, and age inconsistencies across storyboard scenes.
  - Verifies presence of wardrobe and hairstyle tokens in every scene prompt, automatically appending continuity clauses if omitted.
- **Setting Resolution Priority & Heteronym Domain Decoupling**:
  - Minimal pair words (e.g. `eyes`, `ice`, `wind`, `tear`) are decoupled from broad setting domains, ensuring explicit scenario keywords take full precedence over acoustic keywords.
- **Option [7] Mass Ready Scripts Extended to Stage A & Stage B (`--from-mass-ready-scripts`)**:
  - Full cross-stage parity: Option `[7]` (Mass Ready Scripts) and Option `[6]` (Ready Scripts CSV) are now natively supported in Script Generation (`_A_video_scripts`) and Voice Generation (`_B_voice_generation`) as well as Image Creation (`_C_image_generation`), allowing multi-file batch targeting across ready scripts CSV queues.

### Visual Director 4-Beat Roleplay Architecture, Dynamic Assembly Cuts & Chalkboard Upgrades
- **Dynamic 4-Beat Roleplay Storyboard Sequence**:
  - Eliminates redundant identical images in Roleplay by reducing generated scenes from 6 to 4 (hook, dialogue_part_2, dialogue_part_3, payoff), saving 33% GPU generation time.
  - Automatically enriches hook with opening dialogue context and payoff with breakthrough resolution context in _C_image_generation.
- **Dynamic Virtual Camera Cuts in Video Assembly (_G_video_assembly)**:
  - Automatically resolves companion fallbacks (dialogue_part_1 -> hook.png and dialogue_part_4 -> payoff.png) by applying dynamic 1.25x punch-in cuts framed high on character faces.
  - Produces 6 active visual cuts synchronized to speaker transitions from 4 generated illustrations with zero repetitive poses.
- **Universal Multi-Character Gender Specification Rule (Zero-Ambiguity Mandate)**:
  - Enforces explicit sex definitions for all characters whenever more than one character appears, preventing model gender confusion.
  - Interactive dual-character gender casting with 120s timeout in image_modifier.py.
- **High-Resolution FreeType Chalkboard Renderer & Masking**:
  - Offloads game challenge rendering to CPU with clean typography, automatic trailing punctuation stripping, and answer masking (_________) for listening challenges.

### Syntactic Carrier & Continuous Prosody Architecture with Kokoro-82M Hybrid Engine
- **Syntactic Carrier Conditioning (Purge of Fake Respellings)**:
  - Solves tokenizer fragmentation and tense vowel distortion by strictly purging artificial BPE respellings (`pri-ZENT`, `PRAHJ-ekt`, `RECK-ord`).
  - Conditions heteronyms within living spoken sentences using natural syntactic carriers: determiners/articles for nouns (`a PREsent`, `the REcord`, `a PROject`, `a PERmit`) and infinitives/particles for verbs (`to preSENT`, `to reCORD`, `to proJECT`, `to perMIT`).
  - Synthesizes dialogue turns in continuous single acoustic takes per segment to guarantee natural prosodic pitch contours and intonation.
- **Acoustic Prominence Quality Gate (`core/acoustic_evaluator.py`)**:
  - Multi-candidate sampling (`--candidates 3`): generates multiple takes via ComfyUI.
  - Evaluates syllable-level Peak RMS energy ratios and fundamental frequency ($F_0$) pitch excursions against strict phonetic prominence thresholds (Noun RMS $\ge 1.05$; Verb RMS $\ge 1.10$; $F_0$ delta $> 0$).
  - Automatically ranks and selects the most prominent take.
- **Kokoro-82M Precision Hybrid Engine & Pronunciation Bank (`core/kokoro_engine.py` & `core/pronunciation_bank.py`)**:
  - Seamless zero-latency fallback: if stochastic autoregressive takes do not pass acoustic prominence gating, the pipeline falls back to certified clips from the Standing Pronunciation Bank (`main/input/audio/heteronym_bank/`).
  - Powered locally by **Kokoro-82M (`kokoro-onnx` + `espeak-ng`)**, executing phonemic IPA representations with 100% deterministic syllable stress control.
  - 100% coverage across all 58 core heteronym slots with both male (`am_adam`) and female (`af_heart`) reference voices.
  - CLI management tool: `py main/tools/manage_pronunciation_bank.py` (`--status`, `--audit`, `--populate-kokoro`).
- **Hormozi Syllable Stress Subtitle Synchronization (`video_creation/_G_video_assembly/core/subtitle_builder.py`)**:
  - Case-preserving subtitle rendering: preserves mixed-case syllable capitalization (`PREsent` vs `preSENT`, `PROject` vs `proJECT`) while keeping all other words in Hormozi-style all-caps.
  - Unified hyphenated token merging (`re-CORD`) with combined start and end timestamps.
- **Full Production Parity & State Synchronization**:
  - Brought `voice_modifier.py` to 100% feature parity with `main.py` (candidate selection and acoustic prominence gating).
  - Synchronized and validated all state JSON files across EXPRESSION, GAME, and ROLEPLAY to ensure complete syntactic carrier conditioning.

### Google Sheets Suite, Modular Architecture & Ready Scripts Scanner
- **Modular Connectivity Suite (`main/connectivity/`)**:
  - Organized into dedicated packages: `core/`, `apps_script/`, `sheet_sync/`, `corrected_scripts/`, `reconcile/`, `post_scripts/`, `ready_scripts/`.
  - 5 principal root runners: `sync_sheets.py`, `fetch_corrected_scripts.py`, `reconcile_scripts.py`, `post_scripts.py`, `scan_ready_scripts.py`.
  - Master Web App with Option A dynamic routing (`?id=<SPREADSHEET_ID>`) supporting both `doGet` (reads Columns A–H) and `doPost` (in-place updates & appends).
  - 3-column (`_3_columns`) and 4-column (`_4_columns`) export modes grouped under `synced_sheets/`.
- **Ready Scripts Scanner (`scan_ready_scripts.py`)**:
  - Filters rows where `script_ready` (Column E) is checked and `video_ready` (Column G) is unchecked.
  - Automatically skips completed videos (`video_ready == True`).
  - Groups records by `script_date` into daily files: `<OUTPUT_DIR>/connectivity/ready_scripts/<YYYY-MM-DD>_ready_scripts.csv`.
  - Robust 2-digit (`23/09/26`) and 4-digit date normalization across slash, dash, and dot formats.
  - Automatic fallback to `undated_ready_scripts.csv` and auto-pruning once dates are filled in Google Sheets.
- **Reconciliation Engine (`reconcile_scripts.py`)**:
  - Audits local `scripts_to_see` against Google Sheets canonical order, preserving sheet ordering and appending new local entries.
- **Comprehensive Test Suite Expansion**:
  - 275 automated tests passing across all 5 QA layers (unit, integration, contracts, security, connectivity).
### Controlled Learner Pronunciation Error Simulation & Dynamic Phonetic Vowel Rewriting
- **Pedagogical Controlled Errors**: In roleplay learning scenarios, learners intentionally make realistic mispronunciations (e.g. saying the verb `/rɪˈkɔːrd/` when attempting to say the noun `REcord`, or `/pərˈmɪt/` for `PERmit`).
- **Dynamic Phonetic Vowel Rewriting (`stress_enhancer.py`)**: Neural TTS models (like Qwen3-TTS) have strong language priors that favor standard grammar (forcing noun vowels after *"a new..."*). When visual capitalization indicates an intentional mistake, the system dynamically rewrites the TTS input to its exact phonetic vowel counterpart (`ri-cord`, `per-mit`, `pri-zent`, `pruh-jekt`, `ub-jekt`) to force genuine vowel reduction and stress shift.
- **Citation-Context Safety**: Protects quotation / citation sentences (e.g. *"you must say PERmit"*, *"the word is REcord"*) from being falsely identified as errors.
- **Acoustic Prominence Gate Inversion (`acoustic_evaluator.py`)**: The multi-candidate evaluator scores takes based on the intended error contrast and accounts for Whisper phonetic variations (`RyCord`, `purmit`), ensuring pedagogical error takes win candidate selection.
- **Visual Display & Subtitle Fidelity**: Subtitles (`subtitle_builder.py`) and state JSONs preserve the exact visual capitalization (`reCORD`, `perMIT`) for the viewer.
- **Senior QA Test Suite**: Expanded to **305 automated tests** passing across all layers in ~10 seconds.
