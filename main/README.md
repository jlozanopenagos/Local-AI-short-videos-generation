# Shorts Automation: Automated Generative Short-Form Video Pipeline

An enterprise-grade, deterministic automated pipeline engineered for high-throughput production of educational vertical short-form videos (**YouTube Shorts**, **TikTok**, **Instagram Reels**) tailored for language learners across four target languages: **English**, **French**, **Spanish**, and **Italian**.

The architecture combines local multi-modal generative AI backends (**ComfyUI Diffusion & TTS**, **faster-whisper**, **Transformers MusicGen**, and **FFmpeg** compositing) with an OpenAI-compatible LLM for organic, retention-optimized pedagogical scriptwriting.

---

## Table of Contents
1. [Core Engineering Tenets](#core-engineering-tenets)
2. [End-to-End System Architecture](#end-to-end-system-architecture)
3. [The 4 Content Formats & Narrative Engineering](#the-4-content-formats--narrative-engineering)
4. [Data Architecture & State Machine Design](#data-architecture--state-machine-design)
5. [Hardware Optimization: Low-VRAM (6GB) Engineering](#hardware-optimization-low-vram-6gb-engineering)
6. [The Standing Music Bank Design Pattern](#the-standing-music-bank-design-pattern)
7. [Interactive CLI & Modifier Ecosystem](#interactive-cli--modifier-ecosystem)
8. [External Script Doctoring & LLM Ingestion](#external-script-doctoring--llm-ingestion)
9. [Prerequisites & Installation](#prerequisites--installation)
10. [Configuration & Environment Matrix](#configuration--environment-matrix)
11. [CLI Operational Reference Manual](#cli-operational-reference-manual)
12. [Repository Directory Index](#repository-directory-index)

---

## Core Engineering Tenets

1. **Pipeline-Level Solutions Only (Zero Manual Patching)**:
   Never manually edit generated intermediate files (JSON states, WAV audio, subtitle files, or PNG frames) to fix formatting, word count, or timing discrepancies. All repairs, duration clamping, text normalization, and visual layouts are enforced programmatically inside the core engine, prompt coordinators, FreeType graphics renderers, and audio processors.
2. **Deterministic State Immutability**:
   Every video across the pipeline is governed by a canonical structured identifier (`<Lang><Type><Index:02d>`). Downstream stages never alter IDs or mutate upstream states out-of-order.
3. **Universal Master Database Gate**:
   Assets are tracked in a centralized hybrid database. Pipeline generation scripts **never write `DONE`** status—that privilege belongs solely to the human creator. Completed expressions with `STATUS = DONE` are strictly frozen to prevent accidental overwrites.
4. **Resilient Self-Healing Workflows**:
   All LLM script parsers feature multi-tier extraction strategies (direct JSON decode, `JSONDecoder.raw_decode` stream recovery, bracket boundary scans, and regex repair fallbacks) combined with automated retries on boundary constraint violations.

---

## End-to-End System Architecture

The pipeline models video production as a Directed Acyclic Graph (DAG) partitioned into decoupled stages within `video_creation/`:

```
                           [Prompt Queues]
                     (input/csv/<lang>/expressions_list/)
                                  │
                                  ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │               STAGE 1: video_creation/_A_video_scripts            │
 │   - LLM Ingestion & Format-Specific Prompt Orchestration           │
 │   - Negative Assertion Filters & Script Word-Budget Enforcement   │
 │   - Self-Healing Retries & Automated Chalkboard Fallback          │
 │   - Rich YouTube Metadata & SEO Tag Synthesis                     │
 └────────────────────────────────┬──────────────────────────────────┘
                                  │
                                  ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │               STAGE 2: video_creation/_B_voice_generation         │
 │   - ComfyUI Qwen3-TTS (1.7B fp16) Multi-Speaker Synthesis         │
 │   - Persistent Reference Voice Locking (.wav + seed memory)       │
 │   - Turn-by-turn Dynamic Emotional Acting Inferences              │
 │   - Dynamic Token Budgets & Leading/Trailing Silence Trimming     │
 └───────────────┬────────────────┬──────────────────┬───────────────┘
                 │                │                  │
                 ▼                ▼                  ▼
 ┌────────────────────────┐┌──────────────┐┌─────────────────────────┐
 │  STAGE 3: _C_images    ││STAGE 4: _D_  ││ STAGE 5: _F_thumbnails  │
 │ - ComfyUI SD/Flux      ││Standing Bank ││ - ComfyUI Flux1-dev     │
 │   Scene Generation     ││160 Pre-Made  ││   Reference Model       │
 │ - Native CPU FreeType  ││Curated Audio ││   Stylized Generation   │
 │   Chalkboard Typography││Jams (30s)    ││   (576x1024)            │
 └───────────────┬────────┘└──────┬───────┘└─────────┬───────────────┘
                 │                │                  │
                 └────────────────┼──────────────────┘
                                  │
                                  ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │               STAGE 6: video_creation/_G_video_assembly           │
 │   - Word-Timestamp Audio Transcription via faster-whisper (CPU)   │
 │   - Dynamic ASS Animated Subtitles (Yellow &H0000FFFF, 60pt Bold) │
 │   - Challenge Scene Subtitle Suppression (Prevents Quiz Spoilers) │
 │   - Deterministic Emotion-Based BGM Jam Selection & Ducking       │
 │   - FFmpeg Ken Burns Motion, 2s Intro Bumper, 3s Outro CTA Card   │
 └────────────────────────────────┬──────────────────────────────────┘
                                  │
                                  ▼
                       [Final shorts MP4 Video]
                 (<OUTPUT_DIR>/video_assets/.../final.mp4)
```

### Pre-Flight Service Assertions
Before any processing begins, `config/health.py` validates upstream infrastructure connectivity:
- Confirms local ComfyUI instance status via `/system_stats` HTTP endpoint.
- Asserts LLM availability and valid API connectivity via an authenticated test round-trip.

---

## The 4 Content Formats & Narrative Engineering

Content strategy is divided across four distinct formats, each strictly governed by narrative archetypes, forbidden clichés, and enforced word count budgets:

| Metric / Dimension | EXPRESSION (`*_EXPRESSION.csv`) | ROLEPLAY (`*_ROLEPLAY.csv`) | GAME (`*_GAME.csv`) | FUN_FACTS (`*_FUN_FACTS.csv`) |
| :--- | :--- | :--- | :--- | :--- |
| **Spoken Word Budget** | **85 to 110 words** | **145 to 180 words** | **95 to 125 words** | **95 to 135 words** |
| **Target Runtime** | **38 to 48 seconds** | **60 to 80 seconds** | **40 to 55 seconds** | **40 to 60 seconds** |
| **Speaker Cast** | 1 Voice (Narrator) | 3 Voices (Narrator, P1, P2)| 1 Voice (Narrator) | 1 Voice (Narrator) |
| **Visual Structure** | 5 Narrative Sections | 6 Visual Scenes | 5 Visual Scenes + Chalkboard | 4 Narrative Sections |
| **JSON Keys** | `title`, `hook`, `setup`, `discovery`, `example`, `payoff` | `title`, `hook`, `DIALOGUE_PART_1`–`4`, `PAYOFF` | `title`, `hook`, `challenge`, `pressure`, `answer`, `explanation` | `title`, `hook`, dynamic discovery keys, `payoff` |

### 1. EXPRESSION: Micro-Storytelling
- **Pedagogical Standard**: Etymology, phonetic mechanics, and historical roots are hooks—**practical usage is the primary goal**. The `example` key is the anchor of the script, delivering complete colloquial usage in an authentic register.
- **Narrative Progression**: 
  - `hook` (10–15w): High-curiosity dilemma or insider secret.
  - `setup` (20–25w): Cultural trap or humorous misunderstanding.
  - `discovery` (20–25w): Authentic native nuance and context.
  - `example` (15–20w): Spoken real-world sentence illustrating the idiom.
  - `payoff` (15–20w): Punchy human observation + mandatory call-to-action (CTA).
- **Hard Guardrails**: Banned generic infomercial phrases (*"game changer"*, *"level up"*, *"sounds like a native"*). Mandatory explicit naming of English trap words for false friend lessons. Strict Italian double-consonant phonetic validation.

### 2. ROLEPLAY: Authentic Peer Dialogue
- **Strict Speaker Discipline**:
  - `NARRATOR`: Speaks exclusively in `hook` and `PAYOFF`. Banned from inside dialogue parts.
  - `PERSON_ONE` & `PERSON_TWO`: Strictly alternate turns starting with P1 in every part.
- **Direct-Causality & Zero-Hallucination Quotes**: Speakers strictly respond to the exact words uttered in the immediately preceding turn. No phantom quotes.
- **Trigger Direction**: PERSON_ONE sets up their real-world problem or error; PERSON_TWO introduces the idiom naturally in `DIALOGUE_PART_1`. P1 never self-diagnoses with the idiom in turn 1.
- **TTS Stress Notation**: For heteronyms and minimal pairs, stressed syllables are capitalized (`REcord` vs `reCORD`, `PROject` vs `proJECT`) to instruct the TTS model.
- **Dynamic Setting Injection**: `prompt_builder.py` deterministically cycles 10 realistic settings via `script_id % 10` (airports, street markets, flat-pack assembly, train commutes, gym tracks, café terraces).

### 3. GAME: Fast-Paced Interactive Trivia
- **Trivia Standard**: Pure educational quiz game—no fictional narratives or roleplay acting.
- **5 Authorized Mechanics**:
  1. *Rapid Acoustic Ear Challenge*: Word stress, heteronyms, minimal pairs.
  2. *Native or Weird?*: Idiomatic naturalness vs literal translation trap.
  3. *What Does It Really Mean?*: True figurative meaning vs comical literal trap.
  4. *Counter Reflex / Real-Life Dilemma*: Fast barista, peer, or workplace response.
  5. *Spot the Imposter*: 2 genuine idioms vs 1 fabricated phrase.
- **Acoustic Challenge Delivery (Zero Spoken Blanks)**:
  Spoken challenge audio NEVER contains raw blanks (`___`) or unnatural pauses. The Narrator speaks the sentence fluently and presents options verbally (`"Did you hear A: CONtract or B: conTRACT?"`).
- **Visual Chalkboard Renderer**: Visual blanks (`___`) and letter badges (A, B, C, D) are rendered exclusively on the visual graphic using Pillow and FreeType typography on `empty_chalkboard.png`. Subtitles are suppressed during the challenge to preserve mystery.
- **Suspense Gap**: Audio engine inserts an exact 2.20-second suspense pause (`pressure_gap`) between `pressure` and `answer`.

### 4. FUN_FACTS: Viral Linguistic Curiosities
- **Target Language Localization**: Prompts and state contents are localized 100% in the target language (French, Spanish, Italian, English) to guarantee authentic regional nuance and zero translation artifacts.
- **6 Authorized Formats**: Format A (3 Facts), Format B (One Big Curiosity), Format C (Challenge), Format D (Mystery), Format E (Comparison), Format F (Ranking/List).
- **Factual Integrity**: Programmatic guardrails reject folk etymologies and unverified language myths.

---

## Data Architecture & State Machine Design

### Canonical Script ID Schema
Every script across all 16 prompt queues receives an immutable, collision-free canonical identifier:

$$\textbf{<Language\_Code><Type\_Code><Index:02d>}$$

- **Language Code**: `E` (English), `F` (French), `S` (Spanish), `I` (Italian).
- **Type Code**: `E` (Expression), `G` (Game), `R` (Roleplay), `F` (Fun Facts).
- **Sequential Index**: 2-digit zero-padded index per language/type pair (e.g. `EE01`, `FG01`, `SR02`, `FF15`).

### Streamlined CSV Input Queues
CSVs located in `input/csv/<language>/expressions_list/` retain strictly content-essential fields. The ingestion engine automatically infers:
- `TARGET_LANGUAGE`: Inferred from path and filename.
- `VIDEO_TYPE`: Inferred from filename and ID prefix.
- `SPECIFIC_CONSTRAINT`: Inferred from authoritative prompt rule matrices.
- `STATUS`: Managed by state JSON files and database.

### Universal Hybrid Database & Master Gate
The expression tracking system couples SQLite with per-language CSV files:
- **Database Engine**: `database/expressions.db` (SQLite) synchronized with `database/<lang>_expressions.csv`.
- **Master Gate Rule**: Pipeline generation tools **never mutate STATUS to DONE**. Only the human creator may set an expression to `DONE`. When `STATUS == DONE`, all pipeline stages strictly skip the record, freezing downstream assets.
- **Two-Way Synchronization**: Running `python tools/database/sync_prompts.py` ensures 1-to-1 cross-queue parity, verifies ID alignment, and mirrors CSV updates into SQLite.

### Centralized Pipeline Manifest
- `state/pipeline_status.csv` tracks progress for all 1,200+ prompts across all 6 production stages.
- Stage workers query `core/status_tracker.py` prior to task execution to filter pending items, preventing unnecessary disk I/O.

### Privacy & Schema Template Architecture
To maintain privacy for production content and proprietary prompt libraries, production datasets and runtime states are excluded from version control via `.gitignore`:
- **Private Production Assets**: Production prompt queues (`input/csv/**/*.csv`), database files (`database/*.db`, `database/*.csv`), and intermediate states (`state/**/*.json`) are strictly gitignored.
- **Canonical Schema Templates**:
  - `input/csv/sample_templates/`: Schema models for all 4 video formats (`EXPRESSION.sample.csv`, `GAME.sample.csv`, `ROLEPLAY.sample.csv`, `FUN_FACTS.sample.csv`) and `CALL_TO_ACTIONS.sample.csv`.
  - `database/expressions.sample.csv`: Master schema for expression progress tracking.
  - `state/script_state.sample.json`: Canonical reference schema for stage-by-stage JSON state machines.
  - `.env.example`: Safe environment configuration template.
- **Queue Documentation**: See [input/csv/README.md](file:///c:/AI/shorts_automation/input/csv/README.md) for detailed column requirements and validation standards.

---

## Hardware Optimization: Low-VRAM (6GB) Engineering

The pipeline is engineered to execute end-to-end on budget and consumer GPUs with a **6.00 GB VRAM ceiling** (e.g., NVIDIA GeForce RTX 2060):

```
┌────────────────────────────────────────────────────────────────────────┐
│                   6GB VRAM ALLOCATION STRATEGY                         │
├───────────────────────────────┬────────────────────────────────────────┤
│ Optimization Technique        │ Engineering Mechanism & Impact         │
├───────────────────────────────┼────────────────────────────────────────┤
│ SenseVoice ASR CPU Offload    │ In ComfyUI-Qwen3-TTS/nodes.py, set     │
│                               │ device_str = "cpu". Frees ~700MB VRAM. │
│ fp16 Locked Precision         │ TTS model weights locked to fp16 for   │
│                               │ native Tensor Core acceleration.       │
│ CPU Chalkboard Typography     │ Pillow + FreeType typography on CPU.   │
│                               │ Completely replaces heavy Flux Img2Img │
│                               │ inference for quizzes (0MB VRAM).      │
│ Smart Cache Preservation      │ Intrusive /free calls removed to       │
│                               │ allow ComfyUI weight-caching to work.  │
│ Input Folder Auto-Cleanup     │ Temporary reference WAVs/PNGs deleted  │
│                               │ immediately post-inference.            │
└───────────────────────────────┴────────────────────────────────────────┘
```

---

## The Standing Music Bank Design Pattern

To eliminate repetitive inference overhead and avoid slow per-video music generation, the pipeline incorporates a **Standing Music Bank** in `<OUTPUT_DIR>/bank_music/`:
- **Library Scale**: **160 distinctly orchestrated 30-second jams** (10 unique tracks across 16 categories: 4 languages × 4 video types).
- **Instrumentation Curation**:
  - *Spanish*: Flamenco nylon guitar, rhythmic clapping, lively Cajón.
  - *French*: Parisian café accordion, gypsy jazz swing guitars.
  - *Italian*: Mandolin, Morricone-inspired cinematic acoustic strings.
  - *English*: Warm Rhodes neo-soul, upbeat lo-fi hip-hop grooves.
  - *Game*: Ticking clock suspense and marimba pizzicato.
- **Dynamic Emotion Matching**: In Stage `_G`, `video_assembler.py` analyzes the script's `EMOTIONAL_TRIGGER`, `emotion`, and format, hashing the script ID against candidate jams for consistent variety without repetitive soundtrack fatigue.

---

## Interactive CLI & Modifier Ecosystem

Every pipeline stage provides an interactive terminal interface managed by `core/cli_prompt.py`:

```
=========================================================
  Lingoverse Automation - Part A: Script Generation
=========================================================
Select execution mode:
  [1] Mass-produce all pending assets
  [2] Select specific script(s) by ID (e.g. EE01, EE02)
  [3] Number Range Groups (e.g. 10 - 20)
---------------------------------------------------------
Enter choice (1-3) [default: 1 in 10s]:
```

- **Interactive 10s Countdown**: Automatically defaults to mass-producing pending assets if unattended.
- **Range Expander**: Option `[3]` prompts for start and end integers (e.g. `10` to `20`), automatically expanding across active formats (`EE10..EE20`, `EG10..EG20`, `ER10..ER20`).

### Dedicated CLI Modifier Utilities
Located in `tools/modifiers/`:
- **`script_modifier.py`**: Ingests custom text scripts verbatim, normalizes JSON structure, enforces canonical key order (`title` first), and updates review CSVs in `scripts_to_see/`.
- **`voice_modifier.py`**: Audition reference voices from `open-swara`, manually cast actors per character, and re-generate voiceovers.
- **`image_modifier.py`**: Interactively steer visual prompts, swap scene illustrations, or re-render chalkboard exercises.
- **`subtitles_modifier.py`**: Inspect subtitle timings, execute find/replace on `.ass` files, and re-render final MP4s in seconds without re-running Whisper.

---

## External Script Doctoring & LLM Ingestion

The repository includes `system_prompts_editor.csv` for human-in-the-loop workflows where scripts are polished using external state-of-the-art LLMs (Claude, ChatGPT, Gemini):
- Contains dedicated system prompt personas for each video format (`EXPRESSION`, `ROLEPLAY`, `GAME`, `FUN_FACTS`).
- Defines target durations, word budgets, section keys, and strict editorial rules.
- Polished scripts can be pasted directly into `script_modifier.py` for automated JSON formatting and state injection.

---

## Prerequisites & Installation

### System Requirements
- **Operating System**: Windows 10/11 (PowerShell / CMD) or Linux / macOS
- **Python Runtime**: Python 3.10 or higher
- **GPU**: NVIDIA GPU with 6GB+ VRAM (NVIDIA CUDA 11.8+ or 12.1+)
- **System Binaries**: `ffmpeg` and `ffprobe` installed and added to system `PATH`
- **ComfyUI**: Running ComfyUI instance with standard nodes and Qwen3-TTS wrapper

### Installation Steps

```bash
# 1. Clone repository
git clone <your-repository-url>
cd shorts_automation

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# or .venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize prompt queues & database (optional for new environments)
# Copy templates from input/csv/sample_templates/ into input/csv/<lang>/expressions_list/
python tools/database/sync_prompts.py
```

---

## Configuration & Environment Matrix

Copy the environment template:
```bash
cp .env.example .env
```

Configure your local endpoints in `.env`:

```ini
# ==============================================================================
# LLM Configuration (OpenAI-compatible server e.g. Ollama, LM Studio, vLLM, OpenAI)
# ==============================================================================
LLM_API_KEY=your_api_key_here
LLM_API_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL_NAME=Gemma-4-E2B

# ==============================================================================
# ComfyUI Configuration
# ==============================================================================
COMFY_API_URL=http://127.0.0.1:8188
# COMFY_DIR=C:/AI/ComfyUI_windows_portable
# COMFY_OUTPUT_DIR=C:/AI/ComfyUI_windows_portable/ComfyUI/output
# COMFY_INPUT_DIR=C:/AI/ComfyUI_windows_portable/ComfyUI/input
# OPEN_SWARA_DIR=C:/AI/ComfyUI_windows_portable/open-swara/voices

# ==============================================================================
# Media Storage Directory
# Isolates bulky videos, WAVs, and review CSVs onto high-capacity storage
# ==============================================================================
OUTPUT_DIR=./output
```

---

## CLI Operational Reference Manual

### Master Pipeline Execution
```bash
# Launch end-to-end interactive runner (executes Part A & B sequentially)
python main.py
```

### Stage-by-Stage Execution
```bash
# Part A: Script Generation
python video_creation/_A_video_scripts/main.py
python video_creation/_A_video_scripts/main.py --script-id EE01 --force

# Part B: Voice Generation (TTS)
python video_creation/_B_voice_generation/main.py
python video_creation/_B_voice_generation/main.py --script-id EE01

# Part C: Scene Image Generation
python video_creation/_C_image_generation/main.py
python video_creation/_C_image_generation/main.py --script-id EE01 --seed 42

# Part D: Standing Music Bank Generation
python video_creation/_D_music_generation/main.py --language english --video-type expression

# Part F: Thumbnail Generation
python video_creation/_F_thumbnail_image_generation/main.py --script-id EE01

# Part G: Video Assembly
python video_creation/_G_video_assembly/main.py --script-id EE01
python video_creation/_G_video_assembly/main.py --script-id EE01 --keep-subtitles
```

### Database, Auditing & Maintenance Utilities
```bash
# Display database statistics and progress
python tools/database/db.py stats

# Synchronize all prompt CSVs with SQLite expressions.db
python tools/database/sync_prompts.py

# Run real-time pipeline audit dashboard across all languages
python tools/auditing/status_scraper.py
python tools/auditing/status_scraper.py --samples

# Audit encoding, schema, and cross-format alignment across CSVs
python tools/auditing/audit_all_csvs.py
```

---

## Repository Directory Index

```
shorts_automation/
├── .git/                               # Central Git version control repository
├── .gitignore                          # Global exclusion rules protecting secrets, media & cache
├── main/                               # Production pipeline and core applications
│   ├── config/                         # Central configuration, paths, and health checks
│   │   ├── health.py                   # Pre-flight service health assertions (LLM, ComfyUI)
│   │   ├── settings.py                 # Core path mappings, pauses, and voice maps
│   │   └── __init__.py
│   ├── core/                           # Shared infrastructure and utilities
│   │   ├── cli_prompt.py               # Interactive CLI menus with 10s countdown timers
│   │   ├── expression_db.py            # SQLite + CSV hybrid database implementation
│   │   ├── state_manager.py            # Script state machine and lifecycle manager
│   │   ├── status_tracker.py           # Cross-queue pipeline progress manifest auditor
│   │   └── chalkboard_renderer.py      # FreeType chalk typography renderer on CPU
│   ├── database/                       # Centralized expression stores
│   │   ├── expressions.sample.csv      # Reference schema for master expression tracking
│   │   ├── expressions.db              # SQLite expression database (gitignored, auto-synced locally)
│   │   └── <lang>_expressions.csv      # Auto-synced CSV status trackers (gitignored locally)
│   ├── input/
│   │   ├── csv/
│   │   │   ├── README.md               # Prompt queue documentation and column schemas
│   │   │   ├── sample_templates/       # Canonical .sample.csv templates for all 4 formats & CTAs
│   │   │   ├── <lang>/expressions_list/# Active prompt queues per format (gitignored for privacy)
│   │   │   └── <lang>/game_call_to_action_phrases/ # CTA phrase libraries (gitignored for privacy)
│   │   └── images/                     # Static brand assets
│   │       ├── game_images/            # Empty chalkboard template and waiting illustrations
│   │       ├── openning_closure_images/# Opening bumper (2.0s) and outro CTA cards (3.0s)
│   │       ├── thumbnail_models/       # Reference character portraits for Flux Img2Img
│   │       └── watermark/              # Channel watermark logo (.png)
│   ├── state/                          # Runtime script state artifacts (JSONs ignored by git)
│   │   ├── README.md                   # State directory guide and schema documentation
│   │   └── script_state.sample.json    # Canonical reference state schema
│   ├── tools/                          # Developer utilities and operations CLI
│   │   ├── auditing/                   # Status scrapers, CSV validation, and language check tools
│   │   ├── database/                   # DB sync, ID assignment, and CLI query tools
│   │   ├── maintenance/                # Migration and mass-update utilities
│   │   ├── modifiers/                  # Interactive single & mass asset modifiers
│   │   └── prompt_builders/            # Multi-lingual queue builders and overhaul tools
│   ├── video_creation/                 # Core generation stages (_A through _G)
│   │   ├── workflows/                  # Exported ComfyUI JSON API workflow definitions
│   │   ├── _A_video_scripts/           # Scriptwriting, prompt rules, and metadata synthesis
│   │   ├── _B_voice_generation/        # Qwen3-TTS multi-speaker voice generation
│   │   ├── _C_image_generation/        # Scene illustration generation
│   │   ├── _D_music_generation/        # Standing Music Bank generator and catalog
│   │   ├── _F_thumbnail_image_generation/ # Flux thumbnail generation
│   │   └── _G_video_assembly/          # Whisper subtitles, audio ducking, and FFmpeg assembly
│   ├── main.py                         # Primary execution orchestrator
│   ├── requirements.txt                # Production runtime dependencies
│   ├── system_prompts_editor.csv       # External LLM system prompts for script doctoring
│   ├── .env.example                    # Environment variable configuration template
│   └── README.md                       # Comprehensive pipeline manual (this document)
└── test/                               # Isolated QA test suite and validation layer
    ├── contracts/                      # CSV, JSON, and prompt schema contract tests
    ├── integration/                    # DB, status tracker, and mock service health tests
    ├── security/                       # Secrets, privacy, and oversized binary leak detection
    ├── unit/                           # Pure unit tests for core pipeline modules
    ├── conftest.py                     # Shared pytest/unittest fixtures & sys.path setup
    ├── pytest.ini                      # Pytest discovery settings and custom test markers
    ├── README.md                       # Test suite documentation & CLI execution guide
    ├── requirements-test.txt           # Test-specific dependencies (pytest)
    └── run_tests.py                    # Standalone CLI test runner (zero external dependencies)
```

---

## License & Operational Usage
Private enterprise language-learning automated video production system. Designed for high-retention vertical short-form publishing workflows.
