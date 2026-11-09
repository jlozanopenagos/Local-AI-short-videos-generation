# State Directory

This directory stores real-time JSON execution states for each video script as it moves through the pipeline stages:

1. `_A_video_scripts`: Script text generation, canonical section segmentation & YouTube SEO metadata
2. `_B_voice_generation`: Speech synthesis audio paths, speaker timbres, and word-level timestamps
3. `_C_image_generation`: Visual scene illustrations, story world anchor, and chalkboard graphics
4. `_D_music_generation`: Background jam assignment and audio ducking parameters
5. `_F_thumbnail_image_generation`: YouTube thumbnail image and localized title graphics
6. `_G_video_assembly`: Final assembled vertical MP4 video and dynamic ASS subtitles

---

## Directory Structure

```text
state/
├── english/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
├── french/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
├── spanish/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
├── italian/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
├── pipeline_status.csv         # Global generation progress manifest across all 1,200+ scripts
└── script_state.sample.json    # Canonical reference schema for state files
```

Individual script state files (`script_<ID>.json`) and `pipeline_status.csv` are generated dynamically by pipeline runs and are ignored by git to keep commits clean.

---

## State Schema & GAME Format Architecture

Every state file contains:
- `script_id`: Canonical identifier (e.g. `EG03`, `EE01`, `FR12`).
- `status`: Lifecycle dictionary mapping each stage (`script_generation`, `voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `"pending"` or `"done"`.
- `content_metadata.script`: Canonical section breakdown dictionary.

### Canonical GAME Format Rules
For all GAME video scripts (e.g. `EG*`, `FG*`, `SG*`, `IG*`), the state structure enforces strict consistency:

1. **5 Canonical Sections**:
   - `hook`: Fast dilemma or ear test setup (12-18 words).
   - `challenge`: Spoken test sentence and verbal options presentation (25-40 words).
   - `pressure`: Snappy countdown line urging immediate decision (8-14 words, e.g. *"Which one is it? A or B? Your answer is coming!"*).
   - `answer`: Reveal of the winning option with linguistic justification (15-22 words).
   - `explanation`: Practical native usage rule and engaging loop CTA (20-30 words).

2. **Spoken Challenge & Options Syntax**:
   - **Neutral Lowercase Speech**: The challenge sentence MUST use neutral lowercase words (e.g. `record`, `present`, `contract`). It MUST NOT contain uppercase stress giveaways like `REcord` or `PREsent` in the spoken challenge sentence, which would spoil the test.
   - **Explicit Option Tags**: Options MUST start with uppercase letter and colon: `A: `, `B: `, etc.
   - **Zero Connectors**: NO coordinating conjunctions or connectors (`or`, `and`, `o`, `ou`, `oppure`, `e`) or commas before option tags.
   - **Carrier Context for Single Words**: When options are single words, specify their grammatical category or carrier context (e.g. `A: a record. B: to record.`).
   - **Punctuation & Termination**: Every option MUST terminate with a period (`.`). The last option must NEVER end with `?`.
   - **Zero Countdown Pollution in Challenge**: Countdown and urge phrases belong strictly in `pressure`, never inside `challenge`.

3. **Chalkboard Exercise Synchronization**:
   - `chalkboard_exercise` MUST be kept 100% synchronized with `challenge`.
   - `script_text` is dynamically constructed from all spoken sections in canonical order.

---

## State Invalidation Rules

To guarantee end-to-end asset coherence:
- Updating a script (via `script_modifier.py`, WebUI, or `check_script_changes.py`) automatically resets downstream stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `"pending"`.
- Regenerating a voiceover automatically resets `video_assembly` to `"pending"`.
- Completed expressions with `STATUS = DONE` in `database/expressions.db` are strictly frozen from automated pipeline overwrites.
