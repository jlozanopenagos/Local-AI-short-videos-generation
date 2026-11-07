# Project Context: Shorts Automation

## Overview
This project is an automated pipeline for generating viral, educational short-form vertical videos (YouTube Shorts, TikTok, Instagram Reels) focusing on language learning (English, Spanish, French, Italian). The pipeline is orchestrated in Python and coordinates local AI models (ComfyUI image & TTS generation, Transformers MusicGen, and FFmpeg assembly) with an LLM for scriptwriting.

---

## The 4 Video Formats

The content strategy consists of four distinct formats queued from CSV files in `input/csv/<language>/expressions_list/` (e.g. `ENGLISH_READY_PROMPTS_*.csv`, `FRENCH_READY_PROMPTS_*.csv`, `SPANISH_READY_PROMPTS_*.csv`, `ITALIAN_READY_PROMPTS_*.csv`):

1. **EXPRESSION (`*_READY_PROMPTS_EXPRESSION.csv`)**:
   - **Purpose**: Explains a linguistic expression, slang term, or idiom in the chosen target language (English, French, Spanish, Italian) through viral, magnetic micro-storytelling.
   - **Anti-Cliché Standard**: Strict ban on formulaic titles, copied intros, and textbook lectures (e.g. *"The Stress Shift That Changes Everything"*, *"Move the stress just one syllable..."*, *"Si tu traduis [X] littéralement..."*, *"First syllable for the thing, second syllable for the action"*, *"Stop saying [X]!"*, *"Did you know..."*). Also bans generic infomercial language in payoffs (*"changes everything"*, *"game changer"*, *"speak like a native"*, *"level up"*, *"the ultimate"*, *"unlock"*, *"take your [language] to the next level"*).
   - **Practical Usage Is Always the Core Goal**: Etymology, origin stories, and acoustic secrets are hooks and setups — NOT the end goal. The viewer's primary takeaway MUST be practical, confident usage in real life. The `example` key is the most important key in the entire script — it carries proof that the expression is usable and must use the complete idiomatic form with correct emotional register.
   - **One Script = One Lesson (Strict)**: Each expression script teaches EXACTLY one linguistic point. If the expression data involves related words or a comparison (e.g., *attendre vs assister*), the script chooses the single primary confusion and builds the entire script around it.
   - **5 Storytelling Archetypes (with Priority Guidance)**:
     1. *The Bizarre Origin / Etymology Mystery*: Surprising historical or visual roots. Use only when the origin genuinely illuminates meaning or usage — etymology is a hook tool, not the entire lesson.
     2. *The Social Blunder / Awkward Translation*: Cringe word-for-word translation trap vs what locals actually heard.
     3. *The Native Slang / Street Level-Up*: Upgrading stiff classroom phrasing to authentic peer banter. Use only for genuine slang or register shifts, not as a generic template.
     4. *The Sound & Stress Secret / Minimal Pair Duel*: Contrasting acoustic rhythm, physical mouth feel, or syllable stress.
     5. *The Dramatic Slice of Life / In-Medias-Res*: High-stakes, relatable human moment where the idiom lands. **Prioritized** for high-stakes idioms and false friend dilemmas.
   - **English-Speaker False Friend Protocol (Mandatory When Applicable)**: When teaching a false friend that specifically traps English-speaking learners, the hook or setup MUST name the English trap word explicitly in quotes (e.g. in Spanish: *"Muchos angloparlantes escuchan 'embarazada' y piensan en 'embarrassed', pero en realidad..."*). The English word is the source of confusion — name it directly. Never substitute the English word with a target-language synonym.
   - **Italian Double Consonant Phonetic Accuracy (Mandatory)**: For Italian double consonant minimal pairs (*anno/ano*, *fatto/fato*, *penne/pene*): double consonant = short, tense vowel with held consonant; single consonant = longer, open vowel. Strictly forbidden phonetic reversals (e.g. *"anno è aperto"* is backwards).
   - **5-Section Micro-Story Narrative Architecture** (EXACTLY 6 JSON keys: `title` + 5 spoken sections):
     - `hook` (Narrator, 10–15 words): High-curiosity opening hook presenting dilemma, absurdity, or insider secret.
     - `setup` (Narrator, 20–25 words): The friction point, formality trap, or humorous literal misunderstanding.
     - `discovery` (Narrator, 20–25 words): Authentic native meaning, cultural context, and conversational nuance.
     - `example` (Narrator, 15–20 words): Everyday realistic spoken sentence demonstrating the complete expression in action with correct emotional register.
     - `payoff` (Narrator, 15–20 words): Specific human observation about the scene, finished with mandatory CTA line. Never CTA alone — payoff MUST start with a punchy observation.
   - **Target Duration & Word Budget**: **38 to 48 seconds** (strictly **85–110 spoken words** across all 5 spoken sections).
   - **Automated EXPRESSION Validation & Repair**: `main.py` validates EXPRESSION scripts for mandatory keys (`title`, `hook`, `setup`, `discovery`, `example`, `payoff`), rejects illegal invented keys, and enforces the 85–110 word budget with automatic retry on failure.
   - **Status**: **Fully functional and verified end-to-end** (scripting, voice generation, scene imagery, and final video assembly).

2. **ROLEPLAY (`*_READY_PROMPTS_ROLEPLAY.csv`)**:
   - **Purpose**: USE previously learned language in an authentic, entertaining real-life situation through engaging character dialogue.
   - **Dialogue Roles & Strict Speaker Discipline (3 Voices)**:
     - `NARRATOR`: Speaks **exclusively** in `hook` and `PAYOFF`. Strictly banned from speaking inside dialogue parts.
     - `PERSON_ONE` & `PERSON_TWO`: Strictly alternate turns in every dialogue part (Turn 1: `PERSON_ONE (Emotion): ...\n` Turn 2: `PERSON_TWO (Emotion): ...`). Speaker order never flips — every dialogue part begins with PERSON_ONE.
   - **Autonomous Personalities & Anti-Tutor Standard**: Characters are real peers, friends, travel buddies, coworkers, siblings, or roommates talking naturally. **Strictly forbidden**:
     - *No polite tutor trope*: P1 must never act like a confused student while P2 acts like a condescending dictionary teacher. Banned tutor sequence: `P1 mistakes → P2 corrects smugly → P1 asks "why?" → P2 gives dictionary definition → P1 says "Oh! Now I get it!"`.
     - *No betting clichés*: Zero tolerance for *"Free [coffee/pizza] on the line..."*, *"Bet you five bucks..."*, *"Apuesta: no te dejo pedir un café..."*.
     - *Organic Dynamics*: 5 varied human dynamics (embarrassing retrospective disaster, real-world task pressure in airports/markets/shops, sarcastic street smarts banter, mutual comedy of errors, or reacting to bizarre text messages/overheard conversations).
   - **Strict Direct-Causality & Zero-Hallucination Quotes**:
     - Speakers must directly respond to each other in real time. Neither character may ever react to words, accusations, or phrases not explicitly uttered in the immediately preceding dialogue turn.
     - If PERSON_TWO says *"Wait, you said 'X'?"*, PERSON_ONE must have literally just said *"X"*. Zero phantom quotes.
   - **Idiom / Expression Trigger Direction (Mandatory — Critical)**:
     - The target expression MUST arrive in `DIALOGUE_PART_1` as PERSON_TWO's natural speech, reacting to PERSON_ONE's established situation/state/behavior.
     - PERSON_ONE sets the scene (their problem, situation, anxiety, or error). PERSON_TWO then drops the idiom or phonetic observation naturally. PERSON_ONE reacts to hearing it.
     - PERSON_ONE must NEVER self-diagnose by using the target expression about themselves in their own opening line (e.g. ❌ *"J'ai le cafard"*, ❌ *"Creo que estoy frito"*, ❌ *"I think I need to break a leg here"*).
   - **False Friend / Confusion Direction (Mandatory)**: When the scenario describes a false friend confusion: PERSON_ONE MUST make the described mistake in `DIALOGUE_PART_1` — using the wrong word in a natural sentence. PERSON_TWO reacts authentically to the mistake they just heard. Never invert this direction.
   - **`SPECIAL_TREATMENT` — Expression Classification (Optional Column)**:
     Each ROLEPLAY row may carry a `SPECIAL_TREATMENT` value that classifies the target expression under **one mutually exclusive primary lens**. The value drives a type-specific instruction block injected by `prompt_builder.py` **before** the standard arc rules:

     | Value | Primary Lens | Prototypical Examples |
     |---|---|---|
     | `idiomatic` | Fixed multi-word phrase with figurative, non-compositional meaning | *break a leg*, *costar un ojo de la cara*, *poser un lapin*, *C'est pas la mer à boire* |
     | `phonetic` | Stress-shift, heteronym, or minimal pair contrast | *REcord vs reCORD*, *anno vs ano*, *PERmit vs perMIT* |
     | `false_friend` | Cross-language false cognate trap | *embarrassed/embarazada*, *attendre/assister*, *parenti/genitori* |
     | *(blank)* | LLM decides best approach (default behavior, no change) | — |

     **Rule**: One expression, one lens. An expression is classified by how a learner would **primarily** struggle with it — never combine types.

     **Mandatory Idiomatic Arc** (active when `SPECIAL_TREATMENT=idiomatic`):
     This arc exists to fix **Error #4 — No Usage Modeling**: the most common quality failure in idiomatic roleplays, where P1 only nods along while P2 explains, but never uses the idiom themselves.
     - `DIALOGUE_PART_1`: P2 drops the **complete, untruncated** idiom form (❌ *"costar un ojo"*, ✅ *"costar un ojo de la cara"*).
     - `DIALOGUE_PART_2`: P1 reacts to the **literal image** of the idiom (the comic engine). P2 gives **exactly one sentence** of real meaning — then the conversation moves on. Multi-sentence dictionary explanations are banned.
     - `DIALOGUE_PART_3`: P2 uses the idiom in a **brand-new real-life sentence**. P1 attempts their own use in a new context (usage modeling begins).
     - `DIALOGUE_PART_4` (**Critical Quality Gate**): **P1 MUST use the complete idiom in an original sentence of their own** — not a question, not a meta-comment, not a confirmation. This is the proof of learning, equivalent to the EXPRESSION format's `example` key.

     **Automated Quality Gate**: `validate_idiomatic_roleplay()` in `_A_video_scripts/main.py` checks two conditions post-generation when `SPECIAL_TREATMENT=idiomatic`:
     1. Full idiom form appears verbatim in `DIALOGUE_PART_1`.
     2. `PERSON_ONE`'s line in `DIALOGUE_PART_4` contains the idiom in active use.
     Failure triggers an **auto-retry** with explicit `IDIOMATIC ARC FIX REQUIRED` instructions appended to the retry prompt.

     **`SPECIAL_TREATMENT` is consumed by the prompt builder and excluded from the raw LLM parameter string** — it shapes the prompt architecture, not the LLM's content input.
   - **Factual Accuracy for Heteronym Verb Forms (Mandatory)**: When demonstrating noun/verb pairs, PERSON_TWO must use each form with its correct real-world meaning and syntactic pattern (e.g. *obJECT* always takes preposition *TO*; *proJECT* means to cast/throw forward, not to plan; *conTRACT* means to shrink/tighten, not to sign).
   - **Word Stress & Minimal Pair Notation for TTS**: For heteronyms/homographs, stressed syllables **must be capitalized** in the text (e.g. `REcord` vs `reCORD`, `PROject` vs `proJECT`, `CONtract` vs `conTRACT`). Double consonants and minimal pairs are emphasized acoustically in dialogue.
   - **Language Purity in Dialogue (Strict — All Languages)**: ALL text inside `DIALOGUE_PART_1` through `DIALOGUE_PART_4` must be 100% in TARGET_LANGUAGE. Foreign words — including English fillers (*"Precisely"*, *"Wait"*, *"Right"*) inside non-English scripts — are strictly forbidden. Use target-language equivalents (*"Exactement"*, *"Attends"*, *"Espera"*, *"Esatto"*).
   - **Banned Hook Formulas (Narrator Opener)**: Zero tolerance for *"Stop messing up [X]!"*, *"This mistake will cost you..."*, *"Attention !"* as the entire hook. Hook MUST be a scene-based statement placing the viewer inside a specific human moment.
   - **Banned Infomercial Payoff Vocabulary**: Zero tolerance for *"changes everything"*, *"game changer"*, *"sounds like a pro"*, *"the ultimate"*, *"unlock"*, *"level up"*, *"clarity is power"*, *"go get that promotion"*. Payoff MUST be a short, specific human observation about the scene — NOT a self-help advertisement.
   - **4-Image Visual Architecture across 4 Dialogue Parts (6 Assembly Beats)** (EXACTLY 7 JSON keys: `title`, `hook`, 4 dialogue parts, `PAYOFF`):
      - `hook` (Narrator, 15–20 words): High-energy scene-based narrator hook establishing stakes or misunderstanding.
      - `DIALOGUE_PART_1` (P1 & P2, 30–38 words): Premise & Trigger — P1 states situation, P2 drops the target expression.
      - `DIALOGUE_PART_2` (P1 & P2, 30–38 words): Reaction & Confusion — P1 reacts to exact words, P2 points out real meaning.
      - `DIALOGUE_PART_3` (P1 & P2, 30–38 words): Acoustic / Nuance Demonstration (native cadence or street reality).
      - `DIALOGUE_PART_4` (P1 & P2, 30–38 words): Breakthrough & Modeling — P1 uses the target expression actively in an original sentence.
      - `PAYOFF` (Narrator, 20–25 words): Specific human observation about the scene + mandatory CTA line.
    - **Dynamic 4-Beat Storyboard Sequence & Dynamic Assembly Punch-In Cuts**:
      To eliminate repetitive duplicate poses and save 33% GPU generation time, Roleplay generates 4 distinct, visually engaging illustrations in Stage C:
      1. `hook` — **Scenario Establishing Shot**: Medium-wide shot establishing physical tension, environment, and situational stakes (visually grounds the hook and opening dialogue exchange).
      2. `DIALOGUE_PART_2` — **180° Reverse Angle Over-The-Shoulder (Reverse OTS)**: Camera flipped over Speaker 1's shoulder focusing on `PERSON_TWO` mentoring/reacting and naturally delivering the target expression.
      3. `DIALOGUE_PART_3` — **Kinetic Interaction & Prop Demonstration Shot**: Dynamic medium shot with active motion showcasing the physical object or interaction (smartphone, menu, tickets, tools, coffee counter) grounding the dialogue.
      4. `PAYOFF` — **Celebratory Resolution Two-Shot**: Both characters together in the frame sharing a laugh, high-five, or confident outro in the established story world.
      In video assembly (`_G_video_assembly`), when `DIALOGUE_PART_1` and `DIALOGUE_PART_4` occur in the audio timeline, the assembler automatically applies dynamic 1.25x punch-in cuts from their companion scenes (`hook` and `payoff`), framing high on characters' faces. This delivers 6 rhythmically timed visual cuts aligned with character speech from 4 generated illustrations with zero repetitive poses.
    - **Universal Multi-Character Gender Specification Rule (Zero-Ambiguity Mandate)**:
      Whenever MORE THAN ONE character appears in a visual scene prompt, the sex/gender of **EACH individual character MUST be explicitly specified** (e.g. *"one youthful 14-year-old teen boy and one youthful 14-year-old companion teen girl"*).
      - **Strict Prohibition on Generic Ambiguous Plurals**: Banned phrases like *"two teens"*, *"two friends"*, *"the characters"*, or *"they"* that cause the diffusion model or LLM to randomly assign or alter character sexes.
      - **Dual-Character State Persistence**: Roleplay states track explicit character sexes via `speakers_gender: {"PERSON_ONE": "female"|"male", "PERSON_TWO": "female"|"male"}`. Both characters receive distinct thematic wardrobes, hairstyles, and color palettes that remain locked across the entire scene sequence.
    - **Unconditional Setting Diversity**: `prompt_builder.py` **always** injects a deterministically cycled scene setting for **every** roleplay script (via `script_id % 10`), cycling across 10 realistic templates (airport departure gates, street food markets, flat-pack furniture assembly, train commutes, gym/running tracks, park benches, thrift/vintage shops, music rehearsal studios, café terraces, kitchen brunches). Previously gated behind office-scenario matching — now unconditional.
    - **Strict Voice Distinctness Mandate (Roleplay & Multi-Speaker)**:
      In roleplay videos, if the **Narrator** and either dialogue character (`PERSON_ONE` or `PERSON_TWO`) share the same gender, they **MUST NOT share the same reference voice file or Kokoro recipe**. All 3 speakers must have acoustically distinct voices so the narrator never sounds identical to a character.
    - **Static Narrator Persona**: Configured in `config/settings.py` (`STATIC_NARRATOR_PERSONALITY`) as an upbeat, charismatic YouTube Shorts storyteller and viral language mentor (never a boring book narrator).
    - **Target Duration & Word Budget**: **60 to 80 seconds max** (strictly **145–180 spoken words** total across all 6 spoken sections).
    - **Status**: **Fully functional and verified end-to-end** (multi-turn character dialogue, emotion-infused TTS acting, voice consistency, 4-image visual storyboard with 6 dynamic assembly cuts, and final video assembly).

3. **GAME (`*_READY_PROMPTS_GAME.csv`)**:
   - **Purpose**: Fast-paced, educational interactive trivia quiz game show to test viewers' language skills.
   - **Format Rules**: Strictly an educational trivia quiz game, NOT a roleplay or narrative story. Fictional scenarios, backstories, and theatrical setups are strictly forbidden. The LLM picks the best fit from 5 authorized game mechanics:
     1. *The Rapid Acoustic Ear Challenge*: Word stress, heteronyms, minimal pairs, double consonants — viewer identifies which option was spoken.
     2. *Native or Weird? / Which One Sounds Natural?*: False friends, collocations, nuances — option A is natural, option B is an awkward literal trap.
     3. *What Does It Really Mean?*: Idioms and slang — true figurative meaning vs comical literal trap vs plausible opposite.
     4. *The Real-Life Dilemma / Counter Reflex*: In-medias-res pressure — reply to a barista, boss, or friend naturally.
     5. *Spot the Imposter*: 3 options with 2 genuine native expressions and 1 bizarre fabricated imposter.
   - **Anti-Cliché Standard & Negative Bans**: Strict ban on copy-pasted hooks (*"Native speaker trap! Can you spot the right pronunciation in 3 seconds?"*, *"Le piège des faux-amis !"*, *"Trappola del madrelingua!"*), generic countdown lines (*"Quick, A or B? Trust your gut..."*), repetitive reveal formulas (*"takes the crown"*), and the overused *"listening to a native podcast"* hook.
   - **6 Dynamic Situational Archetypes**: Rotated deterministically by `script_id % 6` in `prompt_builder.py`:
     1. *The Transit / Public Announcement*: Rushing to catch a flight or metro train and deciphering an announcement in seconds.
     2. *The Smartphone Text Message Dilemma*: Decoding a friend's or roommate's text message without an awkward reply.
     3. *The Rapid Acoustic Ear Challenge*: Fast phonetic distinction (front beat vs back beat, double consonant vs single).
     4. *The Café / Counter Reflex*: Ordering or replying naturally under pressure at a bakery or coffee counter.
     5. *Spot the Weird Imposter*: Identifying an unnatural or fabricated phrase among genuine native expressions.
     6. *The Coworker Slack / Desk Dilemma*: Interpreting a colleague's quick team chat message.
   - **Mandatory Distractor Strategy & Zero-Duplicates**: All options (A, B, C, D) must be **100% unique and distinct**. Never duplicate option text. Idioms provide 1 true native meaning, 1 funny literal trap, and 1 plausible opposite. Binary face-offs strictly provide 2 options (A vs B).
   - **Clean Prompt Queues**: All GAME prompt CSVs in `input/csv/` contain clean target-language contrast pairs (e.g. `blessé vs béni`, `embarazada vs avergonzada`, `parenti vs genitori`), removing English glosses that confuse the LLM.
   - **Language Purity**: 100% in the target language with zero foreign countdown remnants or translation questions.
   - **Structure**: 5 mandatory spoken sections: `title`, `hook`, `challenge`, `pressure`, `answer`, `explanation`.
    - **Option A Spoken Challenge Delivery (Zero Spoken Blanks)**:
      - **Strict Ban on Spoken Underscores**: The spoken `challenge` field NEVER contains raw blanks (`___`), ellipsis gaps, or prompt parentheticals. TTS requires continuous, natural spoken flow.
      - **Acoustic Ear & Natural Spoken Delivery**: The Narrator speaks the sentence out loud naturally, pronouncing the target word/rhythm, and explicitly asks which option was heard/used (e.g. *"Both parties signed the employment CONtract yesterday. Did you hear A: CONtract, or B: conTRACT?"*).
      - **Mandatory Spoken Options**: The spoken `challenge` must always voice all options clearly (`A: [Option A], or B: [Option B]`), never cutting off abruptly.
    - **Chalkboard Exercise (Visual Graphic)**: Mandatory `chalkboard_exercise` field with the concrete test sentence containing a blank (`___`) on line 1, followed by distinct newline options (`\nA) ...\nB) ...`). Auto-synthesizes clean fallbacks from `CONTEXT` if omitted by the LLM.
    - **Narrator Persona**: High-energy, charismatic storyteller and viral mentor (`STATIC_NARRATOR_PERSONALITY`). Spoken entirely by the Narrator.
    - **Target Duration**: 40 to 55 seconds (strictly 95–125 words total across spoken sections).
    - **Pacing & Audio**: `audio_processor.py` inserts a dedicated 2.20-second suspenseful pause (`pressure_gap`) between `pressure` and `answer` to give viewers time to solve the quiz.
    - **Visuals**:
      - `hook`: Dilemma / situation setup in 2D cartoon illustration style via ComfyUI Z-Image.
      - `challenge`: **Native High-Resolution Chalkboard Renderer** (`core/chalkboard_renderer.py`). Uses PIL and FreeType (Segoe Print Bold) to render clean, authentic typography directly onto `input/images/game_images/empty_chalkboard.png` with chalk-yellow questions, dividers, translucent green option cards, and yellow letter badges (A, B, C, D).
        - *Clean Option Text Isolation (`clean_option_text`)*: Programmatically strips trailing punctuation and coordinating conjunctions (`or`, `and`, `o`, `ou`, `e`) from option choices, ensuring pristine options without trailing commas or awkward words (e.g. `B: Are you ready to win.?` instead of `B: Are you ready to win.?, or`).
        - *Automatic Spoken Answer Masking in Listening Challenges (`mask_revealed_answer_in_question`)*: For acoustic and listening quizzes where the spoken narrative pronounces the answer, the renderer automatically detects if an option phrase appears in the question text and masks it with `_________`. This prevents the visual chalkboard from prematurely spoiling the spoken quiz.
        - *CPU Execution & Zero VRAM Overhead*: Generates 576x1024 quiz graphics in milliseconds on CPU, bypassing heavy diffusion models.
      - `pressure`: Static pre-made waiting illustration per language from `input/images/game_images/<lang>/<lang>_waiting.png`.
      - `answer`: Real-life resolution with character celebrating success (2D cartoon via ComfyUI Z-Image).
      - `explanation`: Real-world application showing native speakers using the expression naturally.
    - **Subtitles**: Subtitles are suppressed exclusively during the `challenge` section so the chalkboard exercise remains clear and uncluttered, and the answer is never spoiled in text while the challenge audio plays. Subtitles resume normally for all other sections.
   - **Status**: **Fully implemented, verified, and operational**.

4. **FUN_FACTS (`*_READY_PROMPTS_FUN_FACTS.csv`)**:
   - **Purpose**: Umbrella category for short, entertaining, surprising, curious, challenging, unusual, or fascinating language discoveries. Follows **HOOK $\rightarrow$ DISCOVERY $\rightarrow$ PAYOFF $\rightarrow$ CTA / REACTION** (not traditional academic lectures).
   - **Content Pillars**: Language Curiosities, Word Curiosities, Etymology & Origins, Language History, Regional & Cultural Differences, Pronunciation Curiosities, Language Comparisons, Language Challenges, Language Myths, Language Records & Extremes.
   - **6 Authorized Formats**: Format A (3 Facts), Format B (One Big Curiosity), Format C (Challenge), Format D (Mystery), Format E (Comparison), Format F (Ranking/List).
   - **Narrator Persona**: Spoken entirely by the charismatic, witty LingoVerse storyteller and viral mentor (`STATIC_NARRATOR_PERSONALITY`). Relaxed, playful, surprising, fast cadence.
   - **Target Duration**: 40 to 60 seconds (strictly 95–135 words total across spoken sections).
   - **Target Language Localization**: All content in `*_READY_PROMPTS_FUN_FACTS.csv` (`TOPIC`, `FACT_DETAILS`, `HOOK_ANGLE`, `EMOTIONAL_TRIGGER`) must be written directly in the **target language of the video** (French, Spanish, Italian, English). This guarantees authentic native vocabulary and prevents translation artifacts.
   - **Factual Accuracy Standard**: Strict guardrail against hallucinated folk etymologies, false history, or fabricated records.
   - **Visuals**: 2D cartoon illustration style matching LingoVerse visual identity; existing channel opening and closing images.
   - **Dynamic Scene Count Adaptability (4 vs 6 Scenes)**: Image generation in Stage C dynamically inspects the section keys present in `content_metadata.script`. Standard 4-section curiosity formats (`hook`, `setup`, `discovery`, `payoff`) generate 4 distinct thematic scene images, while multi-fact or historical scripts (`hook`, `fact_1`..`fact_4`, `payoff` or `hook`, `setup`, `discovery_1`, `discovery_2`, `example`, `payoff`) generate 6 distinct scenes with full story-world consistency.
   - **Subtitles**: Continuous word-level animated subtitles (ASS) throughout runtime.
   - **Status**: **Fully implemented, verified, and operational**.

---

## Streamlined Input CSV Schema & Automatic Inference

Input queues in `input/csv/<language>/expressions_list/` are streamlined to contain strictly content-essential fields, eliminating redundant boilerplate columns:

- **EXPRESSION (`*_READY_PROMPTS_EXPRESSION.csv`)**:
  `ID,EXPRESSION,SUBJECT,CONTEXT,ANGLE,LEXICAL_FIELD,EMOTIONAL_TRIGGER`
- **GAME (`*_READY_PROMPTS_GAME.csv`)**:
  `ID,EXPRESSION,CONTEXT,SUBJECT,LEXICAL_FIELD`
  *(Clean Target-Language Standard: The `EXPRESSION` column strictly contains target-language contrast pairs or native expressions like `blessé vs béni` or `embarazada vs avergonzada`, while `CONTEXT` provides concrete test sentences with blanks (`___`) where the expression is used).*
- **ROLEPLAY (`*_READY_PROMPTS_ROLEPLAY.csv`)**:
  `ID,ROLEPLAY_SCENARIO,SUBJECT,LEXICAL_FIELD,EMOTIONAL_TRIGGER,SPECIAL_TREATMENT`
  *(Optional `SPECIAL_TREATMENT` column classifies the expression under one mutually exclusive pedagogical lens — see ROLEPLAY section above for valid values and arc rules.)*
- **FUN_FACTS (`*_READY_PROMPTS_FUN_FACTS.csv`)**:
  `ID,TOPIC,PILLAR,FORMAT,FACT_DETAILS,HOOK_ANGLE,EMOTIONAL_TRIGGER`

### Automatic Field Inference & Elimination of Boilerplate
1. **`TARGET_LANGUAGE`**: Inferred automatically from the directory path (`input/csv/<language>/...`) and filename.
2. **`VIDEO_TYPE`**: Inferred automatically from the filename (`..._EXPRESSION.csv`, `..._GAME.csv`, `..._ROLEPLAY.csv`, `..._FUN_FACTS.csv`) and the 2nd character of the ID.
3. **`SPECIFIC_CONSTRAINT`**: Omitted from CSVs. Target durations (EXPRESSION: 38–48s [85–110 words], GAME: 40–55s [95–125 words], ROLEPLAY: 60–80s [145–180 words], FUN_FACTS: 40–60s [95–135 words]) and word budgets are authoritatively defined and validated directly inside `video_creation/_A_video_scripts/prompts/` and `main.py`.
4. **`FORMAT`**: For EXPRESSION, GAME, and ROLEPLAY, JSON format is enforced by prompt rules. For FUN_FACTS, the optional `FORMAT` column lets creators select one of the 6 authorized format structures (e.g. `ONE_BIG_CURIOSITY`, `3_FACTS`, `CHALLENGE`, `MYSTERY`, `COMPARISON`, `RANKING_LIST`) or leave blank for autonomous LLM selection.
5. **`STATUS`**: Omitted from CSVs. Script progress is tracked solely through the state machine (`state/<language>/<video_type>/script_<ID>.json`).

### Privacy & Version Control: Sample Templates
To protect the creator's proprietary prompt libraries and production assets:
- Production CSV queues in `input/csv/<language>/` are strictly gitignored via `.gitignore`.
- Canonical schema templates are maintained in `input/csv/sample_templates/`:
  - `EXPRESSION.sample.csv`: Schema for the 5-section micro-story storytelling format.
  - `GAME.sample.csv`: Schema for educational trivia challenges and clean contrast pairs.
  - `ROLEPLAY.sample.csv`: Schema for 3-speaker peer dialogue scenarios. Includes `SPECIAL_TREATMENT` column — see valid values (`idiomatic`, `phonetic`, `false_friend`, blank) in the ROLEPLAY section above.
  - `FUN_FACTS.sample.csv`: Schema for 6 viral language curiosity formats.
  - `CALL_TO_ACTIONS.sample.csv`: Schema for randomized outro engagement lines.
- Complete documentation on CSV columns and validation rules is available in `input/csv/README.md`.

---

## Structured Script ID Standard

Every video across the pipeline is assigned a canonical, non-overlapping identifier following the format:

$$\textbf{<Language\_Code><Type\_Code><Index:02d>}$$

- **Language Code** (1st char): `E` (English), `F` (French), `S` (Spanish), `I` (Italian).
- **Video Type** (2nd char): `E` (Expression), `G` (Game), `R` (Roleplay), `F` (Fun Facts).
- **Sequential Index** (3rd–4th digits): 2-digit zero-padded index per (language, type) pair (`01`, `02`, ..., `99`, `100`+).
- **Localized Canonical Examples**:
  - `FE01`: French Expression #1 (*Poser un lapin*)
  - `FG01`: French Game #1 (*Poser un lapin*)
  - `FR01`: French Roleplay #1 (*Poser un lapin*)
  - `FF01`: French Fun Facts #1 (*Pourquoi les nombres en français font des maths*)
  - `EE01`: English Expression #1 (*Break a leg*)
  - `EF01`: English Fun Facts #1 (*Silent K in Knight and Knee*)
  - `SE01`: Spanish Expression #1 (*Costar un ojo de la cara*)
  - `SF01`: Spanish Fun Facts #1 (*Por qué el español usa signos de interrogación invertidos*)
  - `IE01`: Italian Expression #1 (*In bocca al lupo*)
  - `IF01`: Italian Fun Facts #1 (*L'alfabeto italiano ha solo 21 lettere*)
- **Active Prompt Library (1,224 Prompts across 16 CSVs)**:
  - **English** (372): 119 expressions across `EXPRESSION` (`EE01`–`EE119`), `GAME` (`EG01`–`EG119`), `ROLEPLAY` (`ER01`–`ER119`) + 15 `FUN_FACTS` (`EF01`–`EF15`).
  - **French** (270): 85 expressions across `EXPRESSION` (`FE01`–`FE85`), `GAME` (`FG01`–`FG85`), `ROLEPLAY` (`FR01`–`FR85`) + 15 `FUN_FACTS` (`FF01`–`FF15`).
  - **Spanish** (279): 88 expressions across `EXPRESSION` (`SE01`–`SE88`), `GAME` (`SG01`–`SG88`), `ROLEPLAY` (`SR01`–`SR88`) + 15 `FUN_FACTS` (`SF01`–`SF15`).
  - **Italian** (303): 96 expressions across `EXPRESSION` (`IE01`–`IE96`), `GAME` (`IG01`–`IG96`), `ROLEPLAY` (`IR01`–`IR96`) + 15 `FUN_FACTS` (`IF01`–`IF15`).
  - **Total**: 388 unique linguistic expressions $\times$ 3 formats + 60 localized FUN_FACTS prompts = **1,224 synchronized records**.
- **Lifecycle & Immutability**:
  - IDs are assigned in the input CSVs (standardized via `py tools/database/sync_prompts.py`, or generated on-the-fly for unassigned rows in `_A_video_scripts/main.py`).
  - Once generated into `state/<language>/<video_type>/script_<ID>.json`, downstream stages (`_B`, `_C`, `_D`, `_F`, `_G`) read the state's ID directly. **IDs are never re-created or altered across pipeline stages**.
  - **Collision Prevention**: Allocation logic preserves existing valid IDs and incrementally allocates `max_existing_index + 1` for newly appended rows.

---

## Current Production State & Metrics

Real-time audit compiled via `py tools/auditing/status_scraper.py` and `py tools/database/db.py stats`:

- **Total Video Prompts Tracked**: 1,224 across 16 synchronized CSV queues.
- **Part A (Script Generation)**: **1,176 / 1,224 (96.1% Complete)** across active production batches:
  - **English**: 372 / 372 scripts generated (100% Complete)
  - **French**: 270 / 270 scripts generated (100% Complete)
  - **Italian**: 303 / 303 scripts generated (100% Complete)
  - **Spanish**: 231 / 279 scripts generated (82.8% Complete)
  - **Breakdown by Format**: `EXPRESSION`: 388 / 388 (100%) | `GAME`: 388 / 388 (100%) | `FUN_FACTS`: 60 / 60 (100%) | `ROLEPLAY`: 340 / 388 (87.6%)
  - **Pending Scripts**: 48 prompt rows in queue awaiting LLM generation (all in Spanish Roleplay).
- **Script Modifications Audit & Sync**: **359 / 359 scripts (100% Complete & Synchronized)** across all 16 CSV queues in `input/csv/script_to_change/` matching local state JSONs with zero section duplication.
- **Proof-of-Concept Pilot Videos (End-to-End Operational)**:
  - `EE01` (English Expression #1 - *Break a leg*): 100% complete assets on disk (Script, Voice, Image, Music, Thumbnail, Assembly)
  - `EG01` (English Game #1 - *Break a leg*): 100% complete assets on disk (Script, Voice, Image, Music, Thumbnail, Assembly)
  - `ER01` (English Roleplay #1 - *Break a leg*): 100% complete assets on disk (Script, Voice, Image, Music, Assembly)
- **Standing Music Bank (`_D_music_generation`)**: **160 / 160 (100.0% Complete)** across all 16 categories in `<OUTPUT_DIR>/bank_music/` (10 curated tracks each for 4 languages × 4 formats).
- **Pending Downstream Production**: 1,221 videos awaiting audio synthesis (`_B`), scene images (`_C`), thumbnails (`_F`), and final rendering (`_G`).
- **Master Expression Database**: 1,224 records in `database/expressions.db` (all initialized to `PENDING`).

---

## Pipeline Architecture & Execution Stages

All workflow stages and shared templates are organized inside the `video_creation/` package:

```
[Input CSVs]
     │
     ▼
1. video_creation/_A_video_scripts           (LLM script & metadata generation)
     │
     ▼
2. video_creation/_B_voice_generation        (TTS multi-speaker generation via ComfyUI Qwen3-TTS)
     │
     ├────────────────────────────────────────┬────────────────────────────────────────┐
     ▼                                        ▼                                        ▼
3. video_creation/_C_image_generation   4. video_creation/_D_music_generation   5. video_creation/_F_thumbnail_image_generation
  (ComfyUI SD/Flux scenes)                (Standing Music Bank Library)           (ComfyUI Flux image-to-image)
     │                                    (<OUTPUT_DIR>/bank_music/<lang>/<type>)      │
     │                                        │                                        │
     └────────────────────────────────────────┴────────────────────────────────────────┘
                                              │
                                              ▼
                                       6. video_creation/_G_video_assembly
                                        (Whisper subtitles + Emotion-Based Jam Selection + FFmpeg)
                                              │
                                              ▼
                                     [Final Shorts Video]
```

> **Execution Flow & Interactive Generation Mode**:
> 1. **Pre-flight Service Verification**: When `main.py` of any stage is executed, it first performs connection checks via `config/health.py` (`require_services`) asserting that required backends (LLM, ComfyUI) are online and responsive before proceeding.
> 2. **Harmonized Interactive Mode Selection (10s Countdown)**: After services are verified, pipeline stages present a unified interactive console prompt via `core/cli_prompt.py`:
>    - `[1] Mass-produce all pending assets` (automatically selected if the 10-second timer expires with no input).
>    - `[2] Select specific script(s) by ID`: Prompts for Script IDs (single or comma-separated e.g. `EE01, EE02`), validates that the script state JSON exists in `state/`, prompts `Add another script to produce? [y/N]: `, and queues all specified scripts for execution.
>    - `[3] Number Range Groups (e.g. 10 - 20)`: Prompts for language selection and numeric start/end range (e.g. `10-20`), executes the batch across selected language(s), and prompts whether to run another group without restarting the process.
>    - `[4] Fun Facts only`: Filters production strictly to Fun Facts scripts (`EF`, `FF`, `SF`, `IF`), offering all languages or specific language range.
>    - `[5] Target scripts from CSV`: Reads IDs from dedicated workflow queues:
>      - Stage A: `input/csv/script_to_change/` (script text modification & repair)
>      - Stage B: `input/csv/voice_to_change/` (Option [5]) or Ready Scripts CSV (Option [6])
>      - Stage C: `input/csv/image_to_change/` (Option [5]) or Ready Scripts CSV (Option [6])
>      - Stage F (Thumbnails): Directly uses `[5] From Ready Scripts CSV (<date>_ready_scripts.csv)` scanning `D:\AI\output\connectivity\ready_scripts`
>      - Stage G (Video Assembly): Directly uses `[5] From Ready Scripts CSV (<date>_ready_scripts.csv)` scanning `D:\AI\output\connectivity\ready_scripts`
>    - **Interactive Countdown Input (`timed_input`)**: All terminal prompts requiring user decisions (such as character gender selection in `_C_image_generation` or manual voice prompts in `_B_voice_generation`) implement a 10s countdown timer that automatically defaults if unattended, while pausing countdown when the user starts typing.
>    - **CLI Overrides**: Passing `--script-id <ID1,ID2...>`, `--auto`, `--fun-facts`, `--from-csv [PATH]`, or `--from-ready-scripts [PATH]` on the command line immediately triggers targeted execution and bypasses the interactive timer.
> 3. **Modular Execution**: Stages can be run individually, via root `main.py` (which orchestrates Part A & B with an interactive checkpoint review), or queued in automated batches.

### Stage Details & CLI Commands (inside `video_creation/`):

1. **`video_creation/_A_video_scripts`**:
   - Ingests prompts from `input/csv/<language>/expressions_list/*READY_PROMPTS_*.csv`.
   - Uses an LLM (configured via `.env`) to generate structured JSON scripts adhering to strict pacing, word counts, and format rules.
   - **Modular Prompt Rules Architecture (`prompts/`)**:
     - `prompts/prompt_builder.py`: Main prompt coordinator injecting global guidelines, system roles, unconditionally cycling across 10 realistic scene settings for roleplays (via `script_id % 10`), rotating 6 situational archetypes for games, and assigning archetype-specific instructions for expressions.
     - `prompts/common_rules.py`: Shared global content rules across all video types — language purity, anti-repetition, audience awareness, and mandatory JSON output format.
     - `prompts/prompts_data.py`: YouTube metadata generation prompt (`METADATA_PROMPT`) for producing titles, descriptions, tags, hashtags, labels, and filenames.
     - `prompts/expression_rules.py`: Strict anti-cliché standard eliminating repetitive titles and template intros; enforces the 5-section micro-story architecture (`hook`, `setup`, `discovery`, `example`, `payoff`), 85–110 spoken words (38–48s), 5 storytelling archetypes with priority guidance, English-speaker false friend protocol, Italian double consonant phonetic accuracy, "One Script = One Lesson" strict rule, and practical usage emphasis. Includes 3 few-shot examples (Etymology, Acoustic, False Friend) for structural inspiration only.
     - `prompts/roleplay_rules.py`: Autonomous peer personalities with zero tolerance for betting clichés, condescending tutor dynamics, or infomercial payoff language; enforces the 6-scene visual architecture across 4 dialogue parts plus `hook` and `PAYOFF`, 145–180 spoken words (60–80s), strict direct-causality & zero-hallucinated quotes, mandatory idiom trigger direction (P2 introduces idiom in `DIALOGUE_PART_1`), false friend confusion direction, factual accuracy for heteronym verb forms, language purity in dialogue (no English fillers in non-English scripts), banned hook formulas, word stress capitalization for TTS, and 3-speaker isolation. Includes 2 few-shot examples for structural inspiration only.
     - `prompts/game_rules.py`: 5 authorized game mechanics catalog with flexible chalkboard option counts (2 to 5 options, not locked to A-B-C-D), banning canned countdown hooks (`"Native speaker trap!..."`), repetitive payoff phrases (`"takes the crown"`), podcast templates, spoken blanks (`___`), and prompt leakage.
     - `prompts/fun_facts_rules.py`: 6 authorized viral discovery formats with factual accuracy constraints.
   - **6 Rotating Game Situational Archetypes (`script_id % 6`)**: Transit announcements, text message dilemmas, rapid acoustic challenges, counter reflex decisions, spot-the-imposter quizzes, and coworker Slack chat dilemmas.
   - **Automated Multi-Layer GAME Validation & Repair**:
      - *Spoken Blank Rejection (`___`)*: Programmatically detects and retries drafts where the LLM placed raw blanks (`___` or `....`) into the spoken `challenge` audio.
      - *Spoken Options Assertion*: Validates that options A and B are explicitly voiced in the spoken `challenge` text, never cutting off abruptly.
      - *Prompt Leakage Filter*: Automatically strips prompt notes, definitions, or translation glosses (e.g. `(attendre = patienter vs assister = aider)`) from script audio.
      - *Post-Chalkboard Option A Finalizer*: Automatically aligns spoken `challenge` with the finalized chalkboard choices, seamlessly substituting the target expression into the spoken test sentence so audio flows with zero gaps.
      - *Duplicate Option Rejection*: Automatically detects and retries drafts containing identical or cloned option choices.
      - *Negative Assertion Guardrails*: Programmatically rejects drafts containing banned podcast hooks, `"takes the crown"` reveals, abstract questions without context, or foreign language leaks.
      - *Chalkboard Fallback Synthesizer*: Automatically generates a clean, well-formatted `\nA) ...\nB) ...` chalkboard exercise if the LLM omits or malforms the field.
   - **Automated EXPRESSION Validation & Repair**: Validates mandatory keys (`title`, `hook`, `setup`, `discovery`, `example`, `payoff`), rejects illegal invented keys, enforces the 85–110 word budget, and retries generation on failure.
   - **Automated ROLEPLAY Validation & Repair**: Validates mandatory 7-key structure, rejects illegal keys, detects narrator intrusion inside dialogue parts, catches unresolved questions in `DIALOGUE_PART_4`, and enforces the 145–180 word budget with automatic retry.
   - **Automated FUN_FACTS Validation & Repair**: Validates mandatory `hook` and `payoff` sections, rejects illegal keys not in the authorized set, and enforces the 95–135 word budget with automatic retry.
   - **Resilient JSON Parsing**: Multi-strategy extraction via direct parse, `JSONDecoder.raw_decode`, balanced bracket scan, and regex fallback — all with `strict=False` to tolerate unescaped newlines in multi-line string fields.
   - **Interactive Modes**: Supports `[1] Mass-produce`, `[2] Specific Script IDs`, `[3] Number Range Groups`, `[4] Fun Facts only`, `[5] Change scripts from CSV` (`script_to_change/`), `[6] From Ready Scripts CSV` (`<date>_ready_scripts.csv`), and `[7] Mass Ready Scripts` (Choose multiple/all ready_scripts files to run on production).
   - Automatically injects `character_personalities` and builds rich YouTube metadata (`title`, `description`, `tags`, `hashtags`).
   - **Robotic Payoff Sanitizer**: Automatically detects and replaces generic robotic filler phrases in payoffs (e.g. *"Follow for more essential idioms and comments below!"*) with randomly selected CTA phrases from the call-to-action CSV library.
   - **Command**: `py video_creation/_A_video_scripts/main.py [--script-id <ID>] [--auto] [--force] [--script-input <FILE>] [--fun-facts] [--from-csv [PATH]] [--from-ready-scripts [PATH]] [--from-mass-ready-scripts [PATH]]`
   - **Interactive Tool**: `script_modifier.py` (`py tools/modifiers/script_modifier.py` or `py video_creation/_A_video_scripts/script_modifier.py`) allows single-script and **Mass Script Changes** plain-text ingestion (queueing multiple IDs and custom scripts before launching LLM batch formatting) while strictly keeping user script text verbatim. Enforces canonical key ordering (`title` strictly first key, followed by standard section sequences without generic `: Shorts Guide` suffixes) and automatically synchronizes review CSVs in `output/scripts_to_see/<lang>/<vtype>/` upon every modification.
   - **Script Doctoring Tool**: `system_prompts_editor.csv` — a companion CSV containing per-video-type system prompts for an external LLM script doctor (e.g. ChatGPT/Claude). Each row defines the doctoring principles for a video type (EXPRESSION, ROLEPLAY, GAME, FUN_FACTS): language mirroring, substantive script elevation, ban on generic formulas, word budget enforcement, and format-specific structural rules. Used for external script polishing workflows.

2. **`video_creation/_B_voice_generation`**:
   - Generates natural, expressive voiceovers using **Qwen3-TTS (1.7B fp16)** via local ComfyUI workflow (`video_creation/workflows/Qwen3-TTS Voice.json`).
   - Multi-speaker voice assignment via `core/voice_manager.py`:
     - Assigns distinct reference voices from `open-swara` across genders (`male`, `female`) and languages (`english`, `french`, `spanish`, `italian`).
     - Prioritizes reserved `NARRATOR_VOICES` from `config/settings.py`.
     - **Voice Consistency**: Locks each character's reference audio file and random seed into memory so voices never drift across dialogue turns.
   - **Acting Emotions & Pacing**:
     - Automatically infers dramatic acting tone per turn (`infer_dialogue_emotion`), passing explicit acting directives to Qwen3-TTS.
     - Prevents dead silence via dynamic token limits (`max_new_tokens = max(96, min(240, words * 12))`) and `repetition_penalty = 1.15`.
     - Automatically trims dead trailing air (`trim_trailing_silence`) and concatenates segments with tight YouTube Shorts pauses (0.20s dialogue, 0.40s section, 2.20s pressure pause).
   - **Syntactic Carrier & Continuous Prosody Architecture with Kokoro-82M Hybrid Engine**:
     - **Problem Solved**: Direct input of isolated uppercase heteronym syllables (`reCORD`, `PROject`, `deCREASE`), hyphenated spellings (`re-CORD`), or artificial respellings (`pri-ZENT`, `PRAHJ-ekt`) causes sub-word tokenizer fragmentation and distorted vowel phonemes in autoregressive TTS. Furthermore, isolated words spoken without context fall back to flat citation stress.
     - **Syntactic Carrier Protocol**:
       - Heteronyms and minimal pairs are primed by natural syntactic carriers:
         - Nouns are conditioned with determiners/articles (`a PREsent`, `the REcord`, `a PROject`, `a PERmit`, `an OBject`).
         - Verbs are conditioned with infinitives/particles (`to preSENT`, `to reCORD`, `to proJECT`, `to perMIT`, `to obJECT`).
       - Continuous single-take generation: dialogue turns and narrator explanations are generated in single acoustic takes per segment, preserving natural pitch contours and prosodic flow.
       - Artificial respellings (`PREH`, `PROH`, `prih`, `pruh`, `RECK-ord`) are strictly purged across all prompt queues and state scripts.
     - **Acoustic Prominence Quality Gate (`core/acoustic_evaluator.py`)**:
       - Triggers automatically when `is_stress_pronunciation_vital()` detects heteronym or syllable stress topics.
       - Multi-candidate sampling (`--candidates 3` by default): generates multiple takes via ComfyUI.
       - Computes mathematical acoustic prominence metrics:
         - Peak RMS energy ratio between target syllables.
         - Fundamental frequency ($F_0$) pitch excursion delta.
         - Vowel duration contrast.
       - Evaluates candidates against strict stress thresholds (Noun RMS ratio >= 1.05; Verb RMS ratio >= 1.10; $F_0$ delta > 0) and automatically selects the highest-scoring candidate.
     - **Kokoro-82M Precision Hybrid Engine & Pronunciation Bank (`core/kokoro_engine.py` & `core/pronunciation_bank.py`)**:
       - When stochastic autoregressive generation falls below acoustic prominence thresholds, the pipeline seamlessly falls back to a curated Standing Pronunciation Bank (`main/input/audio/heteronym_bank/`).
       - The bank is powered by **Kokoro-82M (`kokoro-onnx` + `espeak-ng`)**, an 82M-parameter precision TTS engine executing phonemic IPA representations with 100% deterministic syllable stress control.
       - 100% coverage across all 58 core heteronym clips with both male (`am_adam`) and female (`af_heart`) reference voices.
       - CLI management: `py main/tools/manage_pronunciation_bank.py` supports `--status`, `--audit`, `--populate-kokoro`, `--import-clip`, and `--export-json`.
     - **Syllable Stress Subtitle Synchronization (`subtitle_builder.py`)**:
       - Hormozi-style all-caps subtitle renderer preserves mixed-case syllable capitalization (`PREsent` vs `preSENT`, `PROject` vs `proJECT`) by cross-referencing script state text against Whisper word-level timestamps.
     - **Full Feature Parity in Voice Modifier**:
       - Both `main.py` and `voice_modifier.py` implement identical multi-candidate sampling (`--candidates`), acoustic quality gating (`select_best_voice_candidate`), and bank fallback.
     - **Multilingual Phonetic Guidance**:
       - *Italian Dizione*: Contrast between single and double consonants (`t` vs `tt`, `n` vs `nn`), short open vowels preceding geminates, crisp dental articulation.
       - *Spanish Dicción*: Contrast between single tap `r` and double alveolar trill `rr`, pure bright vowels without English diphthongization.
       - *French Diction*: Natural phrase-final tonic accent, clean liaisons, melodic cadence, fluid prosody.
       - Strict language isolation: English ALL-CAPS instructions are never passed to French, Italian, or Spanish prompts.
     - **Linguistic vs. Anxiety Topic Separation**: Disambiguates linguistic stress scripts from psychological anxiety topics (e.g. *"le stress des examens"*, *"gestion du stress"*), preventing prompt overrides on non-phonetic scripts.
   - **Harmonized Production Modes**: Supports Mass-produce (10s countdown default), Specific IDs, Group Ranges, Fun Facts only, CSV lists from `input/csv/voice_to_change/`, Ready Scripts CSV from `D:\AI\output\connectivity\ready_scripts/<date>_ready_scripts.csv` (Option `[6]`), and Mass Ready Scripts across multiple/all ready_scripts files (Option `[7]`).
   - **Interactive Tool (`voice_modifier.py`)**:
     - **Immediate Pre-Flight Health Checks**: Executes ComfyUI and local Kokoro engine health assertions on startup before prompting for user input.
     - **Streamlined Gender Selection (Zero Manual File Selection)**: Users specify only speaker genders (`male`/`female`), with `Enter` keeping state defaults. Eliminates manual file selection lists.
     - **Automated Random Voice Casting**: Automatically selects random distinct reference voices from the pool, matching `main.py`.
     - **Strict Roleplay Voice Distinctness**: Enforces that Narrator and characters sharing the same gender never share the same voice.
     - **Automatic Downstream State Invalidation**: Sets `status.video_assembly = "pending"` upon master audio generation so video assembly can be re-run with the updated audio.
     - **Resilient Fallback Parsing**: Integrates `strict=False` and fallback to `content_metadata.script` to ensure scripts with raw newlines parse cleanly without failing.
   - **Command**: `py video_creation/_B_voice_generation/main.py [--script-id <ID>] [--force] [--auto] [--candidates <INT>] [--fun-facts] [--video-type <TYPE>] [--language <LANG>] [--from-csv [PATH]] [--from-ready-scripts [PATH]] [--from-mass-ready-scripts [PATH]]`

3. **`video_creation/_C_image_generation`**:
   - Generates high-quality vertical visuals (576x1024, 9:16 aspect ratio) for each script scene using local ComfyUI workflow `video_creation/workflows/AcademiaSD_Z-Image_v05.json`.
   - Outputs saved to `output/video_assets/<language>/<video_type>/script_<ID>/images/`.
   - **Two-Pass Visual Director Engine (`core/prompt_builder.py`)**:
     - *Pass 1: Story World Anchor (`build_general_prompt`)*: Establishes a cohesive physical setting, architectural details, lighting, color palette, and character designs with explicit sexes and thematic wardrobes matching the scenario (e.g. stage vest in theater, chef coat in kitchen, studio smock in workshop). Persisted in `script_data["assets"]["general_prompt"]` and `content_metadata["anchor_environment"]`.
     - *Pass 2: Complete Storyboard Director (`build_storyboard_prompts`)*: Synthesizes per-scene visual prompt variations maintaining strict story-world consistency anchored to the General Prompt while executing format-specific shot dynamics:
       - **ROLEPLAY**: Enforces the 4-beat dynamic cinematic sequence (`hook` scenario establishing dilemma $\rightarrow$ `dialogue_part_2` 180° reverse OTS on P2 $\rightarrow$ `dialogue_part_3` kinetic prop action $\rightarrow$ `payoff` celebratory resolution outro). In video assembly, `dialogue_part_1` and `dialogue_part_4` automatically reuse their companion scenes with dynamic 1.25x punch-in cuts, producing 6 active visual cuts from 4 generated images with zero repetitive poses.
       - **EXPRESSION**: Rotates across 5 physical micro-zones within the environment with zero-duplicate props and active kinetic motion on the `example` scene.
       - **FUN_FACTS**: Dynamically generates 4 or 6 scenes matching the script's section structure with historical and cultural detail parity.
       - **GAME**: Generates 2D cartoon scenes for `hook`, `answer`, and `explanation` while routing `challenge` to the native chalkboard renderer and `pressure` to static language illustrations.
   - **Character Continuity & Locked Anchors (`extract_or_build_character_anchors`)**:
     - Automatically extracts or locks character traits (hair color, hairstyle, attire, 15-year-old high-school student age profile) across the entire storyboard.
     - Verifies character continuity tokens in each generated scene prompt, appending an explicit continuity clause if hair or attire tokens are omitted by the LLM.
   - **Strict Gender-Accurate Hairstyle Sanitization (`sanitize_character_hair`)**:
     - Programmatic regex and token-based enforcement preventing male characters from receiving female hairstyles (buns, bobs, ponytails, chignons, hairbands) and female characters from receiving masculine haircuts (quiffs, buzz cuts, crew cuts).
     - Guarantees short, clean-cut styling for male teens (`short textured dark hair with clean tapered sides and a neat side-part`) and stylish styling for female teens (`dark wavy hair tied in an elegant high ponytail`, `textured caramel-brown hair styled in soft shoulder-length waves`).
   - **Scenario Priority & Heteronym Domain Decoupling**:
     - Minimal pair words (e.g. `eyes`, `ice`, `wind`, `tear`) are decoupled from broad setting domains, ensuring explicit scenario keywords (e.g. *"creative modern animation studio at late night"*) take full precedence over acoustic keywords.
   - **Native FreeType Chalkboard Renderer (`core/chalkboard_renderer.py`)**:
     - Renders GAME `challenge` graphics directly onto `empty_chalkboard.png` on CPU using PIL and Segoe Print Bold chalk typography in milliseconds with zero VRAM overhead.
     - Automatically cleans option text (stripping trailing punctuation and conjunctions like `or`, `and`, `o`, `ou`, `e`).
     - Automatically masks spoken answers with `_________` in listening and acoustic challenges, ensuring the graphic never spoils the audio quiz.
   - **Harmonized Production Modes**: Supports Mass-produce (10s countdown default), Specific IDs, Group Ranges, Fun Facts only, CSV lists from `input/csv/image_to_change/`, and Ready Scripts CSV from `D:\AI\output\connectivity\ready_scripts/<date>_ready_scripts.csv` (Option `[6]`).
   - **Interactive Modifier Suite (`image_modifier.py`)**:
     - *Single Scene Recreation Mode*: Allows prompt editing, seed selection, and individual scene re-rendering.
     - *Batch / Group Recreation Mode (`modify_group_interactive`)*: Re-prompts and re-generates ALL scenes for a script simultaneously, anchored to the confirmed general prompt for total visual coherence.
     - *Dual-Character Gender Casting*: For Roleplays, interactively prompts for `PERSON_ONE` and `PERSON_TWO` genders independently, updating `speakers_gender` and persisting to the state machine.
     - *120-Second (2-Minute) Timeout*: Uses `GENDER_SELECTION_TIMEOUT = 120.0s`, providing ample time for creators to cast characters or customize prompts.
     - *Chalkboard Live Editor*: Edit quiz questions and options directly and immediately re-render 576x1024 challenge graphics on CPU.
     - *Automatic Stale Image Purge*: Automatically detects and cleans up obsolete scene images from legacy schemas.
   - **Command**: `py video_creation/_C_image_generation/main.py [--script-id <ID>] [--force] [--seed <INT>] [--auto] [--fun-facts] [--video-type <TYPE>] [--language <LANG>] [--from-csv [PATH]] [--from-ready-scripts [PATH]] [--from-mass-ready-scripts [PATH]]`

4. **`video_creation/_D_music_generation` (Standing Music Bank)**:
   - Eliminates wasteful per-script audio generation by maintaining a **Standing Music Bank** in `<OUTPUT_DIR>/bank_music/<language>/<video_type>/`.
   - Contains a curated catalog of **160 distinctly orchestrated prompts** (10 unique jams per category across 16 categories: 4 languages × 4 formats) tailored to the emotional triggers discovered across all CSV queues (e.g. Flamenco nylon guitar for Spanish, Parisian café accordion/gypsy jazz for French, Mandolin/Morricone cinematic for Italian, Rhodes neo-soul for English, ticking clock suspense for Games, marimba/bells for Fun Facts).
   - Each category directory includes `bank_catalog.json` detailing the 10 tracks, BPM, instrumentation, emotion tags, and disk status.
   - **Command**: `py video_creation/_D_music_generation/main.py [--language <LANG>] [--video-type <TYPE>] [--limit <N>] [--force] [--catalog-only]`

5. **`video_creation/_F_thumbnail_image_generation`**:
   - Generates eye-catching vertical thumbnails using ComfyUI's Flux1-dev image-to-image workflow (`video_creation/workflows/flux1_dev_uso_reference_image_gen.json`).
   - Transforms input reference models in `input/images/thumbnail_models/` to styled output thumbnails saved to `output/video_assets/<language>/<video_type>/script_<ID>/thumbnail.png`.
   - **Harmonized Production Modes**: Supports Mass-produce (10s countdown default), Specific IDs, Group Ranges, Fun Facts only, and `[5] From Ready Scripts CSV (<date>_ready_scripts.csv)` scanning `D:\AI\output\connectivity\ready_scripts`.
   - **Command**: `py video_creation/_F_thumbnail_image_generation/main.py [--script-id <ID>] [--force] [--auto] [--fun-facts] [--video-type <TYPE>] [--language <LANG>] [--from-ready-scripts [PATH]]`

6. **`video_creation/_G_video_assembly`**:
   - Transcribes the master audio with word timestamps using faster-whisper (`base` model, int8 on CPU), with lazy loading inside `Transcriber.__init__` for clean diagnostics and zero overhead when skipping transcription.
   - **Dynamic Animated Subtitles (ASS format)**: Generates high-impact Hormozi-style word-by-word animated subtitles (Yellow primary `&H0000FFFF`, Arial 60 bold, black outline, semi-transparent shadow, center-center). Automatically detects and merges consecutive tokens for hyphenated phonetic words (e.g. `re-CORD` or `re-cord` split by Whisper into `re` + `CORD`) into unified subtitle tokens with combined timestamps, preventing awkward single-syllable flashes. For GAME videos, automatically suppresses subtitles during the `challenge` scene so chalkboard options remain unobstructed.
   - **Emotion-Based Jam Selection**: Dynamically matches the script's emotional triggers (`EMOTIONAL_TRIGGER`, `emotion`, `game_type`) to the best available audio jam in `<OUTPUT_DIR>/bank_music/<language>/<video_type>/`, using deterministic script-ID hashing for consistent variety across scripts.
   - **Branding & Audio Ducking**: Overlays watermark logo (`watermark.png`, 120px, 60% opacity at bottom-right), prepends 2.0s opening card and appends 3.0s closing card with language and dialect detection, and ducks bank BGM (volume 0.05) under master speech using FFmpeg `amix`.
   - Produces the final polished `.mp4` video in `output/video_assets/<language>/<video_type>/script_<ID>/script_<ID>_final.mp4`.
   - **Fast Re-assembly**: Use `--keep-subtitles` (or `--skip-transcribe`) to reuse existing `.ass` files without re-running Whisper.
   - **Harmonized Production Modes**: Supports Mass-produce (10s countdown default), Specific IDs, Group Ranges, Fun Facts only, and `[5] From Ready Scripts CSV (<date>_ready_scripts.csv)` scanning `D:\AI\output\connectivity\ready_scripts`.
   - **Interactive Tool**: `subtitles_modifier.py` (`py tools/modifiers/subtitles_modifier.py` or `py video_creation/_G_video_assembly/subtitles_modifier.py`) allows inspecting subtitle lines/timings, finding/replacing words across `.ass` files, opening `.ass` in an editor, and re-rendering final MP4s in seconds without re-running Whisper or regenerating audio.
   - **Command**: `py video_creation/_G_video_assembly/main.py [--script-id <ID>] [--force] [--auto] [--keep-subtitles] [--fun-facts] [--video-type <TYPE>] [--language <LANG>] [--from-ready-scripts [PATH]]`

---

## Hardware Environment & Recommended Settings

- **Recommended Baseline GPU**: NVIDIA GPU with 6GB+ VRAM (e.g. RTX 2060, RTX 3060, or better).
- **ComfyUI Setup**: Path configurable via `COMFY_DIR` in `.env` (defaults to local ComfyUI installation).
  - Recommended launch arguments: `--force-fp16` for GPUs with 6GB VRAM.
- **Python Runtime**: Python 3.10+ (Windows `py` launcher or `python3`).
- **Low-VRAM (6GB) Optimizations Applied**:
  - **SenseVoice ASR Offloaded to CPU**: In `ComfyUI-Qwen3-TTS/nodes.py`, the SenseVoice ASR model runs on `cpu` (`device_str = "cpu"`), freeing ~700MB VRAM for TTS generation.
  - **fp16 Precision**: Qwen3-TTS loader precision locked to `fp16` (native Tensor Core acceleration).
  - **Stage-Boundary VRAM Reclamation**: Calls `/free` (`free_memory=True, unload_models=False`) only between generation stages via `ComfyServerPool.free_vram()` to reclaim PyTorch caching memory while preserving model weights in RAM.
  - **ComfyUI Input Folder Auto-Cleanup**: Copied reference `.wav` and `.png` files are automatically deleted after generation to avoid disk bloating.
  - **Chalkboard Typography Offload**: Eliminates heavy Flux Img2Img inference for quiz challenges, running natively on CPU in milliseconds with zero VRAM overhead.

---

## Key Files & Entry Points

| File / Folder | Role |
| :--- | :--- |
| `main/main.py` | Main orchestrator to run pipeline stages sequentially with pre-flight health verification. |
| `test/run_tests.py` | Standalone test runner for unit, integration, contract, and security test layers. |
| `main/config/` | Central configuration & health package: `config/settings.py` (paths, endpoints, voices, pauses) and `config/health.py` (centralized LLM & ComfyUI connectivity checks & assertions). |
| `main/video_creation/` | Consolidated package containing all 6 workflow generation stages (`_A` through `_G`). |
| `main/core/` | Central infrastructure package: `core/state_manager.py` (state machine & JSON state manager), `core/status_tracker.py` (cross-queue status auditor & manifest manager), `core/cli_prompt.py` (interactive 10s countdown mode prompt), `core/chalkboard_renderer.py` (high-res FreeType chalk typography & auto-masking on CPU), and canonical ID resolution. |
| `main/tools/` | Dedicated CLI utilities organized into functional subfolders & root tools: <ul><li>**`auditing/`**: `status_scraper.py` (pipeline status compiler), `json_health_checker.py` (JSON audit/repair), `scrapper_script.py` (script review exporter)</li><li>**`database/`**: `db.py` (DB & CSV manager), `sync_prompts.py` (queue sync), `reset_stage_status.py` (mass stage reset)</li><li>**`modifiers/`**: `script_modifier.py` (verbatim single, mass & ready_scripts script repair), `voice_modifier.py` (voice audition & recasting), `image_modifier.py` (single scene & batch group recreation, dual gender casting, chalkboard editor), `subtitles_modifier.py` (subtitle timing & ASS editor)</li><li>**`prompt_builders/`**: `generate_editor_prompts_csv.py` (system editor prompts generator)</li><li>**`voice_quality/`**: `build_voicedesign_references.py` (7-register VoiceDesign generator), `audit_reference_voices.py` (reference clip auditor)</li><li>**Root Tools**: `comfy.py` (headless ComfyUI supervisor), `check_script_changes.py` (script change auditor)</li></ul> |
| `main/database/` | Centralized expression tracking: `database/expressions.sample.csv` (reference schema), `database/expressions.db` (SQLite, gitignored), and auto-synced per-language CSVs (`database/<lang>_expressions.csv`: `english`, `french`, `spanish`, `italian`, gitignored). Schema: `ID,EXPRESSION,CONTEXT,VIDEO_TYPE,STATUS`. Manages master completion status (`PENDING` vs `DONE`). |
| `main/connectivity/` | Modular Google Sheets integration suite: <ul><li>**Principal Runners**: `sync_sheets.py` (Sheet sync), `fetch_corrected_scripts.py` (Column D corrections), `reconcile_scripts.py` (audit & reorganize), `post_scripts.py` (safe update/publish), `scan_ready_scripts.py` (scan ready scripts by date)</li><li>**`core/`**: `endpoints.py` (Option A master router, 16 endpoints), `client.py` (resilient HTTP client with 302 redirects & retries)</li><li>**`apps_script/`**: `google_apps_script.js`, `google_apps_script.sample.js`, `README.md` (Web App implementation for `doGet` and `doPost`)</li><li>**`sheet_sync/`**: `sync_service.py` (syncs Columns A, B, C or A:D to `D:\AI\output\connectivity\synced_sheets\`)</li><li>**`corrected_scripts/`**: `fetcher.py` (pulls Column D `SCRIPT_CHANGED` to `input/csv/script_to_change/`)</li><li>**`reconcile/`**: `service.py` (reconciles local scripts to Google Sheets order into `scripts_to_post/`)</li><li>**`post_scripts/`**: `poster.py` (posts scripts to Google Sheets with 3-col or 4-col options)</li><li>**`ready_scripts/`**: `scanner.py` (scans ready scripts, filters out video_ready, normalizes 2/4-digit dates, auto-prunes resolved undated items, groups by script_date)</li></ul> |
| `main/input/csv/` | Prompt & batch queue root: `sample_templates/` (schemas), `<lang>/expressions_list/` (prompts), `script_to_change/` (Stage A text changes), `voice_to_change/` (Stage B audio regeneration queues), `image_to_change/` (Stage C image regeneration queues). |
| `main/state/<language>/<video_type>/script_<ID>.json` | State machine artifact tracking stage status, metadata, character personalities, and asset paths using structured IDs. |
| `main/state/pipeline_status.csv` | Centralized pipeline status manifest tracking generation progress for all 1,224 video prompts across all 6 stages (`script_generation_status`, `voice_generation_status`, `image_generation_status`, `music_generation_status`, `thumbnail_generation_status`, `video_assembly_status`). |
| `main/system_prompts_editor.csv` | Per-video-type system prompts for external LLM script doctoring (EXPRESSION, ROLEPLAY, GAME, FUN_FACTS). Defines doctoring principles, word budgets, structural rules, and anti-cliché constraints for script polishing workflows. |
| `test/` | Complete QA test layer (275 tests passing): unit tests (`test/unit/`), integration tests (`test/integration/`), contract validations (`test/contracts/`), security checks (`test/security/`), connectivity tests (`test/connectivity/`), runner (`test/run_tests.py`), and pytest config (`test/pytest.ini`). |
| `output/` (configured via `OUTPUT_DIR` in `.env`) | External output location configured via `OUTPUT_DIR` in `.env` (can point to `./output` or secondary high-capacity drive like `D:\AI\output`). Contains `scripts_to_see/<lang>/<kind>/<lang>_<kind>_scripts.csv` and `video_assets/<language>/<video_type>/script_<ID>/`. |

---

## Agent Guidelines & Best Practices

1. **State Persistence**: Always read and update script states via `core/state_manager.py` (or `StateManager`). Stages must check prerequisites before executing.
2. **Audio Duration Rule**: All YouTube Shorts voiceovers must stay strictly within target durations: **38 to 48 seconds** (strictly 85–110 words) for EXPRESSION, **40 to 55 seconds** (strictly 95–125 words) for GAME, **60 to 80 seconds max** (strictly 145–180 words) for ROLEPLAY, and **40 to 60 seconds** (strictly 95–135 words) for FUN_FACTS. Never generate untrimmed pauses or uncalibrated word counts.
3. **Roleplay Voice Consistency**: In `_B_voice_generation`, ensure characters maintain their assigned reference `.wav` file and seed across all turns.
4. **Charismatic Delivery**: TTS instructions must enforce energetic, conversational pacing and authentic acting tone; avoid slow audiobook phrasing.
5. **GPU Awareness**: Be mindful of the 6GB VRAM ceiling. Heavy models should not run simultaneously; keep large models isolated or offloaded when not in use.
6. **Pipeline-Level Solutions Only (Never Manual Output Patching)**: Never manually edit generated output files (`state/<language>/<video_type>/script_<ID>.json`, audio files, images) to patch duration or formatting errors. All fixes, word limits, and normalization must be implemented directly inside the codebase, prompts, validators, and processors so the pipeline functions autonomously end-to-end.
7. **Structured Script IDs (`<Lang><Type><02d>`)**: Always adhere to canonical IDs (e.g. `FE01`, `EG01`, `SR02`). Downstream stages (`_B` through `_G`) never re-create or mutate IDs; they strictly inherit them from `state/<language>/<video_type>/script_<ID>.json`. Any new CSV prompt row without an ID must be assigned via `tools/database/sync_prompts.py` or the collision-free incremental allocator in `_A_video_scripts/main.py`.
8. **Streamlined Input Queues**: When adding new prompt rows to CSVs, keep them clean and content-focused. Never re-introduce static boilerplate columns (`TARGET_LANGUAGE`, `VIDEO_TYPE`, `STATUS`, `FORMAT`, `SPECIFIC_CONSTRAINT`); the ingestion engine automatically infers and injects them in memory for state and prompt construction.
9. **Expression Database Master Gate (User-Only 'DONE' Status)**: A centralized database (`database/expressions.db` and auto-synced per-language CSVs `database/<lang>_expressions.csv`) tracks all expressions with columns `ID, EXPRESSION, CONTEXT, VIDEO_TYPE, STATUS`. By default, expressions are `PENDING`. **Pipeline scripts NEVER mutate STATUS to DONE—only the user can set DONE**. When `STATUS` is `DONE` (case-insensitive), all 6 workflow generation stages (`_A` through `_G`) strictly skip that expression, freezing and protecting existing assets. When `STATUS` is `PENDING`, each stage respects its own state JSON (e.g. `voice_generation == 'done'`) and never overwrites or deletes already created assets unless explicitly run with `--force`.
10. **Configurable Output Storage (`OUTPUT_DIR`)**: High-capacity video assets and review scripts reside in `OUTPUT_DIR` (configured in `.env`, e.g. `./output` or secondary storage like `D:\AI\output`). This isolates bulky media files (WAV, MP4, PNG) onto designated storage. All scripts resolve paths via `config.get_script_output_dir` and `config.OUTPUT_DIR`.
11. **Prompt Queue Maintenance & Unified Synchronization (`tools/database/sync_prompts.py`)**:
    - **1-to-1 Cross-Format Alignment**: For every target language, the 3 expression formats (`EXPRESSION`, `GAME`, `ROLEPLAY`) must share identical row ordering and expression topics (sharing the same numeric index `01`..`N`, with prefixes `E`, `G`, `R`). When new expressions are added to `*_READY_PROMPTS_EXPRESSION.csv`, the corresponding `GAME` and `ROLEPLAY` CSVs must be updated with matching rows.
    - **Target-Language Content**: All `FUN_FACTS` rows (`TOPIC`, `FACT_DETAILS`, `HOOK_ANGLE`) must be written directly in the video's target language (French, Spanish, Italian, English).
    - **Automated Sync**: After making any modifications, additions, or re-indexing to prompt CSVs in `input/csv/`, always run:
      ```powershell
      py tools/database/sync_prompts.py
      ```
      This standardizes IDs, verifies 1-to-1 cross-queue alignment, syncs all records to `database/expressions.db`, and exports the companion CSVs in `database/<lang>_expressions.csv` with initial status `PENDING`.
12. **Pipeline Status Manifest & Pre-Flight Task Filtering (`state/pipeline_status.csv` & `core/status_tracker.py`)**:
    - **Centralized Manifest**: `state/pipeline_status.csv` maintains real-time status across all 1,224 prompts for all 6 stages (`script_generation_status`, `voice_generation_status`, `image_generation_status`, `music_generation_status`, `thumbnail_generation_status`, `video_assembly_status`).
    - **No Mixing of Created vs. Uncreated Scripts**: All stage entrypoints (`_A` through `_G` and root `main.py`) query `core/status_tracker.py` before executing tasks to immediately filter pending scripts. They never iterate through uncreated dummy states or mix finished and unfinished assets.
    - **Audit & Review**: Creators can run `py tools/auditing/status_scraper.py` (or `py tools/auditing/status_scraper.py --samples`) at any time to re-audit disk states and display generation progress.
    - **Mass Pipeline Stage Status Reset Tool (`tools/database/reset_stage_status.py`)**: Allows resetting any stage (`voice_generation`, `image_generation`, `video_assembly`, etc. or `all`) to `pending` across all 1,224 state files or filtered by language (`-l`), video type (`-t`), or script ID (`-id`). Automatically synchronizes `state/pipeline_status.csv` upon completion.
13. **Organic Scriptwriting & Anti-Cliché Mandate (`_A_video_scripts`)**:
    - **Organic Roleplay Dynamics & Direct-Causality Mandate**: In `ROLEPLAY`, strictly prohibit artificial bets (*"Free coffee/pizza on the line..."*, *"Bet you five bucks..."*), teacher-student tropes, phantom quote hallucinations, or infomercial payoff language (*"changes everything"*, *"game changer"*, *"level up"*). Enforce the 4-dialogue-part architecture (6 visual scenes), strict turn alternation (`PERSON_ONE` then `PERSON_TWO`), mandatory idiom trigger direction (P2 introduces expression in `DIALOGUE_PART_1`), false friend confusion direction, factual accuracy for heteronym verb forms, language purity in dialogue (no English fillers in non-English scripts), mandatory capitalized stress syllables (`REcord` vs `reCORD`), and 145–180 word budget (60–80s).
    - **5-Section Expression Micro-Story Architecture**: In `EXPRESSION`, enforce the 5 storytelling archetypes with priority guidance and 5-section narrative progression (`hook`, `setup`, `discovery`, `example`, `payoff`) strictly calibrated to 85–110 words (38–48s). Ban textbook introductions (*"Stop saying X"*, *"In this video"*), robotic drills, and infomercial payoff language in favor of authentic colloquial examples and cultural context. Enforce practical usage as the core goal, English-speaker false friend protocol, Italian double consonant phonetic accuracy, and "One Script = One Lesson" strict rule.
    - **Contextual Game Mechanics & Flexible Options**: In `GAME`, challenges must fit the specific expression naturally. Never force every challenge into a generic 4-option A/B/C/D grid; use 2 to 5 dynamic options on the chalkboard matching the 5 authorized game mechanics (Rapid Acoustic Ear, Native or Weird, What Does It Mean, Counter Reflex, Spot the Imposter). Ban repetitive canned countdown hooks (*"Native speaker trap!..."*, *"Think fast!..."*), podcast templates, abstract questions without context, and identical payoff scripts (*"takes the crown"*).
    - **Mandatory Distractor Strategy & Zero-Duplicates**: In `GAME`, all options (A, B, C, D) must be **100% unique and distinct**. Never duplicate option text. Provide 1 true native meaning, 1 humorous literal trap, and 1 plausible opposite. Binary challenges strictly provide 2 options (A vs B).
    - **Clean Contrast Pairs & Target-Language Input**: In `GAME` prompt CSVs (`*_READY_PROMPTS_GAME.csv`), the `EXPRESSION` field must strictly contain target-language contrast pairs or native expressions (e.g. `blessé vs béni`, `embarazada vs avergonzada`, `parenti vs genitori`) without foreign translations or English glosses in parentheses, preventing definition swapping and foreign language contamination.
    - **Option A Spoken Challenge Architecture**: In `GAME`, the spoken audio must NEVER contain raw blanks (`___`) or awkward pauses. The Narrator speaks the sentence out loud pronouncing the challenge word or rhythm, and explicitly speaks all options (`A: [Option A], or B: [Option B]`). The chalkboard graphic alone contains the visual blank (`___`), and word-level subtitles are suppressed during the challenge section to preserve the quiz mystery without spoiling the answer.
    - **Automated Validation Guardrails & Synthesizers (All Video Types)**: Automated checks in `_A_video_scripts/main.py` enforce per-format validation:
      - *GAME*: Spoken blank rejection, mandatory voiced options, prompt leakage suppression, duplicate option rejection, negative assertion filters (anti-podcast, anti-crown, anti-abstract, language purity), and fallback chalkboard synthesis.
      - *EXPRESSION*: Mandatory key validation (`hook`, `setup`, `discovery`, `example`, `payoff`), illegal key rejection, and 85–110 word budget enforcement with retry.
      - *ROLEPLAY*: 7-key structure validation, narrator intrusion detection in dialogue, unresolved question detection in `DIALOGUE_PART_4`, illegal key rejection, and 145–180 word budget enforcement with retry.
      - *FUN_FACTS*: Mandatory `hook`/`payoff` validation, authorized key set enforcement, and 95–135 word budget with retry.
      All formats include robotic payoff sanitization (replacing generic filler with CTA library phrases) guaranteeing production-ready scripts without manual patching.
    - **Anti-Anchoring**: When prompting LLMs, never use narrow few-shot examples that cause models to mimic specific catchphrases, food stakes, or conversational cadences across multiple languages. Rotate across diverse situational archetypes (e.g. transit announcements, smartphone texts, ear challenges, counter reflexes, imposter quizzes, and desk chats) to maintain dynamic variety across batches.
14. **Verbatim Script Ingestion & Zero-Hallucination Updates (`script_to_change/` & `script_modifier.py`)**:
    - When users supply final scripts via `input/csv/script_to_change/*.csv` (columns `ID, NEW_SCRIPT`), `parse_user_script_into_sections()` directly maps paragraphs to canonical section keys (`hook`, `setup`, `discovery`, `example`, `payoff` for Expression; `hook`, `challenge`, `pressure`, `answer`, `explanation` for Game; `hook`, `DIALOGUE_PART_1`..`4`, `PAYOFF` for Roleplay; `hook`, `setup`, `discovery`, `payoff` for Fun Facts).
    - The LLM is **strictly forbidden** from altering, rephrasing, or summarizing user-provided spoken text. Spoken sections are saved 100% verbatim into `content_metadata.script`. The LLM is utilized solely to synthesize the video title and surrounding YouTube metadata.
    - CSV readers sanitize trailing commas outside quotes and spaces after commas before quotes (`skipinitialspace=True`) to prevent multiline script truncation.
15. **Google Sheets Connectivity & Safe Column Modification (`main/connectivity/`)**:
    - **Feature 1 (`sync_sheets.py`)**: Pulls sheet records into `D:\AI\output\connectivity\synced_sheets\_3_columns\` (Columns A-C) or `_4_columns\` (Columns A-D).
    - **Feature 2 (`fetch_corrected_scripts.py`)**: Filters Column D (`SCRIPT_CHANGED`) and exports non-empty corrections directly into `main/input/csv/script_to_change/<lang>_<type>_script_to_change.csv` with schema `ID, NEW_SCRIPT`.
    - **Feature 3 (`reconcile_scripts.py`)**: Audits local scripts (`D:\AI\output\scripts_to_see`) against Google Sheets data (`synced_sheets/_3_columns`), preserves sheet order and canonical expression names, appends new local entries at end, and outputs mass-update-ready CSVs to `D:\AI\output\connectivity\scripts_to_post\`.
    - **Feature 4 (`post_scripts.py`)**: Pushes scripts from `scripts_to_post` (or `scripts_to_see` / `synced_sheets/_4_columns`) to Google Sheets. In standard mode (choice 1), affects **only Columns A, B, and C**; Column D (`SCRIPT_CHANGED`) is strictly preserved unless 4 columns mode (choice 2) is explicitly selected.
    - **Feature 5 (`scan_ready_scripts.py`)**: Scans Google Sheets for rows where Column E (`script_ready`) is checked and Column G (`video_ready`) is unchecked. Skips completed videos (`video_ready == True`). Exports grouped `ID, expression` records into daily CSV files in `D:\AI\output\connectivity\ready_scripts\<YYYY-MM-DD>_ready_scripts.csv` (or `undated_ready_scripts.csv` if date is blank).
    - **Option A Dynamic Routing**: All 16 sheets route through a master Google Apps Script Web App URL (`main/connectivity/apps_script/google_apps_script.sample.js`) with `?id=<SPREADSHEET_ID>`.
16. **Syntactic Carrier & Continuous Prosody Architecture with Kokoro-82M Hybrid Engine (`_B_voice_generation`)**:
    - **Syntactic Carrier Protocol (Ban on Fake Respellings)**: Never use artificial phonetic respellings (`PREH`, `PROH`, `prih`, `pruh`, `RECK-ord`). Instead, embed heteronyms within natural syntactic carrier frames (`a PREsent` / `to preSENT`, `a PROject` / `to proJECT`, `a REcord` / `to reCORD`). Mixed-case syllable capitalization (`PREsent` vs `preSENT`) is preserved in script state JSONs, titles, and video subtitles.
    - **Acoustic Prominence Quality Gate**: When `is_stress_pronunciation_vital()` is triggered, `_B_voice_generation/main.py` and `voice_modifier.py` sample multiple candidates (`--candidates 3`), analyze syllable RMS energy ratios and $F_0$ pitch delta using `select_best_voice_candidate()`, and select the optimal acoustic take.
    - **Kokoro-82M Pronunciation Bank Fallback**: If candidate prominence scores fall below threshold, the pipeline automatically falls back to curated 100% deterministic phonemic clips from `main/input/audio/heteronym_bank/` generated via Kokoro-82M (`kokoro_engine.py` & `pronunciation_bank.py`).
    - **Case-Preserving Subtitles**: In `_G_video_assembly/core/subtitle_builder.py`, mixed-case syllable capitalization is preserved during Hormozi all-caps rendering, ensuring viewers visually see the exact stressed syllable. Split hyphenated tokens are unified (`re-CORD`) with merged timestamps.
    - **Multilingual Diction Guidance**: For non-English pronunciation scripts, avoid English ALL-CAPS stress rules. Guide the model using native articulatory directives: Italian *dizione* (single vs double consonants `t` vs `tt`, `n` vs `nn`), Spanish *dicción* (tap `r` vs alveolar trill `rr`, pure bright vowels), and French *diction* (phrase-final tonic accent, liaison, melodic prosody).
    - **Linguistic vs. Anxiety Topic Separation**: Always distinguish between linguistic pronunciation/stress scripts and psychological or conversational topics about stress/anxiety (e.g. *"le stress des examens"*, *"gestion du stress"*), preventing false persona or style overrides on non-phonetic scripts.
    - **Language Normalization & Native Voice Allocation**: `VoiceManager` normalizes compound metadata labels (e.g. `'French | Culture | Fun Facts'`) to canonical target languages (`french`, `spanish`, `italian`, `english`). It enforces voice allocation strictly within the target language's Open-Swara voice pool (`open-swara/voices/<lang>/<gender>/`), guaranteeing non-English scripts always receive native voice references with interactive selection support in `voice_modifier.py`.
17. **Universal Multi-Character Gender Specification & Visual Staging (`_C_image_generation`)**:
    - **Zero-Ambiguity Multi-Character Mandate**: In any generated scene featuring more than one character (Roleplay dialogues, peer discussions, workplace situations), the sex of **EACH individual character MUST be explicitly specified** (e.g. *"one youthful 15-year-old teen boy and one youthful 15-year-old teen girl"*). Never use generic plurals like *"two teens"*, *"two friends"*, or *"the characters"*.
    - **4-Image Roleplay Storyboard Sequence**: In Roleplay storyboards, ban static two-shot framing and eliminate redundant images. Enforce the 4-scene sequence: `hook` (scenario establishing dilemma) $\rightarrow$ `dialogue_part_2` (180° reverse OTS on Speaker 2) $\rightarrow$ `dialogue_part_3` (kinetic prop interaction) $\rightarrow$ `payoff` (celebratory resolution two-shot). In `_G_video_assembly`, `dialogue_part_1` and `dialogue_part_4` receive dynamic 1.25x punch-in cuts framed high on character faces, delivering 6 dynamic cuts from 4 generated illustrations.
    - **Master Story World Anchor (`general_prompt`)**: Every visual sequence is anchored to a comprehensive master prompt specifying physical setting, lighting, architectural details, and locked character traits persisted to `assets.general_prompt` and `content_metadata.anchor_environment`.
    - **Locked Character Anchors & Continuity Protocol**: `extract_or_build_character_anchors()` extracts and locks distinct hairstyles, wardrobes, and facial features. Scene prompts without character continuity tokens are automatically augmented with `anchors["continuity_summary"]`.
    - **Strict Gender-Accurate Hairstyle Sanitization (`sanitize_character_hair`)**: Male characters are strictly prohibited from receiving female hairstyles (buns, bobs, ponytails, chignons, hair clips) and female characters from receiving masculine haircuts (quiffs, buzz cuts, crew cuts). Both prompt generation and post-processing enforce gender-appropriate hair directives.
    - **Scenario Priority over Acoustic Domains**: Setting resolution decouples minimal pair words from broad setting domains, ensuring explicit scenario keywords take precedence over phonetic keyword matches.
    - **Dual-Character State Persistence**: Roleplay states track explicit character genders via `speakers_gender: {"PERSON_ONE": "...", "PERSON_TWO": "..."}`.
    - **Batch Group Recreation in Modifier**: In `image_modifier.py`, creators can utilize batch group recreation (`modify_group_interactive`) to regenerate all scenes simultaneously anchored to the confirmed general prompt, with dual-character gender prompts and a 120-second (2-minute) timeout.
18. **Native FreeType Chalkboard Typography & Spoken Answer Masking (`_C_image_generation`)**:
    - **CPU Execution**: In GAME videos, `challenge` visual graphics are rendered exclusively via `core/chalkboard_renderer.py` using PIL and FreeType (Segoe Print Bold) onto `input/images/game_images/empty_chalkboard.png` in milliseconds with zero VRAM usage.
    - **Option Text Isolation (`clean_option_text`)**: All option strings are sanitized to strip trailing punctuation, commas, semicolons, and coordinating conjunctions (`or`, `and`, `o`, `ou`, `e`). Options must render clean and isolated without awkward trailing conjunctions.
    - **Automatic Spoken Answer Masking (`mask_revealed_answer_in_question`)**: For acoustic listening challenges where the spoken audio deliberately voices the target answer, the renderer detects if an option phrase appears in the question sentence and replaces it with `_________`. This guarantees the graphic presents a true blank challenge and never spoils the answer prematurely.
    - **Dynamic Scene Counts for Fun Facts**: Stage C dynamically adapts image generation to the number of sections defined in `content_metadata.script` (4 images for standard curiosity formats; 6 images for multi-fact or historical scripts), ensuring 100% visual asset coverage without missing or orphaned frames.

19. **Script Change Auditor & Automated Synchronization (`tools/check_script_changes.py`)**:
    - **Automated Column D Synchronization**: When human script modifications arrive via Column D (`SCRIPT_CHANGED`) fetched by `fetch_corrected_scripts.py`, `check_script_changes.py` performs deep normalization, diff comparison, and automated application into local State JSONs.
    - **Speaker Prefix & Formatting Normalization**: Normalizes speaker prefixes (`Narrator:`, etc.), curly quotation marks, and line structures to prevent false-positive diff reports.
    - **Zero-Duplication Parsing Fix**: In `script_modifier.py`, 4-paragraph inputs are cleanly split into distinct `setup` and `discovery` (or `challenge` and `pressure`) sections, or delegated to the LLM with strict schema constraints, strictly prohibiting sentence duplication across JSON keys.
    - **Automatic Downstream State Reset**: Applying updates automatically resets downstream generation stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `'pending'` in the script state JSON, ensuring assets are regenerated cleanly.
    - **CLI Auditing Modes**: Supports `--check-only`, `--apply`, targeting specific CSVs (`--csv <file>`), or single scripts (`--script-id <ID>`). Located at `main/tools/check_script_changes.py`.
20. **Chalkboard Thumbnail Title Sanitization & Emoji Purge (`_F_thumbnail_image_generation`)**:
    - **Language Purity & Emoji Purge on Tito's Chalkboard**: In `thumbnail_renderer.py`, `clean_thumbnail_title()` and `sanitize_thumbnail_title()` eliminate emojis, bracketed tags, and repetitive English suffix clichés (`: The Native Secret`, `: The Secret`, `: The Native Sound Trap`) on chalkboard thumbnails across all languages, ensuring clean, punchy 3–6 word titles.
    - **Expression Title Fallback**: Replaces bloated scenario text or sentence leaks with the authentic target expression title, ensuring Tito's chalkboard visual is 100% localized, uncluttered, and linguistically accurate.
21. **Senior QA Testing Layer (275 Automated Tests)**:
    - The entire pipeline is covered by 275 automated tests across 5 layers (`unit/`, `integration/`, `contracts/`, `security/`, `connectivity/`), completing in ~20 seconds with 100% pass rate.
    - Tests run completely in memory or inside isolated sandboxes with zero external network or GPU dependencies.
22. **Title & Metadata Singularity and Strict Emoji Purge (`_A_video_scripts`, `metadata_builder`, `thumbnail_renderer`)**:
    - **Zero-Emoji Mandate**: Emojis are strictly banned from all YouTube titles (`metadata.TITLE`), descriptions, and chalkboard titles (`content_metadata.script.title`). All prompt templates, LLM system instructions, and post-processing filters (`strip_emojis()`, `clean_thumbnail_title()`) enforce this across the entire lifecycle.
    - **Anti-Cliché Title Policy**: Banned generic repetition of "Native Secret" formulas (*The Native Secret*, *El Secreto de los Nativos*, *Il Segreto dei Nativi*, *Le Secret des Natifs*).
    - **Two-Tier Option B Structure**:
      - **Chalkboard Titles (`script.title`)**: Clean, standardized format indicators optimized for Tito's chalkboard graphic (headers auto-split on colon into styled top badge + large phrase):
        - *EXPRESSION*: `<Expression>` (e.g. `Break a leg`, `Costar un ojo de la cara`, `Poser un lapin`, `In bocca al lupo`).
        - *GAME*: `Quiz: <Expression>` (French: `Quiz : <Expression>`).
        - *ROLEPLAY*: `In Action: <Expression>` (Spanish: `En Acción: ...`, French: `En Action : ...`, Italian: `In Azione: ...`).
        - *FUN_FACTS*: `Origin: <Expression>` (Spanish: `Origen: ...`, French: `Origine : ...`, Italian: `Origine: ...`).
      - **YouTube Titles (`metadata.TITLE`)**: High-converting Shorts titles (45–75 chars) with uppercase hook words, tension, and distinct format archetypes:
        - *EXPRESSION*: Focuses on literal vs real meaning, social traps, and authentic usage (e.g. *BREAK A LEG | Why Actors Wish You Harm*).
        - *GAME*: Focuses on interactive ear tests and quizzes (e.g. *BREAK A LEG | Can You Guess the True Meaning?*).
        - *ROLEPLAY*: Focuses on situational stakes and dialogue blunders (e.g. *BREAK A LEG | When You Wish Disaster Before the Show*).
        - *FUN_FACTS*: Focuses on bizarre origin stories and linguistic quirks (e.g. *BREAK A LEG | The Bizarre Superstition Behind the Theater Slang*).

23. **Headless ComfyUI Supervisor & Connection Pool Pattern (`core/comfy_manager.py`, `core/comfy_pool.py`, `tools/comfy.py`)**:
    - **Zero-Terminal / Windowless Execution**: Runs ComfyUI headless via `pythonw.exe` with `CREATE_NO_WINDOW | DETACHED_PROCESS`. Totally eliminates Windows console QuickEdit mode freezes where clicking inside the terminal pauses the process.
    - **Rotating Log Directory (`main/logs/comfyui/comfyui.log`)**: All stdout and stderr output is redirected to disk with automated size-based log rotation (25MB limit), viewable on demand via `py tools/comfy.py logs` or live streaming via `py tools/comfy.py logs -f`.
    - **Persistent HTTP/WebSocket Connection Pool (`ComfyConnectionPool`)**: Eliminates socket churn by sharing a persistent `requests.Session` with keep-alive, connection pooling (`pool_connections=10`, `pool_maxsize=10`), and exponential backoff retry policies across both `_B_voice_generation` and `_C_image_generation`.
    - **VRAM Concurrency Arbiter (`vram_guard`)**: Enforces mutual exclusion between heavy Flux image diffusion and Qwen3-TTS voice generation, preventing GPU memory exhaustion and driver crashes on constrained hardware (e.g. 6GB RTX 2060).
    - **Automated VRAM Cache Cleanup**: Calls `/free` (`free_memory=True, unload_models=False`) between generation stages to reclaim PyTorch caching memory without evicting models from RAM.

24. **Little Short / Teaser Clip Generation (`video_creation/_G_video_assembly/little_short_creation.py`)**:
    - **Purpose**: Generates bite-sized video snippets (teasers / highlight shorts) from any completed script ID by slicing a specific seconds lapse (e.g. 10-16 or 4-10), prepending the brand Opening card (2s, closure card omitted), and saving directly to the script output directory (`script_<ID>_little_<start>-<end>.mp4`).
    - **Dual CLI & Interactive Workflow**: Can be executed interactively via terminal prompt (`py main/video_creation/_G_video_assembly/little_short_creation.py`) which displays script info and landmark timings, or non-interactively via flags (`--id <ID> --lapse <start-end>`).
    - **Audio Anti-Pop Fades**: Sliced clip audio applies 50ms micro-fade in/out (`afade=t=in:ss=0:d=0.05, afade=t=out:st=...:d=0.05`) to eliminate waveform click artifacts when transitioning from silence.
    - **State Asset Persistence**: Generated little shorts are recorded in the script state JSON under `assets.little_shorts["<start>-<end>"]`.
25. **Controlled Learner Pronunciation Error Simulation & Dynamic Phonetic Vowel Rewriting (`_B_voice_generation`)**:
    - **Pedagogical Purpose**: In language learning roleplays, learners frequently make controlled pronunciation mistakes (e.g., using the verb stress `/rɪˈkɔːrd/` when attempting to say the noun `REcord`, or saying `/pərˈmɪt/` for `PERmit`).
    - **Linguistic Root Cause & Neural Priors**: Neural TTS models (Qwen3-TTS) have strong language model priors. When fed standard spelling like `"a new record"`, the model prioritizes English grammar rules and pronounces the noun vowel `/ˈrɛk.ərd/` ("reh-cord") even when instructed via style prompts.
    - **Visual Casing Ground Truth**: Syllable capitalization (`reCORD`, `perMIT`, `proJECT` vs `REcord`, `PERmit`, `PROject`) is treated as the author's ground truth intent, overriding syntax in `detect_roles_in_text()`.
    - **Dynamic Phonetic Rewriting (`stress_enhancer.py`)**: When visual capitalization conflicts with syntactic context (e.g. `reCORD` in a noun slot), the system maps the target word to an explicit phonetic spelling (`ri-cord`, `per-mit`, `pri-zent`, `pruh-jekt`, `ub-jekt`) for the TTS model. This forces authentic vowel reduction (/ɪ/, /ə/) and second-syllable stress.
    - **Citation-Context Protection**: Speech/citation contexts quoting the word (e.g. *"you must say PERmit"*, *"the word is REcord"*) are detected as quotations rather than errors, preserving standard pronunciation.
    - **Acoustic Prominence Gate Inversion (`acoustic_evaluator.py`)**: The multi-take evaluator evaluates candidate takes for the intended error role (e.g., measuring `verb_ratio` for `reCORD` in noun slots) and recognizes phonetic Whisper variants (`RyCord`, `purmit`), ensuring the intended learner take wins candidate selection.
    - **Case-Preserving Visual Fidelity**: In `subtitle_builder.py` and state JSONs, visual casing (`reCORD`, `perMIT`) is preserved in subtitles and video text. Whisper transcribes phonetic takes cleanly back to the base word.
