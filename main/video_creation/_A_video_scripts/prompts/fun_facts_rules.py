FUN_FACTS_RULES = """
-----------------------------
BRANCH: FUN_FACTS (LANGUAGE DISCOVERIES)
-----------------------------
PURPOSE: Create curiosity, surprise, amusement, discovery, fascination, and "Wait, really?" reactions about language.

FUN_FACTS is an umbrella category for short, entertaining, surprising, curious, challenging, unusual, or fascinating content about languages.
It is NOT restricted to literal "fun facts". It encompasses:
- Word origins & etymology
- Language history & lost letters
- Pronunciation curiosities & silent letters
- Regional & dialect differences
- False friends & surprising comparisons
- Untranslatable concepts
- Mini language puzzles & guessing challenges
- Language myths debunked
- Language extremes & unusual records

CORE PRINCIPLE:
Do NOT ask "What should the learner study?"
Instead ask: "What about this language would make someone curious?"
Every video must pass the "Wait, What?" test: would someone who likes languages naturally think "Wait, what?" when hearing the hook?

The video is NOT a traditional classroom lesson:
ENTERTAIN -> SURPRISE -> DISCOVER (instead of EXPLAIN -> TEACH -> TEST).
The tone must feel:
- Relaxed
- Entertaining
- Conversational
- Curious
- Playful
- Surprising
- Light
- Fast

-----------------------------
FACTUAL ACCURACY (CRITICAL)
-----------------------------
Entertainment does NOT justify misinformation.
Do NOT invent:
- False word origins or folk etymologies
- Fake historical facts or events
- Made-up statistics or world records
- Absolute claims like "Nobody can pronounce..." or "This is the only language that..." unless verified.
Base the script strictly on reliable linguistic facts or the supplied FACT_DETAILS.

-----------------------------
PACING & WORD COUNTS (CRITICAL)
-----------------------------
Target duration: 40 to 60 seconds.
STRICTLY 95 to 135 spoken words total across all sections (excluding title).
Any script under 95 words or exceeding 135 words is INVALID.
- Short, punchy spoken sentences.
- Fast cadence.
- Zero academic lecture or textbook filler.
- Spoken entirely by the charismatic Narrator.

-----------------------------
AUTHORIZED SCRIPT FORMATS (CHOOSE ONE)
-----------------------------
If FORMAT is specified in the prompt parameters, follow that format. Otherwise, choose the format that best fits the topic:

FORMAT A — 3 FACTS:
Mandatory sections in JSON `script`:
- "title": Catchy, curiosity-inducing title.
- "hook": Instant curiosity trigger (e.g. "3 things you probably didn't know about French.").
- "fact_1": First surprising fact with immediate clarity.
- "fact_2": Second curiosity escalating the interest.
- "fact_3": Third, most unexpected or fascinating fact.
- "payoff": Memorable takeaway + punchy CTA closing.

FORMAT B — ONE BIG CURIOSITY:
Mandatory sections in JSON `script`:
- "title": Intriguing question or statement.
- "hook": Strong curiosity gap (e.g. "Why does English have so many silent letters?").
- "setup": The confusing or strange reality of the language.
- "discovery": The surprising historical or linguistic reason why it happened.
- "payoff": Satisfying resolution + punchy CTA closing.

FORMAT C — CHALLENGE:
Mandatory sections in JSON `script`:
- "title": Game/challenge title.
- "hook": Engaging challenge to the viewer (e.g. "Can you guess what this bizarre word means?").
- "challenge": The puzzle or mystery word presented clearly.
- "thinking_time": Quick suspenseful prompt/countdown (e.g. "Three seconds on the clock: guess now!").
- "answer": Triumphant, surprising reveal of the true meaning.
- "payoff": Fun insight on how it's used + punchy CTA closing.

FORMAT D — MYSTERY:
Mandatory sections in JSON `script`:
- "title": Mystery title.
- "hook": A linguistic paradox or weird phenomenon (e.g. "Why does this word look completely wrong?").
- "mystery": Laying out the puzzle that confuses learners.
- "clues": The hidden clue in the language's history or sound system.
- "reveal": The shocking, elegant explanation that solves the puzzle.
- "payoff": Memorable takeaway + punchy CTA closing.

FORMAT E — COMPARISON:
Mandatory sections in JSON `script`:
- "title": Comparison title.
- "hook": Direct comparison hook (e.g. "English and Spanish do this completely differently!").
- "comparison_a": How Language A handles the concept.
- "comparison_b": How Language B completely flips it on its head.
- "surprise": The unexpected insight or hilarious difference.
- "payoff": Memorable conclusion + punchy CTA closing.

FORMAT F — RANKING / LIST:
Mandatory sections in JSON `script`:
- "title": Ranking title.
- "hook": High-curiosity list hook (e.g. "3 of the strangest words in Spanish.").
- "item_3": Number 3 on the list (good curiosity).
- "item_2": Number 2 on the list (even weirder).
- "item_1": Number 1 top discovery (mind-blowing payoff).
- "payoff": Memorable takeaway + punchy CTA closing.

-----------------------------
ONE CORE PAYOFF
-----------------------------
Every video must have ONE clear, satisfying payoff. Do not pack unrelated trivia together.
The viewer should leave with one memorable discovery.
"""
