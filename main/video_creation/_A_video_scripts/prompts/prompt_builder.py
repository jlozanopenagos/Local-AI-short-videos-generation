import csv
import random
import re
from pathlib import Path

from .common_rules import COMMON_CONTENT_RULES
from .expression_rules import EXPRESSION_RULES
from .game_rules import GAME_RULES
from .roleplay_rules import ROLEPLAY_RULES
from .fun_facts_rules import FUN_FACTS_RULES

def load_call_to_actions(language: str = None) -> list[str]:
    # Support input/csv/<language>/game_call_to_action_phrases/CALL_TO_ACTIONS.csv
    root_dir = Path(__file__).resolve().parents[3]
    input_dir = root_dir / "input"
    input_csv_dir = input_dir / "csv"
    
    cta_files = []
    if language:
        lang_lower = language.lower()
        if input_csv_dir.exists():
            lang_cta_dir = input_csv_dir / lang_lower / "game_call_to_action_phrases"
            if lang_cta_dir.exists():
                cta_files.extend(sorted(lang_cta_dir.glob("*.csv")))
        # Fallback to legacy input/<language>/...
        if not cta_files and input_dir.exists():
            lang_cta_dir = input_dir / lang_lower / "game_call_to_action_phrases"
            if lang_cta_dir.exists():
                cta_files.extend(sorted(lang_cta_dir.glob("*.csv")))

    # Search all language CTA folders if not language-specific or not found
    if not cta_files:
        if input_csv_dir.exists():
            cta_files.extend(sorted(input_csv_dir.glob("*/game_call_to_action_phrases/*.csv")))
        if not cta_files and input_dir.exists():
            cta_files.extend(sorted(input_dir.glob("*/game_call_to_action_phrases/*.csv")))
            if not cta_files:
                root_cta = input_dir / "CALL_TO_ACTIONS.csv"
                if root_cta.exists():
                    cta_files.append(root_cta)

    if not cta_files:
        legacy_cta = Path(__file__).parent.parent / "data" / "CALL_TO_ACTIONS.csv"
        if legacy_cta.exists():
            cta_files.append(legacy_cta)

    ctas = []
    for cta_file in cta_files:
        with cta_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cta = row.get("CALL_TO_ACTION", "").strip()
                if cta and cta not in ctas:
                    ctas.append(cta)
    return ctas

def validate_params(params: dict):
    """
    Ensure required parameters exist before sending to the LLM based on VIDEO_TYPE.
    """
    video_type = params.get("VIDEO_TYPE")
    if not video_type:
        raise ValueError("Missing required field: VIDEO_TYPE")

    required_common = ["TARGET_LANGUAGE"]
    for field in required_common:
        if not params.get(field):
            raise ValueError(f"Missing required field: {field}")

    if video_type == "EXPRESSION":
        required = ["EXPRESSION", "CONTEXT", "ANGLE"]
    elif video_type == "GAME":
        required = ["EXPRESSION"]
    elif video_type == "ROLEPLAY":
        required = ["ROLEPLAY_SCENARIO"]
    elif video_type in ["FUN_FACTS", "FUNFACTS"]:
        required = ["TOPIC"]
    else:
        raise ValueError(f"Unknown VIDEO_TYPE: {video_type}")

    for field in required:
        if not params.get(field):
            raise ValueError(f"Missing required field for {video_type}: {field}")

    return params

def build_prompt(params: dict) -> str:
    params = validate_params(params)
    video_type = params.get("VIDEO_TYPE")

    if video_type == "EXPRESSION":
        branch_rules = EXPRESSION_RULES
    elif video_type == "GAME":
        branch_rules = GAME_RULES
    elif video_type == "ROLEPLAY":
        branch_rules = ROLEPLAY_RULES
    elif video_type in ["FUN_FACTS", "FUNFACTS"]:
        branch_rules = FUN_FACTS_RULES

    effective_params = dict(params)
    extra_instructions = []

    if video_type == "ROLEPLAY":
        scenario = str(effective_params.get("ROLEPLAY_SCENARIO", ""))
        script_id = str(params.get("ID", ""))

        # Check for repetitive office meeting template:
        # e.g.: In an office meeting: PERSON_ONE mispronounces 'record' by stressing the wrong syllable, and PERSON_TWO playfully demonstrates how 'REcord' differs from 'reCORD'.
        office_match = re.search(
            r"In an office meeting:\s*PERSON_ONE mispronounces\s*'([^']+)'\s*by stressing the wrong syllable,\s*and PERSON_TWO playfully demonstrates how\s*'([^']+)'\s*differs from\s*'([^']+)'",
            scenario,
            re.IGNORECASE,
        )

        templates = [
            (
                "An airport departure gate while waiting for boarding",
                "Two travel buddies reacting to a confusing gate announcement and clarifying '{noun}' vs '{verb}' before boarding.",
                "Airport Travel Banter",
            ),
            (
                "A bustling street market or food truck festival",
                "Two friends exploring food stalls, discussing a menu item and bantering about '{noun}' vs '{verb}'.",
                "Street Market Banter",
            ),
            (
                "A shared living room assembling flat-pack furniture",
                "Roommates reading assembly instructions out loud and stumbling over '{noun}' vs '{verb}' while holding a shelf.",
                "Roommate DIY Comedy",
            ),
            (
                "A local train or metro commute across the city",
                "Two friends checking a message on their phone and having a quick, witty exchange about '{noun}' vs '{verb}'.",
                "Commute Banter",
            ),
            (
                "A neighborhood gym or running track during a breather",
                "Workout partners taking a break, joking about how a word completely changes meaning depending on how you say it.",
                "Workout Break Banter",
            ),
            (
                "A relaxed park bench walking a dog on a sunny afternoon",
                "Friends chatting casually, one recounting an awkward moment they had yesterday with '{noun}' vs '{verb}'.",
                "Park Anecdote",
            ),
            (
                "A thrift shop or vintage clothing store",
                "Two friends inspecting a vintage jacket and playfully disagreeing over the exact term for the item.",
                "Shopping Banter",
            ),
            (
                "A music rehearsal room or creator studio",
                "Bandmates or co-hosts taking a sound check and laughing over an acoustic word distinction.",
                "Studio Banter",
            ),
            (
                "A sunny café terrace watching the street",
                "Two peers enjoying a drink, having a funny, observant chat about how people speak.",
                "Café Observation",
            ),
            (
                "A kitchen preparing a weekend brunch together",
                "Friends cooking, one mentioning a funny phrase they heard and both laughing at the nuance.",
                "Kitchen Cooking Banter",
            ),
        ]

        # Deterministically cycle through templates based on script ID digits to guarantee adjacent scripts differ
        id_digits = re.findall(r"\d+", script_id)
        idx = int(id_digits[0]) % len(templates) if id_digits else random.randint(0, len(templates) - 1)
        chosen_setting, chosen_dynamic, archetype_name = templates[idx]

        # Change G: ALWAYS inject the chosen setting for every roleplay script (unconditional).
        # Previously gated behind office_match — this caused most non-office scripts to receive no setting override.
        if office_match:
            word = office_match.group(1)
            noun = office_match.group(2)
            verb = office_match.group(3)
            new_dynamic = chosen_dynamic.format(word=word, noun=noun, verb=verb)
            effective_params["ROLEPLAY_SCENARIO"] = f"Setting: {chosen_setting}. Dynamic: {new_dynamic} (Archetype: {archetype_name})."
        else:
            # Append the assigned setting hint to the existing scenario without overwriting it
            existing_scenario = effective_params.get("ROLEPLAY_SCENARIO", "")
            effective_params["ROLEPLAY_SCENARIO"] = (
                f"{existing_scenario}\n[ASSIGNED SCENE SETTING: {chosen_setting} — Archetype: {archetype_name}]"
            )

        # Detect if scenario has stress shift or minimal pair
        is_stress_pair = bool(re.search(r"([A-Z]{2,}[a-z]+|[a-z]+[A-Z]{2,})", str(scenario))) or any(
            term in str(scenario).lower() for term in ["stress", "syllable", "pronounce", "heteronym", "minimal pair", "doppia consonante"]
        )
        stress_inst = ""
        if is_stress_pair:
            stress_inst = """- MANDATORY WORD STRESS & ACOUSTIC CONTRAST (CRITICAL):
  * Retain UPPERCASE syllable capitalization in the dialogue (e.g. 'REcord' for noun vs 'reCORD' for verb, or 'PERmit' vs 'perMIT')!
  * In DIALOGUE_PART_1: PERSON_ONE uses the word or makes the pronunciation/stress slip.
  * In DIALOGUE_PART_2: PERSON_TWO catches the exact acoustic stress shift (e.g. "Wait, did you say REcord or reCORD?").
  * In DIALOGUE_PART_3: Both characters clearly demonstrate the two sounds with relatable banter.
  * In DIALOGUE_PART_4: PERSON_ONE has the humorous breakthrough and PERSON_TWO drops the punchline."""

        # ---------------------------------------------------------------
        # SPECIAL TREATMENT: idiomatic arc (Error #4 fix — usage modeling)
        # ---------------------------------------------------------------
        special_treatment = str(effective_params.get("SPECIAL_TREATMENT", "")).strip().lower()
        idiomatic_arc_inst = ""
        if special_treatment == "idiomatic":
            idiomatic_arc_inst = """
-----------------------------
SPECIAL TREATMENT: IDIOMATIC EXPRESSION — MANDATORY ARC (READ CAREFULLY)
-----------------------------
This roleplay teaches a FIXED, NON-COMPOSITIONAL IDIOM whose meaning cannot be guessed
from its individual words (e.g. 'break a leg', 'costar un ojo de la cara', 'poser un lapin',
'C'est pas la mer à boire'). The pedagogical arc is DIFFERENT from a phonetic lesson.

MANDATORY 4-PART IDIOMATIC ARC:
- DIALOGUE_PART_1 (Premise & Trigger):
  * PERSON_ONE sets the scene (their problem, anxiety, or situation).
  * PERSON_TWO drops the COMPLETE idiom in FULL IDIOMATIC FORM — never truncate it.
    ❌ WRONG: 'eso te va a costar un ojo' / 'c'est la mer à boire'
    ✅ RIGHT:  'eso te va a costar un ojo de la cara' / 'c'est pas la mer à boire'

- DIALOGUE_PART_2 (Literal Image Reaction — The Comic Engine):
  * PERSON_ONE reacts with GENUINE SURPRISE to the LITERAL IMAGE of the idiom
    (the rabbit, the eye, the sea, the leg). This comic confusion is the hook.
  * PERSON_TWO gives EXACTLY ONE SHORT SENTENCE of real meaning — then moves on.
    ❌ BANNED: Multi-sentence dictionary explanations ('Es una expresión. Significa que X.
      Se usa cuando Y. En España también dicen Z.')
    ✅ RIGHT: 'Significa que es carísimo, nada más.' — one sentence, done.

- DIALOGUE_PART_3 (Usage Modeling — NEW Example in the Wild):
  * PERSON_TWO uses the COMPLETE idiom in a BRAND NEW real-life sentence
    (a different situation from DIALOGUE_PART_1 — new context, same idiom).
  * PERSON_ONE attempts their own usage or testing in a new context.
    ❌ BANNED: Continuing to ask 'So it means X?' or 'Is it used when Y?'
    ✅ RIGHT: P2 says 'El restaurante del centro me costó un ojo de la cara.',
             P1 tests: 'Entonces si invitamos a diez personas…'

- DIALOGUE_PART_4 (THE USAGE BREAKTHROUGH — CRITICAL QUALITY GATE):
  * PERSON_ONE MUST use the COMPLETE FULL IDIOM in an ORIGINAL, NEW SENTENCE of their own.
    This is the equivalent of the EXPRESSION format's 'example' key — the proof of learning.
  * PERSON_ONE's line is NOT a question, NOT a meta-comment, NOT 'Oh so it means X!'.
    It IS a spontaneous, natural use of the idiom in a new situation.
    ❌ BANNED P1 lines: 'Ya sé qué significa.' / '¡Ahora lo entiendo!' / '¿O sea que es muy caro?'
    ✅ REQUIRED P1 lines: 'Si invito a toda la familia a cenar fuera, me va a costar un ojo de la cara.'
  * PERSON_TWO reacts with humor, surprise, or a sharp punchline to P1's successful usage.

BANNED IN ALL IDIOMATIC ROLEPLAYS (ZERO TOLERANCE):
❌ P2 giving more than 1 sentence of definition/explanation in DIALOGUE_PART_2.
❌ DIALOGUE_PART_3 continuing the explanation instead of modeling new usage.
❌ P1 ending DIALOGUE_PART_4 with a question or a nodding confirmation instead of active usage.
❌ Using a shortened/truncated form of the idiom anywhere in the dialogue.
"""

        extra_instructions.append(f"""
-----------------------------
MANDATORY ROLEPLAY DIVERSITY & ANTI-CLICHE RULES (60-80s RUNTIME):
-----------------------------
- Assigned Scene Setting: {chosen_setting}
- Archetype Style: {archetype_name}
- MANDATORY 4 DIALOGUE PARTS & 7 KEYS:
  * "script" MUST contain EXACTLY 7 keys: "title", "hook", "DIALOGUE_PART_1", "DIALOGUE_PART_2", "DIALOGUE_PART_3", "DIALOGUE_PART_4", "PAYOFF".
  * TOTAL WORD BUDGET: Strictly 145 to 180 words across all 6 spoken sections.
- STRICT CONVERSATIONAL CAUSALITY & ALTERNATING TURNS:
  * In every DIALOGUE_PART, the order is STRICTLY PERSON_ONE first, then PERSON_TWO.
  * The target idiom or key phonetic word MUST be explicitly spoken in DIALOGUE_PART_1 BY PERSON_TWO reacting to P1's situation!
  * PERSON_ONE must NEVER open DIALOGUE_PART_1 by using the target expression about themselves.
  * ZERO hallucinated quotes: A character must NEVER say "Wait, you said X" unless the other character literally said X in the preceding turn.
{stress_inst}
{idiomatic_arc_inst}
- ZERO TOLERANCE FOR BETS & TUTOR TROPES:
  * DO NOT start with "Free [coffee/food/pizza] on the line..." or "Bet you [X] bucks..."!
  * DO NOT make characters act like a polite teacher and confused student!
  * Characters must speak like realistic, witty friends or peers sharing an authentic moment.
- BANNED HOOK OPENERS (narrator "hook" field):
  * "Stop messing up [X]!" / "Stop making this mistake!"
  * "This mistake will cost you..." / "This confusion can cost you..."
  * "Attention !" / "Attention à ce mot !" as the entire hook (French)
  * "Tu utilises [X] et tu te trompes !" (French)
  * Any hook that is a WARNING or SCOLDING. Hook must be scene-specific: a moment, an absurdity, a mystery.
- BANNED PAYOFF VOCABULARY (infomercial language — strictly forbidden):
  * "changes everything" / "game changer" / "sounds like a pro" / "speak like a native"
  * "the ultimate" / "unlock" / "level up" / "instantly boost your confidence"
  * "master this" as a payoff opener / "clarity is power" / "one new phrase unlocked"
  * "go get that promotion" / "you belong in the boardroom"
  * PAYOFF must be a SHORT, SPECIFIC human observation about the scene just witnessed. NOT an ad.
""")

    # Build the param string dynamically (excluding internal/redundant fields)
    # SPECIAL_TREATMENT is excluded from the param_str — it has already been consumed by
    # the prompt builder above to inject type-specific arc instructions. Sending it raw
    # to the LLM as a data field adds noise without pedagogical value.
    ignored_keys = {"ID", "STATUS", "SPECIAL_TREATMENT"}
    if video_type not in ["FUN_FACTS", "FUNFACTS"]:
        ignored_keys.add("FORMAT")
    param_str = "\n".join([f"{k}: {v}" for k, v in effective_params.items() if v and k not in ignored_keys])

    target_lang = params.get("TARGET_LANGUAGE")
    ctas = load_call_to_actions(target_lang)
    if ctas:
        chosen_cta = random.choice(ctas)
        cta_instruction = f"""
-----------------------------
MANDATORY PAYOFF CLOSING LINE:
-----------------------------
The VERY LAST sentence of your "PAYOFF" section MUST be EXACTLY:
"{chosen_cta}"
Do NOT write generic robotic phrases like "Follow for more essential idioms and comments below!". 
You MUST finish the payoff with this exact closing sentence.
"""
    else:
        cta_instruction = ""

    # False friends / cross-language guardrail
    param_text_all = " ".join(str(v) for v in params.values()).lower()
    if any(k in param_text_all for k in ["falso amico", "falsi amici", "false friend", "faux ami", "faux-ami", "amigo falso"]):
        false_friends_guard = f"""
-----------------------------
CRITICAL: FALSE FRIENDS / LINGUISTIC TRAPS INSTRUCTION
-----------------------------
This lesson addresses a FALSE FRIEND or confusing word comparison.
- The learner is studying {target_lang.upper()}.
- You MUST write the entire video, narration, trivia question, choices, and explanations 100% in {target_lang.upper()}.
- Teach the meaning of the {target_lang.upper()} word in {target_lang.upper()}.
- Do NOT insert foreign language sentences into the spoken script.
- However, when exposing an English false friend trap (e.g. 'embarrassed', 'exit', 'blessed', 'parents', 'money'), you MUST explicitly mention the English trap word in quotation marks to show the exact point of confusion, while keeping the rest of the sentence and explanation 100% in {target_lang.upper()}.
"""
    else:
        false_friends_guard = ""

    if video_type == "GAME":
        expr = str(params.get("EXPRESSION", ""))
        context = str(params.get("CONTEXT", ""))
        pillar = str(params.get("PILLAR", ""))
        script_id = str(params.get("ID", ""))
        combined_text = f"{expr} {context} {pillar}".lower()

        id_digits = re.findall(r"\d+", script_id)
        sid_num = int(id_digits[0]) if id_digits else 0

        game_archetypes = [
            (
                "THE TRANSIT / ANNOUNCEMENT CHALLENGE (Archetype 1)",
                f"""- Scenario context: A fast announcement at an airport departure gate, train station platform, or metro speaker.
- In 'hook': Focus on catching the sound on the go (e.g. rushing to catch a train or flight and deciphering the message in 3 seconds).
- NEVER use the phrase "listening to a native podcast"!"""
            ),
            (
                "THE SMARTPHONE TEXT MESSAGE DILEMMA (Archetype 2)",
                f"""- Scenario context: A local friend, roommate, or group chat texts this line.
- In 'hook': Focus on deciphering what your friend actually means or replying without an embarrassing misunderstanding.
- NEVER use the phrase "listening to a native podcast"!"""
            ),
            (
                "THE RAPID ACOUSTIC EAR CHALLENGE (Archetype 3)",
                f"""- Scenario context: Sharp auditory contrast (front beat vs back beat, double consonant vs single, minimal pair).
- In 'hook': Focus on the microscopic acoustic difference that native ears catch instantly.
- In 'challenge': Focus directly on which acoustic rhythm or syllable fits the context.
- NEVER use the phrase "listening to a native podcast"!"""
            ),
            (
                "THE CAFÉ / COUNTER REFLEX (Archetype 4)",
                f"""- Scenario context: Ordering coffee, bakery goods, or street food at a counter under pressure.
- In 'hook': Focus on ordering or responding naturally with zero hesitation at the front of the line.
- NEVER use the phrase "listening to a native podcast"!"""
            ),
            (
                "SPOT THE WEIRD IMPOSTER (Archetype 5)",
                f"""- Scenario context: Identifying an unnatural or fabricated phrase among genuine native expressions.
- In 'hook': Focus on how two phrases sound 100% native, but one is an awkward imposter.
- NEVER use the phrase "listening to a native podcast"!"""
            ),
            (
                "THE COWORKER SLACK / DESK DILEMMA (Archetype 6)",
                f"""- Scenario context: A quick workplace or study message from a coworker or classmate.
- In 'hook': Focus on understanding what your colleague is really saying before you hit reply.
- NEVER use the phrase "listening to a native podcast"!"""
            ),
        ]

        chosen_archetype_name, chosen_archetype_inst = game_archetypes[sid_num % len(game_archetypes)]

        context_clean = context.strip()
        if context_clean:
            context_inst = f"""
-----------------------------
MANDATORY TARGET TEST SENTENCE / USAGE CONTEXT:
-----------------------------
Context / Reference Sentence: "{context_clean}"
- You MUST construct your challenge around this exact sentence or context!
- In "challenge" and "chalkboard_exercise", present the test sentence with a blank (___) where only ONE option works naturally.
"""
        else:
            context_inst = f"""
-----------------------------
MANDATORY CONCRETE TEST SENTENCE:
-----------------------------
- You MUST write a realistic target-language test sentence with a blank (___) or clear conversational choice.
- NEVER ask an abstract question like "Which one is the correct word?" without a test sentence!
"""

        is_word_stress = any(term in combined_text for term in ["word stress", "heteronym", "syllable"]) or (
            any(k in expr for k in [" vs ", " / "]) and any(c.isupper() for c in expr if c.isalpha())
        )

        is_binary = is_word_stress or any(sep in combined_text for sep in [" vs ", " vs. ", " / ", "versus", "noun vs verb", "minimal pair"])
        if is_binary:
            word_stress_guidance = ""
            if is_word_stress:
                word_stress_guidance = f"""
* WORD STRESS & SYLLABLE CAPITALIZATION (CRITICAL):
  - Retain the exact UPPERCASE syllable stress notation in 'challenge', 'answer', and 'chalkboard_exercise' (e.g. '{expr}')!
  - NEVER write both options as regular capitalized words (e.g. DO NOT write 'A) Project B) Project'). Write 'A) PROject B) proJECT'!
  - The uppercase letters show the viewer and the TTS voice actor exactly where the acoustic beat falls!
  - In English, two-syllable heteronyms stress the FIRST syllable for nouns (e.g. PROject, PERmit, REcord) and the SECOND syllable for verbs (e.g. proJECT, perMIT, reCORD).
  - Your test sentence MUST clearly require either a NOUN or a VERB.
  - In 'answer' & 'explanation', explain that in this specific sentence it is a [noun/verb], and contrast how the stress flips for the other role!
"""
            extra_instructions.append(f"""
-----------------------------
MANDATORY GAME ARCHETYPE: {chosen_archetype_name}
-----------------------------
{chosen_archetype_inst}
{context_inst}
-----------------------------
CRITICAL: BINARY FACE-OFF (STRICTLY 2 DISTINCT OPTIONS):
-----------------------------
This challenge is a direct two-way contrast ('{expr}').
- You MUST provide strictly 2 options: Option A vs Option B.
- Both Option A and Option B must be completely distinct.{word_stress_guidance}
- NEVER invent duplicate, filler, or artificial options C and D!
- In "challenge": Read the complete test sentence with the blank (___) and present the two distinct choices in the situational context of {chosen_archetype_name}.
- In "pressure": Use a punchy two-option countdown (DO NOT use "Quick, A or B? Trust your gut, 3 seconds!").
- In "answer": Reveal the winning option (e.g. "It's A!...") with direct linguistic punch explaining why it fits this sentence. DO NOT say "takes the crown"!
- In "chalkboard_exercise": Line 1 MUST be the complete test sentence with the blank (___), then the 2 distinct options:
  [Complete Test Sentence with ___ in {target_lang.upper()}]
  A) [Choice 1]
  B) [Choice 2]
""")
        else:
            extra_instructions.append(f"""
-----------------------------
MANDATORY GAME ARCHETYPE: {chosen_archetype_name}
-----------------------------
{chosen_archetype_inst}
{context_inst}
-----------------------------
MANDATORY DISTRACTOR RULES (3 OPTIONS):
-----------------------------
- ZERO DUPLICATE OPTIONS: Every option (A, B, C) MUST have completely unique, distinct wording.
- Structure the 3 options as:
  * Option 1: True native meaning or correct natural phrase.
  * Option 2: Literal/word-for-word interpretation trap (what learners mistakenly assume).
  * Option 3: Plausible opposite or different situational reaction.
- In 'challenge': Present the test scenario or sentence with all 3 options clearly.
- In 'answer': Direct energetic reveal explaining the true native usage. DO NOT say "takes the crown"!
- In 'chalkboard_exercise':
  Line 1: Test sentence with ___ or Challenge Question in {target_lang.upper()}
  Line 2: A) [Option A]
  Line 3: B) [Option B]
  Line 4: C) [Option C]
""")

    elif video_type == "EXPRESSION":
        expr = str(params.get("EXPRESSION", ""))
        context = str(params.get("CONTEXT", ""))
        subject = str(params.get("SUBJECT", ""))
        angle = str(params.get("ANGLE", ""))
        script_id = str(params.get("ID", ""))
        combined_text = f"{expr} {context} {subject} {angle}".lower()

        is_phonetic_contrast = any(
            sep in combined_text
            for sep in [
                " vs ", " vs. ", " / ", "versus", "word stress", "heteronym",
                "minimal pair", "pronunciation & word stress", "pronunciation & phonetics",
                "noun '", "verb '", "stress on first", "stress on second",
            ]
        )

        is_false_friend = any(
            k in combined_text
            for k in ["faux-ami", "faux ami", "falso amico", "falsi amici", "false friend", "amigo falso"]
        )

        id_digits = re.findall(r"\d+", script_id)
        sid_num = int(id_digits[0]) if id_digits else 0

        if is_phonetic_contrast:
            archetype_name = "THE SOUND & STRESS SECRET (Archetype 4)"
            phonetic_hooks = [
                "Open with the acoustic vocal rhythm or physical mouth sensation of the front beat versus the back beat.",
                "Open with how a native listener's ear instantly categorizes the sound the millisecond they hear the first beat.",
                "Open with a high-speed auditory contrast that makes the viewer immediately hear the shift.",
                "Open with an everyday dilemma where pronouncing the word with the wrong rhythm flips the entire meaning.",
            ]
            chosen_hook_style = phonetic_hooks[sid_num % len(phonetic_hooks)]
            archetype_instruction = f"""- Assigned Archetype: {archetype_name}
- Focus: Highlight how shifting stress or a tiny vowel sound turns one word into something completely different.
- In 'hook': {chosen_hook_style}
- NEVER write: "The Stress Shift That Changes Everything" as title!
- NEVER write: "Move the stress just one syllable..." in the hook!
- In 'setup': Contrast the two sounds/stresses with energetic acoustic punch.
- In 'discovery': Give a fresh, memorable trick to master the pronunciation.
- In 'example': A realistic spoken sentence where the target pronunciation is delivered in natural conversational flow.
- In 'payoff': Quick phonetic lock-in rule and call to action without copying clichés."""
        elif is_false_friend:
            archetype_name = "THE SOCIAL BLUNDER / AWKWARD TRANSLATION (Archetype 2)"
            false_friend_hooks = [
                "Open with the instant, comical reaction of a native speaker who hears the false friend in context.",
                "Open with an unexpected linguistic twist between the two languages that surprises the viewer.",
                "Open with an in-medias-res moment where someone says the word and the conversation takes a hilarious turn.",
            ]
            chosen_ff_hook = false_friend_hooks[sid_num % len(false_friend_hooks)]
            archetype_instruction = f"""- Assigned Archetype: {archetype_name}
- Focus: The awkward, cringe, or funny misunderstanding when a learner translates literally.
- In 'hook': {chosen_ff_hook}
- NEVER write: "Si tu traduis [X] littéralement..." or "Pourquoi le mot [X] ne signifie pas..."!
- In 'setup': What the literal trap sounds like vs what locals actually think.
- In 'discovery': How locals naturally deliver the authentic phrase with confidence.
- In 'example': A real-life dialogue line or sentence showing the correct native phrase rescuing the conversation.
- In 'payoff': The insider save that prevents awkward mistakes + call to action."""
        else:
            idiom_archetypes = [
                (
                    "THE BIZARRE ORIGIN / ETYMOLOGY MYSTERY (Archetype 1)",
                    """- Assigned Archetype: THE BIZARRE ORIGIN / ETYMOLOGY MYSTERY (Archetype 1)
- Focus: Start with the bizarre mental image or surprising historical question.
- In 'hook': Ask why locals use this bizarre imagery (e.g. "Why on earth do locals talk about [bizarre image] when they mean [meaning]?").
- In 'setup': Unpack the strange historical origin or visual metaphor.
- In 'discovery': Show how modern speakers effortlessly drop it into casual conversation.
- In 'example': A real-life conversational sentence showing how someone naturally drops the phrase today.
- In 'payoff': A memorable punchline tying back to the mental image + call to action.
- REMINDER: DO NOT say "Stop saying [X]!" in the hook.""",
                ),
                (
                    "THE NATIVE SLANG / STREET LEVEL-UP (Archetype 3)",
                    """- Assigned Archetype: THE NATIVE SLANG / STREET LEVEL-UP (Archetype 3)
- Focus: The vibrant gap between stiff textbook language and real living street rhythm.
- In 'hook': Challenge the robotic textbook way to say it (e.g. "Textbooks teach you to say '...', but on the street that sounds like a robot from 1995.").
- In 'setup': Why the formal phrase lacks vibe, and what attitude the idiom brings.
- In 'discovery': The snappy cadence and swagger of the native expression in action.
- In 'example': A punchy colloquial sentence showing the expression in everyday street banter.
- In 'payoff': The confidence boost to speak like a local peer + call to action.
- REMINDER: DO NOT say "Stop saying [X]!" in the hook.""",
                ),
                (
                    "THE DRAMATIC SLICE OF LIFE (Archetype 5)",
                    """- Assigned Archetype: THE DRAMATIC SLICE OF LIFE (Archetype 5)
- Focus: An in-medias-res dramatic or relatable everyday human moment.
- In 'hook': Drop the viewer into a vivid situation (e.g. "Picture this: you've been working on something for three months, and in two seconds...").
- In 'setup': The emotional tension of the moment.
- In 'discovery': The exact feeling this idiom captures that normal words can't touch.
- In 'example': A high-impact conversational sentence capturing that exact emotional moment.
- In 'payoff': High-energy wrap-up + call to action.
- REMINDER: DO NOT say "Stop saying [X]!" in the hook.""",
                ),
            ]
            id_digits = re.findall(r"\d+", script_id)
            cycle_idx = int(id_digits[0]) % len(idiom_archetypes) if id_digits else random.randint(0, len(idiom_archetypes) - 1)
            archetype_name, archetype_instruction = idiom_archetypes[cycle_idx]

        extra_instructions.append(f"""
-----------------------------
MANDATORY EXPRESSION DIVERSITY & ANTI-CLICHE RULES:
-----------------------------
{archetype_instruction}
- ZERO TOLERANCE FOR REPETITIVE CLICHES:
  * NEVER begin the hook with: "Stop saying [X]!", "Are you tired of...", "Don't use a boring word!", or "When you think of..."
  * NEVER say in the body: "In [language], we don't say X, we say Y", "Forget the textbook word", or "Literally it means A, but it actually means B"
  * NEVER use generic filler: "Imagine your friend..." or "Think about that one time you aced a test..."
  * Mandatory JSON keys in 'script': EXACTLY "title", "hook", "setup", "discovery", "example", "payoff".
  * Spoken word count across all 5 sections MUST be strictly 85 to 110 words.
""")

    extra_instructions_str = "\n".join(extra_instructions)

    return f"""
{COMMON_CONTENT_RULES}

{branch_rules}
{cta_instruction}
{false_friends_guard}
{extra_instructions_str}
-----------------------------
GENERATE SCRIPT WITH (METADATA):
-----------------------------

{param_str}

-----------------------------
REMINDER ON OUTPUT LANGUAGE:
-----------------------------
The TARGET_LANGUAGE is strictly {target_lang.upper()}.
Every section, title, dialogue, and chalkboard_exercise MUST be written 100% in {target_lang.upper()}.
Zero mixing or English template copying allowed.

-----------------------------
OUTPUT:
-----------------------------

Generate the JSON object as requested.
"""


def build_fun_facts_formatting_prompt(raw_script: str, params: dict) -> str:
    """
    Builds a prompt instructing the local LLM to adapt and structure a user-provided
    raw script into the standardized LingoVerse FUN_FACTS JSON format with calibrated word limits.
    """
    target_lang = params.get("TARGET_LANGUAGE", "English")
    topic = params.get("TOPIC") or params.get("EXPRESSION") or params.get("SUBJECT") or "Language Curiosity"
    pillar = params.get("PILLAR", "Language Curiosities")
    format_type = params.get("FORMAT", "")

    ctas = load_call_to_actions(target_lang)
    cta_clause = ""
    if ctas:
        chosen_cta = random.choice(ctas)
        cta_clause = f"""
-----------------------------
MANDATORY PAYOFF CLOSING LINE:
-----------------------------
The VERY LAST sentence of your "payoff" section MUST finish with:
"{chosen_cta}"
"""

    return f"""
You are an expert short-form video script adapter and formatter for LingoVerse vertical Shorts.

You have been given a raw script written for a YouTube Short about:
- Target Language: {target_lang}
- Topic: {topic}
- Pillar: {pillar}
- Preferred Format: {format_type or "Auto-selected best fitting format"}

-----------------------------
RAW USER SCRIPT TO ADAPT & FORMAT:
-----------------------------
{raw_script}

-----------------------------
YOUR TASK (CRITICAL):
-----------------------------
1. Adapt, split, and format this exact script into our required LingoVerse FUN_FACTS JSON structure.
2. The spoken content must use ONLY the TARGET LANGUAGE ({target_lang}).
3. Maintain the core ideas, discoveries, and voice from the raw script, but ensure it is cleanly divided into logical short-form video sections:
   - "title": Catchy, curiosity-inducing title.
   - "hook": Immediate curiosity gap / hook addressing the viewer directly.
   - Body sections: Split the body into 2 to 3 logical scenes based on the content. Use standard keys that best fit:
     * If 3 distinct facts: "fact_1", "fact_2", "fact_3"
     * If one core curiosity / story: "setup", "discovery"
     * If a mystery: "mystery", "clues", "reveal"
     * If a challenge / puzzle: "challenge", "thinking_time", "answer"
     * If a comparison: "comparison_a", "comparison_b", "surprise"
     * If a ranking / list: "item_3", "item_2", "item_1"
   - "payoff": Memorable takeaway + punchy conclusion and call to action.
4. WORD COUNT (CRITICAL): Total spoken words across all sections (excluding title) MUST be STRICTLY between 95 and 135 words (target 40-60s duration).
   - If the raw script is too long, tighten and condense sentences without losing key facts.
   - If the raw script is too short, expand and enrich the curiosity and takeaway naturally.
5. Tone: Relaxed, entertaining, conversational, curious, playful, surprising, light, fast.
{cta_clause}
-----------------------------
OUTPUT FORMAT (MANDATORY):
-----------------------------
You MUST return ONLY a JSON object. Do NOT wrap in markdown code blocks.
Example JSON:
{{
    "video_type": "FUN_FACTS",
    "language": "{target_lang.lower()}",
    "category": "FUN_FACTS",
    "topic": "{topic}",
    "script": {{
        "title": "...",
        "hook": "...",
        "setup": "...",
        "discovery": "...",
        "payoff": "..."
    }}
}}
"""