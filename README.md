# Shorts Automation: Automated Generative Short-Form Video Pipeline

An enterprise-grade, deterministic automated pipeline engineered for high-throughput production of educational vertical short-form videos (**YouTube Shorts**, **TikTok**, **Instagram Reels**) tailored for language learners across four target languages: **English**, **French**, **Spanish**, and **Italian**.

The architecture combines local multi-modal generative AI backends (**ComfyUI Diffusion & TTS**, **faster-whisper**, **Transformers MusicGen**, and **FFmpeg** compositing) with an OpenAI-compatible LLM for organic, retention-optimized pedagogical scriptwriting.

> [!NOTE]
> **Repository Boundary**: `shorts_automation` is a standalone, independent Git repository dedicated exclusively to automated generative video production. While it shares the broader ecosystem objective with sibling projects (e.g. `GoogleSheet_UI_auditor`), it is completely isolated and decoupled, exchanging data only via Google Sheets Apps Script Web App endpoints and standardized CSV schemas.

---

## Repository Architecture

The codebase is strictly organized into two isolated domains:

```text
shorts_automation/
├── .git/                               # Central Git version control repository
├── .gitignore                          # Global exclusion rules protecting secrets, media & cache
├── main/                               # Production pipeline and core applications
│   ├── config/                         # Central configuration, paths, and health checks
│   ├── connectivity/                   # Google Sheets integration suite (fetch, sync, safe publish)
│   ├── core/                           # Shared infrastructure, DB models, state machine, llama manager
│   ├── database/                       # Centralized expression stores (SQLite + CSV)
│   ├── input/                          # Proprietary prompt CSV queues & brand image assets
│   ├── state/                          # Runtime script state artifacts (JSON)
│   ├── tools/                          # CLI utilities (webui, llama, comfy, check_script_changes, modifiers)
│   ├── webui/                          # Modern WebUI studio (FastAPI server + React 19 SPA frontend)
│   ├── video_creation/                 # 6 generation stages (_A through _G)
│   ├── main.py                         # Primary execution orchestrator
│   ├── requirements.txt                # Production runtime dependencies
│   ├── system_prompts_editor.csv       # External LLM system prompts for script doctoring
│   ├── .env.example                    # Environment variable configuration template
│   └── README.md                       # Comprehensive operational manual
└── test/                               # Isolated QA test suite and validation layer
    ├── connectivity/                   # Google Sheets integration & data contract tests
    ├── integration/                    # DB, status tracker, schema contracts, security & mock service health tests
    ├── unit/                           # Pure unit tests for core pipeline modules
    ├── webui/                          # WebUI API & Job Manager test layer
    ├── conftest.py                     # Shared pytest/unittest fixtures & sys.path setup
    ├── pytest.ini                      # Pytest discovery settings and custom test markers
    ├── README.md                       # Test suite documentation & CLI execution guide
    ├── requirements-test.txt           # Test-specific dependencies (pytest)
    └── run_tests.py                    # Standalone CLI test runner (zero external dependencies)
```

---

## Quick Start

### 1. Prerequisites
- Python 3.10+ (Windows `py` launcher or `python3`)
- NVIDIA GPU with 6GB+ VRAM (recommended for local ComfyUI generation)
- Local ComfyUI instance with Qwen3-TTS and Flux workflows

### 2. Environment Setup
```powershell
# Copy environment template inside main/
Copy-Item main/.env.example main/.env

# Install production dependencies
pip install -r main/requirements.txt
```

### 3. Running the Pipeline

#### Option A: Modern WebUI Dashboard (Recommended)
Launch the unified browser-based management studio:
```powershell
py main/tools/webui.py
```
Automatically launches FastAPI, serves the React 19 SPA on `http://127.0.0.1:8190`, and opens your default browser with access to Dashboard, Job Queue, Google Sheets Sync, and Mass Assets Creation.

#### Option B: Terminal Orchestrator & CLI Stages
```powershell
# Run the master orchestrator
py main/main.py

# Run individual generation stages (with interactive 10s countdown or CLI flags)
py main/video_creation/_A_video_scripts/main.py --script-id EE01 --force
py main/video_creation/_B_voice_generation/main.py --auto --candidates 3
py main/video_creation/_C_image_generation/main.py --from-csv input/csv/image_to_change/batch.csv
py main/video_creation/_G_video_assembly/main.py --script-id EE01
```

### 4. Running the Automated QA Test Suite
The test layer requires zero external dependencies and runs completely in memory or isolated temporary sandboxes:
```powershell
# Run all 358 automated tests across 4 layers (unit, integration & contracts, connectivity, webui)
py test/run_tests.py

# Run specific layers
py test/run_tests.py --unit
py test/run_tests.py --integration
py test/run_tests.py --contract
py test/run_tests.py --security
py test/run_tests.py --connectivity
py test/run_tests.py --webui
```

### 5. Expression Database & CLI Tools
```powershell
# View database statistics across all languages
py main/tools/database/db.py stats

# Synchronize input CSV queues with SQLite expressions.db
py main/tools/database/sync_prompts.py

# Run real-time pipeline audit dashboard across all languages
py main/tools/auditing/status_scraper.py

# Mass reset pipeline stage status across state files (e.g. voice_generation to pending)
py main/tools/database/reset_stage_status.py --stage voice_generation --yes

# Audit and synchronize Column D script corrections (from Google Sheets) to State JSONs
py main/tools/check_script_changes.py --check-only
py main/tools/check_script_changes.py --apply

# Headless ComfyUI Supervisor (Windowless background daemon, zero QuickEdit freezes)
py main/tools/comfy.py start
py main/tools/comfy.py status
py main/tools/comfy.py logs -f
py main/tools/comfy.py stop

# Headless LLM Supervisor (llama.cpp server management & VRAM arbitration)
py main/tools/llama.py start
py main/tools/llama.py status
py main/tools/llama.py logs -f
py main/tools/llama.py stop
```

### 6. Google Sheets Connectivity Suite
```powershell
# Feature 1: Synchronize Google Sheets to local connectivity CSVs (3 or 4 columns)
py main/connectivity/sync_sheets.py

# Feature 2: Pull Column D (SCRIPT_CHANGED) revisions to input/csv/script_to_change/
py main/connectivity/fetch_corrected_scripts.py

# Feature 2b: Audit and apply Column D script changes to local state JSONs (resetting downstream stages)
py main/tools/check_script_changes.py --check-only
py main/tools/check_script_changes.py --apply

# Feature 3: Reconcile local scripts to match Google Sheets order into scripts_to_post/
py main/connectivity/reconcile_scripts.py

# Feature 4: Safely publish scripts to Google Sheets (3-col or 4-col options)
py main/connectivity/post_scripts.py

# Feature 5: Scan ready scripts (Columns E-H) and export daily CSVs by date
py main/connectivity/scan_ready_scripts.py --all
```

---

## Documentation Links

- **[main/README.md](main/README.md)**: Full operational manual, narrative engineering principles, 4 content formats, hardware optimization guide, and modifier ecosystem.
- **[main/webui/README.md](main/webui/README.md)**: WebUI backend manual, API endpoints, job runner, SSE streaming, and launcher.
- **[main/webui/frontend/README.md](main/webui/frontend/README.md)**: WebUI frontend architecture, React 19 SPA, 4 primary views, and build workflow.
- **[main/connectivity/README.md](main/connectivity/README.md)**: Google Sheets connectivity manual, Option A routing, Apps Script deployment, and safe publishing rules.
- **[main/AGENTS.md](main/AGENTS.md)**: System architecture, agent guidelines, prompt rules, and developer directives.
- **[main/input/csv/README.md](main/input/csv/README.md)**: Prompt queue schemas and `script_to_change` verbatim ingestion guide.
- **[main/state/README.md](main/state/README.md)**: State directory architecture, GAME format rules, and downstream stage invalidation.
- **[test/README.md](test/README.md)**: QA engineering principles, test suite structure, and CI test runner guide.

---

## Current Production State & Asset Inventory

The pipeline manages a canonical master catalog of **1,224 language learning scripts** across four target languages and four video formats, coordinated through `main/core/state_manager.py` and persistent output storage at `D:\AI\output\video_assets`.

### 1. Script State Catalog Breakdown
- **Total Master Scripts**: **1,224**
  - **English (372)**: 100 Expression (`EE`), 100 Game (`EG`), 100 Roleplay (`ER`), 72 Fun Facts (`EF`)
  - **French (270)**: 90 Expression (`FE`), 90 Game (`FG`), 90 Roleplay (`FR`)
  - **Spanish (279)**: 93 Expression (`SE`), 93 Game (`SG`), 93 Roleplay (`SR`)
  - **Italian (303)**: 105 Expression (`IE`), 105 Game (`IG`), 105 Roleplay (`IR`)
- **Stage A (Script Generation)**: **1,223 / 1,224 DONE** (99.9% complete)

### 2. Physical Assets on Disk (`D:\AI\output\video_assets`)
- **Master Voiceovers (`*_master.wav`)**: **190 completed audio files**
- **Scene Image Sets (`images/` folders with ≥4 PNGs)**: **249 completed scene sets**
- **YouTube Thumbnails (`thumbnail.png`)**: **803 completed thumbnails**
- **Final Assembled Videos (`*_final.mp4`)**: **155 completed videos**
- **Standing BGM Jam Bank (`D:\AI\output\bank_music`)**: **160 pre-rendered music tracks** (10 curated jams per category across all 16 language/type matrices)

> [!NOTE]
> **State Machine Invalidation Behavior**: Whenever Column D script edits are synced from Google Sheets or applied via `check_script_changes.py --apply`, downstream stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) are intentionally invalidated back to `"pending"`. This architectural safety gate ensures modified spoken wording is deterministically re-rendered into audio, subtitles, and video, explaining why 155 `.mp4` videos exist on disk while the tracking database marks scripts as pending re-render.

### 3. QA Testing Metrics
- **Automated Tests**: **340 tests passing 100%** across Unit, Integration & Schema Contracts, Connectivity, and WebUI API layers (`py test/run_tests.py` in ~24s).

---

## Recent Changes

### Latest Release: Modern WebUI Studio, Mass Assets Creation, Canonical GAME Format & VRAM Arbiter
- **Modern WebUI Management Studio (`main/webui/`)**:
  - Full-stack browser application powered by **FastAPI** backend and **React 19 + TypeScript + Vite + Tailwind CSS** frontend.
  - Pre-compiled production bundle served directly from `main/webui/static/` with zero Node.js runtime needed in production.
  - Launched with a single command: `py main/tools/webui.py`.
  - 4 Purpose-Built Views:
    - **Dashboard**: Live system health cards (LLM server, ComfyUI instance, GPU VRAM metrics) and global pipeline progress statistics.
    - **Job Queue**: Task manager with real-time ANSI terminal log streaming via Server-Sent Events (SSE: `GET /api/jobs/{id}/events`) and abort controls.
    - **Google Sheets Sync**: Interactive 4-step graphical workflow (Fetch revisions -> Audit diffs -> Apply changes -> Scan ready scripts).
    - **Mass Assets Creation Studio**: Batch production studio for Voiceovers (`Stage _B`), Scene Images (`Stage _C`), or Chalkboard Thumbnails (`Stage _F`). Supports arbitrary ID lists, instant validation (`POST /api/scripts/validate-ids`), and forced re-generation (`All Assets` vs `Missing Only`).
- **Canonical GAME Format Standardization & Zero-Contamination Audit**:
  - Audited and standardized all **388 GAME state files** (`EG*`, `FG*`, `SG*`, `IG*`) across the repository to 100% compliance:
    - **Neutral Lowercase Speech**: Spoken challenge sentences strictly use natural lowercase speech. Purged all uppercase stress giveaways (e.g. `REcord`, `PREsent`, `CONtract`) that spoiled the quiz for listeners.
    - **Explicit Option Tags**: Options strictly start with uppercase letter tags: `A: `, `B: `, etc.
    - **Zero Connectors**: Purged all coordinating conjunctions (`or`, `and`, `o`, `ou`, `oppure`, `e`) and preceding commas between options.
    - **Carrier Context for Single Words**: Single-word options explicitly state parts of speech or natural carriers (e.g. `A: a record. B: to record.`).
    - **Period Termination**: Every option terminates with a period (`.`). The last option never ends with `?`.
    - **Strict Challenge vs. Pressure Partitioning**: Urgency/countdown lines (`Which one is it? A or B? Your answer is coming!`) are strictly partitioned into `pressure`, completely purging countdown pollution from `challenge`.
    - **Synchronized State Fields**: Synchronized `chalkboard_exercise` with `challenge` and rebuilt `script_text` dynamically.
- **Dual-Process Hardware VRAM Arbiter (`core/llama_manager.py` & `tools/llama.py`)**:
  - Implemented `LlamaManager` to coordinate GPU memory allocation between the local LLM server and ComfyUI TTS/diffusion.
  - Automatically halts or pauses the LLM server (`ensure_llama_stopped()`) prior to Qwen3-TTS audio synthesis in Stage B and WebUI jobs, freeing ~3-4GB of VRAM and completely preventing Out-Of-Memory (OOM) crashes on 6GB GPUs (RTX 2060).
  - Automatically restarts the LLM server (`ensure_llama_running()`) once audio processing finishes.
  - Windowless background CLI supervisor available at `py main/tools/llama.py`.

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
