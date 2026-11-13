"""
types/game/rules.py — Authoritative, non-contradictory rules for the LINGUISTIC GAME format.
Cleanly separates visual chalkboard display specifications from TTS spoken audio narration.
"""

from __future__ import annotations

GAME_RULES = """-----------------------------
BRANCH: LINGUISTIC GAME
-----------------------------
PURPOSE: TEST the learner using a dynamic, fast-paced linguistic game.

The game must be:
- Very engaging, interactive, and grounded in authentic everyday speech.
- Solvable in approximately 3-7 seconds.
- Spoken entirely by a high-energy, charismatic NARRATOR (not a boring teacher).

-----------------------------
BAN REPETITIVE HOOKS & CLICHÉS (STRICT NEGATIVE CONSTRAINTS)
-----------------------------
STRICTLY FORBIDDEN FORMULAS (DO NOT USE):
❌ "You're listening to a native podcast..." / "Estás escuchando un podcast..." / "Tu as entendu dans un podcast..." (BANNED CLICHÉ!)
❌ "Native speaker trap! Can you spot the right pronunciation in 3 seconds?" (BANNED CLICHÉ!)
❌ "Le piège des faux-amis !" / "Trappola del madrelingua!" / "Trampa de nativos" (BANNED CLICHÉ!)
❌ "Quick, A or B? Trust your gut, three seconds!" (BANNED COUNTDOWN!)
❌ "Option [A/B] takes the crown!" (BANNED REPETITIVE FORMULA!)
❌ "Stop saying [X]!"

-----------------------------
AUDIO NARRATION VS VISUAL CHALKBOARD (CRITICAL DISTINCTION)
-----------------------------
1. SPOKEN "challenge" PROPERTY (AUDIO FOR TTS):
   ❌ NEVER put "___", "____", or raw underscores in the spoken challenge! TTS cannot pronounce underscores.
   👉 The Narrator in audio reads the complete test sentence naturally (voicing Option A or the target rhythm in place), and then explicitly announces the choices.
   👉 Natural casing: Do NOT yell or spell out all-caps syllables in spoken text. Write natural lowercase/sentence case for smooth TTS inflection.
   👉 Option formatting: Options must begin with "A: ", "B: ", "C: ", and optionally "D: ". Terminate each option with a period (.).
   👉 Provide 3 or 4 options (or 2 for binary stress contrasts).
   👉 Zero connectors between options: Clean juxtaposition ("A: [Option A].  B: [Option B].  C: [Option C]."). NEVER use "or", "and", "y", "ou", "o".

2. VISUAL "chalkboard_exercise" PROPERTY (DISPLAYED ON SCREEN):
   👉 The visual chalkboard is for the viewer's eyes!
   👉 The first line MUST be the test sentence or challenge header in TARGET_LANGUAGE.
   👉 Followed by each option on its own separate line starting with A), B), C), and optionally D):
      "chalkboard_exercise": "[Sentence with ___ in TARGET_LANGUAGE]\\nA) [Option A]\\nB) [Option B]\\nC) [Option C]\\nD) [Option D]"
   👉 For syllable stress contrasts (heteronyms), the chalkboard options retain the UPPERCASE syllable stress notation (e.g. "A) PROject\\nB) proJECT") so the visual contrast is immediately clear to the viewer.

-----------------------------
STRICT SEPARATION OF CHALLENGE AND PRESSURE
-----------------------------
❌ NEVER include countdown lines or urgency prompts inside the "challenge" property!
👉 All countdowns, time limits, and urgency lines belong strictly in the "pressure" property.

-----------------------------
PACING & WORD COUNTS (CRITICAL)
-----------------------------
Target duration: 40-55 seconds.
STRICTLY 95-135 SPOKEN WORDS total across all spoken sections (title, hook, challenge, pressure, answer, explanation).
Any script under 95 spoken words or exceeding 135 spoken words is INVALID.
- Short, punchy sentences with fast spoken cadence.
- No emojis.

-----------------------------
SCRIPT STRUCTURE (MANDATORY JSON KEYS)
-----------------------------
Your JSON `script` object MUST contain EXACTLY these 5 spoken sections (plus title):
- "title": Catchy, high-energy trivia challenge title in TARGET_LANGUAGE (3-6 words, ZERO EMOJIS).
- "hook": Immediate, high-energy trivia challenge hook setting up the dilemma (100% in TARGET_LANGUAGE).
- "challenge": Direct test sentence spoken naturally by the Narrator (NO "___" in spoken audio!) and explicitly voiced options ("A: [Option A].  B: [Option B].  C: [Option C].").
- "pressure": Fast, snappy countdown line encouraging immediate response (100% in TARGET_LANGUAGE).
- "answer": Direct reveal of the winning option (e.g. "It's A!", "¡Es la B!") with the linguistic reason. DO NOT say "takes the crown"!
- "explanation": Crisp explanation of how natives use it and real-life contrast, followed by a punchy CTA/loop.

At the root of the JSON object, include:
- "chalkboard_exercise": Multiline visual chalkboard text with challenge sentence and options A), B), C) (and optionally D).
"""

