# Shorts Automation CLI Tools & Utilities

This folder contains command-line utilities and interactive review tools for the shorts automation pipeline, strictly organized into 5 functional subdirectories.

---

## Folder Organization Overview

| Subdirectory | Focus / Responsibility | Tools Included |
| :--- | :--- | :--- |
| **`modifiers/`** | Canonical interactive asset & script modification forwarders | `script_modifier.py`, `voice_modifier.py`, `image_modifier.py`, `subtitles_modifier.py` |
| **`auditing/`** | Quality inspection, metrics & health checks | `status_scraper.py`, `json_health_checker.py`, `scrapper_script.py` |
| **`database/`** | Expression database, queue sync & stage resets | `db.py`, `sync_prompts.py`, `reset_stage_status.py` |
| **`prompt_builders/`**| System editor prompts generator | `generate_editor_prompts_csv.py` |
| **`voice_quality/`** | Qwen3-TTS VoiceDesign 7-register generator & reference voice auditor | `build_voicedesign_references.py`, `audit_reference_voices.py` |
| **Root Tools** | Headless ComfyUI supervisor & script change auditor | `comfy.py`, `check_script_changes.py` |

---

### 1. Database & Queue Management (`tools/database/`)

#### Expression Database Manager (`db.py`)
Tracks all expressions across languages in `database/expressions.db` and auto-synced `database/<language>_expressions.csv`.
- **Golden Rule**: Pipeline scripts **never** set `STATUS = DONE`. Only you can set `DONE`.
- **Workflow Gate**: If `STATUS` is `DONE`, all pipeline stages automatically skip that expression.
```bash
# View database statistics (total, DONE, PENDING)
py tools/database/db.py stats

# List pending expressions
py tools/database/db.py list --status PENDING

# Check status of an expression
py tools/database/db.py status EE01

# Mark an expression as DONE (or PENDING)
py tools/database/db.py set-status EE01 DONE
py tools/database/db.py set-status EE01 PENDING

# Force two-way sync with database/expressions.csv and seed any new prompts
py tools/database/db.py sync
```

#### Prompt & Database Synchronizer (`sync_prompts.py`)
Validates that all input CSV queues (`EXPRESSION`, `GAME`, `ROLEPLAY`, and `FUN_FACTS`) are 100% aligned, checks for missing IDs or fields, and automatically synchronizes SQLite and the tracking CSVs.
```bash
py tools/database/sync_prompts.py
```

#### Mass Pipeline Stage Status Reset Tool (`reset_stage_status.py`)
Resets pipeline stage status (`voice_generation`, `image_generation`, `script_generation`, `thumbnail_generation`, `video_assembly`, or `all`) to `pending` across all 1,224 state files or filtered by language, video type, or script ID. Automatically re-scrapes and synchronizes `state/pipeline_status.csv` master manifest.
```bash
# Reset voice_generation to pending across all 1,224 state files and resync pipeline manifest
py tools/database/reset_stage_status.py --stage voice_generation --yes

# Reset image_generation for all French expressions
py tools/database/reset_stage_status.py --stage image_generation -l french -t expression --yes

# Reset specific scripts
py tools/database/reset_stage_status.py --stage voice_generation -id EE01,EE02,FR05 --yes

# Dry run preview (reports counts and breakdown without writing)
py tools/database/reset_stage_status.py --stage voice_generation --dry-run
```

---

### 2. Auditing & Inspection (`tools/auditing/` & `tools/check_script_changes.py`)

#### Script Change Auditor & Automated Synchronizer (`tools/check_script_changes.py`)
Scans all CSV files in `main/input/csv/script_to_change/` (populated from Google Sheets Column D `SCRIPT_CHANGED` via `fetch_corrected_scripts.py`), compares them against local State JSON files, reports detailed diffs and word counts, and synchronizes changes.
- **Zero-Duplication Assurance**: Leverages the updated `script_modifier.py` parsing engine to cleanly partition sentences without duplicating lines across `setup`/`discovery` or `challenge`/`pressure`.
- **Intelligent Normalization**: Strips speaker prefixes (`Narrator:`, etc.), curly quotes, and detects section reordering without false positives.
- **Safe State Invalidation**: Automatically resets downstream stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `'pending'` upon applying updates.
- **Placement**: Located at `main/tools/check_script_changes.py`.

```bash
# Preview pending changes across all 16 CSVs without writing
py tools/check_script_changes.py --check-only

# Apply all pending script changes and reset downstream stages
py tools/check_script_changes.py --apply

# Audit/apply a specific CSV queue
py tools/check_script_changes.py --csv english_game_script_to_change.csv --apply

# Audit/apply a single script ID
py tools/check_script_changes.py --script-id EE56 --apply
```

#### Pipeline Status Scraper (`status_scraper.py`)
Audits all 16 prompt queues and `state/` JSON files, reports real-time generation progress, and compiles the master tracking CSV at `state/pipeline_status.csv`.
```bash
# View dashboard and compile state/pipeline_status.csv
py tools/auditing/status_scraper.py

# View dashboard with sample previews of next pending scripts per stage
py tools/auditing/status_scraper.py --samples
```

#### JSON Health Checker & Repair Tool (`json_health_checker.py`)
Deep-audits generated state JSON files across `state/` for structural integrity, sentence cut-offs/truncations, missing metadata, word count anomalies, and missing generated assets.
```bash
# Run interactive audit across all state files
py tools/auditing/json_health_checker.py

# Audit without modifying (dry-run report only)
py tools/auditing/json_health_checker.py --dry-run

# Audit a specific script ID
py tools/auditing/json_health_checker.py --script-id SE01

# Automatically reset all problematic scripts to 'pending' without interactive prompts
py tools/auditing/json_health_checker.py --auto-reset
```

#### Export Scripts for Human Review (`scrapper_script.py`)
Scrapes and unescapes generated scripts from `state/` JSON files into clean, readable CSV files in `OUTPUT_DIR/scripts_to_see/<language>/<type>/<language>_<type>_scripts.csv`.
- **Deduplication & Sample Filtering**: Automatically ignores `.sample` templates (e.g. `script_state.sample.json`) and tracks seen script IDs per language/type pair, guaranteeing 100% duplicate-free review CSVs.
- **Feeder for Google Sheets Publishing**: The generated CSV files match the exact schema (`ID,expression,script`) required by `main/connectivity/post_scripts.py` to publish scripts directly to Google Sheets Columns A, B, and C.
```bash
py tools/auditing/scrapper_script.py
py tools/auditing/scrapper_script.py -l english -t roleplay
```

---

### 3. Interactive Modifiers (`tools/modifiers/`)

#### Interactive Script Modifier (`script_modifier.py`)
Interactive utility to modify or repair a video script using a plain text input while strictly preserving the provided script text verbatim.
- **Zero-Hallucination Verbatim Ingestion**: When raw text is supplied, `parse_user_script_into_sections()` segments paragraphs into canonical format sections (`hook`, `setup`, `discovery`, `example`, `payoff`, etc.) and sets them directly into `content_metadata.script`. The LLM is used strictly for metadata/title synthesis and is forbidden from altering spoken text.
- **Mass Script Changes**: Supports queueing multiple IDs and plain-text scripts before launching LLM batch processing.
- **Enforces Canonical Standards**: Enforces canonical key ordering (`title` strictly first key, clean catchy names without generic `: Shorts Guide` suffixes) and automatically synchronizes review CSVs in `output/scripts_to_see/<lang>/<vtype>/` upon every modification.
```bash
# Interactive mode (prompts to choose [1] Single Script or [2] Mass Script Changes)
py tools/modifiers/script_modifier.py

# Direct Mass Script Changes interactive mode
py tools/modifiers/script_modifier.py --mass

# Direct CLI target (single or comma-separated batch)
py tools/modifiers/script_modifier.py --script-id EE01
py tools/modifiers/script_modifier.py --script-id EE01,FG02,SR03

# With script file and automated downstream reset
py tools/modifiers/script_modifier.py --script-id EE01 --script-file my_script.txt --reset-downstream
```

#### Interactive Voice Modifier (`voice_modifier.py`)
Auditions reference voices from `open-swara`, manually recasts character voices, adjusts pauses, and regenerates TTS audio per script. Features 100% parity with `main.py` for multi-candidate sampling (`--candidates`), acoustic prominence scoring, and Kokoro-82M pronunciation bank fallback.
```bash
py tools/modifiers/voice_modifier.py
py tools/modifiers/voice_modifier.py --script-id EE04 --candidates 3
```

#### Interactive Image & Chalkboard Modifier (`image_modifier.py`)
Recreates individual scene illustrations, modifies visual prompts, and live-edits chalkboard exercise text for game trivia shorts.
```bash
py tools/modifiers/image_modifier.py
py tools/modifiers/image_modifier.py --script-id EG01
```

#### Interactive Subtitles Modifier (`subtitles_modifier.py`)
Allows inspecting subtitle timings, finding/replacing words in `.ass` files, and re-rendering final shorts videos without re-running Whisper speech recognition.
```bash
py tools/modifiers/subtitles_modifier.py
py tools/modifiers/subtitles_modifier.py --script-id ER01
```

---

### 4. Prompt Builders (`tools/prompt_builders/`)

- **`generate_editor_prompts_csv.py`**: Compiles calibrated external LLM system prompts (`system_prompts_editor.csv`) across all four video types (EXPRESSION, ROLEPLAY, GAME, FUN_FACTS) for external script doctoring.

```bash
py tools/prompt_builders/generate_editor_prompts_csv.py
```

---

### 5. Voice Quality & Vocal Register Bank (`tools/voice_quality/`)

Utilities for building and auditing the 7 vocal-register reference clips (`alto`, `mezzo`, `soprano`, `bass`, `baritone`, `tenor`, `narrator`) used by `Qwen3-TTS` across English, French, Spanish, and Italian.

```bash
# Generate the 7 vocal-register golden references via Qwen3-TTS-12Hz-1.7B-VoiceDesign
py tools/voice_quality/build_voicedesign_references.py

# Audit reference WAVs in input/voices/ for SNR, clipping, and Whisper language fidelity
py tools/voice_quality/audit_reference_voices.py
```
---

### 6. Headless ComfyUI Process Supervisor (`tools/comfy.py`)

A windowless process supervisor and CLI manager for ComfyUI. Completely decouples ComfyUI from visible terminal sessions, eliminates Windows console QuickEdit freeze deadlocks, directs output to rotating logs (`main/logs/comfyui/comfyui.log`), and arbitrates VRAM concurrency between Voice TTS and Image Diffusion.

```bash
# Start ComfyUI headless in the background (zero terminal windows)
py tools/comfy.py start

# Check status, PID, active GPU, VRAM usage, and queue metrics
py tools/comfy.py status

# Inspect recent runtime logs
py tools/comfy.py logs

# Follow live log output (press Ctrl+C to stop following; ComfyUI keeps running)
py tools/comfy.py logs -f

# Restart ComfyUI cleanly
py tools/comfy.py restart

# Stop ComfyUI process cleanly
py tools/comfy.py stop
```
