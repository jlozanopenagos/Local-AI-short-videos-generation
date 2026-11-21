# Input CSV Prompt Queues Specification

This directory manages the prompt queue CSV files for each target language.

> [!NOTE]
> To protect proprietary content libraries and creator strategy, actual production prompt CSV files (`*.csv`) are excluded from version control via `.gitignore`. Sample templates (`*.sample.csv`) are provided to illustrate the required schema.

## Directory Structure
```
input/csv/
├── <language>/                    # 'english', 'french', 'spanish', 'italian'
│   ├── expressions_list/
│   │   ├── <LANG>_READY_PROMPTS_EXPRESSION.csv
│   │   ├── <LANG>_READY_PROMPTS_GAME.csv
│   │   ├── <LANG>_READY_PROMPTS_ROLEPLAY.csv
│   │   └── <LANG>_READY_PROMPTS_FUN_FACTS.csv
│   └── game_call_to_action_phrases/
│       └── <LANG>_CALL_TO_ACTIONS.csv
├── script_to_change/              # CSV queues to replace existing video scripts
│   ├── model_ids_to_fetch.csv     # Model reference template for ID filtering
│   ├── ids_to_fetch.csv           # Active ID list for targeted Google Sheets sync
│   └── <lang>_<type>_script_to_change.csv # Auto-generated from Google Sheets Column D
├── voice_to_change/               # CSV queues for targeted voice generation (_B_voice_generation)
│   └── model_ids_to_voice.sample.csv # Template with ID column
├── image_to_change/               # CSV queues for targeted image generation (_C_image_generation)
│   └── model_ids_to_image.sample.csv # Template with ID column
├── sample_templates/              # Reusable schema templates
│   ├── READY_PROMPTS_EXPRESSION.sample.csv
│   ├── READY_PROMPTS_GAME.sample.csv
│   ├── READY_PROMPTS_ROLEPLAY.sample.csv
│   ├── READY_PROMPTS_FUN_FACTS.sample.csv
│   ├── CALL_TO_ACTIONS.sample.csv
│   └── script_to_change.sample.csv
```

## Schema Reference

### 0. SCRIPT TO CHANGE (`script_to_change/*.csv`)
- **Columns**: `ID,NEW_SCRIPT`
- **Purpose**: Modifies existing scripts using human-crafted or externally edited text. Canonical `ID` determines target language and video format.
- **Automated Ingestion via Connectivity**: Can be populated directly from Google Sheets Column D (`SCRIPT_CHANGED`) via `main/connectivity/fetch_corrected_scripts.py`.
- **Targeted ID Filtering Templates**:
  - `script_to_change/model_ids_to_fetch.csv`: Reference template schema (`ID`).
  - `script_to_change/ids_to_fetch.csv`: Active list of IDs to fetch from Google Sheets when running Option 4 (CSV ID list).
- **Verbatim Ingestion Guarantee**: Paragraphs are parsed directly into canonical format sections (`hook`, `setup`, `discovery`, `example`, `payoff` for Expression; `hook`, `challenge`, `pressure`, `answer`, `explanation` for Game; `hook`, `DIALOGUE_PART_1`..`4`, `PAYOFF` for Roleplay; `hook`, `setup`, `discovery`, `payoff` for Fun Facts). Spoken text is injected **100% verbatim** into `content_metadata.script` with zero LLM paraphrasing or summarization.
- **State Rule**: After applying a revised script, the studio marks script generation done and resets voice, images, thumbnails, assembly, and Drive delivery to pending.
- **Automated Verification & Sync Tool (`check_script_changes.py`)**: Creators can run `py main/tools/check_script_changes.py --check-only` at any time to compare all CSVs in `script_to_change/` against local state JSONs, previewing diffs and word counts. Running with `--apply` performs a batch sync with zero section duplication.
- **Robust CSV Parsing**: Sanitizes multiline quoted text and spaces after commas before quotes (`skipinitialspace=True`) to prevent truncation or malformed rows.

### 0b. Studio batch selection

In **Mass Creation**, pick the target stage and paste IDs, upload an ID CSV, or select scripts from the catalog. Use an `ID` or `script_id` column for voice or image redo lists. The studio validates each ID against local state before queuing it.

The ready-script scanner writes `ID,expression` exports under `<OUTPUT_DIR>/connectivity/ready_scripts/`. Use an export as the ID CSV for voice, images, thumbnails, or assembly. Apply reviewed script revisions through **Sheets Sync** before rendering.

### 1. EXPRESSION
- **Filename**: `<LANG>_READY_PROMPTS_EXPRESSION.csv`
- **Columns**: `ID,EXPRESSION,SUBJECT,CONTEXT,ANGLE,LEXICAL_FIELD,EMOTIONAL_TRIGGER`

### 2. GAME
- **Filename**: `<LANG>_READY_PROMPTS_GAME.csv`
- **Columns**: `ID,EXPRESSION,CONTEXT,SUBJECT,LEXICAL_FIELD`
- **Rule**: `EXPRESSION` contains target-language contrast pairs or idioms (e.g. `blessé vs béni`, `record (noun vs verb)`).
- **Spoken Challenge & Option Constraints**:
  - The spoken challenge sentence uses natural lowercase speech with **zero uppercase stress giveaways** (e.g. write `record`, not `REcord`).
  - Options MUST explicitly begin with uppercase letter tags: `A: `, `B: `, etc.
  - ZERO connectors between options: never include words like `or`, `and`, `o`, `ou`, `oppure`, `e`, or commas before options.
  - Single-word options MUST specify parts-of-speech / carrier context (e.g. `A: a record. B: to record.`).
  - Every option MUST terminate with a period (`.`). The last option must NEVER end with `?`.
  - Countdown and urgency phrases belong strictly in `pressure`, never in `challenge`.

### 3. ROLEPLAY
- **Filename**: `<LANG>_READY_PROMPTS_ROLEPLAY.csv`
- **Columns**: `ID,ROLEPLAY_SCENARIO,SUBJECT,LEXICAL_FIELD,EMOTIONAL_TRIGGER,SPECIAL_TREATMENT`
- **Column Details**:
  - `SPECIAL_TREATMENT` *(optional, backward compatible)*: Classifies the target expression under one mutually exclusive pedagogical lens:
    - `idiomatic`: Fixed multi-word figurative phrases (*break a leg*, *costar un ojo de la cara*, *poser un lapin*). Enforces mandatory 4-part idiomatic arc where **PERSON_ONE must use the complete idiom in an original sentence in DIALOGUE_PART_4** (Error #4 fix), with automated validation and retry.
    - `phonetic`: Minimal pairs, heteronyms, stress shifts (*REcord vs reCORD*).
    - `false_friend`: Cross-language cognate traps (*embarrassed / embarazada*).
    - *(blank)*: Default LLM generation behavior preserved.

### 4. FUN_FACTS
- **Filename**: `<LANG>_READY_PROMPTS_FUN_FACTS.csv`
- **Columns**: `ID,TOPIC,PILLAR,FORMAT,FACT_DETAILS,HOOK_ANGLE,EMOTIONAL_TRIGGER`
- **Rule**: All columns must be written directly in the video's target language.
