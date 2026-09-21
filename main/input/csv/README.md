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
│   └── *.csv                      # CSV files with columns 'ID' and 'NEW_SCRIPT'
└── sample_templates/             # Reusable schema templates
    ├── READY_PROMPTS_EXPRESSION.sample.csv
    ├── READY_PROMPTS_GAME.sample.csv
    ├── READY_PROMPTS_ROLEPLAY.sample.csv
    ├── READY_PROMPTS_FUN_FACTS.sample.csv
    ├── CALL_TO_ACTIONS.sample.csv
    └── script_to_change.sample.csv
```

## Schema Reference

### 0. SCRIPT TO CHANGE (`script_to_change/*.csv`)
- **Columns**: `ID,NEW_SCRIPT`
- **Purpose**: Modifies existing scripts using custom text. The canonical `ID` determines target language and video format.
- **State Rule**: Automatically updates the state JSON format property from `"script_generation": "done"` to `"pending"` BEFORE generating the new script.

### 1. EXPRESSION
- **Filename**: `<LANG>_READY_PROMPTS_EXPRESSION.csv`
- **Columns**: `ID,EXPRESSION,SUBJECT,CONTEXT,ANGLE,LEXICAL_FIELD,EMOTIONAL_TRIGGER`

### 2. GAME
- **Filename**: `<LANG>_READY_PROMPTS_GAME.csv`
- **Columns**: `ID,EXPRESSION,CONTEXT,SUBJECT,LEXICAL_FIELD`
- **Rule**: `EXPRESSION` must contain target-language contrast pairs or idioms (e.g. `blessé vs béni`). `CONTEXT` must provide a concrete sentence with a visual blank (`___`).

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
