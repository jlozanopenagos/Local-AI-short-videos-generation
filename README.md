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

# Run individual generation stages
py main/video_creation/_A_video_scripts/main.py
py main/video_creation/_B_voice_generation/main.py
py main/video_creation/_C_image_generation/main.py
py main/video_creation/_G_video_assembly/main.py
```

### 4. Running the Automated QA Test Suite
The test layer requires zero external dependencies and runs completely in memory or isolated temporary sandboxes:
```powershell
# Run all 131 automated tests across 5 layers (unit, integration, contracts, security, connectivity)
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
# Feature 1: Synchronize all Google Sheets to local connectivity CSVs
py main/connectivity/cli.py

# Feature 2: Pull Column D (SCRIPT_CHANGED) revisions to input/csv/script_to_change/
py main/connectivity/corrected_scripts/corrected_scripts_fetching.py

# Feature 3: Safely publish review scripts from D:\AI\output\scripts_to_see to Google Sheets
py main/connectivity/post_scripts/post_scripts.py
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

### `feature/connectivity` — Google Sheets Suite, Verbatim Ingestion & Deduplication
- **Modular Connectivity Suite (`main/connectivity/`)**:
  - Modular architecture: `core/`, `sheet_sync/`, `corrected_scripts/`, `post_scripts/`.
  - Master Web App with Option A routing (`?id=<SPREADSHEET_ID>`) supporting both `doGet` (reads) and `doPost` (in-place updates & appends).
  - Syncs to `D:\AI\output\connectivity\<lang>\<type>\<lang>_<type>_connectivity.csv`.
  - Column D safety rule: Publishing via `post_scripts.py` modifies **only Columns A, B, and C**. Column D (`SCRIPT_CHANGED`) is **strictly preserved and never overwritten**.
- **Zero-Hallucination Verbatim Script Changes (`script_to_change`)**:
  - `parse_user_script_into_sections()` directly maps user-crafted paragraphs into canonical JSON format keys.
  - Spoken text is preserved **100% verbatim** in `content_metadata.script` with zero LLM alterations.
  - CSV parser enhanced with `skipinitialspace=True` and regex comma sanitization to prevent row truncation.
- **Scraper Deduplication & Sample Exclusion**:
  - Excluded `.sample` templates in `scrapper_script.py` and enforced unique canonical ID tracking per language/type pair, guaranteeing 100% duplicate-free review CSVs in `D:\AI\output\scripts_to_see`.
- **Comprehensive Test Suite Expansion**:
  - 131 automated tests across all 5 QA layers (unit, integration, contracts, security, connectivity).

