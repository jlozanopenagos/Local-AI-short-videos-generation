# Shorts Studio architecture

Shorts Studio is a WebUI for producing educational vertical videos in English, French, Spanish, and Italian. Start with the [repository quick start](../README.md) to configure and launch the studio.

The architecture combines local multi-modal generative AI backends (**ComfyUI Diffusion & TTS**, **faster-whisper**, **Transformers MusicGen**, and **FFmpeg** compositing) with an OpenAI-compatible LLM for organic, retention-optimized pedagogical scriptwriting.

---

## Table of Contents
1. [Core Engineering Tenets](#core-engineering-tenets)
2. [End-to-End System Architecture](#end-to-end-system-architecture)
3. [The 4 Content Formats & Narrative Engineering](#the-4-content-formats--narrative-engineering)
4. [Voice Generation: Modular Architecture, VoiceDesign Bank & Syntactic Carrier Prosody](#voice-generation-modular-architecture-voicedesign-bank--syntactic-carrier-prosody)
5. [Data Architecture & State Machine Design](#data-architecture--state-machine-design)
6. [Hardware Optimization: Low-VRAM (6GB) Engineering & Dual-Process Arbitration](#hardware-optimization-low-vram-6gb-engineering--dual-process-arbitration)
7. [The Standing Music Bank Design Pattern](#the-standing-music-bank-design-pattern)
8. [Operator Tools](#operator-tools)
9. [Modern WebUI Management Studio](#modern-webui-management-studio)
10. [Google Sheets & Drive Connectivity Suite](#google-sheets--drive-connectivity-suite)
11. [External Script Doctoring & LLM Ingestion](#external-script-doctoring--llm-ingestion)
12. [Prerequisites & Installation](#prerequisites--installation)
13. [Configuration & Environment Matrix](#configuration--environment-matrix)
14. [Studio production and maintenance](#studio-production-and-maintenance)
15. [Repository Directory Index](#repository-directory-index)

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
5. **Repository Scope & Isolation**:
   `shorts_automation` is a standalone, decoupled Git repository focused exclusively on the generative video creation pipeline. Sibling companion repositories (e.g. `GoogleSheet_UI_auditor`) operate on their own independent lifecycles, interfacing with this pipeline solely via Google Sheets Apps Script Web App endpoints and standardized CSV schemas.

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
  │   - Hybrid Engine: ElevenLabs (eleven_v3, 227-voice catalog, LRU) │
  │     for ROLEPLAY / EXPRESSION / FUN_FACTS + Local Qwen3-TTS       │
  │     (52 baseline voices) for GAME / offline fallback              │
  │   - Accent routing (60/40 ES), ICL refs & Roleplay acting cues    │
  │   - Syntactic Carrier Prosody, ?/! Contours & Stress Gating       │
  │   - Per-Type Pause Choreography & Scipy Broadcast Mastering       │
  └───────────────┬────────────────┬──────────────────┬───────────────┘
  ├─────────────────────────────────────────────────────────────────────────────────────────┐
  │        │                │                  │                                            │
  │        ▼                ▼                  ▼                                            │
  │  ┌────────────────────────┐┌──────────────┐┌─────────────────────────┐                  │
  │  │  STAGE 3: _C_images    ││STAGE 4: _D_  ││ STAGE 5: _F_thumbnails  │                  │
  │  │ - Modular visual/      ││Standing Bank ││ - Native CPU Pillow +   │                  │
  │  │   + Cultural Worlds    ││160 Pre-Made  ││   FreeType (20 templates│                  │
  │  │ - Positive 19yo 1:7.5  ││Curated Audio ││   + ES LatAm/Spain)     │                  │
  │  │   sclera eyes cfg=1.0  ││Jams (30s)    ││ - Zero VRAM Generation  │                  │
  │  │ - Native CPU FreeType  │└──────┬───────┘│   (576x1024)            │                  │
  │  │   Chalkboard Typography│       │        └─────────┬───────────────┘                  │
 │  └───────────────┬────────┘       │                  │                                  │
 │                  └────────────────┼──────────────────┘                                  │
 │                                   ▼                                                     │
 │  ┌───────────────────────────────────────────────────────────────────┐                  │
 │  │               STAGE 6: video_creation/_G_video_assembly           │                  │
 │  │   - Modular assembly/ Split by Video Type + Neutral Lang Hooks    │                  │
 │  │   - Word-Timestamp Audio Transcription via faster-whisper (CPU)   │                  │
 │  │   - Script-to-Audio Forced Alignment (100% Homophone Fidelity)    │                  │
 │  │   - Lower-Middle Safe-Zone ASS Subtitles (Roleplay Speaker Colors)│                  │
 │  │   - Challenge Scene Subtitle Suppression (Prevents Quiz Spoilers) │                  │
 │  │   - Per-Type BGM Volume Envelopes & Cosine-Eased Motion Curves    │                  │
 │  │   - Smooth FFmpeg xfade Cuts, 2s Intro Bumper, 3s Outro CTA Card  │                  │
 │  └────────────────────────────────┬──────────────────────────────────┘                  │
 │                                   │                                                     │
 │                                   ▼                                                     │
 │                        [Final shorts MP4 Video] ──(optional sync_drive.py)──> [Drive]  │
 │                  (<OUTPUT_DIR>/video_assets/.../final.mp4)                              │
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
| **Visual Structure** | 5 Visual Scenes (ComfyUI) | 6 Visual Scenes (6 ComfyUI Renders) | 5 Scenes (3 ComfyUI + Chalkboard + Static Tito) | 5 Visual Scenes (ComfyUI) |
| **JSON Keys** | `title`, `hook`, `setup`, `discovery`, `example`, `payoff` | `title`, `hook`, `DIALOGUE_PART_1`–`4`, `PAYOFF` | `title`, `hook`, `challenge`, `pressure`, `answer`, `explanation` | `title`, `hook`, `setup`, `discovery`, `explanation`, `payoff` |

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
- **TTS Stress Notation & Syntactic Carrier Protocol**: For heteronyms and minimal pairs, stressed syllables are capitalized in the script JSON (`REcord` vs `reCORD`, `PROject` vs `proJECT`) for title/graphic clarity. Downstream in Stage 2, dialogue turns are generated in continuous single takes using natural syntactic carriers (`a PREsent` / `to preSENT`, `a PROject` / `to proJECT`), eliminating artificial BPE respellings, and scored via the Acoustic Prominence Quality Gate (`stress_enhancer.py` + `acoustic_evaluator.py`).
- **4-Tier Cultural World Atlas (`visual/common/environment.py` & `visual/languages/*.py`)**: Replaces generic studio/workshop/greenhouse settings with **124 culturally authentic venues** across the 4 languages (**36** English global Anglophone, **32** Spanish Spain + Latin America, **28** French France + Francophone, **28** Italian regional Italy), paired with stylish venue-matched teen fashion, a **Triplet Collision Guard** ensuring matching-number `E`/`G`/`R` topics receive distinct worlds, and **Gemini Prompt Auditor** auto-reroll excluding previous draft settings.
- **6-Beat Calibrated Roleplay Storyboard (`visual/types/roleplay/rules.py`)**:
  Roleplay renders **6 distinct illustrations** via ComfyUI (`hook`, `dialogue_part_1`–`4`, `payoff`):
  1. `hook`: Medium-wide `35mm` establishing diagonal OTS two-shot crossing a physical threshold (0% camera eye contact).
  2. `dialogue_part_1`: Solo **3/4 angled waist-up** medium dialogue shot on `PERSON_ONE` (`50mm` lens, turned 3/4 right looking off-camera toward `PERSON_TWO`, active mid-sentence gesture or setting prop interaction, `PERSON_TWO` off-camera).
  3. `dialogue_part_2`: `180°` reverse **3/4 angled waist-up** medium dialogue shot on `PERSON_TWO` (`50mm` lens, turned 3/4 left looking off-camera toward `PERSON_ONE`, optional soft-focus foreground shoulder OTS cue, calm reassuring gesture/lean).
  4. `dialogue_part_3`: `90°` side profile or high-angle top-down two-shot prop interaction (`50mm` lens, both characters).
  5. `dialogue_part_4`: Solo medium-wide 3/4 dynamic motion shot on `PERSON_ONE` (`35mm` lens, wider knees-up/hips-up framing stepping forward with renewed confidence).
  6. `payoff`: Celebratory wide action two-shot in motion (`28mm` lens).
- **Story World Anchor & Purely-Positive Z-Image-Turbo (`cfg=1.0`) Pipeline**:
  `_C_image_generation` executes a two-pass architecture under `visual/`: Pass 1 builds an overarching `general_prompt` locking setting, lighting, and complete layered character designs (upper garment + trousers/chinos/skirt; omitting footwear in cropped shots); Pass 2 synthesizes non-repetitive scene prompts anchored to this world (`GAME`, `EXPRESSION`, `FUN_FACTS` `hook` shots and `ROLEPLAY` dialogue shots use cropped waist-up / mid-thigh framing and strip wearable footwear via `strip_footwear_clauses` / `_CROPPED_SCENES`). Because Z-Image-Turbo runs at `cfg=1.0`, `sanitize_and_style_prompt()` appends a concise **purely-positive** style anchor (`19-year-old young adult`, `realistic young-adult 1:7.5 head-to-body proportions`, `expressive 2D animated eyes with clean white sclera, dark pupils, defined eyelids, and bright catchlights`, `pure text-free visual illustration`), never skips the proportion anchor on shortened tails, protects compound nouns (`reading lamp`, `reading alcove`, `reading hall`, `reading boxes`, `calling card`, `speaking lectern`), strips legacy negated tails idempotently, and upgrades younger ages/dot eyes automatically.
- **Strict Gender-Accurate Hairstyle Sanitization (`sanitize_and_style_prompt`)**:
  Enforces programmatic guardrails preventing male characters from receiving female hairstyles (buns, bobs, ponytails, chignons) or female garments, and female characters from receiving masculine haircuts (quiffs, buzz cuts, crew cuts).
- **Locked Character Continuity Anchors (`extract_or_build_character_anchors` / `CharacterCast`)**:
  Extracts and persists character hairstyles, skin tones, eye anchors, wardrobes, and `19-year-old` profiles across all scenes in state JSONs.
- **Universal Multi-Character Gender Specification Rule (Zero-Ambiguity Mandate)**:
  Whenever MORE THAN ONE character appears in a visual prompt, the sex of each character must be explicitly defined (e.g. *"one 19-year-old young man and one 19-year-old young woman"*). Roleplay states track explicit character genders via `speakers_gender: {"PERSON_ONE": "...", "PERSON_TWO": "..."}` with complete upper + lower venue outfits.
- **`SPECIAL_TREATMENT` Classification System**:
  - Optional 6th CSV column (`idiomatic`, `phonetic`, `false_friend`, or blank) defining the primary learning lens.
  - **Idiomatic Arc (Error #4 Fix)**: For multi-word figurative idioms, the LLM is instructed to enforce active usage modeling: P2 drops the full idiom in Part 1; P1 reacts to literal image while P2 clarifies in ≤1 sentence in Part 2; P2 demonstrates a new real-life usage in Part 3; and **P1 must use the complete idiom in an original sentence in Part 4** (the proof of learning).
  - **Automated Quality Gate**: Stage A's Roleplay validation rules verifies both the full idiom in Part 1 and P1 active usage in Part 4, triggering auto-retries with targeted feedback upon failure.

### 3. GAME: Fast-Paced Interactive Trivia
- **Trivia Standard**: Pure educational quiz game—no fictional narratives or roleplay acting.
- **5 Authorized Archetypes (`types/game/archetypes.py`)**:
  1. *FALSE_FRIEND_TRAP*: Deceptive translation blunders, false cognates, and native idiom testing vs literal blunders (*parenti* vs *parents*, *embarazada* vs *embarrassed*, *poser un lapin*, *break a leg*).
  2. *ODD_ONE_OUT*: Pattern recognition challenge with 3 or 4 candidates where one breaks a hidden grammar or category rule.
  3. *SPOT_THE_MISTAKE*: Learner ego-challenge targeting common preposition or false agreement errors.
  4. *MINIMAL_PAIR_SHOWDOWN*: Auditory perception challenge testing word stress (`PROject` vs `proJECT`) or phonemic contrasts.
  5. *FILL_IN_THE_BLANK_SPEEDRUN*: High-velocity collocation and idiomatic sprint with 3 or 4 candidate options.
- **Canonical 5-Section Narrative Architecture**:
  - `[HOOK]` (12–18 words): Fast dilemma or ear test setup.
  - `[CHALLENGE]` (25–40 words): Narrator speaks the scenario and candidate options cleanly with zero stress giveaways, zero connectors, and without spoiling the answer.
  - `[PRESSURE]` (8–14 words): Snappy countdown urging decision (*"Which one is it? A or B? Your answer is coming!"*). Strict separation: NEVER leave countdown/pressure text inside `[CHALLENGE]`.
  - `[ANSWER]` (15–22 words): Clear reveal of the winning option with linguistic justification.
  - `[EXPLANATION]` (20–30 words): Practical native usage rule, contrast summary, and punchy call-to-action.
- **Acoustic Challenge Delivery & Syntax Rules**:
  - **No Answer Spoilers in Spoken Audio**: The Narrator voices the scenario or prompt question clearly WITHOUT spoiling the solution in the test sentence before presenting the candidate choices.
  - **Neutral Lowercase Speech (Zero Stress Giveaways)**: Spoken challenge sentences use standard lowercase natural speech. NEVER write uppercase stress giveaways (e.g. `REcord` or `CONtract`) in the spoken challenge sentence, which would spoil the ear test.
  - **Explicit Option Tags**: Options MUST start with uppercase letter tags: `A: `, `B: `, `C: `, and optionally `D: `. Provide 3 or 4 options (or 2 for binary pairs).
  - **Zero Connectors**: NO coordinating conjunctions or connectors (`or`, `and`, `o`, `ou`, `oppure`, `e`) or commas before option tags.
  - **Carrier Context for Single Words**: When options are single words (e.g. heteronym nouns vs verbs), specify their grammatical category or carrier context (e.g. `A: a record. B: to record.`).
  - **Period Termination**: Every option MUST terminate with a period (`.`). The last option must NEVER end with `?`.
  - **Zero Spoken Blanks**: Spoken challenge audio NEVER contains raw blanks (`___` or `____`). The visual blank belongs ONLY on the chalkboard.
- **Chalkboard Exercise Synchronization & Localization**:
  - The `chalkboard_exercise` property in state JSON MUST be kept 100% synchronized with the `challenge` property.
  - **100% Target Language Purity**: Localized headers via `get_localized_game_header()` (e.g. `QUE SIGNIFIE CETTE EXPRESSION ?`, `OÙ EST L'ERREUR ? / COMPLÉTEZ :`, `¿QUÉ SIGNIFICA ESTA EXPRESIÓN?`, `TROVA L'INTRUSO:`). Zero English words or headers on French, Spanish, or Italian chalkboards.
- **Visual Chalkboard Renderer (`_C_image_generation/core/chalkboard_renderer.py`)**:
  - High-resolution typography rendered on CPU using Pillow and FreeType (Segoe Print Bold) onto `empty_chalkboard.png` with chalk-yellow questions, dividers, translucent green option cards, and yellow letter badges (A, B, C, D) in milliseconds with zero VRAM usage.
  - **Clean Option Text Isolation (`clean_option_text`)**: Programmatically strips trailing punctuation and coordinating conjunctions (`or`, `and`, `o`, `ou`, `e`) from option choices, ensuring pristine options without trailing commas or awkward words.
  - **Automatic Spoken Answer Masking in Listening Challenges (`mask_revealed_answer_in_question`)**: For acoustic and listening quizzes where the spoken narrative pronounces the answer, the renderer automatically detects if an option phrase appears in the question text and masks it with `_________`. This guarantees the visual chalkboard never spoils the spoken quiz.
  - **Subtitles**: Subtitles are suppressed exclusively during the `challenge` section so the chalkboard exercise remains clear and uncluttered, and the answer is never spoiled in text while the challenge audio plays. Subtitles resume normally for all other sections.
- **Suspense Gap**: Audio engine inserts an exact 2.20-second suspense pause (`pressure_gap`) between `pressure` and `answer`.
- **5-Scene Calibrated Image Pipeline (3 ComfyUI Renders)**:
  - ComfyUI renders **3 distinct scenes** (`hook`, `answer`, and `explanation`), with zero duplicate images between `answer` and `explanation`.
  - `challenge` is rendered natively on CPU via FreeType onto `empty_chalkboard.png`.
  - `pressure` is resolved via `resolve_static_scene_path` from static per-language `<lang>_waiting.png` (zero-copy).

### 4. FUN_FACTS: Viral Linguistic Curiosities
- **Target Language Localization**: Prompts and state contents are localized 100% in the target language (French, Spanish, Italian, English) to guarantee authentic regional nuance and zero translation artifacts.
- **6 Authorized Formats**: Format A (3 Facts), Format B (One Big Curiosity), Format C (Challenge), Format D (Mystery), Format E (Comparison), Format F (Ranking/List).
- **Calibrated 5-Scene Count**: Generates 5 distinct thematic scene images (`hook`, `setup`, `discovery`, `explanation`, `payoff`) via ComfyUI with story-world consistency.
- **Factual Integrity**: Programmatic guardrails reject folk etymologies and unverified language myths.

---

## Voice Generation: Hybrid ElevenLabs + Local Qwen3-TTS & VoiceDesign Bank

Stage 2 (`_B_voice_generation`) combines **ElevenLabs (`eleven_v3`)** cloud synthesis (`_B_voice_generation/elevenlabs/`) for `ROLEPLAY`, `EXPRESSION`, and `FUN_FACTS` (`ELEVENLABS_HYBRID_TYPES`) with local **Qwen3-TTS** (`1.7B-Base` cloning + `1.7B-VoiceDesign` reference bank) for `GAME` and local overrides (`VOICE_PROVIDER=local`). Both share per-type **broadcast DSP vocal mastering** (`dsp_mastering.py`) and raised-cosine fade trimming (`audio_processor.py`).

- **ElevenLabs Hybrid Routing (`elevenlabs/{catalog,client,orchestrator,tags}.py`)**: Curated **227-voice** `voice_catalog.json` (`EN: 57`, `FR: 70`, `IT: 50`, `ES: 50`) using full-cycle LRU rotation (`max_history=60`), same-speaker-only `previous_text`/`next_text` stitching, native `voice_settings["speed"]` (`0.94` Roleplay, `0.92` Expression/Fun Facts), and balanced Narrator genders (`male <-> female`) across `(E, R)` pairs while preserving local `speakers_voice` untouched.

### 1. Tokenizer Fragmentation & The Citation Monotone Trap
- **The BPE Tokenizer Flaw**: In autoregressive TTS models (such as Qwen3-TTS), sub-word tokenizers split artificial phonetic respellings (`pri-ZENT`, `PRAHJ-ekt`) or hyphenated words into fragmented tokens. This causes the neural vocoder to hallucinate tense, unnatural vowel phonemes (e.g. `/reɪ/` "ray-cord" instead of reduced `/rɪˈkɔːrd/`).
- **The Citation Trap**: Words spoken in isolation or unconditioned citation forms (e.g. *"A: record, or B: record?"*) drop pitch inflection and revert to flat citation tone, completely wiping out educational stress contrast.

### 2. Syntactic Carrier Architecture (Pure Natural Priming)
- **Carrier Conditioning**: Autoregressive acoustic models naturally deduce part-of-speech, vowel reduction, and pitch contours from syntactic syntax:
  - **Noun Carrier Priming**: Nouns are conditioned with determiners/articles (`a PREsent`, `the REcord`, `a PROject`, `a PERmit`, `an OBject`).
  - **Verb Carrier Priming**: Verbs are conditioned with infinitives/particles (`to preSENT`, `to reCORD`, `to proJECT`, `to perMIT`, `to obJECT`).
- **Continuous Single-Take Synthesis**: Sentences and dialogue turns are synthesized in continuous single takes, avoiding unnatural cross-fade boundaries and ensuring natural intonation contours ($F_0$ pitch reset and cadence).
- **Purge of Artificial Respellings**: All fake phonetic respellings (`PREH`, `PROH`, `prih`, `pruh`, `RECK-ord`) are strictly purged across all prompt CSV queues, LLM generation rules, and state script JSONs.

### 3. Acoustic Prominence Quality Gate (`core/acoustic_evaluator.py`)
When `is_stress_pronunciation_vital()` detects heteronyms or syllable stress topics, Stage 2 activates an automated acoustic evaluation quality gate:
- **Multi-Candidate Sampling (`--candidates <N>`)**: Generates $N$ candidates (default 3) per segment under varied random seeds.
- **Mathematical Prominence Metrics**:
  - **Peak RMS Energy Ratio**: Compares root-mean-square amplitude between the target stressed and unstressed syllables.
  - **Fundamental Frequency ($F_0$) Delta**: Calculates pitch peak excursion across syllable boundaries.
  - **Duration Contrast**: Evaluates vowel elongation on the accented syllable.
- **Threshold Gating**:
  - **Nouns**: Require front-syllable prominence (RMS ratio $\ge 1.05$, $F_0$ delta $> 0$).
  - **Verbs**: Require back-syllable prominence (RMS ratio $\ge 1.10$, $F_0$ delta $> 0$).
- Automatically selects the candidate with the highest prominence score.

### 4. Intentional Error Simulation & `kokoro_golden` Reference Fallback (`core/stress_enhancer.py`)
- **Learnable Phonetic Error Contrasts**: When Roleplay dialogue scripts model an intentional learner pronunciation error (`detect_intentional_stress_errors()`), `enhance_stress_text_for_tts()` applies targeted phonetic rewrites (`INTENTIONAL_ERROR_PHONETIC_REWRITES`) so neural language priors do not auto-correct the mistake, while preserving clean visual stress notation for captions.
- **Tiered Reference Fallback**: Curated VoiceDesign clips and clean `open_swara` clips are always preferred for voice casting; legacy `kokoro_golden_*.wav` reference clips remain only as a last-resort fallback (`tier=2` in `VoiceCastingEngine`).

### 5. Syllable Stress Subtitle Synchronization (`subtitle_builder.py`)
In `_G_video_assembly/core/subtitle_builder.py`, word-level animated subtitles (Hormozi style) preserve mixed-case syllable capitalization (`PREsent` vs `preSENT`, `PROject` vs `proJECT`) while rendering all other words in uppercase. Viewers visually see the exact syllable being emphasized in real time.

### 6. Studio voice jobs

Studio's Voice job calls `synthesize_script_voice()` through the shared adapter. **Force** rerenders the selected scripts. **Recast** requests a different cast. The job supports accent and engine overrides, and the catalog reads the generated master WAV and section timings. A failed forced render preserves the previous master and timings.

Studio keeps one known candidate ahead when a section already requires multiple takes. Conditional retries wait for the acoustic checks. Narrator recovery uses a bounded attempt and can select from finished takes when it times out. Studio cancels only the ComfyUI prompts owned by its voice job. The standalone voice modifier remains as a maintenance utility.

### 7. Multilingual Native Diction Guidance
Non-English pronunciation scripts receive native articulatory guidance tailored to each language's phonology:
- **Italian Dizione**: Crisp distinction between single and double consonants (`t` vs `tt`, `n` vs `nn`), short open vowels preceding geminate consonants, and dental stop precision.
- **Spanish Dicción**: Sharp contrast between single tap `r` and double alveolar trill `rr`, pure bright vowels without English diphthongs.
- **French Diction**: Natural phrase-final tonic accent, clean liaison and elision, melodic cadence and prosody.

### 8. Topic Disambiguation: Linguistic vs. Psychological Stress
`is_stress_pronunciation_vital()` disambiguates between linguistic pronunciation scripts and conversational/psychological topics (e.g. *"le stress des examens"*, *"gestion du stress"*, *"stress relief"*). Scripts addressing anxiety or relaxation retain standard expressive acting styles with zero phonetic prompt pollution.

### 9. Modular Language Profiles, Neutral Casting & `VOICE_ENGINE` Rollback (`_B_voice_generation/voice/`)
Each target language owns an independent `LanguageVoiceProfile` under `voice/languages/` coupled with deterministic anti-repetition casting (`VoiceCastingEngine` persisted in `<OUTPUT_DIR>/voice_quality/casting_history.json`) and rollback/provider toggles (`VOICE_PROVIDER=auto|local|elevenlabs` and `VOICE_ENGINE=typed|legacy|legacy:<type,lang>`):
- **English (`voice/languages/english.py`)**: 70/30 `en_us_neutral` / `en_uk_neutral` neutral accent mix (local `narrator_sampling`: `0.79`/`0.76`) with automatic UK/US topic locking and **English-manifest ICL locking** (`ComfyClient._has_manifest_ref_text()` sets `use_icl=True` / `x_vector_only=False` + exact `ref_text`).
- **French (`voice/languages/french.py`)**: Parisian *esprit français* legato *groupes rythmiques* and liaisons (`fr_standard`, local `narrator_sampling`: `0.79`/`0.76`).
- **Spanish (`voice/languages/spanish.py`)**: Exact Bresenham accent rotation (**60% `es_latam_neutral`** / **40% `es_spain_castilian`**) with automatic Spain vs. LatAm dialect locking (`detect_dialect_hint()`), plus non-destructive `prepare_tts_prosody_text()` opening `¿`/`¡` injection (`narrator_sampling`: `0.79`/`0.76`).
- **Italian (`voice/languages/italian.py`)**: High-energy melodic prosody and crisp double consonants (`it_standard`, local `narrator_sampling`: `0.79`/`0.76`).
- **Sampling Ceilings & Quality Gates**: `compute_segment_sampling()` caps `temperature <= 0.90` and `subtalker_temperature <= 0.86`; narrator-only clean Fast-Pass skips extra candidate reruns at score `>= 0.70`; `GAME` checks `high_impact_sections = ("hook", "answer")` and `FUN_FACTS` checks `("hook",)`; `acoustic_evaluator.py` restricts `Flat question intonation` checks to `word_count <= 9`.

### 10. Local voice bank and format-specific delivery

The current workstation bank contains **52 baseline voices** (after retiring the 75 unused Roleplay emotion-variant clips), indexed in `<VOICE_BANK_DIR>/voice_bank_manifest.json` with 100% verified `ref_text` and `f0_mean`. Casting excludes `roleplay_*` actor baselines from `GAME`/`FUN_FACTS`, removes blacklisted fallback speakers **before** accent locking, and keeps `kokoro_golden` clips only as a legacy fallback.

Automatic casting prefers a warm narrator for teaching and an expressive host for Game when the matching pool supports rotation. Voices flagged in listening review for overly subdued or forceful delivery stay available for deliberate casting or as fallbacks. Narrator instructions favor contrast through timing and word stress at conversational volume.

- **Expression, Roleplay, and Fun Facts** default to **ElevenLabs (`eleven_v3`)** when configured (`ELEVENLABS_HYBRID_TYPES`) with same-speaker stitching context, and seamlessly support Local Qwen3-TTS via `VOICE_PROVIDER=local`.
- **Game** uses **Local Qwen3-TTS** by default with a single narrator, even option emphasis, and fixed `0.26s` option micro-pauses.
- **Roleplay** gives each character a continuous turn, a performance cue (or ElevenLabs audio tag), and the other character's preceding turn as instruction-only context on local renders. The cast stays pinned across all four dialogue parts.

Build staged auditions with `--auditions-only --bank-dir <scratch-bank> --skip-variants`. Filter with `--language` or `--speaker-ids` for a small batch. Use `--promote-from <scratch-bank> --speaker-ids <approved-ids>` to add reviewed and validated references to the active bank. Add `--dry-run` to inspect the selection first.

### 11. Per-Type Pause Choreography & Scipy Broadcast Vocal Mastering
Stage B applies format-specific pause timing and pure `numpy` + `scipy` DSP mastering (`voice/common/dsp_mastering.py`: HPF, mud cut, warmth, presence EQ, air shelf, split-band de-esser, soft-knee RMS compressor, ITU-R BS.1770 LUFS target leveling, and `-1.0 dBFS` / `0.891` true-peak soft limiter):

| Video Type | Target LUFS | Presence EQ (`Q`) / Comp Ratio | Signature Pause Choreography |
| :--- | :---: | :--- | :--- |
| **EXPRESSION** | `-15.2 LUFS` | `+2.6 dB @ 3.5 kHz` (`0.9`) / `2.9:1` | `hook_to_next_gap=0.28s`, `pre_discovery_gap=0.38s` |
| **FUN_FACTS** | `-15.2 LUFS` | `+2.6 dB @ 3.2 kHz` (`0.9`) / `2.8:1` | `hook_to_next_gap=0.32s`, `pre_discovery_gap=0.45s` |
| **GAME** | `-15.0 LUFS` | `+2.6 dB @ 3.5 kHz` (`0.9`) / `3.2:1` | `pressure_gap=2.20s`, `option_micro_pause=0.26s`, `answer_to_explanation_gap=0.28s` |
| **ROLEPLAY** | `-16.0 LUFS` | `+1.5 dB @ 3.2 kHz` (`1.0`) / `2.2:1` | `hook_to_next_gap=0.38s`, `dialogue_to_payoff_gap=0.35s` |

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
- **Queue Documentation**: See [input/csv/README.md](input/csv/README.md) for detailed column requirements and validation standards.

---

## Hardware Optimization: Low-VRAM (6GB) Engineering & Dual-Process Arbitration

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
│ Smart Cache & Stage Cleanup   │ Reclaims VRAM via /free only on stage  │
│                               │ transitions while keeping model cache. │
│ Input Folder Auto-Cleanup     │ Temporary reference WAVs/PNGs deleted  │
│                               │ immediately post-inference.            │
│ Dual-Process VRAM Arbiter     │ Pauses/stops local LLM server prior to │
│                               │ Qwen3-TTS audio synthesis via          │
│                               │ LlamaManager. Frees ~3-4GB VRAM.       │
└───────────────────────────────┴────────────────────────────────────────┘
```

### Dual-Process VRAM Arbitration (`core/llama_manager.py` & `tools/llama.py`)
On consumer GPUs with 6GB to 8GB of VRAM, running both an LLM server (for script writing) and ComfyUI Qwen3-TTS (for voice generation) simultaneously can cause Out-Of-Memory (OOM) crashes:
- **`LlamaManager` Dynamic Lifecycle**:
  - `ensure_llama_stopped()`: Halts or pauses the LLM server background process and triggers memory reclamation before audio synthesis starts.
  - `ensure_llama_running()`: Resumes or restarts the LLM server once voice generation completes.
- **Headless Supervisor CLI (`tools/llama.py`)**: Provides complete command-line lifecycle management: `start`, `stop`, `status`, `restart`, and `logs -f`.

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

## Operator Tools

Use the [operator tools](tools/README.md) for service supervision, media bank preparation, teaser extraction, and targeted maintenance. Use the studio to queue standard production stages.

## Modern WebUI Management Studio

The production entry point is the browser-based studio (`main/webui/`) powered by a **React 19 + TypeScript + Vite** frontend and a **FastAPI** backend:

- **Launch Command**:
  ```powershell
  py main/tools/webui.py
  ```
  Opens `http://127.0.0.1:8190` automatically in your default browser.

- **The 6 Core Views**:
  1. **Home**: High-level pipeline overview, active KPI summaries, and quick launch actions.
  2. **Script Catalog (`ScriptList.tsx` & `ScriptDetailModal.tsx`)**: Filter/search all `1,224` scripts, inspect sections/audio/images/SEO metadata, edit thumbnail/chalkboard text (`render-thumbnail`, `render-chalkboard`), run the **Gemini Prompt Auditor**, redo single scenes or queue a full image rebuild preserving your edited `general_prompt` (`preserve_general_prompt=True` via two-phase Llama + ComfyUI handoff), or upload scoped assets to Google Drive (`POST /api/drive/scripts/{script_id}/upload`).
  3. **Queue (`JobQueueView.tsx`)**: Task runner with live terminal log streaming via WebSockets (`/ws/jobs/{job_id}`), progress bars, and cancellation controls.
  4. **Mass Assets Creation Studio (`MassAssetsCreationView.tsx`)**:
     - Targeted batch execution across all **7 stages**: **Script Dialogues** (Stage A), **Scene Images** (Stage C — `preserve_general_prompt=False` so `force` / `regenerate_prompts` rebuilds both `general_prompt` and storyboard `image_prompts`), **Voice Files** (Stage B — hybrid ElevenLabs `eleven_v3` + Local Qwen3-TTS with credit estimator & provider/model selectors), **Thumbnail Images** (Stage F — 20 CPU templates + Spanish LatAm/Spain variants), **Chalkboard Images** (Game only, CPU), **Video Assembly** (Stage G — strict `keep_subtitles` toggle, non-overlapping ASS subtitles, staged MP4 replacement), and **Google Drive Upload** (`drive_upload` — scoped `all`/`video`/`thumbnail` replacement).
     - Accepts arbitrary ID lists, CSV drag-and-drop, or one-click catalog presets (including pending thumbnails filtering `stages.thumbnails !== 'done'`) with real-time validation (`POST /api/scripts/validate-ids`).
  5. **Google Sheets Sync (`GoogleSheetsSyncView.tsx`)**: Supports both **Script Modifications** (`POST /api/sheets/sync`: Column D + Column B across all 16 sheets with `GAME` option merging and `Counter`-based diffing) and **Thumbnail Titles Sync** (`POST /api/sheets/sync-thumbnails`: Column J `THUMBNAIL_TITLE` across all 16 sheets, resetting only `thumbnail_generation`).
  6. **Bingo Matrix (`BingoMatrixView.tsx`)**: At-a-glance asset readiness matrix across all 16 language/format matrices.

---

## Google Sheets & Drive Connectivity Suite

Located in `main/connectivity/`, this modular suite coordinates both external Google Sheets synchronization (16 language/type matrices using Option A routing `?id=<SPREADSHEET_ID>`) and automated Google Drive clean replacement uploads:

```
main/connectivity/
├── sync_sheets.py                  # Principal Runner 1: Syncs Sheets to synced_sheets/_3_columns/ or _4_columns/
├── fetch_corrected_scripts.py      # Principal Runner 2: Pulls Column D (SCRIPT_CHANGED) to CSV
├── reconcile_scripts.py            # Principal Runner 3: Audits & reorganizes local scripts against Sheets
├── post_scripts.py                 # Principal Runner 4: Posts scripts to Google Sheets (Cols A-C or A:D)
├── scan_ready_scripts.py           # Principal Runner 5: Scans ready scripts and exports by date
├── sync_drive.py                   # Principal Runner 6: Replace a Google Drive video and thumbnail bundle
├── core/                           # Endpoints registry & resilient HTTP client (redirects & retries)
├── apps_script/                    # Apps Script Web App implementation (doGet/doPost) & deployment guide
├── drive_sync/                     # Google Drive API v3 client (`drive_client.py`) & replacement sync (`sync_service.py`)
├── sheet_sync/                     # Syncs Columns A-C (or A:D) to local CSV files
├── corrected_scripts/              # Pulls Column D (SCRIPT_CHANGED) to input/csv/script_to_change/
├── reconcile/                      # Reorganizes local scripts to match Google Sheets order
├── post_scripts/                   # Safe script publisher to Google Sheets
└── ready_scripts/                  # Scans ready scripts and groups by script_date
```

### 6 Core Capabilities & Principal Runner Scripts:
1. **Master Sheet Synchronization (`connectivity/sync_sheets.py`)**:
   Fetches records from Google Sheets and writes standardized CSV files to `<OUTPUT_DIR>/connectivity/synced_sheets/_3_columns/` or `_4_columns/`.
2. **Pulling External Corrections (`connectivity/fetch_corrected_scripts.py`)**:
   Scans Column D (`SCRIPT_CHANGED`) for user or external editor revisions. Outputs filtered modifications to `main/input/csv/script_to_change/<lang>_<type>_script_to_change.csv` with schema `ID, NEW_SCRIPT`. Supports full sheets, ranges (e.g. `01-50`), single IDs, or reading IDs from `input/csv/script_to_change/ids_to_fetch.csv`.
3. **Reconcile & Reorganize Scripts (`connectivity/reconcile_scripts.py`)**:
   Audits local scripts against Google Sheets order, preserving sheet row sequences and canonical expression names while appending new local entries at the end. Exports clean mass-update CSVs to `<OUTPUT_DIR>/connectivity/scripts_to_post/`.
4. **Safe Script Publishing (`connectivity/post_scripts.py`)**:
   Publishes scripts from `scripts_to_post` (or `scripts_to_see` / `_4_columns`) back to Google Sheets.
   - **Column D Safety Guarantee**: In standard 3-column mode, modifies **ONLY Columns A, B, and C** (`ID`, `EXPRESSION`, `SCRIPT`). Column D (`SCRIPT_CHANGED`) is **strictly preserved and never overwritten** unless 4-column mode is explicitly selected.
   - Interactive scopes: All sheets, specific sheet (language + type), number range (e.g. `10-20`), or specific ID list.
   - Supports both in-place updates of existing IDs and automatic appending of new records.
5. **Scan Ready Scripts by Date (`connectivity/scan_ready_scripts.py`)**:
   Scans Google Sheets for rows where `script_ready` (Column E) is checked and `video_ready` (Column G) is NOT checked. Skips completed videos (`video_ready == True`). Exports grouped `ID, expression` records into daily CSV files in `<OUTPUT_DIR>/connectivity/ready_scripts/<YYYY-MM-DD>_ready_scripts.csv` (or `undated_ready_scripts.csv` if date is blank).
6. **Google Drive Export & Scoped Replacement Sync (`connectivity/sync_drive.py` & `drive_sync/`)**:
   Supports `drive_scope` (`all`, `video`, or `thumbnail`), validates the required local asset(s) (including paired Spanish `thumbnail_latam.png` + `thumbnail_spain.png`), automatically falls back from expired `token.json` to `client_secret.json` browser OAuth re-auth, removes duplicate `<script_id>` folders and old target files inside `<root>/<language>/<expressions|fun_facts|game|role_play>/<script_id>/`, and updates `StateManager`.

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
# ComfyUI, Local Qwen3-TTS & ElevenLabs Hybrid Voice Configuration
# ==============================================================================
COMFY_API_URL=http://127.0.0.1:8188
# COMFY_DIR=../../ComfyUI_windows_portable
# COMFY_OUTPUT_DIR=../../ComfyUI_windows_portable/ComfyUI/output
# COMFY_INPUT_DIR=../../ComfyUI_windows_portable/ComfyUI/input
# OPEN_SWARA_DIR=../../ComfyUI_windows_portable/open-swara/voices
# VOICE_BANK_DIR=../../ComfyUI_windows_portable/open-swara/voices/voice_design_bank
# VOICE_ENGINE=typed
# VOICE_PROVIDER=auto            # auto | elevenlabs | local
# ELEVENLABS_API_KEY=            # Configured via main/.env or WebUI modal
# ELEVENLABS_MODEL_ID=eleven_v3
# GEMINI_API_KEY=                # Configured for WebUI Gemini Prompt Auditor

# ==============================================================================
# Media Storage Directory
# Isolates bulky videos, WAVs, and review CSVs onto high-capacity storage
# ==============================================================================
OUTPUT_DIR=./output
```

---

## Studio production and maintenance

Launch the studio with `python tools/webui.py` from this directory. Start a script from **Script Catalog**, or use **Mass Creation** to paste IDs, upload an ID CSV, or choose scripts from the catalog. Queue voice, scenes, thumbnails, and assembly in order. Use **Queue** to see progress and logs, and **Media Players** in the script details to inspect the assets. Assembly requires completed voice and scene stages.

Mass Creation includes optional image seeds, voice accent and engine overrides, voice recasting, and subtitle reuse. **Sheets Sync** applies remote script revisions. **Drive Upload** delivers completed video and thumbnail pairs.

### Standalone maintenance tools

Music-bank creation, voice-bank creation, teaser extraction, and database and auditing tasks have separate operator tools.

```bash
python video_creation/_D_music_generation/main.py --language english --video-type expression
python video_creation/_B_voice_generation/tools/build_voice_bank.py --dry-run
python video_creation/_G_video_assembly/little_short_creation.py --id EE01 --lapse 10-16
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

# Mass reset pipeline stage status across state files and resync status manifest
python tools/database/reset_stage_status.py --stage voice_generation --yes
python tools/database/reset_stage_status.py --stage image_generation -l french -t expression --yes
python tools/database/reset_stage_status.py --stage voice_generation --dry-run

# Audit & synchronize Column D script changes to state JSONs
python tools/check_script_changes.py --check-only
python tools/check_script_changes.py --apply

# Headless ComfyUI Process Supervisor & CLI
python tools/comfy.py start
python tools/comfy.py status
python tools/comfy.py logs -f
python tools/comfy.py stop

# Headless LLM Server Process Supervisor & CLI
python tools/llama.py start
python tools/llama.py status
python tools/llama.py logs -f
python tools/llama.py stop

# Modern WebUI Management Studio (FastAPI + React 19 SPA)
python tools/webui.py
python tools/webui.py --port 8080 --no-browser
```

### Google Sheets & Drive Connectivity Suite
```bash
# Feature 1: Synchronize all Google Sheets to local connectivity CSVs (synced_sheets/_3_columns or _4_columns)
python connectivity/sync_sheets.py --all

# Feature 2: Pull Column D (SCRIPT_CHANGED) revisions to input/csv/script_to_change/
python connectivity/fetch_corrected_scripts.py

# Feature 3: Reconcile & reorganize local scripts against Google Sheets order
python connectivity/reconcile_scripts.py

# Feature 4: Safely publish scripts from scripts_to_post to Google Sheets
python connectivity/post_scripts.py

# Feature 5: Scan ready scripts across all sheets and export daily tracking CSVs
python connectivity/scan_ready_scripts.py --all

# Feature 6: Replace a Google Drive video and thumbnail bundle
python connectivity/sync_drive.py --script-id EE01
python connectivity/sync_drive.py --all
python connectivity/sync_drive.py --all --language spanish --video-type game
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
│   ├── connectivity/                   # Modular Google Sheets & Drive integration suite
│   │   ├── sync_sheets.py              # Principal Runner 1: Syncs Sheets to CSV (_3_cols / _4_cols)
│   │   ├── fetch_corrected_scripts.py  # Principal Runner 2: Pulls Column D (SCRIPT_CHANGED) to CSV
│   │   ├── reconcile_scripts.py        # Principal Runner 3: Audits & reorganizes local scripts
│   │   ├── post_scripts.py             # Principal Runner 4: Posts scripts to Google Sheets
│   │   ├── scan_ready_scripts.py       # Principal Runner 5: Scans ready scripts and exports by date
│   │   ├── sync_drive.py               # Principal Runner 6: Google Drive bundle replacement CLI
│   │   ├── core/                       # Option A endpoints router & resilient HTTP client
│   │   ├── apps_script/                # Apps Script Web App implementation & deployment guide
│   │   ├── drive_sync/                 # Google Drive API v3 client (drive_client.py) & sync_service.py
│   │   ├── sheet_sync/                 # Sheet to CSV synchronization service
│   │   ├── corrected_scripts/          # Column D (SCRIPT_CHANGED) fetching engine
│   │   ├── reconcile/                  # Reconcile & reorganization service
│   │   ├── post_scripts/               # Safe script publisher engine
│   │   ├── ready_scripts/              # Ready scripts scanner & date exporter
│   │   └── README.md                   # Full connectivity manual and deployment guide
│   ├── credentials/                    # Local OAuth2 / Service Account JSONs (gitignored) & setup guide
│   ├── core/                           # Shared infrastructure and utilities
│   │   ├── cli_prompt.py               # Shared prompts for operator utilities
│   │   ├── expression_db.py            # SQLite + CSV hybrid database implementation
│   │   ├── gemini_auditor.py           # Gemini Prompt Auditor (cfg=1.0 positive rules + Cultural World reroll)
│   │   ├── state_manager.py            # Script state machine and lifecycle manager
│   │   └── status_tracker.py           # Cross-queue pipeline progress manifest auditor
│   ├── database/                       # Centralized expression stores
│   │   ├── expressions.sample.csv      # Reference schema for master expression tracking
│   │   ├── expressions.db              # SQLite expression database (gitignored, auto-synced locally)
│   │   └── <lang>_expressions.csv      # Auto-synced CSV status trackers (gitignored locally)
│   ├── input/
│   │   ├── csv/
│   │   │   ├── README.md               # Prompt queue documentation and column schemas
│   │   │   ├── sample_templates/       # Canonical .sample.csv templates for all 4 formats & CTAs
│   │   │   ├── script_to_change/       # Replaces existing scripts (populated manually or via connectivity)
│   │   │   ├── voice_to_change/        # Targeted audio regeneration queues for _B_voice_generation
│   │   │   ├── image_to_change/        # Targeted scene illustration queues for _C_image_generation
│   │   │   ├── <lang>/expressions_list/# Active prompt queues per format (gitignored for privacy)
│   │   │   └── <lang>/game_call_to_action_phrases/ # CTA phrase libraries (gitignored for privacy)
│   │   └── images/                     # Static brand assets
│   │       ├── game_images/            # Empty chalkboard template and waiting illustrations
│   │       ├── openning_closure_images/# Opening bumper (2.0s) and outro CTA cards (3.0s)
│   │       ├── thumbnail_models/       # 20 category-specific master templates (<lang>/<cat>/template.png + ES latam/spain)
│   │       └── watermark/              # Channel watermark logo (.png)
│   ├── state/                          # Runtime script state artifacts (1,224 JSONs, ignored by git)
│   │   ├── README.md                   # State directory guide and schema documentation
│   │   └── script_state.sample.json    # Canonical reference state schema
│   ├── tools/                          # Developer utilities and operations CLI
│   │   ├── auditing/                   # Status scrapers, CSV validation, and language check tools
│   │   ├── database/                   # DB sync, ID assignment, and CLI query tools
│   │   ├── modifiers/                  # Interactive single & mass asset modifiers (script, voice, image, subtitles)
│   │   ├── prompt_builders/            # System editor prompt compilation tools
│   │   ├── webui.py                    # WebUI launcher tool (port 8190)
│   │   ├── llama.py                    # Headless LLM supervisor tool
│   │   ├── comfy.py                    # Headless ComfyUI supervisor tool
│   │   └── check_script_changes.py     # Script change auditor & synchronizer (Counter GAME diffing)
│   ├── webui/                          # Modern WebUI Management Studio (FastAPI + React 19)
│   │   ├── frontend/                   # React 19, TypeScript, Vite 8 & Tailwind source code
│   │   ├── jobs/                       # Background task runner & stage adapters (scripts, voice, images, chalkboard, thumbnails, assembly, drive)
│   │   ├── routers/                    # API route controllers (system, jobs, scripts, media, sheets, drive)
│   │   ├── static/                     # Pre-compiled production React SPA assets
│   │   ├── server.py                   # FastAPI server factory
│   │   └── README.md                   # WebUI architecture & API documentation
│   ├── video_creation/                 # Core generation stages (_A through _G)
│   │   ├── workflows/                  # Exported ComfyUI JSON API workflows (incl. Qwen3-TTS VoiceDesign.json)
│   │   ├── _A_video_scripts/           # Scriptwriting, prompt rules, verbatim parser, and metadata synthesis
│   │   ├── _B_voice_generation/        # Stage B Hybrid ElevenLabs + Local Qwen3-TTS & VoiceDesign bank suite
│   │   │   ├── elevenlabs/             # 227-voice catalog (LRU), Eleven v3 client, hybrid orchestrator & audio tags
│   │   │   ├── core/                   # comfy_client.py, acoustic_evaluator.py, audio_processor.py, voice_manager.py, script_parser.py, stress_enhancer.py
│   │   │   ├── data/                   # voice_bank_personas.json & ref transcript CSVs
│   │   │   ├── tools/                  # build_voice_bank.py (1.7B-VoiceDesign bank + HPS/spectral gate)
│   │   │   ├── voice/                  # Modular common/ (casting, punctuation, dsp_mastering, orchestrator), languages/ (4), types/ (4)
│   │   │   └── voice_modifier.py       # Interactive recaster & modifier (100% parity with orchestrator)
│   │   ├── _C_image_generation/        # Scene illustration & visual direction suite
│   │   │   ├── core/                   # prompt_builder.py, chalkboard_renderer.py, comfy_client.py
│   │   │   ├── visual/                 # Modular common/style/sanitizer, 124 Cultural Worlds (languages/), and typed rules (types/)
│   │   │   ├── image_modifier.py       # Single scene & batch group recreation, dual gender casting
│   │   │   └── service.py              # Shared Stage C generation service called by WebUI ImagesAdapter
│   │   ├── _D_music_generation/        # Standing Music Bank generator and catalog
│   │   ├── _F_thumbnail_image_generation/ # Native CPU category thumbnail renderer (20 templates + Spanish variants)
│   │   └── _G_video_assembly/          # Modular assembly/ (types/ + languages/), Whisper subtitles (non-overlap), audio ducking & FFmpeg
│   ├── requirements.txt                # Production runtime dependencies
│   ├── system_prompts_editor.csv       # External LLM system prompts for script doctoring
│   ├── .env.example                    # Environment variable configuration template
│   └── README.md                       # Comprehensive pipeline manual (this document)
└── test/                               # Isolated QA test suite and validation layer
    ├── connectivity/                   # Google Sheets integration & data contract tests
    ├── fixtures/                       # Frozen Stage C golden image prompt regression snapshots
    ├── integration/                    # DB, status tracker, schema contracts, security & mock service health tests
    ├── unit/                           # Pure unit tests for core pipeline modules & Drive sync
    ├── webui/                          # WebUI API & Job Manager adapter tests
    ├── conftest.py                     # Shared pytest/unittest fixtures & sys.path setup
    ├── pytest.ini                      # Pytest discovery settings and custom test markers
    ├── README.md                       # Test suite documentation & CLI execution guide
    └── requirements-test.txt           # Test-specific dependencies
```

---

## License & Operational Usage
Private enterprise language-learning automated video production system. Designed for high-retention vertical short-form publishing workflows.
