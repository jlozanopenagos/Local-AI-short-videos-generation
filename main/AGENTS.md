# Project Context: Shorts Automation

## Overview
This project is an automated, enterprise-grade pipeline for generating viral, educational short-form vertical videos (YouTube Shorts, TikTok, Instagram Reels) focusing on language learning across four target languages: **English**, **Spanish**, **French**, and **Italian**. The pipeline coordinates local multi-modal generative AI backends (ComfyUI Diffusion & TTS, faster-whisper, Transformers MusicGen, and FFmpeg compositing) with an OpenAI-compatible local LLM (llama.cpp) for organic, retention-optimized pedagogical scriptwriting.

In addition to headless CLI batch scripts and interactive terminal tools, the project features a full **WebUI MVC application** built with a FastAPI backend and a modern React 19 + TypeScript + Vite frontend.

> [!NOTE]
> **Repository Scope & Isolation**: The `shorts_automation` directory is its own standalone Git repository with an independent git history, working tree, and testing infrastructure. It operates independently from companion projects (e.g. `GoogleSheet_UI_auditor`), exchanging data exclusively through the Google Apps Script Web App API and standard CSV interfaces. All agents must restrict edits strictly within `shorts_automation/`.

---

## The 4 Video Formats

The content strategy consists of four distinct formats queued from CSV files in `input/csv/<language>/expressions_list/` (e.g. `ENGLISH_READY_PROMPTS_*.csv`, `FRENCH_READY_PROMPTS_*.csv`, `SPANISH_READY_PROMPTS_*.csv`, `ITALIAN_READY_PROMPTS_*.csv`):

1. **EXPRESSION (`*_READY_PROMPTS_EXPRESSION.csv`)**:
   - **Purpose**: Explains a linguistic expression, slang term, or idiom in the chosen target language through viral, magnetic micro-storytelling.
   - **Anti-Cliché Standard**: Strict ban on formulaic titles, copied intros, and textbook lectures (e.g. *"The Stress Shift That Changes Everything"*, *"Move the stress just one syllable..."*, *"Si tu traduis [X] littéralement..."*, *"Stop saying [X]!"*, *"Did you know..."*). Banned generic infomercial language in payoffs (*"changes everything"*, *"game changer"*, *"speak like a native"*, *"level up"*, *"unlock"*).
   - **Practical Usage Is the Core Goal**: Etymology and origin stories are hooks and setups — NOT the end goal. The viewer's primary takeaway MUST be practical, confident usage in real life. The `example` key is the anchor of the script.
   - **One Script = One Lesson (Strict)**: Each script teaches EXACTLY one linguistic point.
   - **5 Storytelling Archetypes**:
     1. *The Bizarre Origin / Etymology Mystery*: Historical or visual roots (use only when illuminating usage).
     2. *The Social Blunder / Awkward Translation*: Literal translation trap vs what locals actually heard.
     3. *The Native Slang / Street Level-Up*: Upgrading stiff classroom phrasing to authentic peer banter.
     4. *The Sound & Stress Secret / Minimal Pair Duel*: Contrasting acoustic rhythm, mouth feel, or syllable stress.
     5. *The Dramatic Slice of Life / In-Medias-Res*: High-stakes, relatable human moment where the idiom lands.
   - **English-Speaker False Friend Protocol**: Hook/setup MUST name the English trap word explicitly in quotes (e.g. in Spanish: *"Muchos angloparlantes escuchan 'embarazada' y piensan en 'embarrassed', pero en realidad..."*).
   - **Italian Double Consonant Phonetic Accuracy**: For Italian double consonant minimal pairs (*anno/ano*, *fatto/fato*, *penne/pene*): double consonant = short, tense vowel with held consonant; single consonant = longer, open vowel.
   - **5-Section Micro-Story Narrative Architecture** (EXACTLY 6 JSON keys: `title` + 5 spoken sections):
     - `hook` (Narrator, 10–15 words): High-curiosity opening hook presenting dilemma, absurdity, or insider secret.
     - `setup` (Narrator, 20–25 words): The friction point, formality trap, or humorous literal misunderstanding.
     - `discovery` (Narrator, 20–25 words): Authentic native meaning, cultural context, and conversational nuance.
     - `example` (Narrator, 15–20 words): Everyday realistic spoken sentence demonstrating the complete expression in action with correct emotional register.
     - `payoff` (Narrator, 15–20 words): Specific human observation about the scene, finished with mandatory CTA line.
   - **Target Duration & Word Budget**: **38 to 48 seconds** (strictly **85–110 spoken words** across all 5 spoken sections).
   - **Automated Validation & Repair**: `main.py` validates EXPRESSION scripts for mandatory keys, rejects illegal keys, and enforces the 85–110 word budget with automatic retry on failure.
   - **Status**: **Fully functional and verified end-to-end**.

2. **ROLEPLAY (`*_READY_PROMPTS_ROLEPLAY.csv`)**:
   - **Purpose**: USE previously learned language in an authentic, entertaining real-life situation through engaging character dialogue.
   - **Dialogue Roles & Strict Speaker Discipline (3 Voices)**:
     - `NARRATOR`: Speaks **exclusively** in `hook` and `PAYOFF`. Strictly banned from speaking inside dialogue parts.
     - `PERSON_ONE` & `PERSON_TWO`: Strictly alternate turns in every dialogue part (`PERSON_ONE (Emotion): ...\nPERSON_TWO (Emotion): ...`). Speaker order never flips — every dialogue part begins with PERSON_ONE.
   - **Autonomous Personalities & Anti-Tutor Standard**: Characters are real peers, friends, travel buddies, coworkers, siblings, or roommates talking naturally. Strictly banned: polite tutor trope (no smug corrections), betting clichés (*"Bet you five bucks..."*), and robotic textbook exchanges.
   - **Strict Direct-Causality & Zero-Hallucination Quotes**: Speakers respond directly to each other in real time with zero phantom quotes.
   - **Idiom / Expression Trigger Direction (Critical)**: Target expression MUST arrive in `DIALOGUE_PART_1` as PERSON_TWO's natural speech, reacting to PERSON_ONE's established situation. PERSON_ONE must NEVER self-diagnose by using the target expression in their opening line.
   - **False Friend Direction**: PERSON_ONE makes the described mistake in `DIALOGUE_PART_1`; PERSON_TWO reacts authentically.
   - **`SPECIAL_TREATMENT` Optional Column**:
     - `idiomatic`: Enforces the mandatory 4-part idiomatic arc ending with PERSON_ONE actively modeling the complete idiom in `DIALOGUE_PART_4`.
     - `phonetic`: Heteronym, stress-shift, or minimal pair contrast.
     - `false_friend`: Cross-language false cognate trap.
   - **4-Image Visual Architecture across 4 Dialogue Parts (6 Assembly Beats)**:
     - `hook` (Narrator, 15–20 words): Scenario Establishing Shot.
     - `DIALOGUE_PART_1` (P1 & P2, 30–38 words): Premise & Trigger (auto punch-in cut from hook in assembly).
     - `DIALOGUE_PART_2` (P1 & P2, 30–38 words): 180° Reverse OTS on Speaker 2.
     - `DIALOGUE_PART_3` (P1 & P2, 30–38 words): Kinetic Interaction & Prop Demonstration Shot.
     - `DIALOGUE_PART_4` (P1 & P2, 30–38 words): Breakthrough & Modeling (auto punch-in cut from payoff in assembly).
     - `PAYOFF` (Narrator, 20–25 words): Celebratory Resolution Two-Shot + CTA.
   - **Multi-Character Gender Specification**: Sex of EACH individual character MUST be explicitly specified in prompts (e.g. *"one youthful 15-year-old teen boy and one youthful 15-year-old companion teen girl"*). Dual-character state persistence via `speakers_gender: {"PERSON_ONE": "...", "PERSON_TWO": "..."}`.
   - **Target Duration & Word Budget**: **60 to 80 seconds max** (strictly **145–180 spoken words** across all 6 spoken sections).
   - **Status**: **Fully functional and verified end-to-end**.

3. **GAME (`*_READY_PROMPTS_GAME.csv`)**:
   - **Purpose**: Fast-paced, educational interactive trivia quiz game show to test viewers' language skills.
   - **Format Rules**: Strictly an educational trivia quiz game, NOT a narrative story. The LLM picks the best fit from 5 authorized game mechanics:
     1. *The Rapid Acoustic Ear Challenge*: Word stress, heteronyms, minimal pairs, double consonants.
     2. *Native or Weird? / Which One Sounds Natural?*: False friends, collocations, nuances.
     3. *What Does It Really Mean?*: Idioms and slang.
     4. *The Real-Life Dilemma / Counter Reflex*: In-medias-res pressure situations.
     5. *Spot the Imposter*: 2 genuine expressions vs 1 fabricated imposter.
   - **5 Mandatory Spoken Sections**: `title`, `hook`, `challenge`, `pressure`, `answer`, `explanation`.
   - **Canonical Challenge & Option Syntax Standard (Strict Mandate)**:
     - **No Stress / Capitalization Giveaways**: The challenge test sentence and options MUST be written in natural lowercase (e.g. `record`, `present`, `contract`, `project`). Syllables must **never** be capitalized (`REcord`, `preSENT`, `conTRACT`), which gives away the answer visually.
     - **Option Tags**: Options must strictly begin with an uppercase letter followed by a colon: `A: `, `B: `, `C: `.
     - **Zero Connectors**: No conjunctions (`or`, `and`, `ou`, `o`, `oppure`, `y`, `e`) and no separating commas between options.
     - **Part of Speech Specification for Single Words**: When options are single words (distinguishing noun vs verb heteronyms), a grammatical contextualizer is mandatory (`a record` for noun, `to record` for verb; `a present` vs `to present`; articles/prepositions in other languages).
     - **Period Punctuation**: Every option MUST terminate with a period (`.`). The last option **NEVER ends with a question mark (`?`)**.
     - **Canonical Challenge Examples**:
       - *English*: `"She broke the world record in swimming. Which word did you hear? A: a record.  B: to record."`
       - *Spanish*: `"¿Qué significa realmente la popular frase costar un ojo de la cara? A: Exigir un gran esfuerzo físico.  B: Ser extremadamente caro."`
       - *French*: `"Quelle expression utilise un natif quand quelqu'un ne vient jamais à un rendez-vous ? A: Piser un lapin.  B: Poser un lapin."`
       - *Italian*: `"Cosa dici a un amico prima di un esame importante? A: Forza e coraggio.  B: In bocca al lupo."`
   - **Strict Separation of Challenge and Pressure**:
     - `challenge`: Exclusively contains the test sentence and options (`A: ...  B: ...`).
     - `pressure`: Exclusively contains countdown lines, time limits, and urgency prompts (*"Which one is it? A or B? Your answer is coming!"*, *"Tic-tac !"*, *"Il tempo scorre!"*). Pressure lines must **never** be placed inside `challenge`.
   - **Multi-Property State Synchronization**:
     - `content_metadata.script.challenge`
     - `content_metadata.chalkboard_exercise` (must match the clean challenge)
     - `script_text` (JSON string serialized from updated script)
     - All 388 GAME state files are 100% audited, aligned, and synchronized.
   - **Visuals & Chalkboard Rendering**:
     - `hook`: Dilemma / situation setup in 2D cartoon illustration via ComfyUI.
     - `challenge`: **Native High-Resolution Chalkboard Renderer** (`core/chalkboard_renderer.py`). Uses PIL and FreeType (Segoe Print Bold) to render clean typography directly onto `empty_chalkboard.png` on CPU in milliseconds with zero VRAM overhead.
     - `pressure`: Static pre-made waiting illustration per language from `input/images/game_images/<lang>/<lang>_waiting.png`.
     - `answer` & `explanation`: Real-life resolution illustrations.
   - **Pacing & Audio**: `audio_processor.py` inserts a dedicated 2.20-second suspense pause (`pressure_gap`) between `pressure` and `answer`. Subtitles are suppressed exclusively during `challenge` so options remain unobstructed and the answer is never spoiled in text.
   - **Target Duration & Word Budget**: **40 to 55 seconds** (strictly **95–125 spoken words** across all sections).
   - **Status**: **Fully implemented, verified, and operational**.

4. **FUN_FACTS (`*_READY_PROMPTS_FUN_FACTS.csv`)**:
   - **Purpose**: Umbrella category for short, entertaining, surprising language discoveries following **HOOK $\rightarrow$ DISCOVERY $\rightarrow$ PAYOFF $\rightarrow$ CTA / REACTION**.
   - **6 Authorized Formats**: Format A (3 Facts), Format B (One Big Curiosity), Format C (Challenge), Format D (Mystery), Format E (Comparison), Format F (Ranking/List).
   - **Target Language Localization**: All content in `*_READY_PROMPTS_FUN_FACTS.csv` (`TOPIC`, `FACT_DETAILS`, `HOOK_ANGLE`, `EMOTIONAL_TRIGGER`) is written directly in the target language (French, Spanish, Italian, English).
   - **Dynamic Scene Count (4 vs 6 Scenes)**: Image generation dynamically inspects script section keys, generating 4 images for standard formats or 6 images for multi-fact/historical scripts.
   - **Target Duration & Word Budget**: **40 to 60 seconds** (strictly **95–135 spoken words** across all sections).
   - **Status**: **Fully implemented, verified, and operational**.

---

## WebUI MVC Application Architecture

The project features a full **Model-View-Controller (MVC)** WebUI providing an intuitive graphical interface for all pipeline workflows, real-time background execution, and asset management.

### Architecture Overview

```text
[Browser: React 19 + Vite] ──HTTP / REST──> [FastAPI Backend: main/webui/server.py]
      │                                                │
      ├── SSE Log Stream (/api/jobs/{id}/stream) <─────┤
      └── SSE Sync Stream (/api/sheets/sync/stream) <──┤
                                                       ▼
                                           [Job Manager & Adapters]
                                        (main/webui/jobs/manager.py)
                                                       │
                                   ┌───────────────────┼───────────────────┐
                                   ▼                   ▼                   ▼
                              [VoiceAdapter]     [ImagesAdapter]    [ThumbnailsAdapter]
                               (Stage B)           (Stage C)           (Stage F)
```

- **Frontend (`main/webui/frontend/`)**: React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons. Built assets are compiled directly into `main/webui/static/` and served as a single-page application.
- **Backend API (`main/webui/server.py`)**: FastAPI application mounted with modular routers:
  - `/api/scripts`: Script catalog querying, filtering, search, detail modals, and ID validation.
  - `/api/media`: Audio, image, and video streaming with proper MIME types.
  - `/api/jobs`: Background job queue management, execution console, SSE log streaming, pause/cancel.
  - `/api/system`: Real-time service monitoring (ComfyUI and Llama-server status, GPU VRAM, PIDs) and service control.
  - `/api/sheets`: Google Sheets 4-step synchronization worker and progress streaming.
- **Launcher**: Launch with a single command:
  ```powershell
  py main/tools/webui.py
  ```
  The launcher checks Python dependencies, validates Node/npm build status, resolves port conflicts automatically, and opens the default browser.

### The 4 WebUI Views

1. **Dashboard (`/`)**:
   - **System Health Cards**: Live monitoring of ComfyUI and Llama-server processes, GPU VRAM allocation, PIDs, and one-click start/stop controls.
   - **Stage Metrics**: Real-time asset completion counts across all 6 pipeline stages.
   - **Filterable Script Catalog**: Instant filtering by Language (English, French, Italian, Spanish), Video Format (Expression, Game, Roleplay, Fun Facts), and Pipeline Status (Pending, Done, In Progress). Searchable by expression or ID.
   - **Script Detail Modal (`ScriptDetailModal.tsx`)**: Inspects script narrative sections, master audio playback with interactive waveform, scene illustrations, thumbnail preview, and YouTube SEO metadata (Title, Description, Tags, Hashtags).
2. **Job Queue / Execution Console (`/jobs`)**:
   - Asynchronous background job queue (`webui/jobs/manager.py`) executing batch jobs across pipeline stages.
   - Live terminal log stream (Server-Sent Events) with pause, resume, and cancel buttons.
   - Step-by-step progress bars showing script completion count, current stage, and elapsed time.
3. **Handle Google Sheets Changes (`/sheets`)**:
   - **Step 1/4 (Cache Purge)**: Purges stale cached CSVs in `input/csv/script_to_change/` to ensure fresh synchronization.
   - **Step 2/4 (API Fetch)**: Connects to the Google Apps Script Web App API across all 16 sheets, fetching Column D (`SCRIPT_CHANGED` / `NEW_SCRIPT`).
   - **Step 3/4 (Audit & Diff)**: Audits differences against local State JSONs using GAME-aware comparison logic that eliminates false positives from option formatting.
   - **Step 4/4 (Apply & Reset)**: Applies script modifications into State JSONs, cleans GAME challenges, resets downstream stages (`voice`, `images`, `thumbnails`, `assembly`) to `pending`, and refreshes review CSVs.
4. **Mass Assets Creation (`/mass-creation`)**:
   - Mass generation of **Scene Images** (Stage C), **Voice Files** (Stage B), or **Thumbnail Images** (Stage F) for arbitrary lists of script IDs across all languages and video formats.
   - **3 ID Collection Modes**:
     - *Manual Input*: Comma/space/line-separated IDs with debounced real-time validation via `POST /api/scripts/validate-ids`.
     - *CSV Drag & Drop*: Upload CSV/TXT files to automatically extract and validate target script IDs.
     - *Preset Catalogs*: One-click buttons to load "All Pending Images", "All Pending Voice", or "All Pending Thumbnails".
   - **Interactive Validated Script Grid**: Clickable chips showing format, language, and current asset status, with quick-remove buttons and one-click inspection via `ScriptDetailModal`.
   - **Forced Re-generation**: Toggle (`force: true` default) ensuring assets are re-rendered and overwritten even if the state JSON marks them as `done`.
   - **Pre-flight Service Checks**: Displays warnings if ComfyUI is offline when images or thumbnails are selected.
   - **Execution Console Redirect**: Launches the batch directly into the background Job Manager and navigates to the Execution Console for live tracking.

---

## Hardware Environment & GPU VRAM Management

- **Target Baseline**: NVIDIA GPU with 6GB+ VRAM (e.g. RTX 2060, RTX 3060).
- **Automated VRAM Arbiter (`core/llama_manager.py`)**:
  - `LlamaManager` manages the local `llama-server` process in the background.
  - Exposes `ensure_llama_stopped()` and `ensure_llama_running()` as both module functions and class methods.
  - In Stage B (`VoiceAdapter` / `voice.py`), `ensure_llama_stopped()` is called immediately before Qwen3-TTS audio synthesis to free ~2GB VRAM.
  - CLI management tool: `py main/tools/llama.py {start|stop|restart|status|logs}`.
- **Headless ComfyUI Supervisor (`tools/comfy.py` & `core/comfy_manager.py`)**:
  - Spawns ComfyUI in the background via `pythonw.exe` (`CREATE_NO_WINDOW | DETACHED_PROCESS`), immunizing the system against Windows QuickEdit terminal freeze deadlocks.
  - CLI management tool: `py main/tools/comfy.py {start|stop|restart|status|logs}`.
- **Low-VRAM Optimizations**:
  - SenseVoice ASR offloaded to CPU in ComfyUI Qwen3-TTS.
  - Qwen3-TTS precision locked to `fp16`.
  - Stage-boundary VRAM reclamation via `/free` HTTP calls.
  - Native CPU FreeType chalkboard typography offload (zero VRAM overhead).

---

## Google Sheets Connectivity Suite

The `connectivity/` package coordinates Google Sheets data exchanges:

1. **Option A Master Router (`connectivity/core/endpoints.py`)**: 16 endpoints mapped to Google Sheets IDs via Google Apps Script Web App (`google_apps_script.js`).
2. **Feature 1 (`sync_sheets.py`)**: Pulls sheet records into `<OUTPUT_DIR>/connectivity/synced_sheets/` (Columns A-C or A-D).
3. **Feature 2 (`fetch_corrected_scripts.py`)**: Filters Column D (`SCRIPT_CHANGED`) and exports corrections into `input/csv/script_to_change/` with schema `ID, NEW_SCRIPT`.
4. **Feature 2b (`tools/check_script_changes.py`)**:
   - Deep comparison engine between CSV Column D corrections and local runtime State JSONs.
   - **GAME-Aware Normalization**: Ignores formatting differences in option connectors, stress capitalization, and option punctuation (`?` vs `.`) to eliminate false positives.
   - CLI flags: `--check-only`, `--apply`, `--csv <file>`, `--script-id <ID>`.
5. **Feature 3 (`reconcile_scripts.py`)**: Reconciles local scripts against Google Sheets order into `scripts_to_post/`.
6. **Feature 4 (`post_scripts.py`)**: Safely publishes scripts to Google Sheets (preserves Column D in 3-column mode).
7. **Feature 5 (`scan_ready_scripts.py`)**: Scans Google Sheets for rows where Column E (`script_ready`) is checked and Column G (`video_ready`) is unchecked, exporting daily batch CSVs.

---

## Structured Script ID Standard

Every video across the pipeline is assigned a canonical, non-overlapping identifier following the format:

$$\textbf{<Language\_Code><Type\_Code><Index:02d>}$$

- **Language Code** (1st char): `E` (English), `F` (French), `S` (Spanish), `I` (Italian).
- **Video Type** (2nd char): `E` (Expression), `G` (Game), `R` (Roleplay), `F` (Fun Facts).
- **Sequential Index** (3rd–4th digits): 2-digit zero-padded index per (language, type) pair (`01`, `02`, ..., `99`, `100`+).
- **1,224 Synchronized Records across 16 CSVs**:
  - **English** (372): 100 `EE` + 100 `EG` + 100 `ER` + 72 `EF`
  - **French** (270): 90 `FE` + 90 `FG` + 90 `FR`
  - **Spanish** (279): 93 `SE` + 93 `SG` + 93 `SR`
  - **Italian** (303): 105 `IE` + 105 `IG` + 105 `IR`
- **Immutability**: Once generated into `state/<language>/<video_type>/script_<ID>.json`, downstream stages strictly inherit the state's ID. **IDs are never re-created or altered across pipeline stages**.

### Current Production State & Asset Counts
- **Stage A (Scripts)**: 1,223 / 1,224 JSON state files generated.
- **Physical Assets on Disk (`D:\AI\output\video_assets`)**:
  - `*_master.wav`: 190 audio files
  - `images/` directories (≥4 images): 249 illustration sets
  - `thumbnail.png`: 803 thumbnails
  - `*_final.mp4`: 155 final assembled shorts
  - `bank_music`: 160 pre-rendered BGM jam tracks (10 per category across all 16 matrices)
- **Downstream Invalidation Note**: Downstream stages are intentionally set to `pending` whenever a script is edited or updated from Google Sheets Column D, ensuring that modified scripts are re-rendered into audio, subtitles, and video.

---

## Key Files & Entry Points

| File / Folder | Role |
| :--- | :--- |
| `main/tools/webui.py` | Dedicated launcher for the WebUI MVC application (FastAPI on port 8190 + React 19 SPA). |
| `main/webui/server.py` | FastAPI backend server with modular routers for `scripts`, `media`, `jobs`, `system`, and `sheets`. |
| `main/webui/frontend/` | React 19 + TypeScript + Vite frontend source code. |
| `main/webui/static/` | Compiled static production bundle served directly by FastAPI. |
| `main/webui/jobs/manager.py` | Background Job Manager with SSE/WebSocket logging and pipeline stage adapters (`voice`, `images`, `thumbnails`, `assembly`). |
| `main/main.py` | Main CLI orchestrator to run pipeline stages sequentially with health verification. |
| `main/core/llama_manager.py` | Process supervisor for local llama.cpp server with VRAM freeing and status monitoring. |
| `main/tools/llama.py` | CLI supervisor tool for manual control of llama-server (`start`, `stop`, `status`, `logs`). |
| `main/tools/comfy.py` | Headless ComfyUI background supervisor (`start`, `stop`, `status`, `logs`). |
| `main/tools/check_script_changes.py` | CLI auditor & synchronizer between Google Sheets Column D CSVs and local State JSONs. |
| `main/video_creation/_A_video_scripts/script_modifier.py` | Script modifier supporting direct parsing, LLM structuring, and automatic `clean_game_challenge()` enforcement. |
| `main/video_creation/_A_video_scripts/prompts/game_rules.py` | Authoritative GAME prompt rules enforcing clean option formatting, no stress giveaways, and separation of challenge and pressure. |
| `main/connectivity/` | Google Sheets integration suite (Apps Script Web App client, fetcher, reconciler, poster, scanner). |
| `test/run_tests.py` | Test runner for automated unit, integration, contract, and WebUI API tests (340 tests passing 100%). |

---

## Agent Guidelines & Best Practices

1. **State Persistence**: Always read and update script states via `core/state_manager.py` (`StateManager`).
2. **Audio Duration Rule**: Adhere strictly to target durations: **38–48s** (85–110w) for EXPRESSION, **40–55s** (95–125w) for GAME, **60–80s max** (145–180w) for ROLEPLAY, and **40–60s** (95–135w) for FUN_FACTS.
3. **GAME Challenge Formatting**: Always enforce that GAME challenges use neutral words (no uppercase stress), start options with `A: `, `B: `, include no option connectors, specify grammatical category for single words (`a record` vs `to record`), end each option with `.`, never end with `?`, and keep `chalkboard_exercise` synchronized.
4. **GPU VRAM Discipline**: Never run ComfyUI and Llama-server under high concurrent load on 6GB GPUs. Call `ensure_llama_stopped()` before Qwen3-TTS or ComfyUI generation.
5. **Pipeline-Level Solutions Only (Zero Manual Patching)**: Fix all errors inside the core engine, prompt coordinators, FreeType renderers, and audio processors so the pipeline operates autonomously end-to-end.
6. **Master Expression Database (User-Only 'DONE')**: Pipeline scripts NEVER mutate `STATUS` to `DONE`—that privilege belongs solely to the human creator. Completed expressions with `STATUS = DONE` are strictly frozen.
7. **Verbatim Script Ingestion**: When updating scripts from `script_to_change/` or Google Sheets, the spoken words must be preserved verbatim in `content_metadata.script`.
