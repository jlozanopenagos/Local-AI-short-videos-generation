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
   - **6-Image Visual Architecture across 4 Dialogue Parts (6 ComfyUI Scene Renders)**:
     - `hook` (Narrator, 15–20 words): Scenario Threshold Establishing Two-Shot (35mm lens, 0% fourth-wall eye contact).
     - `DIALOGUE_PART_1` (P1 & P2, 30–38 words): Solo Tight Medium Close-Up on `PERSON_ONE` (85mm portrait lens, `PERSON_TWO` off-camera).
     - `DIALOGUE_PART_2` (P1 & P2, 30–38 words): Solo 180° Reverse-Angle Medium Close-Up on `PERSON_TWO` (85mm portrait lens, `PERSON_ONE` off-camera).
     - `DIALOGUE_PART_3` (P1 & P2, 30–38 words): 90° Side-Profile / High-Angle Two-Shot Prop Interaction (50mm lens, both characters).
     - `DIALOGUE_PART_4` (P1 & P2, 30–38 words): Solo Waist-Up Dynamic Action Shot on `PERSON_ONE` (28mm/50mm lens, `PERSON_TWO` off-camera).
     - `PAYOFF` (Narrator, 20–25 words): Celebratory Resolution Action Two-Shot (28mm wide lens) + CTA.
   - **Multi-Character Gender Specification**: Sex of EACH individual character MUST be explicitly specified in prompts (e.g. *"one youthful 14-16-year-old teen boy and one youthful 14-16-year-old companion teen girl"*). Dual-character state persistence via `speakers_gender: {"PERSON_ONE": "...", "PERSON_TWO": "..."}`.
   - **Target Duration & Word Budget**: **60 to 80 seconds max** (strictly **145–180 spoken words** across all 6 spoken sections).
   - **Status**: **Fully functional and verified end-to-end**.

3. **GAME (`*_READY_PROMPTS_GAME.csv`)**:
   - **Purpose**: Fast-paced, educational interactive trivia quiz game show to test viewers' language skills.
   - **Format Rules**: Strictly an educational trivia quiz game, NOT a narrative story. The LLM picks the best fit from 5 authorized game archetypes (`types/game/archetypes.py`):
     1. *FALSE_FRIEND_TRAP*: Deceptive translation cognates and idiomatic literal traps (e.g. *parenti* vs *parents*, *embarazada* vs *embarrassed*, *poser un lapin*, *break a leg*).
     2. *ODD_ONE_OUT*: Pattern recognition challenge with 3 or 4 choices where one breaks a hidden grammatical or category rule.
     3. *SPOT_THE_MISTAKE*: Learner ego-challenge isolating common preposition, agreement, or lexical blunders.
     4. *MINIMAL_PAIR_SHOWDOWN*: Auditory perception challenge testing word stress (`PROject` vs `proJECT`) or phonemic contrasts.
     5. *FILL_IN_THE_BLANK_SPEEDRUN*: High-velocity collocation and idiomatic sprint with 3 or 4 candidate options.
   - **5 Mandatory Spoken Sections**: `title`, `hook`, `challenge`, `pressure`, `answer`, `explanation`.
   - **Canonical Challenge & Option Syntax Standard (Strict Mandate)**:
     - **No Answer Spoilers in Challenge**: The Narrator voices the scenario or prompt question clearly WITHOUT spoiling the answer before presenting the choices.
       - *Correct*: `"Ton ami te dit : 'Hier soir, Thomas m'a posé un lapin !' Que s'est-il passé ? A: Il lui a offert un animal.  B: Il n'est pas venu au rendez-vous.  C: Il a payé l'addition.  D: Il est arrivé en retard."`
       - *Prohibited*: Never state or imply the solution inside the test sentence (e.g. never write `"Il a décidé de Poser un lapin à son amie..."`).
     - **No Raw Underscores in Audio**: Spoken challenge audio NEVER contains raw blanks (`___` or `____`). The blank belongs exclusively on the visual chalkboard.
     - **No Stress / Capitalization Giveaways**: The challenge test sentence and options MUST be written in natural lowercase (e.g. `record`, `present`, `contract`, `project`). Syllables must **never** be capitalized (`REcord`, `preSENT`, `conTRACT`), which gives away the answer visually.
     - **Option Tags**: Options must strictly begin with an uppercase letter followed by a colon: `A: `, `B: `, `C: `, and optionally `D: `. Provide 3 to 4 options (or 2 for binary minimal pairs).
     - **Zero Connectors**: No conjunctions (`or`, `and`, `ou`, `o`, `oppure`, `y`, `e`) and no separating commas between options.
     - **Part of Speech Specification for Single Words**: When options are single words (distinguishing noun vs verb heteronyms), a grammatical contextualizer is mandatory (`a record` for noun, `to record` for verb; `a present` vs `to present`; articles/prepositions in other languages).
     - **Period Punctuation**: Every option MUST terminate with a period (`.`). The last option **NEVER ends with a question mark (`?`)**.
   - **Visuals & 5-Scene Calibrated Image Generation Pipeline**:
     - Timeline requires EXACTLY 5 distinct, non-repeating scene assets in script_<ID>/images/:
       1. hook: Scenario dilemma setup rendered in 2D cartoon illustration via ComfyUI (symmetrical spotlight framing, 100% direct fourth-wall eye contact).
       2. challenge: High-resolution typography rendered natively on CPU via FreeType onto empty_chalkboard.png with **100% target language localization** (get_localized_game_header(), e.g. QUE SIGNIFIE CETTE EXPRESSION ?, OÙ EST L'ERREUR ? / COMPLÉTEZ :, ¿QUÉ SIGNIFICA ESTA EXPRESIÓN?). **ZERO English headers or text on non-English chalkboards**.
       3. pressure: Static pre-made waiting illustration per language from input/images/game_images/<lang>/<lang>_waiting.png.
       4. nswer: Resolution / victory breakthrough illustration rendered via ComfyUI (dynamic action, triumphant breakthrough).
       5. explanation: Dedicated cultural immersion narrative illustration rendered via ComfyUI (authentic practical real-world usage, ZERO duplicate images with answer).
     - **ComfyUI Batch Processing**: Exactly **3 scenes** (hook, nswer, explanation) are sent to ComfyUI for generation, paired with CPU chalkboard and static Tito to yield 5 distinct timeline cuts.
   - **Zero-Tolerance Text & Quote Scrubbing in Prompts**:
     - Visual prompts must NEVER contain text inside quotation marks, speech verbs (whispering the words...), signboards with text, or letter names.
     - Any parchment, scroll, book, or paper must be described with abstract wavy cartoon doodle lines and geometric diagrams, completely devoid of legible text, words, or letters.
     - sanitize_and_style_prompt scrubs all quoted words and speech phrases, reinforcing negative constraints: NO text, NO words, NO letters, NO quotes, NO signs with text, NO subtitles, NO typography, NO young children, NO elementary kids, NO childish proportions.
   - **Character Appearance Continuity & Demographic Lock**:
     - **General Prompt as Single Source of Truth**: Character demographic anchors (`gender`, `skin_tone`, `eye_color`, `hair_style`, `wardrobe`) originate from `extract_or_build_character_anchors` and are locked into `content_metadata.general_prompt`. All downstream scene prompts inherit visual world anchors directly from this single authoritative truth, preventing contradictory descriptions or ethnicity drift across scenes.
     - **Case-Insensitive Speaker Gender Resolution (`get_speaker_gender_safe`)**: All modules query speaker genders using case-insensitive lookup with fuzzy fallback. This eliminates gender inversion bugs where TitleCase keys (`"Narrator"`, present in >1,038 state files) previously bypassed `.get("NARRATOR")` lookups and defaulted female characters to `"male"`.
     - **Locked Director Prompts**: Storyboard tasks for Game, Fun Facts, and Expression lock `{p1_word}` (`girl`/`boy`) in director tasks based on authoritative anchors.
     - Single source of truth in `content_metadata.character_anchors` (and `assets.character_anchors`) via `CharacterCast` with locked gender, skin tone, eye color, hairstyle, and wardrobe.
     - Strict demographic anchor: *14–16-year-old high-school teenager with natural balanced teenage proportions and healthy youthful athletic build (NOT a child, NOT a kid, NOT an adult)*.
     - **Mandatory Complexion & Eye Color Anchoring**: Explicit skin tone (e.g., *warm tan skin*, *fair peach skin*, *olive skin*) and eye color (e.g., *dark brown cartoon eyes*) must NEVER be omitted in general prompts or scene prompts. Without explicit skin tone anchors, dramatic framing shifts (such as 35mm foreground Hook close-ups vs. medium two-shots) trigger diffusion drift where the model hallucinates a completely different ethnicity or facial structure.
     - Elimination of emaciated/skinny silhouettes and unexpressive deadpan faces: purged `"tall slender proportions"`, `"Wes Anderson-style central balance"`, and `"frozen at a physical crossroads"`.
     - **Natural Facial Acting & Bug-Eye Eradication**: Purged `"conspiratorial glance"` and `"arched eyebrow"` triggers from prompt templates and storyboard directors, which previously caused diffusion models to render excessively open, rounded, or bulging bug-eyes. Replaced with *"engaging, playful knowing smile and natural animated cartoon eyes with relaxed facial acting"*.
     - Fortified negative prompt shield: `NO bulging eyes, NO bug eyes, NO staring unblinking eyes, NO excessively open rounded eyes, NO unnatural wide eyes, NO deadpan blank face, NO emotionless expression, NO stiff mannequin pose, NO gaunt, NO emaciated, NO stick-figure proportions`.
     - Gender-attire integrity: male characters are barred from feminine garments (bodices, corsets, kirtles, skirts, dresses).
     - Elimination of conflicting double prompt injections (no duplicate or contradictory character descriptions within the same prompt).
   - **Zero-Copy Static Shared Asset Architecture**:
     - **Elimination of Duplicate Asset Copies**: Static pre-made assets that never vary across scripts of the same language and video type (e.g. Tito waiting image `pressure.png` for GAME shorts, opening branding cards, closure cards, watermark) are NEVER physically copied into individual script output folders (`D:\AI\output\video_assets\...`).
     - **On-Demand Dynamic Resolution (`resolve_static_scene_path`)**: `config/settings.py` dynamically resolves the canonical asset from `input/images/game_images/` or `input/images/openning_closure_images/` based on script language, video type, and dialect without hardcoded paths.
     - **Decoupled Creation & Assembly**: `_C_image_generation/main.py` and `image_modifier.py` verify central asset existence and skip file duplication, while `_G_video_assembly/core/video_assembler.py` automatically links the central asset directly into the FFmpeg render timeline.
   - **Anti-Cliché Prop & Fallback Trope Mandate (Strict Gift Box Ban)**:
     - **Banned Fallback Props**: Strictly prohibited using generic ribbon-wrapped gift boxes, mystery parcels, or birthday boxes as a fallback metaphor across all video types (Game, Roleplay, Expression, Fun Facts). Gift boxes are exclusively permitted for the English heteronym `present` (PREsent vs preSENT).
     - **Context-Grounded Physical Props**: Characters must interact with authentic physical objects matching the scenario environment (travel luggage/tickets for trips, cookware/platters for culinary buffets, tools/blueprints for design, tuning forks/phonetics mirrors for speech, measuring trays/counting tokens for quantities).
     - **Refined Idiom Detection**: `is_figurative_idiom()` no longer triggers on the generic substring `"expression"`, ensuring standard grammar/vocabulary scripts are not falsely categorized as figurative idioms.
     - **Universal Sanitization Interceptor**: `sanitize_and_style_prompt()` automatically scrubs legacy gift box phrases into setting-authentic props.
   - **Strict Separation of Challenge and Pressure**:
     - `challenge`: Exclusively contains the test scenario and candidate options (`A: ...  B: ...`).
     - `pressure`: Exclusively contains countdown lines, time limits, and urgency prompts (*"Which one is it? A or B? Your answer is coming!"*, *"Tic-tac !"*, *"Il tempo scorre!"*). Pressure lines must **never** be placed inside `challenge`.
   - **Multi-Property State Synchronization**:
     - `content_metadata.script.challenge`
     - `content_metadata.chalkboard_exercise` (must match the clean challenge)
     - `script_text` (JSON string serialized from updated script)
     - All 388 GAME state files are 100% audited, aligned, and synchronized.
   - **Pacing & Audio**: `audio_processor.py` inserts a dedicated 2.20-second suspense pause (`pressure_gap`) between `pressure` and `answer`. Subtitles are suppressed exclusively during `challenge` so options remain unobstructed and the answer is never spoiled in text.
   - **Target Duration & Word Budget**: **40 to 55 seconds** (strictly **95–125 spoken words** across all sections).
   - **Status**: **Fully implemented, calibrated, and operational**.

4. **FUN_FACTS (`*_READY_PROMPTS_FUN_FACTS.csv`)**:
   - **Purpose**: Umbrella category for short, entertaining, surprising language discoveries following **HOOK $\rightarrow$ SETUP $\rightarrow$ DISCOVERY $\rightarrow$ EXPLANATION $\rightarrow$ PAYOFF**.
   - **6 Authorized Formats**: Format A (3 Facts), Format B (One Big Curiosity), Format C (Challenge), Format D (Mystery), Format E (Comparison), Format F (Ranking/List).
   - **Target Language Localization**: All content in `*_READY_PROMPTS_FUN_FACTS.csv` (`TOPIC`, `FACT_DETAILS`, `HOOK_ANGLE`, `EMOTIONAL_TRIGGER`) is written directly in the target language (French, Spanish, Italian, English).
   - **Calibrated Scene Count & 5-Beat Camera Grammar**: Generates **5 distinct thematic scene images** via ComfyUI:
     - `hook` [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking upward in jaw-dropped awe (0% camera eye contact).
     - `setup` [THE CURIOUS CLUE]: Medium 50mm eye-level investigative shot examining an authentic artifact or clue.
     - `discovery` [THE HIDDEN MECHANISM REVEAL]: Dynamic 35mm 3/4 medium action shot revealing the mechanism/origin in motion.
     - `explanation` [LIVING CULTURAL CONTEXT]: Medium-wide 35mm environmental immersion shot showing practical cultural context.
     - `payoff` [MIND-BLOWN MASTERY]: Chest-up celebratory medium close-up (50mm lens) with warm rim lighting.
   - **Target Duration & Word Budget**: **40 to 60 seconds** (strictly **95–135 spoken words** across all sections).
   - **Status**: **Fully implemented, verified, and operational**.

---

## Calibrated Scene & Image Architecture per Video Type

| Video Type | Timeline Scenes | ComfyUI Renders | Special Asset Handling |
| :--- | :---: | :---: | :--- |
| **EXPRESSION** | **5** | **5** | `hook`, `setup`, `discovery`, `example`, `payoff` (all 5 generated via ComfyUI). |
| **GAME** | **5** | **3** | • `hook`, `answer`, `explanation`: Rendered via ComfyUI (3 distinct images).<br>• `challenge`: High-res native chalkboard on CPU via Pillow/FreeType (zero VRAM).<br>• `pressure`: Static Tito waiting image per language (`resolve_static_scene_path`, zero-copy). |
| **ROLEPLAY** | **6** | **6** | `hook`, `dialogue_part_1`, `dialogue_part_2`, `dialogue_part_3`, `dialogue_part_4`, `payoff` (all 6 generated via ComfyUI following the 6-beat camera matrix). |
| **FUN_FACTS** | **5** | **5** | `hook`, `setup`, `discovery`, `explanation`, `payoff` (all 5 generated via ComfyUI following the Scale-of-Wonder 5-beat camera matrix). |

---

## Stage C Modular Visual Prompt Architecture (`_C_image_generation/visual/`)

Stage C separates shared visual rules, language data, and video-type camera profiles so editing one language or video type never leaks into others:

| Layer / File | Responsibility ("Where to Change X") |
| :--- | :--- |
| `visual/common/style.py` | Shared 2D cartoon style pillars, base system prompts, and type-pure storyboard system prompt builder (`build_storyboard_system_prompt`). |
| `visual/common/sanitizer.py` | Idempotent `sanitize_and_style_prompt`, text/quote scrubbing, 14–16yo teen demographic enforcement, and `present` heteronym gift-box exception. |
| `visual/common/cast.py` | `CharacterCast` model, `get_speaker_gender_safe`, centralized default genders (`resolve_default_speakers_gender`), solo-format protection for `GAME`/`FUN_FACTS`, and `persist_character_anchors_in_state`. |
| `visual/common/environment.py` | Anchor environment resolution engine (`resolve_anchor_environment`, `is_figurative_idiom`). |
| `visual/languages/{english,french,spanish,italian}.py` | **Language-only data**: brand color palette mood, idiom detection markers, idiom metaphor environments, heteronyms, and `MULTILINGUAL_SEMANTIC_DOMAINS` (shared with `core/gemini_auditor.py`). Never contains camera angles or video-type rules. |
| `visual/types/{expression,game,roleplay,fun_facts}/` | **Type-only rules & prompts**: `SceneSpec` contracts (`rules.py`), single-scene goals, scene progressions, storyboard director tasks (`prompts.py`), and `VisualProfile` class (`profile.py`). |
| `visual/types/registry.py` | `get_visual_profile(...)` dispatcher (by type name, 1-letter code, or Script ID) + `IMAGE_PROMPT_ENGINE=legacy\|typed` rollback switch. |
| `core/prompt_builder.py` | Public facade (`VisualPromptBuilder` + re-exports of all helper functions for backward compatibility). |

---

## Stage G Modular Video Assembly Architecture (`_G_video_assembly/assembly/`)

Stage G isolates editing rules by video type (`expression`, `game`, `roleplay`, `fun_facts`) with neutral per-language hooks, driven from `core/video_assembler.py`, `core/subtitle_builder.py`, and `_G_video_assembly/main.py`:

| Layer / File | Responsibility ("Where to Change X") |
| :--- | :--- |
| `assembly/common/easing.py` | `MotionSpec` + `build_zoompan_expressions` (`cosine`, `ease_in`, `ease_out`, `linear` zoom/pan curves). |
| `assembly/common/transitions.py` | `TransitionSpec`, frame-accurate `compute_clip_render_durations`, and `chain_clips_with_xfade` (smooth FFmpeg `xfade` at every cut with zero A/V drift). |
| `assembly/common/audio_mix.py` | `AudioMixSpec`, `AudioEnvelopeSegment`, and `build_bgm_volume_expr` (per-type BGM volume bed, section boosts/dips, and closure swell). |
| `assembly/common/subtitles.py` | `SubtitleStyleSpec`, `render_ass_header`, and `format_ass_dialogue_line` (Lower-Middle safe-zone `Alignment=2`, pop-in animation, speaker/highlight ASS styles). |
| `assembly/languages/{english,french,spanish,italian}.py` | Optional per-language overrides (`font_override`, `margin_v_offset`, `bgm_volume_scale`) resolved via `get_assembly_language_profile(...)`. |
| `assembly/types/{expression,game,roleplay,fun_facts}/profile.py` | Per-type editing signatures: `EXPRESSION` push-in/lateral pan/pull-back; `GAME` accelerating `pressure` zoom, steady `challenge` chalkboard, `answer` dip; `ROLEPLAY` 180-deg counter-pans & speaker-colored captions (`PersonOne` Gold / `PersonTwo` Sky-Cyan); `FUN_FACTS` vertical crane tilt-up `hook` & numeric Gold highlights. |
| `assembly/types/registry.py` | `get_assembly_profile(...)` dispatcher + `VIDEO_ASSEMBLY_ENGINE=legacy\|typed\|legacy:<type>` rollback switch. |

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
   - **Bingo Matrix View (`BingoMatrixView.tsx`)**: High-level visual matrix providing an at-a-glance status grid across all 16 language/format combinations (e.g. EE, EG, ER, EF, FE, FG, FR, etc.).
   - **Script Detail Modal (`ScriptDetailModal.tsx`)**: Inspects script narrative sections, master audio playback with interactive waveform, scene illustrations, thumbnail preview, and YouTube SEO metadata (Title, Description, Tags, Hashtags).
     - *Single-Scene Image Redo*: Clickable redo button per scene card in the storyboard tab enqueues an isolated scene generation job to Job Manager using the active scene-specific prompt.
     - *Full Image Set Redo from General Prompt*: "queue redo (all images)" button persists user-edited general prompt, clears stale scene prompts and disk PNGs, and queues a sequential two-phase job: Llama boots up first to regenerate all scene-specific prompts aligned to the new general prompt, persists them to state, and stops to release VRAM; ComfyUI then starts and renders all scene images.
     - *Direct Google Drive Upload*: "upload to google drive" button verifies video & thumbnail existence, uploads both to the appropriate Google Drive subfolder, and provides live feedback.
     - *Zero-Copy Static Asset Architecture*: Reusable assets (e.g. GAME Tito `pressure` waiting cards, opening and closure cards) are dynamically resolved via `resolve_static_scene_path` without copying duplicate PNGs into script asset folders.
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
   - Mass generation of **Scene Images** (Stage C), **Voice Files** (Stage B), **Thumbnail Images** (Stage F), or **Google Drive Upload** for arbitrary lists of script IDs across all languages and video formats.
   - **3 ID Collection Modes**:
     - *Manual Input*: Comma/space/line-separated IDs with debounced real-time validation via `POST /api/scripts/validate-ids`.
     - *CSV Drag & Drop*: Upload CSV/TXT files to automatically extract and validate target script IDs.
     - *Preset Catalogs*: One-click buttons to load "All Pending Images", "All Pending Voice", "All Pending Thumbnails", or "Load Ready Videos".
   - **Mass Drive Upload Mode**: Pre-flight audit via `POST /api/drive/check-readiness` displays real-time readiness status for each script ID (both `_final.mp4` and `thumbnail.png` present). Once validated, `POST /api/drive/mass-upload` enqueues a batch job through `DriveAdapter` with live progress tracking in the Job Manager.
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
  - **Port-Based PID Discovery & Self-Termination Protection**: `ComfyManager.stop()` discovers PIDs strictly via active TCP `LISTENING` sockets on `:8188` (`_discover_pid_from_port()`) and explicitly refuses to kill `os.getpid()` or `os.getppid()`, preventing accidental WebUI server crashes.
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

## Google Drive Export & Cloud Synchronization Suite

The `main/connectivity/drive_sync/` module and `main/connectivity/sync_drive.py` CLI coordinate secure, automated asset delivery to Google Drive:

1. **Authentication Architecture (`auth.py`)**:
   - Primary: OAuth 2.0 User Flow using Google API client credentials (`.credentials/google_drive_credentials.json`). Interactive browser sign-in on first run with tokens automatically persisted and refreshed via `.credentials/drive_token.json`.
   - Fallback: Google Cloud Service Account authentication via service account key JSON.
2. **Directory & Routing Structure (`folder_manager.py`)**:
   - Resolves or creates a root folder (default `youtube_shorts_ready` configured via `GOOGLE_DRIVE_FOLDER_NAME` in `.env`).
   - Automatically maintains hierarchical subdirectories by language (`english`, `french`, `spanish`, `italian`) and format (`expression`, `game`, `roleplay`, `fun_facts`).
3. **Atomic Asset Packaging & Integrity (`uploader.py`)**:
   - Requires both the final video (`<script_id>_final.mp4`) and thumbnail (`thumbnail.png`).
   - Sets standard MIME types (`video/mp4`, `image/png`), checks file sizes, and skips files already present in the target folder with identical names to avoid redundant transfers.
4. **WebUI Integration & Execution**:
   - `GET /api/drive/status`: Reports Google Drive service connection state and authentication mode.
   - `POST /api/drive/check-readiness`: Audits a list of script IDs and returns whether both video and thumbnail exist on disk.
   - `POST /api/drive/upload/{script_id}`: Single-script synchronous upload from `ScriptDetailModal`.
   - `POST /api/drive/mass-upload`: Batch asynchronous upload executed through `DriveAdapter` in `main/webui/jobs/adapters/drive.py`, reporting real-time progress via SSE.
5. **Standalone CLI (`sync_drive.py`)**:
   ```powershell
   py main/connectivity/sync_drive.py --all
   py main/connectivity/sync_drive.py --script-id EE01
   py main/connectivity/sync_drive.py --language spanish --type game
   ```

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
| `main/connectivity/sync_drive.py` | Standalone CLI for uploading finalized video bundles to Google Drive. |
| `main/connectivity/drive_sync/` | Google Drive client suite: OAuth2/Service Account auth, hierarchical folder routing, uploader. |
| `main/webui/routers/drive.py` | FastAPI router for Drive status, readiness audits, single upload, and mass upload dispatch. |
| `main/webui/jobs/adapters/drive.py` | Background Job Manager adapter for batch Google Drive uploads. |
| `main/webui/frontend/src/components/BingoMatrixView.tsx` | Visual matrix tracker across all 16 language/format combinations. |
| `main/video_creation/_A_video_scripts/script_modifier.py` | Script modifier supporting direct parsing, LLM structuring, and automatic `clean_game_challenge()` enforcement. |
| `main/video_creation/_A_video_scripts/prompts/game_rules.py` | Authoritative GAME prompt rules enforcing clean option formatting, no stress giveaways, and separation of challenge and pressure. |
| `main/connectivity/` | Google Sheets integration suite (Apps Script Web App client, fetcher, reconciler, poster, scanner). |
| `test/run_tests.py` | Test runner for automated unit, integration, contract, WebUI, and Drive tests (370 tests passing 100%). |

---

## Agent Guidelines & Best Practices

1. **State Persistence**: Always read and update script states via `core/state_manager.py` (`StateManager`).
2. **Audio Duration Rule**: Adhere strictly to target durations: **38–48s** (85–110w) for EXPRESSION, **40–55s** (95–125w) for GAME, **60–80s max** (145–180w) for ROLEPLAY, and **40–60s** (95–135w) for FUN_FACTS.
3. **GAME Challenge Formatting**: Always enforce that GAME challenges use neutral words (no uppercase stress), start options with `A: `, `B: `, include no option connectors, specify grammatical category for single words (`a record` vs `to record`), end each option with `.`, never end with `?`, and keep `chalkboard_exercise` synchronized.
4. **GPU VRAM Discipline**: Never run ComfyUI and Llama-server under high concurrent load on 6GB GPUs. Call `ensure_llama_stopped()` before Qwen3-TTS or ComfyUI generation.
5. **Pipeline-Level Solutions Only (Zero Manual Patching)**: Fix all errors inside the core engine, prompt coordinators, FreeType renderers, and audio processors so the pipeline operates autonomously end-to-end.
6. **Master Expression Database (User-Only 'DONE')**: Pipeline scripts NEVER mutate `STATUS` to `DONE`—that privilege belongs solely to the human creator. Completed expressions with `STATUS = DONE` are strictly frozen.
7. **Verbatim Script Ingestion**: When updating scripts from `script_to_change/` or Google Sheets, the spoken words must be preserved verbatim in `content_metadata.script`.
