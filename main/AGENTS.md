# Project Context: Shorts Automation

## Overview
This project is an automated, enterprise-grade pipeline for generating viral, educational short-form vertical videos (YouTube Shorts, TikTok, Instagram Reels) focusing on language learning across four target languages: **English**, **Spanish**, **French**, and **Italian**. The pipeline coordinates local multi-modal generative AI backends (ComfyUI Diffusion & TTS, faster-whisper, Transformers MusicGen, and FFmpeg compositing) with an OpenAI-compatible local LLM (llama.cpp) for organic, retention-optimized pedagogical scriptwriting.

Shorts Studio is the production entry point. Launch it with `py main/tools/webui.py` from the repository root. Queue work through Script Catalog or Mass Creation and observe it in Queue. Shared stage code lives in `video_creation/` and is called by the adapters in `webui/jobs/adapters/`. The root runner, individual production launchers, and terminal batch selection menu were retired. Standalone operator tools cover service and asset maintenance. Pytest is the supported test runner.

ComfyUI supplies image and voice generation. The separate Sheets auditor handles editorial review and release planning. The studio applies reviewed revisions and has its own Gemini image-prompt audit.

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
   - **Automated Validation & Repair**: The script engine validates EXPRESSION scripts for mandatory keys, rejects illegal keys, and enforces the 85–110 word budget with automatic retry on failure.

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
     - `hook` (Narrator, 15–20 words): Scenario Threshold Establishing Two-Shot (`35mm` lens, 0% fourth-wall eye contact).
     - `DIALOGUE_PART_1` (P1 & P2, 30–38 words): Solo 3/4 angled waist-up medium dialogue shot on `PERSON_ONE` (`50mm` lens, turned 3/4 right looking off-camera toward `PERSON_TWO`, zero camera eye contact, active mid-sentence hand gesture or setting prop interaction, dramatic side-key lighting, `PERSON_TWO` strictly off-camera).
     - `DIALOGUE_PART_2` (P1 & P2, 30–38 words): 180° reverse 3/4 angled waist-up medium dialogue shot on `PERSON_TWO` (`50mm` lens, turned 3/4 left looking off-camera toward `PERSON_ONE`, optional soft-focus foreground shoulder OTS cue, zero camera eye contact, calm reassuring hand gesture or relaxed counter lean, warm fill light).
     - `DIALOGUE_PART_3` (P1 & P2, 30–38 words): 90° Side-Profile / High-Angle Two-Shot Prop Interaction (`50mm` lens, both characters).
     - `DIALOGUE_PART_4` (P1 & P2, 30–38 words): Solo medium-wide 3/4 dynamic motion shot on `PERSON_ONE` (`35mm` lens, wider knees-up/hips-up framing stepping forward or gesturing boldly with renewed confidence, `PERSON_TWO` strictly off-camera).
     - `PAYOFF` (Narrator, 20–25 words): Celebratory Resolution Action Two-Shot (`28mm` wide lens) + CTA.
   - **Multi-Character Gender Specification**: Sex of EACH individual character MUST be explicitly specified in prompts (e.g. *"one 17-year-old high-school senior boy and one 17-year-old high-school senior girl"*), alongside explicit skin tone, simple black 2D cartoon eyes, hairstyle, and complete layered upper + lower venue outfit (trousers/chinos/skirt; omitting footwear in cropped waist-up and medium shots). Dual-character state persistence via `speakers_gender: {"PERSON_ONE": "...", "PERSON_TWO": "..."}`.
   - **Target Duration & Word Budget**: **60 to 80 seconds max** (strictly **145–180 spoken words** across all 6 spoken sections).

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
     - Timeline requires EXACTLY 5 distinct, non-repeating scene assets in `script_<ID>/images/`:
       1. `hook`: Scenario dilemma setup rendered in 2D cartoon illustration via ComfyUI (waist-up 3/4-angled `50mm` medium shot cropped cleanly at hips/mid-thigh under warm directional spotlighting, footwear omitted, 100% direct fourth-wall eye contact).
       2. `challenge`: High-resolution typography rendered natively on CPU via FreeType onto `empty_chalkboard.png` with **100% target language localization** (`get_localized_game_header()`, e.g. `QUE SIGNIFIE CETTE EXPRESSION ?`, `OÙ EST L'ERREUR ? / COMPLÉTEZ :`, `¿QUÉ SIGNIFICA ESTA EXPRESIÓN?`). **ZERO English headers or text on non-English chalkboards**.
       3. `pressure`: Static pre-made waiting illustration per language from `input/images/game_images/<lang>/<lang>_waiting.png`.
       4. `answer`: Resolution / victory breakthrough illustration rendered via ComfyUI (dynamic 3/4 asymmetrical waist-up medium action, triumphant breakthrough, footwear omitted).
       5. `explanation`: Dedicated cultural immersion narrative illustration rendered via ComfyUI (`35mm` medium-wide authentic practical real-world usage, 0% camera eye contact, ZERO duplicate images with `answer`).
     - **ComfyUI Batch Processing**: Exactly **3 scenes** (`hook`, `answer`, `explanation`) are sent to ComfyUI for generation, paired with CPU chalkboard and static Tito to yield 5 distinct timeline cuts.
   - **Zero-Tolerance Text & Quote Scrubbing in Prompts**:
     - Visual prompts must NEVER contain text inside quotation marks, speech verbs (`whispering the words...`), signboards with text, or letter names (while preserving compound venue nouns like `reading lamp`, `reading alcove`, `reading hall`, `reading boxes`, `calling card`, and `speaking lectern`).
     - Any parchment, scroll, book, or paper must be described with abstract wavy cartoon doodle lines and geometric diagrams, completely devoid of legible text, words, or letters.
     - `sanitize_and_style_prompt()` scrubs all quoted words and speech phrases, strips legacy negated parenthetical clauses that trigger concept leakage under Z-Image-Turbo (`cfg=1.0`), upgrades younger ages (`8–15`, `fourteen-year-old`, `fifteen-year-old`, `14-16yo`, `14-16-year-old`) to `17-year-old` (preserving `16–18`), strips wearable footwear clauses (`strip_footwear_clauses`) when `strip_footwear=True` or cropped framing (`waist-up`, `chest-up`, `mid-torso`, `thigh-up`, `mid-thigh`, `hips-up`, `medium close-up`) is active while preserving venue/prop nouns (`sneaker boutique`, `footwear workshop`, `shoe boxes`), and appends the **purely-positive** 2D cartoon style anchor (`17-year-old high-school senior`, `1:7` proportions, `pure text-free visual illustration`) whenever either `"head-to-body proportions"` or `"pure text-free visual illustration"` is absent.
   - **Character Appearance Continuity & Demographic Lock**:
     - **General Prompt as Single Source of Truth**: Character demographic anchors (`gender`, `skin_tone`, `eye_color`, `hair_style`, `wardrobe`) originate from `extract_or_build_character_anchors` and are locked into `content_metadata.general_prompt`. All downstream scene prompts inherit visual world anchors directly from this single authoritative truth, preventing contradictory descriptions or ethnicity drift across scenes.
     - **Case-Insensitive Speaker Gender Resolution (`get_speaker_gender_safe`)**: All modules query speaker genders using case-insensitive lookup with fuzzy fallback. This eliminates gender inversion bugs where TitleCase keys (`"Narrator"`, present in >1,038 state files) previously bypassed `.get("NARRATOR")` lookups and defaulted female characters to `"male"`.
     - **Locked Director Prompts**: Storyboard tasks for Game, Fun Facts, and Expression lock `{p1_word}` (`girl`/`boy`) in director tasks based on authoritative anchors.
     - Single source of truth in `content_metadata.character_anchors` (and `assets.character_anchors`) via `CharacterCast` with locked gender, skin tone, eye color, hairstyle, and complete layered upper + lower venue wardrobe (trousers/chinos/skirt; omitting footwear in cropped waist-up and medium shots), replacing generic studio/workshop/greenhouse/drafting-vest clichés with culturally grounded city & venue fashion.
     - Strict positive demographic anchor: *`17-year-old high-school senior` with `realistic late-teen 1:7 head-to-body proportions, defined jawline, proportional shoulders, lean athletic teenage build`*.
     - **Mandatory Complexion & Eye Anchoring**: Explicit skin tone (e.g., *warm tan skin*, *fair peach skin*, *olive skin*) and **`lively natural-sized simple black 2D cartoon eyes`** must NEVER be omitted in general prompts or scene prompts. Without explicit skin tone anchors, framing shifts across wide establishing shots and 3/4 medium shots can trigger diffusion drift.
     - Elimination of emaciated silhouettes and unexpressive deadpan faces: purged `"tall slender proportions"`, `"Wes Anderson-style central balance"`, and `"frozen at a physical crossroads"`.
     - **Natural Facial Acting & Relaxed Eye Rendering**: Purged `"conspiratorial glance"` triggers from prompt templates and storyboard directors, replacing them with *"engaging, playful knowing smile and lively natural-sized simple black 2D cartoon eyes with relaxed facial acting"*.
     - **Purely-Positive Z-Image-Turbo (`cfg=1.0`) Anchor Discipline**: Because Z-Image-Turbo runs at `cfg=1.0`, negative-exclusion boilerplate causes concept leakage; therefore relaxed natural eyes, late-teen 1:7 proportions, stylish layered attire, and text-free surfaces are enforced strictly through positive descriptions (`NEGATIVE_PROMPT_SHIELD` excludes `explicit footwear on feet`, and legacy negated parenthetical clauses are stripped idempotently on re-sanitization).
     - Gender-attire integrity: male characters are barred from feminine garments (bodices, corsets, kirtles, skirts, dresses).
     - Elimination of conflicting double prompt injections (no duplicate or contradictory character descriptions within the same prompt).
   - **Zero-Copy Static Shared Asset Architecture**:
     - **Elimination of Duplicate Asset Copies**: Static pre-made assets that never vary across scripts of the same language and video type (e.g. Tito waiting image `pressure.png` for GAME shorts, opening branding cards, closure cards, watermark) are NEVER physically copied into individual script output folders (`D:\AI\output\video_assets\...`).
     - **On-Demand Dynamic Resolution (`resolve_static_scene_path`)**: `config/settings.py` dynamically resolves the canonical asset from `input/images/game_images/` or `input/images/openning_closure_images/` based on script language, video type, and dialect without hardcoded paths.
     - **Decoupled Creation & Assembly**: `_C_image_generation/service.py` and `image_modifier.py` verify central asset existence and skip file duplication, while `_G_video_assembly/core/video_assembler.py` automatically links the central asset directly into the FFmpeg render timeline.
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
     - `hook` [THE SCALE OF WONDER]: Dramatic low-angle heroic 28mm wide shot framed from mid-thigh/waist up in the lower foreground (cropped at hips/mid-thigh, zero footwear) looking sharply upward in jaw-dropped awe (0% camera eye contact).
     - `setup` [THE CURIOUS CLUE]: Waist-up medium 50mm eye-level investigative shot examining an authentic artifact or clue (footwear omitted).
     - `discovery` [THE HIDDEN MECHANISM REVEAL]: Dynamic 35mm 3/4 waist-up medium action shot revealing the mechanism/origin in motion (footwear omitted).
     - `explanation` [LIVING CULTURAL CONTEXT]: Medium-wide 35mm environmental immersion shot showing practical cultural context (0% camera eye contact).
     - `payoff` [MIND-BLOWN MASTERY]: Chest-up celebratory medium close-up (50mm lens, cropped at mid-torso, footwear omitted) with warm rim lighting.
   - **Target Duration & Word Budget**: **40 to 60 seconds** (strictly **95–135 spoken words** across all sections).

---

## Calibrated Scene & Image Architecture per Video Type

| Video Type | Timeline Scenes | ComfyUI Renders | Special Asset Handling |
| :--- | :---: | :---: | :--- |
| **EXPRESSION** | **5** | **5** | `hook`, `setup`, `discovery`, `example`, `payoff` (all 5 generated via ComfyUI). |
| **GAME** | **5** | **3** | • `hook`, `answer`, `explanation`: Rendered via ComfyUI (3 distinct images).<br>• `challenge`: High-res native chalkboard on CPU via Pillow/FreeType (zero VRAM).<br>• `pressure`: Static Tito waiting image per language (`resolve_static_scene_path`, zero-copy). |
| **ROLEPLAY** | **6** | **6** | `hook`, `dialogue_part_1`, `dialogue_part_2`, `dialogue_part_3`, `dialogue_part_4`, `payoff` (all 6 generated via ComfyUI following the 6-beat camera matrix). |
| **FUN_FACTS** | **5** | **5** | `hook`, `setup`, `discovery`, `explanation`, `payoff` (all 5 generated via ComfyUI following the Scale-of-Wonder 5-beat camera matrix). |

---

## Stage B Modular Voice Generation Architecture (`_B_voice_generation/voice/`)

Stage B decouples shared synthesis infrastructure, per-language prosodic fingerprints, and per-video-type pause/mastering rules inside `_B_voice_generation/voice/` so editing one language or format never alters another:

| Layer / File | Responsibility ("Where to Change X") |
| :--- | :--- |
| `voice/common/models.py` | Immutable dataclasses: `SamplingProfile`, `AcousticGateEnvelope`, `PauseChoreography`, `MasteringPreset`, `LanguageVoiceProfile`, `VideoTypeVoiceProfile`, `VoiceBankEntry`. |
| `voice/common/engine.py` | `VOICE_ENGINE=typed\|legacy\|legacy:<type/lang>` rollback switch (`is_typed_voice_enabled`), `detect_dialect_hint()` (auto-locking `es_spain_castilian` / `es_latam_neutral` / `en_uk_neutral` / `en_us_neutral` from explicit `--accent` or script keywords), and `compute_segment_sampling()` (capped at `temperature <= 0.90`, `subtalker_temperature <= 0.86`, protecting `GAME` `challenge` neutrality via `neutral_challenge_lock`). |
| `voice/common/bank_manifest.py` | `VoiceBankManifest` loader for `VOICE_BANK_DIR/voice_bank_manifest.json`, `sanitize_ref_transcript()` for clean `open_swara` transcripts, `LOW_QUALITY_OPEN_SWARA` filtering, and same-speaker `find_speaker_energy_variant()` lookup. |
| `voice/common/casting.py` | Anti-repetition `VoiceCastingEngine` (tiering curated VoiceDesign clips + clean `open_swara` human clips ahead of demoted `kokoro_golden` fallback), `pick_weighted_accent()` (75/25 Spanish, 70/30 English), and 3-speaker uniqueness for Roleplays (`used_identities` and recast exclusions). |
| `voice/common/punctuation.py` | Non-destructive TTS prosody shaping (`prepare_tts_prosody_text`) that preserves screen captions untouched while injecting Spanish opening `¿`/`¡`, restoring safe `?!`/`...` cues, and inserting `GAME` option `[pause:0.26]` micro-pauses. |
| `voice/common/dsp_mastering.py` | Zero-external-binary `numpy` + `scipy` broadcast vocal mastering chain (`apply_vocal_mastering`): sub-rumble HPF, subtractive mud cut, chest warmth, presence EQ, air shelf, split-band de-esser, soft-knee RMS compressor, ITU-R BS.1770 LUFS target leveling, and `0.891` (`-1.0 dBFS`) soft-clip peak limiter. |
| `voice/common/orchestrator.py` | Unified `synthesize_script_voice()` shared by `voice_modifier.py` and WebUI `VoiceAdapter`, including a 1-shot calm recovery retry (`temp - 0.10`, `sub_temp - 0.06`, `seed + 1999`) whenever all high-impact candidates fail `evaluate_voice_take()`. |
| `voice/languages/{english,french,spanish,italian}.py` + `registry.py` | **Language-only prosody**: English (`0.84`/`0.77`, 70/30 `en_us_neutral`/`en_uk_neutral`); French (`0.85`/`0.80`, Parisian *esprit français* legato *groupes rythmiques*); Spanish (`0.85`/`0.79`, neutral-only `75% es_latam_neutral` / `25% es_spain_castilian` + `¿`/`¡` enforcement); Italian (`0.87`/`0.83`, high-energy Mediterranean pitch excursions + crisp geminates). |
| `voice/types/` and `voice/common/delivery.py` | Per-format mastering, assembly gaps, and localized narration. Expression and Fun Facts render continuous sections. Game uses one narrator with even options and existing timing. Roleplay keeps each cast member and renders continuous dialogue with acting direction and the preceding turn as instruction-only context. |
| `core/{comfy_client.py,acoustic_evaluator.py,audio_processor.py,voice_manager.py}` | `_has_manifest_ref_text()` enabling `use_icl=True` (`x_vector_only=False` + exact `ref_text`) for English VoiceDesign clips (conditioning on the same speaker), `?`/`!` pitch/RMS contour gating + Syntactic Carrier heteronym stress gating + `kokoro_golden` fallback WAV support, per-type pause insertion & mastering integration, and `VoiceCastingEngine` + `VOICE_CASTING_HISTORY_PATH` wiring. |
| `tools/build_voice_bank.py`, `data/voice_bank_personas.json`, `workflows/Qwen3-TTS VoiceDesign.json` | Offline Qwen3-TTS 1.7B-VoiceDesign reference bank builder: enforces affirmative-English `voice_instruction` descriptions, Whisper `lang_prob` verification, and an octave-proof 3-harmonic HPS + `P25` + low/high `M/F_E` spectral energy gender-pitch gate (`male`: `85–195 Hz`, `M/F_E >= 0.08`; `female`: `200–285 Hz`, `P25 >= 195 Hz`, `M/F_E <= 0.05`). |

- **Stage B Invariants & Rollback (`VOICE_ENGINE`)**: Setting `VOICE_ENGINE=legacy` (or `VOICE_ENGINE=legacy:<type,lang>`) or setting the Studio voice job's `voice_engine` to `legacy` restores pre-split casting, sampling, pauses, and `-16.0 LUFS` loudness normalization immediately. Syntactic Carrier heteronym precision, `GAME` `pressure_gap=2.20s`, lowercase/neutral `GAME` `challenge` delivery, 3-voice Roleplay distinctness, `ensure_llama_stopped()` VRAM arbitration, and `*_master.wav` / State JSON schemas remain 100% preserved.

---

## Stage C Modular Visual Prompt Architecture (`_C_image_generation/visual/`)

Stage C separates shared visual rules, language data, and video-type camera profiles so editing one language or video type never leaks into others:

| Layer / File | Responsibility ("Where to Change X") |
| :--- | :--- |
| `visual/common/style.py` | Shared 2D cartoon style pillars, base system prompts, and type-pure storyboard system prompt builder (`build_storyboard_system_prompt`). |
| `visual/common/sanitizer.py` | Idempotent `sanitize_and_style_prompt`, `strip_footwear_clauses` (`CROPPED_FRAMING_RE`), text/quote scrubbing (protecting `reading lamp`/`alcove`/`hall`/`boxes`, `calling card`, `speaking lectern`), purely-positive Z-Image-Turbo (`cfg=1.0`) 2D style anchor (`17-year-old high-school senior`, `1:7` late-teen proportions, `lively natural-sized simple black 2D cartoon eyes`, `pure text-free visual illustration`), legacy negated-tail & shortened-tail handling, age upgrades (`8–15`/`14-16yo` -> `17-year-old`), and `present` heteronym gift-box exception. |
| `visual/common/cast.py` | `CharacterCast` model, `get_speaker_gender_safe`, centralized default genders (`resolve_default_speakers_gender`), solo-format protection for `GAME`/`FUN_FACTS`, and `persist_character_anchors_in_state`. |
| `visual/common/environment.py` | 4-Tier Cultural World Atlas & anchor resolver (`resolve_cultural_world`, `resolve_anchor_environment`, `infer_world_ids_from_text`, `is_figurative_idiom`, Triplet Collision Guard ensuring distinct worlds for matching-number `E`/`G`/`R` triplets). |
| `visual/languages/{english,french,spanish,italian}.py` | **Language-only data**: brand color palette mood, idiom detection markers, idiom metaphor environments, heteronyms, and `cultural_worlds` (`CulturalWorld` atlas: **124 worlds total** — 36 English global Anglophone, 32 Spanish Spain + Latin America, 28 French France + Francophone, 28 Italian regional Italy; stylish venue fashion; 100% text-free). Never contains camera angles or video-type rules. |
| `visual/types/{expression,game,roleplay,fun_facts}/` | **Type-only rules & prompts**: `SceneSpec` contracts (`rules.py`) with waist-up/mid-thigh cropped `hook` & medium framing (footwear omitted), single-scene goals, scene progressions, storyboard director tasks (`prompts.py`), and `VisualProfile` class (`profile.py`). |
| `visual/types/registry.py` | `get_visual_profile(...)` dispatcher (by type name, 1-letter code, or Script ID) + `IMAGE_PROMPT_ENGINE=legacy\|typed` rollback switch. |
| `core/prompt_builder.py` | Public facade (`VisualPromptBuilder`, `_CROPPED_SCENES` footwear-stripping enforcement, stripped `wardrobe_cue` hints, and re-exports of all helper functions for backward compatibility). |
| `main/core/gemini_auditor.py` | Gemini Prompt Auditor enforcing purely-positive Z-Image-Turbo (`cfg=1.0`, `17-year-old`, `1:7`, footwear-free `NEGATIVE_PROMPT_SHIELD` and `CHAR_1`/`CHAR_2` templates) and automatic Cultural World reroll excluding the previous draft's setting (unless fixed by the script). |

---

## Stage G Modular Video Assembly Architecture (`_G_video_assembly/assembly/`)

Stage G isolates editing rules by video type (`expression`, `game`, `roleplay`, `fun_facts`) with neutral per-language hooks, driven from `core/video_assembler.py`, `core/subtitle_builder.py`, and `_G_video_assembly/service.py`:

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
      ├── WebSocket Logs (/ws/jobs/{id}, /ws/system) <─┤
      └── Polled Sync State (/api/sheets/status) <─────┤
                                                       ▼
                                           [Job Manager & Adapters]
                                        (main/webui/jobs/manager.py)
                                                       │
       ┌──────────────┬────────────┬───────────┬───────┴────────┬─────────────┬────────────┐
       ▼              ▼            ▼           ▼                ▼             ▼            ▼
[ScriptsAdapter] [VoiceAdapter] [Images] [Chalkboard]     [Thumbnails]  [Assembly]   [DriveAdapter]
   (Stage A)       (Stage B)   (Stage C) (CPU Chalk)       (Stage F)    (Stage G)   (Google Drive)
```

- **Frontend (`main/webui/frontend/`)**: React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons. Built assets are compiled directly into `main/webui/static/` and served as a single-page application.
- **Backend API (`main/webui/server.py`)**: FastAPI application mounted with modular routers:
  - `/api/scripts`: Script catalog querying, filtering, search, detail modals, Gemini Prompt Auditor (`POST /api/scripts/{script_id}/gemini-audit-prompt`), CPU chalkboard rendering, scene/full image redo, and ID validation.
  - `/api/media`: Audio, image, and video streaming with HTTP Range support and MIME type resolution.
  - `/api/jobs`: Background job queue management (`scripts`, `voice`, `images`, `music`, `assembly`, `thumbnails`, `chalkboard`, `drive_upload`), execution console, WebSocket log streaming (`/ws/jobs/{job_id}`, `/ws/system`), and cancellation.
  - `/api/system`: Real-time service monitoring (ComfyUI and Llama-server status, GPU VRAM, PIDs, Gemini API key status) and service control.
  - `/api/sheets`: Google Sheets 4-step synchronization worker and status polling.
  - `/api/drive`: Google Drive configuration status (`GET /api/drive/status`) and single-script upload (`POST /api/drive/scripts/{script_id}/upload`).
- **Launcher**: Launch with a single command:
  ```powershell
  py main/tools/webui.py
  ```
  The launcher checks Python dependencies, validates Node/npm build status, resolves port conflicts automatically, and opens the default browser.

### The 6 WebUI Views (`Navbar.tsx`)

1. **Home (`HomeView.tsx`)**: Pipeline overview, high-level KPI progress summary, and quick launch entry points.
2. **Script Catalog (`ScriptList.tsx` & `ScriptDetailModal.tsx`)**:
   - Instant filtering by Language (English, French, Italian, Spanish), Video Format (Expression, Game, Roleplay, Fun Facts), and Pipeline Status, plus search by expression or ID.
   - **Script Detail Modal (`ScriptDetailModal.tsx`)**: Inspects script narrative sections, master audio playback with interactive waveform, scene illustrations, thumbnail preview, and YouTube SEO metadata (Title, Description, Tags, Hashtags).
     - *Gemini Prompt Auditor*: Calls `POST /api/scripts/{script_id}/gemini-audit-prompt` to audit and auto-reroll the Cultural World setting (excluding the previous draft's setting unless the script requires a fixed venue) and emit purely-positive Z-Image-Turbo prompts.
     - *Single-Scene Image Redo*: Clickable redo button per scene card in the storyboard tab enqueues an isolated scene generation job (`POST /api/scripts/{script_id}/scenes/{scene_type}/redo-image`).
     - *Full Image Set Redo from General Prompt*: "queue redo (all images)" button (`POST /api/scripts/{script_id}/redo-all-images`) persists the edited general prompt, clears stale scene prompts and disk PNGs, and queues a two-phase job with `preserve_general_prompt=True`: Llama regenerates all scene prompts aligned to the saved general prompt (without overwriting it) and stops to free VRAM before ComfyUI renders all scene images.
     - *Direct Google Drive Upload*: "upload to google drive" button (`POST /api/drive/scripts/{script_id}/upload`) verifies video & thumbnail existence, removes duplicate `<script_id>` folders and existing files inside `<script_id>`, and uploads fresh replacements.
     - *Zero-Copy Static Asset Architecture*: Reusable assets (e.g. GAME Tito `pressure` waiting cards, opening and closure cards) are dynamically resolved via `resolve_static_scene_path` without copying duplicate PNGs into script asset folders.
3. **Job Queue / Execution Console (`JobQueueView.tsx`)**:
   - Asynchronous background job queue (`webui/jobs/manager.py`) executing batch jobs across pipeline stages.
   - Live terminal log stream via WebSockets (`/ws/jobs/{job_id}`) with cancel controls, step-by-step progress bars, and elapsed time.
4. **Mass Assets Creation (`MassAssetsCreationView.tsx`)**:
   - Batch generation and cloud sync across **7 target stages**: **Script Dialogues** (Stage A), **Scene Images** (Stage C), **Voice Files** (Stage B), **Thumbnail Images** (Stage F), **Chalkboard Images** (Game only), **Video Assembly** (Stage G), and **Google Drive Upload**.
   - **3 ID Collection Modes**:
     - *Manual Input*: Comma/space/line-separated IDs with debounced real-time validation via `POST /api/scripts/validate-ids`.
     - *CSV Drag & Drop*: Upload CSV/TXT files to automatically extract and validate target script IDs.
     - *Preset Catalogs*: One-click buttons to load pending images/voice/thumbnails, ready for assembly, ready for Drive upload (video + thumb), or Game chalkboards.
   - **Mass Drive Upload Mode**: Uses `validate-ids` and catalog readiness flags (`has_video && has_thumbnail`) to filter upload-ready IDs, then dispatches a `stage="drive_upload"` job via `POST /api/jobs` to `DriveAdapter` for live progress tracking.
   - **Interactive Validated Script Grid**: Clickable chips showing format, language, and current asset status, with quick-remove buttons and one-click inspection via `ScriptDetailModal`.
   - **Forced Re-generation & Prompt Rebuild**: Toggle (`force: true` default) ensuring assets are re-rendered even when marked `"done"`. For **Scene Images** (`ImagesAdapter` & `_C_image_generation/service.py`), Mass Assets Creation (`preserve_general_prompt=False`) rebuilds both `general_prompt` and storyboard `image_prompts` from scratch when `force=True` or `regenerate_prompts=True`. For **Video Assembly**, targeted IDs are forced after voice and images pass prerequisites. Assembly renders an MP4 to a staging directory and replaces the published file after FFmpeg succeeds.
   - **Pre-flight Service Checks**: Displays warnings if ComfyUI is offline when images or voice are selected.
   - **Execution Console Redirect**: Launches the batch directly into the background Job Manager and navigates to the Queue view for live tracking.
5. **Google Sheets Sync (`GoogleSheetsSyncView.tsx`)**:
   - Interactive 4-step workflow triggered via `POST /api/sheets/sync`: Step 1 purges stale CSVs in `input/csv/script_to_change/`, Step 2 fetches Column D (`SCRIPT_CHANGED` or `SCRIPT_CHANGE`) and Column B (`EXPRESSION`) across all 16 sheets (including `FUN_FACTS`), Step 3 runs format-aware audit & diff preview, and Step 4 applies changes cleanly via `script_modifier.py` (5-section `FUN_FACTS` with `explanation`, title/anchor invalidation on topic change) while resetting downstream stages (`voice`, `images`, `thumbnails`, `assembly`) to `pending`.
6. **Bingo Matrix (`BingoMatrixView.tsx`)**:
   - Interactive visual status grid tracking asset readiness across all 16 language/format matrices (`EE`, `EG`, `ER`, `EF`, `FE`, etc.).

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
3. **Feature 2 (`fetch_corrected_scripts.py`)**: Filters Column D (`SCRIPT_CHANGED` or `SCRIPT_CHANGE`) across all 16 sheets (all 4 formats including `FUN_FACTS`) and exports corrections into `input/csv/script_to_change/` with schema `ID, NEW_SCRIPT, EXPRESSION` (preserving Column B `EXPRESSION` updates).
4. **Feature 2b (`tools/check_script_changes.py`)**:
   - Deep comparison engine between CSV Column D corrections (+ Column B `EXPRESSION` topic updates) across all 4 formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`) and local runtime State JSONs.
   - **GAME & FUN_FACTS Format Awareness**: Automatically parses GAME challenges into neutral spoken words (no uppercase stress giveaways), option tags (`A: `, `B: `), zero connectors, parts-of-speech context (`a record.` / `to record.`), period endings, and synchronizes `chalkboard_exercise` with `challenge`; parses 5-section `FUN_FACTS` (`hook`, `setup`, `discovery`, `explanation`, `payoff`) cleanly and invalidates stale titles/anchors on topic change.
   - CLI flags: `--check-only`, `--apply`, `--csv <file>`, `--script-id <ID>`.
5. **Feature 3 (`reconcile_scripts.py`)**: Reconciles local scripts against Google Sheets order into `scripts_to_post/`.
6. **Feature 4 (`post_scripts.py`)**: Safely publishes scripts to Google Sheets (preserves Column D in 3-column mode).
7. **Feature 5 (`scan_ready_scripts.py`)**: Scans Google Sheets for rows where Column E (`script_ready`) is checked and Column G (`video_ready`) is unchecked, exporting daily batch CSVs.

---

## Google Drive Export & Cloud Synchronization Suite

The `main/connectivity/drive_sync/` package (`drive_client.py`, `sync_service.py`) and `main/connectivity/sync_drive.py` CLI coordinate automated asset delivery to Google Drive:

1. **Authentication & Credential Resolution (`drive_client.py`)**:
   - `GoogleDriveClient._resolve_credentials_path()` checks `--credentials`, `GOOGLE_APPLICATION_CREDENTIALS`, and `main/credentials/` in strict priority order: `token.json` -> `service_account.json` -> `client_secret.json`.
   - Supports **OAuth 2.0 Desktop App** (interactive browser consent on first run, saving/refreshing `token.json`) and **Service Account** (`service_account.json`) authentication against Drive API v3 (`SCOPES = ["https://www.googleapis.com/auth/drive"]`).
2. **Directory & Routing Hierarchy (`sync_service.py`)**:
   - Uploads target `DEFAULT_ROOT_FOLDER_ID = "15HhCvcrsaAn3fLQM7Hdv3J0HVgcp39_Z"` (overridable via `--root-folder-id`) with hierarchical folders:
     `<root> / <language> (english|french|italian|spanish) / <video_type> (expressions|fun_facts|game|role_play) / <script_id> /`
   - Places cleanly renamed bundles inside `<script_id>`: `<script_id>.mp4` and `<script_id>_thumbnail.png`.
3. **Drive Bundle Replacement**:
   - Verify both local assets before contacting Drive.
   - Upload the replacement video and thumbnail, and save the new links. Retire previously listed files with the canonical video and thumbnail filenames after both uploads succeed.

4. **WebUI Integration & Execution**:
   - `GET /api/drive/status`: Reports Drive configuration, resolved credentials file, and root folder metadata.
   - `POST /api/drive/scripts/{script_id}/upload`: Single-script upload from `ScriptDetailModal`.
   - Batch asynchronous uploads dispatch via `POST /api/jobs` with `stage="drive_upload"` through `DriveAdapter` (`main/webui/jobs/adapters/drive.py`), streaming live progress over WebSockets.
5. **Standalone CLI (`sync_drive.py`)**:
   ```powershell
   py main/connectivity/sync_drive.py --all
   py main/connectivity/sync_drive.py --script-id EE01
   py main/connectivity/sync_drive.py --all --language spanish --video-type game
   ```

---

## Structured Script ID Standard

Every video across the pipeline is assigned a canonical, non-overlapping identifier following the format:

$$\textbf{<Language\_Code><Type\_Code><Index:02d>}$$

- **Language Code** (1st char): `E` (English), `F` (French), `S` (Spanish), `I` (Italian).
- **Video Type** (2nd char): `E` (Expression), `G` (Game), `R` (Roleplay), `F` (Fun Facts).
- **Sequential Index** (3rd–4th digits): 2-digit zero-padded index per (language, type) pair (`01`, `02`, ..., `99`, `100`+).
- **Immutability**: Once generated into `state/<language>/<video_type>/script_<ID>.json`, downstream stages strictly inherit the state's ID. **IDs are never re-created or altered across pipeline stages**.

### Production State and Verification

- Read per-script status from `StateManager` and inspect media under the configured `OUTPUT_DIR`. Catalog status is a production record and file checks confirm artifact availability.
- Script regeneration and Sheets revisions invalidate voice, images, thumbnails, assembly, and Drive delivery so those stages can be rerun.
- The live local curated bank currently holds 52 baselines and 40 same-speaker variants. Treat the configured manifest as the source for what Studio can cast. Stage new auditions separately and publish reviewed speaker IDs with the builder. Voice jobs stage mastering before publishing a new master and preserve the last successful output on a failed render.
- Run `py -m pytest test -m "not live"` using the [test guide](../test/README.md). Use checked-in fixtures and temporary workspaces for stateful tests. Exercise the real app, production adapters, and file outputs when testing a workflow. Substitute external services at their boundaries.
- Keep live ComfyUI checks opt-in. The required test path includes real local FFmpeg, but does not require a GPU, model weights, or production credentials.

## Key Files & Entry Points

| File / Folder | Role |
| :--- | :--- |
| `main/tools/webui.py` | Dedicated launcher for the WebUI MVC application (FastAPI on port 8190 + React 19 SPA). |
| `main/webui/server.py` | FastAPI backend server with modular routers for `scripts`, `media`, `jobs`, `system`, `sheets`, and `drive`. |
| `main/webui/frontend/` | React 19 + TypeScript + Vite frontend source code. |
| `main/webui/static/` | Compiled static production bundle served directly by FastAPI. |
| `main/webui/jobs/manager.py` | Background Job Manager with WebSocket streaming (`/ws/jobs/{job_id}`, `/ws/system`) and stage adapters (`scripts`, `voice`, `images`, `chalkboard`, `thumbnails`, `assembly`, `drive`). |
| `main/core/llama_manager.py` | Process supervisor for local llama.cpp server with VRAM freeing and status monitoring. |
| `main/core/gemini_auditor.py` | Gemini Prompt Auditor generating purely-positive Z-Image-Turbo prompts with automatic Cultural World reroll. |
| `main/video_creation/_B_voice_generation/voice/` | Modular Stage B voice layer (`common/` orchestrator/casting/punctuation/DSP mastering, `languages/` prosodic prints, `types/` pause choreography & Roleplay acting references). |
| `main/video_creation/_B_voice_generation/tools/build_voice_bank.py` | Offline Qwen3-TTS 1.7B-VoiceDesign reference voice bank builder & HPS + spectral `M/F_E` gender-pitch verifier (`data/voice_bank_personas.json`). |
| `main/tools/llama.py` | CLI supervisor tool for manual control of llama-server (`start`, `stop`, `status`, `logs`). |
| `main/tools/comfy.py` | Headless ComfyUI background supervisor (`start`, `stop`, `status`, `logs`). |
| `main/tools/check_script_changes.py` | CLI auditor & synchronizer between Google Sheets Column D CSVs and local State JSONs. |
| `main/connectivity/sync_drive.py` | Standalone CLI for uploading finalized video bundles to Google Drive with staged bundle replacement. |
| `main/connectivity/drive_sync/` | Google Drive API v3 suite (`drive_client.py`, `sync_service.py`): OAuth2/Service Account auth, hierarchical routing, bundle replacement after successful upload. |
| `main/webui/routers/drive.py` | FastAPI router for Drive credentials status and single-script uploads (batch uploads run via `POST /api/jobs` + `DriveAdapter`). |
| `main/webui/jobs/adapters/drive.py` | Background Job Manager adapter for batch Google Drive clean replacement uploads. |
| `main/webui/frontend/src/components/BingoMatrixView.tsx` | Visual matrix tracker across all 16 language/format combinations. |
| `main/video_creation/_A_video_scripts/script_modifier.py` | Script modifier supporting direct parsing, LLM structuring, and automatic `clean_game_challenge()` enforcement. |
| `main/video_creation/_A_video_scripts/prompts/game_rules.py` | Authoritative GAME prompt rules enforcing clean option formatting, no stress giveaways, and separation of challenge and pressure. |
| `main/connectivity/` | Google Sheets & Google Drive integration suite (Apps Script Web App client, fetcher, reconciler, poster, scanner, Drive sync). |
| `test/pytest.ini` | Studio test discovery and browser/live markers. See `test/README.md` for commands. |

---

## Agent Guidelines & Best Practices

1. **State Persistence**: Always read and update script states via `core/state_manager.py` (`StateManager`).
2. **Audio Duration Rule**: Adhere strictly to target durations: **38–48s** (85–110w) for EXPRESSION, **40–55s** (95–125w) for GAME, **60–80s max** (145–180w) for ROLEPLAY, and **40–60s** (95–135w) for FUN_FACTS.
3. **GAME Challenge Formatting**: Always enforce that GAME challenges use neutral words (no uppercase stress), start options with `A: `, `B: `, include no option connectors, specify grammatical category for single words (`a record` vs `to record`), end each option with `.`, never end with `?`, and keep `chalkboard_exercise` synchronized.
4. **GPU VRAM Discipline**: Never run ComfyUI and Llama-server under high concurrent load on 6GB GPUs. Call `ensure_llama_stopped()` before Qwen3-TTS or ComfyUI generation.
5. **Pipeline-Level Solutions Only (Zero Manual Patching)**: Fix all errors inside the core engine, prompt coordinators, FreeType renderers, and audio processors so the pipeline operates autonomously end-to-end.
6. **Master Expression Database (User-Only 'DONE')**: Pipeline scripts NEVER mutate `STATUS` to `DONE`—that privilege belongs solely to the human creator. Completed expressions with `STATUS = DONE` are strictly frozen.
7. **Verbatim Script Ingestion**: When updating scripts from `script_to_change/` or Google Sheets, the spoken words must be preserved verbatim in `content_metadata.script`.
8. **Qwen3-TTS VoiceDesign Prompt & Spectral Gate Discipline**: When adding or rebuilding personas via `build_voice_bank.py`, write `voice_instruction` strictly in affirmative English describing an adult vocal register (never `"soprano"`, `"bright"`, `"chest voice"`, or negative exclusions like `"never childlike"` / `"zero American"`), keep `language` + `ref_text` in the target language, and verify all clips pass Whisper `lang_prob` and the HPS + `P25` + `M/F_E` spectral gender-pitch gate (`male`: `85–195 Hz`, `M/F_E >= 0.08`; `female`: `200–285 Hz`, `P25 >= 195 Hz`, `M/F_E <= 0.05`). For designated lower-register auditions, the opt-in `lower_register` persona profile uses a 175–245 Hz HPS median, P25 ≥ 160 Hz, and M/F_E ≤ 0.10. Keep these auditions in a separate bank until reviewed by ear.
