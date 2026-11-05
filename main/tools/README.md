# Shorts Automation CLI Tools & Utilities

This folder contains command-line utilities and interactive review tools for the shorts automation pipeline, strictly organized into 5 functional subdirectories.

---

## Folder Organization Overview

| Subdirectory | Focus / Responsibility | Tools Included |
| :--- | :--- | :--- |
| **`modifiers/`** | Canonical interactive asset & script modification forwarders | `script_modifier.py`, `voice_modifier.py`, `image_modifier.py`, `subtitles_modifier.py` |
| **`auditing/`** | Quality inspection, metrics & health checks | `check_script_changes.py`, `audit_all_csvs.py`, `status_scraper.py`, `json_health_checker.py`, `check_language_mixing.py`, `scrapper_script.py` |
| **`database/`** | Expression database, queue sync, stage resets & ID assignment | `db.py`, `sync_prompts.py`, `assign_ids.py`, `reset_stage_status.py` |
| **`prompt_builders/`**| System editor prompts generator | `generate_editor_prompts_csv.py` |
| **Root Tools** | Headless ComfyUI supervisor, connection pool, mass title upgrades & bank management | `comfy.py`, `manage_pronunciation_bank.py`, `upgrade_titles.py`, `reset_stage_status.py` |

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

#### Assign Structured Script IDs (`assign_ids.py`)
Standardizes canonical `<Lang><Type><02d>` identifiers (e.g. `EE01`, `FR02`, `SG01`) across input CSV files and state JSONs without collisions.
```bash
py tools/database/assign_ids.py --dry-run
py tools/database/assign_ids.py
```

#### Mass Pipeline Stage Status Reset Tool (`reset_stage_status.py`)
Resets pipeline stage status (`voice_generation`, `image_generation`, `script_generation`, `thumbnail_generation`, `video_assembly`, or `all`) to `pending` across all 1,224 state files or filtered by language, video type, or script ID. Automatically re-scrapes and synchronizes `state/pipeline_status.csv` master manifest. Accessible via `tools/reset_stage_status.py` or `tools/database/reset_stage_status.py`.
```bash
# Reset voice_generation to pending across all 1,224 state files and resync pipeline manifest
py tools/reset_stage_status.py --stage voice_generation --yes

# Reset image_generation for all French expressions
py tools/reset_stage_status.py --stage image_generation -l french -t expression --yes

# Reset specific scripts
py tools/reset_stage_status.py --stage voice_generation -id EE01,EE02,FR05 --yes

# Dry run preview (reports counts and breakdown without writing)
py tools/reset_stage_status.py --stage voice_generation --dry-run
```

---

### 2. Auditing & Inspection (`tools/auditing/`)

#### Script Change Auditor & Automated Synchronizer (`check_script_changes.py`)
Scans all CSV files in `main/input/csv/script_to_change/` (populated from Google Sheets Column D `SCRIPT_CHANGED` via `fetch_corrected_scripts.py`), compares them against local State JSON files, reports detailed diffs and word counts, and synchronizes changes.
- **Zero-Duplication Assurance**: Leverages the updated `script_modifier.py` parsing engine to cleanly partition sentences without duplicating lines across `setup`/`discovery` or `challenge`/`pressure`.
- **Intelligent Normalization**: Strips speaker prefixes (`Narrator:`, etc.), curly quotes, and detects section reordering without false positives.
- **Safe State Invalidation**: Automatically resets downstream stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `'pending'` upon applying updates.
- **Dual Placement**: Available directly in `main/tools/check_script_changes.py` or `main/connectivity/check_script_changes.py`.

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

#### Master CSV Prompt & Encoding Auditor (`audit_all_csvs.py`)
Deep-audits all 16 prompt CSV files across English, Spanish, French, and Italian for UTF-8 with BOM integrity, absence of mojibake/encoding artifacts, zero duplicate scenarios, zero lazy boilerplate strings, and 1-to-1 cross-format alignment.
```bash
py tools/auditing/audit_all_csvs.py
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

#### Language Mixing Checker (`check_language_mixing.py`)
Audits generated script JSONs across all languages for cross-language contamination (e.g. French in Italian, English in Spanish).
```bash
py tools/auditing/check_language_mixing.py
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

### 5. Pronunciation Bank Management (`tools/manage_pronunciation_bank.py`)

A dedicated CLI utility for inspecting, auditing, and managing the standing heteronym audio bank (`main/input/audio/heteronym_bank/`) backed by the Kokoro-82M precision engine.

```bash
# Check status and audio coverage across all 12 heteronyms
py tools/manage_pronunciation_bank.py --status

# Run acoustic prominence quality audit (RMS ratio, pitch delta) on all bank clips
py tools/manage_pronunciation_bank.py --audit

# Populate all missing clips using Kokoro-82M precision engine
py tools/manage_pronunciation_bank.py --populate-kokoro

# Import a custom studio reference clip
py tools/manage_pronunciation_bank.py --import my_recording.wav --word present --role noun

# Export bank registry and metadata to JSON
py tools/manage_pronunciation_bank.py --export-json bank_metadata.json
```
---

### 6. Title & Metadata Singularity Upgrader (`tools/upgrade_titles.py`)

Automated utility to eliminate repetitive title formulas (e.g. *"Native Secret"*, *"El Secreto de los Nativos"*, *"Il Segreto dei Nativi"*, *"Le Secret des Natifs"*) and purge all emojis from `script.title` (Tito's chalkboard graphic) and `metadata.TITLE` (YouTube Shorts title) across all State JSON files.

- **Two-Tier Option B Architecture**:
  - **Chalkboard Title (`content_metadata.script.title`)**: Standardized format indicators (`<Expression>` for Expression, `Quiz: <Expression>` for Game, `In Action: <Expression>` for Roleplay, `Origin: <Expression>` for Fun Facts, localized per language) that split cleanly on colon into Tito's chalkboard header and phrase.
  - **YouTube Title (`metadata.TITLE`)**: Shorts-optimized (45–75 chars), uppercase hook triggers, high-curiosity tension, format-differentiated, and strictly zero emojis.
- **Format Singularity**: Generates distinct pedagogical titles for all four formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`), even when sharing an underlying expression.
- **Canonical Expression Resolution**: Maps Roleplay (`ER`, `FR`, `SR`, `IR`) and Game IDs back to canonical base expressions from SQLite, eliminating narrative scenario leakage into titles.
- **Downstream Preservation**: Upgrades titles and metadata in-place while strictly preserving `voice_generation`, `image_generation`, and `video_assembly` statuses without invalidating existing renders.

```bash
# Audit titles across all state JSON files (dry-run preview)
py tools/upgrade_titles.py

# Apply title upgrades across all state files
py tools/upgrade_titles.py --apply

# Filter by language or video type
py tools/upgrade_titles.py -l french -t roleplay --apply

# Upgrade specific script IDs
py tools/upgrade_titles.py -id EE01,FR02,SG05 --apply
```
---

### 7. Headless ComfyUI Process Supervisor (`tools/comfy.py`)

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
