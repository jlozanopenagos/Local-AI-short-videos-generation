# Shorts Automation: Automated Generative Short-Form Video Pipeline

An enterprise-grade, deterministic automated pipeline engineered for high-throughput production of educational vertical short-form videos (**YouTube Shorts**, **TikTok**, **Instagram Reels**) tailored for language learners across four target languages: **English**, **French**, **Spanish**, and **Italian**.

The architecture combines local multi-modal generative AI backends (**ComfyUI Diffusion & TTS**, **faster-whisper**, **Transformers MusicGen**, and **FFmpeg** compositing) with an OpenAI-compatible LLM for organic, retention-optimized pedagogical scriptwriting.

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
│   ├── core/                           # Shared infrastructure, DB models, state machine
│   ├── database/                       # Centralized expression stores (SQLite + CSV)
│   ├── input/                          # Proprietary prompt CSV queues & brand image assets
│   ├── state/                          # Runtime script state artifacts (JSON)
│   ├── tools/                          # CLI utilities (auditing, modifiers, sync, builders)
│   ├── video_creation/                 # 6 generation stages (_A through _G)
│   ├── main.py                         # Primary execution orchestrator
│   ├── requirements.txt                # Production runtime dependencies
│   ├── system_prompts_editor.csv       # External LLM system prompts for script doctoring
│   ├── .env.example                    # Environment variable configuration template
│   └── README.md                       # Comprehensive operational manual
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
# Run all 223 automated tests across 5 layers (unit, integration, contracts, security, connectivity)
py test/run_tests.py

# Run specific layers
py test/run_tests.py --unit
py test/run_tests.py --integration
py test/run_tests.py --contract
py test/run_tests.py --security
py test/run_tests.py --connectivity
```

### 5. Expression Database & CLI Tools
```powershell
# View database statistics across all languages
py main/tools/database/db.py stats

# Synchronize input CSV queues with SQLite expressions.db
py main/tools/database/sync_prompts.py

# Run real-time pipeline audit dashboard across all languages
py main/tools/auditing/status_scraper.py
```

### 6. Google Sheets Connectivity Suite
```powershell
# Feature 1: Synchronize Google Sheets to local connectivity CSVs (3 or 4 columns)
py main/connectivity/sync_sheets.py

# Feature 2: Pull Column D (SCRIPT_CHANGED) revisions to input/csv/script_to_change/
py main/connectivity/fetch_corrected_scripts.py

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
- **[main/connectivity/README.md](main/connectivity/README.md)**: Google Sheets connectivity manual, Option A routing, Apps Script deployment, and safe publishing rules.
- **[main/AGENTS.md](main/AGENTS.md)**: System architecture, agent guidelines, prompt rules, and developer directives.
- **[main/input/csv/README.md](main/input/csv/README.md)**: Prompt queue schemas and `script_to_change` verbatim ingestion guide.
- **[test/README.md](test/README.md)**: QA engineering principles, test suite structure, and CI test runner guide.

---

## Recent Changes

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
  - Groups records by `script_date` into daily files: `D:\AI\output\connectivity\ready_scripts\<YYYY-MM-DD>_ready_scripts.csv`.
  - Robust 2-digit (`23/09/26`) and 4-digit date normalization across slash, dash, and dot formats.
  - Automatic fallback to `undated_ready_scripts.csv` and auto-pruning once dates are filled in Google Sheets.
- **Reconciliation Engine (`reconcile_scripts.py`)**:
  - Audits local `scripts_to_see` against Google Sheets canonical order, preserving sheet ordering and appending new local entries.
- **Comprehensive Test Suite Expansion**:
  - 223 automated tests passing across all 5 QA layers (unit, integration, contracts, security, connectivity).

