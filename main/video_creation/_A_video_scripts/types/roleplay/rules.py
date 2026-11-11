"""
types/roleplay/rules.py — Authoritative rules for authentic real-life ROLEPLAY shorts.
Bans the polite tutor trope, mandates strict 2-speaker alternation, and sets spoken word limits.
"""

from __future__ import annotations

ROLEPLAY_RULES = """-----------------------------
BRANCH: ROLEPLAY
-----------------------------
PURPOSE: USE previously learned language in an authentic, entertaining real-life situation.

The role-play should feel like a real slice of life between two genuine human beings — NEVER a dull classroom grammar lesson.

-----------------------------
BAN THE "POLITE TUTOR" & "COFFEE BET" TROPES (ZERO TOLERANCE)
-----------------------------
STRICTLY FORBIDDEN PATTERNS & BANNED FORMULAS:
❌ BANNED BET HOOKS: "Free [coffee/pizza/latte/takeout] on the line..." / "Bet you five bucks..." / "Apuesta: si no sabes..." / "Scommetto che non riesci..."
❌ BANNED TUTOR SEQUENCE:
   `Person 1 makes mistake -> Person 2 corrects like a smug teacher -> Person 1 asks "Wait, but why?" -> Person 2 gives dictionary definition -> Person 1 says "Oh! Now I get it!"`
❌ BANNED CLICHÉ LINES:
   - "Did you just say [X]? That sounds totally wrong!"
   - "I was stressing the wrong syllable because..."
   - "Wait, which one do we actually use?"
   - "Now you sound like a true native!" / "Maintenant tu es un vrai pro !" / "Ora sai come suonare davvero come un italiano !"
❌ BANNED PAYOFF SUMMARY:
   - DO NOT start the payoff with: "Remember: X is the noun, Y is the verb." or "Recuerda: X es..., Y es..."
   - Instead, let the Narrator deliver a punchy, humorous observation about human communication + the CTA.

❌ BANNED HOOK FORMULAS (NARRATOR OPENER — ZERO TOLERANCE):
   The following opening patterns are STRICTLY FORBIDDEN for the "hook" field:
   - "Stop messing up [X]!" / "Stop making this mistake!" / "Stop saying [X]!"
   - "This one word confusion will cost you [X]" / "This mistake can cost you"
   - "Ever mess up [X] in a meeting?" as a standalone question hook
   - Any hook that is a WARNING, THREAT, or SCOLDING instead of a SCENE or MYSTERY.

Characters are NOT student and teacher! They are real peers, friends, travel buddies, coworkers, siblings, or roommates talking naturally.

-----------------------------
SPEAKER ASSIGNMENTS & ROLES (EXACTLY 3 VOICES)
-----------------------------
In a ROLEPLAY video, there are EXACTLY THREE voices, each with a strict, non-overlapping role:

1. NARRATOR:
   - The NARRATOR speaks EXCLUSIVELY in the "hook" and "PAYOFF" sections.
   - The NARRATOR is STRICTLY FORBIDDEN from speaking inside any DIALOGUE_PART.
   - NEVER put a "NARRATOR:" speaker tag inside any dialogue section!

2. PERSON_ONE & PERSON_TWO (STRICT ALTERNATING SEQUENCE IN EVERY PART):
   - Every single dialogue section (DIALOGUE_PART_1 through DIALOGUE_PART_4) MUST contain
     EXACTLY TWO TURNS in this precise order:
     Turn 1: PERSON_ONE (Acting Emotion): Line...
     Turn 2: PERSON_TWO (Acting Emotion): Line...
   - DO NOT make any part a single-character monologue! Both characters MUST speak in EVERY part.
   - Separate the two turns with a newline (\\n).

-----------------------------
ACTING EMOTIONS (BE EXPRESSIVE)
-----------------------------
Use rich, diverse acting tags for both speakers:
(Teasing), (Skeptical), (Deadpan), (Shocked), (Baffled), (Smirking), (Determined), (Chuckling), (Impatient), (Conspiratorial), (Relieved), (Hilarious).

LINE BREAKS:
You MUST insert a newline character (\\n) before every speaker tag so that each turn is on its own line:
"DIALOGUE_PART_1": "PERSON_ONE (Nervous): My audition starts in five minutes and I'm sweating buckets!\\nPERSON_TWO (Teasing): Take a breath! You've got this, so go out there and break a leg!"

-----------------------------
LANGUAGE PURITY IN DIALOGUE (STRICT — ALL LANGUAGES):
-----------------------------
- ALL text inside DIALOGUE_PART_1 through DIALOGUE_PART_4 must be 100% in TARGET_LANGUAGE.
- Foreign words — including English fillers used inside non-English scripts — are STRICTLY FORBIDDEN inside dialogue sections.
- The NARRATOR hook and PAYOFF are also 100% in TARGET_LANGUAGE with zero foreign insertions.

-----------------------------
MANDATORY JSON STRUCTURE:
-----------------------------
The "script" object for ROLEPLAY MUST contain EXACTLY these 7 keys:
1. "title": Catchy, short situational scene title in TARGET_LANGUAGE (3-6 words, ZERO EMOJIS).
2. "hook": Spoken by NARRATOR (15-20 words). High-energy setup (100% in TARGET_LANGUAGE).
3. "DIALOGUE_PART_1": Spoken by PERSON_ONE then PERSON_TWO. Both lines separated by \\n.
4. "DIALOGUE_PART_2": Spoken by PERSON_ONE then PERSON_TWO. Reaction to trigger. Both lines separated by \\n.
5. "DIALOGUE_PART_3": Spoken by PERSON_ONE then PERSON_TWO. Playful nuance demo. Both lines separated by \\n.
6. "DIALOGUE_PART_4": Spoken by PERSON_ONE then PERSON_TWO. Comedic resolution & punchline. Both lines separated by \\n.
7. "PAYOFF": Spoken by NARRATOR (20-25 words). Energetic takeaway and mandatory CTA line.

TOTAL SPOKEN WORD BUDGET (CRITICAL):
Strictly 145-180 spoken words total across all 6 spoken sections.
Word count is measured purely on the spoken dialogue (excluding character labels and parenthetical emotion cues).
"""

