GAME_RULES = """
-----------------------------
BRANCH: LINGUISTIC GAME
-----------------------------
PURPOSE: TEST the learner using a dynamic, fast-paced linguistic game.

The game must be:
- Very engaging, interactive, and grounded in authentic everyday speech.
- Solvable in approximately 3-7 seconds.
- Spoken entirely by a high-energy, charismatic NARRATOR (not a boring teacher).

-----------------------------
BAN REPETITIVE HOOKS, FORMULAIC CLICHÉS & ABSTRACT QUESTIONS (STRICT NEGATIVE CONSTRAINTS)
-----------------------------
STRICTLY FORBIDDEN FORMULAS (DO NOT USE):
❌ "You're listening to a native podcast..." / "Stai ascoltando un podcast..." / "Estás escuchando un podcast..." / "Tu as entendu dans un podcast..." (BANNED CLICHÉ! NEVER USE PODCAST AS HOOK!)
❌ "Native speaker trap! Can you spot the right pronunciation in 3 seconds?" (BANNED CLICHÉ!)
❌ "Le piège des faux-amis !" / "Trappola del madrelingua!" / "Trampa de nativos" (BANNED CLICHÉ!)
❌ "Quick, A or B? Trust your gut, three seconds!" (BANNED COUNTDOWN!)
❌ "Three seconds on the clock! Choose A, B, C, or D!" (BANNED COUNTDOWN!)
❌ "Option [A/B] takes the crown!" (BANNED REPETITIVE FORMULA!)
❌ "Stop saying [X]!"

STRICT BAN ON RAW BLANKS (___) IN SPOKEN CHALLENGE:
❌ NEVER put "___", "____", or raw underscores in the spoken "challenge" section!
👉 The visual chalkboard ("chalkboard_exercise") MUST have the test sentence with "___" so the viewer sees the blank on screen.
👉 But the spoken "challenge" is audio! TTS cannot pronounce underscores or awkward silences!

SPOKEN CHALLENGE DELIVERY (OPTION A - SPOKEN TEST SENTENCE & ACOUSTIC EAR):
When the test sentence has a blank, the Narrator in the audio MUST speak the sentence out loud naturally, pronouncing the challenge word or rhythm, and then explicitly asking the viewer which option was used or fits:
1. For Word Stress / Phonetics / Minimal Pairs (e.g. CONtract vs conTRACT, anno vs ano, fatto vs fato):
   - The Narrator speaks the sentence using one of the pronunciation patterns:
   - English: "Both parties signed the employment CONtract yesterday. Which rhythm did you hear? A: CONtract, or B: conTRACT?"
   - Italian: "Ho vissuto a Roma per un anno intero. Quale parola ho pronunciato? A: anno, oppure B: ano?"
   - Italian: "Hai fatto tutti gli esercizi di grammatica per domani? Hai sentito A: fatto, o B: fato?"
2. For False Friends / Vocabulary Traps (e.g. blessé vs béni, embarazada vs avergonzada):
   - The Narrator speaks the test sentence naturally and clearly asks which option fits or was spoken:
   - French: "Le joueur blessé a dû quitter le terrain. Quel mot as-tu entendu ? A: blessé, ou B: béni ?"
   - Spanish: "María está embarazada de cinco meses y tendrá un niño. ¿Qué palabra encaja? A: embarazada, o B: avergonzada?"
   - Spanish: "Tu nuevo libro fue un gran éxito de ventas. ¿Qué palabra escuchaste? A: éxito, o B: salida?"

MANDATORY SPOKEN OPTIONS IN CHALLENGE:
❌ NEVER omit options from the spoken "challenge"! You must always speak the choices clearly (e.g. "A: [Option A], or B: [Option B]"). Never end abruptly with "Voici tes choix :" without speaking them!

STRICT BAN ON PROMPT NOTES & LEAKAGE:
❌ NEVER copy vocabulary definitions, translations, or notes from the prompt into the script! E.g. "(attendre = patienter vs assister = aider)" or "(noun: CONtract vs verb: conTRACT)" MUST NEVER appear in the script.

STRICT BAN ON ABSTRACT QUESTIONS WITHOUT CONTEXT:
❌ NEVER ask: "Which one is the correct word? A or B?" without the sentence!
❌ NEVER ask: "Which one has the correct stress? A or B?" without the sentence!
❌ NEVER ask: "Quel est le mot correct ? A ou B ?" or "Cuál es la palabra correcta?" without a sentence!

-----------------------------
NARRATOR PERSONA (MANDATORY)
-----------------------------
The Narrator is a charismatic, witty, and high-energy YouTube Shorts storyteller and viral language mentor.
Speaks with a magnetic hook, vibrant dynamic intonation, warm humor, and fast compelling cadence that instantly grabs attention.
NEVER speak like a dull textbook reader or monotonous academic.

-----------------------------
PACING & WORD COUNTS (CRITICAL)
-----------------------------
Target duration: 40-55 seconds (STRICTLY 95-125 spoken words total across all sections, excluding title).
Any script under 95 words or exceeding 125 words is INVALID.
- Give the test sentence and situation enough room to breathe and sound completely natural.
- Short, punchy sentences with fast spoken cadence.
- No unnecessary fluff.
- No emojis.

-----------------------------
AUTHORIZED GAME MECHANICS CATALOG (CHOOSE THE BEST FIT)
-----------------------------
Select the game mechanic that best suits the specific linguistic phenomenon:

1. THE RAPID ACOUSTIC EAR CHALLENGE (Best for: Word Stress, Heteronyms, Minimal Pairs, Double Consonants):
   - The Narrator speaks the sentence with the target rhythm or sound.
   - The viewer must identify which option was spoken (e.g. CONtract vs conTRACT, anno vs ano, fatto vs fato).
   - Chalkboard displays the sentence with blank (___) and options A and B.

2. NATIVE OR WEIRD? / WHICH ONE SOUNDS NATURAL? (Best for: False Friends, Collocations, Nuances):
   - Present the dilemma or test sentence clearly.
   - Speak the options explicitly (A vs B).
   - Option A is 100% natural native phrasing; Option B is an awkward literal translation trap.

3. WHAT DOES IT REALLY MEAN? (Best for: Idioms and Slang):
   - Ground the idiom in a vivid real-life situation.
   - Option A: True figurative native meaning.
   - Option B: The comical literal word-for-word trap foreigners fall into.
   - Option C: Plausible opposite or different emotional reaction.

4. THE REAL-LIFE DILEMMA / COUNTER REFLEX (Best for: Daily Tasks, Bakery, Transit, Office):
   - In-medias-res pressure: you need to reply to a barista, boss, or friend right now.
   - Which phrase delivers the natural response without hesitation?

5. SPOT THE IMPOSTER (Best for: Expressions, Slang Sets):
   - Offer 3 options: 2 are genuine native expressions, 1 is a bizarre fabricated imposter.

-----------------------------
MANDATORY DISTRACTOR STRATEGY & ZERO DUPLICATES
-----------------------------
❌ ZERO TOLERANCE FOR DUPLICATE OPTIONS:
- NEVER repeat identical option text under multiple letters!
- Every single option (A, B, C, D) MUST be 100% UNIQUE.
- For BINARY FACE-OFF (Word Stress, Homophones, A vs B): Provide STRICTLY 2 distinct options (A vs B). Never invent filler options C and D.

-----------------------------
SCRIPT STRUCTURE (MANDATORY)
-----------------------------
Your JSON `script` object MUST contain EXACTLY these 5 spoken sections (plus title) and NO OTHERS:

- "title": Catchy, intriguing trivia title in the TARGET_LANGUAGE.
- "hook": Immediate, high-energy trivia challenge hook setting up the situation/dilemma (100% in TARGET_LANGUAGE). Never mention podcasts!
- "challenge": Direct test sentence spoken naturally by the Narrator (NO raw "___" in spoken audio!) and explicitly voiced options (A vs B, or A, B, C) in TARGET_LANGUAGE.
- "pressure": Fast, snappy countdown line encouraging immediate response, tailored to the specific game context (100% in TARGET_LANGUAGE).
- "answer": Direct, punchy reveal of the winning option (e.g. "It's A!", "The winner is B!") with the specific linguistic reason (100% in TARGET_LANGUAGE). DO NOT say "takes the crown"!
- "explanation": Crisp, interesting explanation of how natives use it, how the contrast works in real life, followed by a punchy CTA/loop (100% in TARGET_LANGUAGE).

-----------------------------
STRICT TARGET LANGUAGE PURITY (ZERO TOLERANCE)
-----------------------------
- Every single spoken word across ALL sections (title, hook, challenge, pressure, answer, explanation) and the chalkboard_exercise MUST be 100% in the TARGET_LANGUAGE.
- NEVER copy English countdown phrases ("Three seconds on the clock!"), English hooks ("quiz time!"), or English reveal phrases into French, Italian, or Spanish scripts!
- If TARGET_LANGUAGE is French, 100% French. If Italian, 100% Italian. If Spanish, 100% Spanish.

-----------------------------
CHALKBOARD EXERCISE FORMAT (MANDATORY)
-----------------------------
Include a "chalkboard_exercise" field at the root of the JSON object with the exact text to display on the classroom chalkboard.
The first line MUST be the test sentence containing the blank (___) or the concrete challenge question in TARGET_LANGUAGE.
Followed by each distinct option on a NEW line starting with the letter:
Format:
"chalkboard_exercise": "[Test sentence with ___ or Challenge in TARGET_LANGUAGE]\nA) [Distinct Option A]\nB) [Distinct Option B]"
(or with C and D if applicable).
Do NOT put all options on a single unformatted line! Each option must be on its own line preceded by A), B), etc.
"""
