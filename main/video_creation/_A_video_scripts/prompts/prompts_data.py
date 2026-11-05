"""
prompts_data.py — Master prompt definitions and format-specific metadata generators.
"""

def get_metadata_prompt(video_type: str = "EXPRESSION", target_language: str = "English") -> str:
    """Returns a format-differentiated, emoji-free YouTube metadata prompt."""
    vtype = (video_type or "EXPRESSION").upper()
    lang = (target_language or "English").title()

    type_guidance = ""
    if vtype == "EXPRESSION":
        type_guidance = """
FORMAT ARCHETYPE: EXPRESSION (Micro-Storytelling)
- Focus: Cultural Lore, Social Blunder, or Everyday Colloquial Nuance.
- Angle: Reveal why locals say this, what cringe mistake foreigners make, or the vivid real-world meaning.
- Title Tone: Intriguing linguistic insight. Never an academic lecture.
- Title Examples:
  * English: Break a Leg: Why Good Luck Is Actually a Curse
  * Spanish: Costar un Ojo de la Cara: El Error de Traducirlo Literal
  * French: Poser un Lapin: Ce Que Les Français Veulent VRAIMENT Dire
  * Italian: In Bocca al Lupo: Perché Non Devi Mai Dire Buona Fortuna
"""
    elif vtype == "GAME":
        type_guidance = """
FORMAT ARCHETYPE: GAME (Interactive Trivia / Ear Challenge)
- Focus: Fast Ear Challenge, Binary Choice, or Instant Reflex Test.
- Angle: Direct challenge to the viewer's ear or intuition. Pits Option A vs Option B or tests reaction.
- Title Tone: High-energy interactive challenge.
- Title Examples:
  * English: Bad vs Bed: Can Your Ears Hear the Difference?
  * Spanish: Recordar vs Acordarse: El Fallo Que el 90% Comete
  * French: Blessé vs Béni: Quel Mot As-Tu Entendu?
  * Italian: Anno vs Ano: Sfida di Ascolto sulla Doppia N
"""
    elif vtype == "ROLEPLAY":
        type_guidance = """
FORMAT ARCHETYPE: ROLEPLAY (Real-World Dialogue & Banter)
- Focus: Character Scene, Social Drama, or Funny Misunderstanding.
- Angle: Two friends/colleagues navigating an awkward moment, misunderstanding an idiom, or cracking a joke.
- Title Tone: Situational comedy or real-life banter.
- Title Examples:
  * English: Break a Leg: Backstage Drama When You Take Idioms Literally
  * Spanish: Tomar el Pelo: Cuando No Entiendes la Broma de Tus Amigos
  * French: Rendez-vous au Café: Quand Ton Ami Te Pose un Lapin
  * Italian: Al Ristorante: L'Errore Più Imbarazzante con le Doppie
"""
    elif vtype == "FUN_FACTS":
        type_guidance = """
FORMAT ARCHETYPE: FUN_FACTS (Linguistic Curiosities & Anomalies)
- Focus: Bizarre Etymology, Historical Accident, or Mind-Bending Record.
- Angle: Fascinating linguistic anomaly that surprises even native speakers.
- Title Tone: Curious, mind-expanding revelation.
- Title Examples:
  * English: The Longest Word in English That Actually Makes Sense
  * Spanish: Por Qué el Español Usa Signos de Interrogación Invertidos
  * French: Pourquoi les Nombres en Français Font Faire des Maths
  * Italian: L'Alfabeto Italiano Ha Soltanto 21 Lettere
"""

    return f"""You are an expert social media manager specialized in high-retention YouTube Shorts for language learning.

Given a script and its generation parameters, produce ALL metadata for the video in a single response.

--------------------------------
VIDEO METRICS & CONTEXT
--------------------------------
- Video Type: {vtype}
- Target Language: {lang}
{type_guidance}

--------------------------------
OUTPUT FORMAT (MANDATORY)
--------------------------------
Return ONLY a valid JSON object — no markdown, no code fences, no commentary.

{{
  "title": "...",
  "description": "...",
  "short_description": "...",
  "tags": "tag1, tag2, tag3, ...",
  "hashtags": "#Tag1 #Tag2 #Tag3",
  "label": "LANGUAGE | SUBJECT | SITUATION | SKILL",
  "filename": "language_subject_expression-context.mp4"
}}

--------------------------------
FIELD RULES
--------------------------------

TITLE (STRICT - ZERO EMOJIS)
- STRICT EMOJI BAN: NEVER include any emojis, symbols, or pictographs in the title. Emojis are strictly forbidden.
- STRICT CLICHÉ BAN: NEVER use formulaic filler suffixes: "The Native Secret", "The Secret", "Secret", "Le Secret des Natifs", "Il Segreto dei Nativi", "El Secreto de los Nativos", "Shorts Guide", "Game Changer", "Changes Everything".
- Structure: Expression or Topic + colon or separator + tension-based hook reflecting the video format.
- Capitalize for readability: Use UPPERCASE for 1–3 high-impact hook words; Title Case for supporting words; lowercase for prepositions/connectors.
- Must be specific to this exact script and format.
- Max 85 characters (ideal 45–70 characters).
- MUST be 100% in {lang.upper()}. Do NOT mix languages.

DESCRIPTION
- Structure: 1-line hook → 2–4 lines of real value (include the EXPRESSION) → 1-line CTA → hashtags on last line.
- Natural, conversational tone. No "in this video". ZERO EMOJIS.
- 200–350 characters ideal, max 500. No links.
- MUST be 100% in {lang.upper()}.

SHORT_DESCRIPTION
- 1-line hook + 1-line value + 3–5 hashtags.
- Max 150 characters. No filler text. ZERO EMOJIS.
- 100% {lang.upper()} only.

TAGS
- 10–15 tags, comma-separated, no # symbols.
- Cover: target language name, the expression itself, the situation, and intent (learn/speak/improve).
- Mix short and long tags. Natural search phrases.

HASHTAGS
- 3–6 hashtags on one line.
- Mix: language (#LearnEnglish), context (#WorkEnglish), intent (#SpeakBetter).
- No repetition. No generic spam (#fyp, #viral). Adapt to {lang.upper()} if applicable.

LABEL
- Format: LANGUAGE | SUBJECT | SITUATION | SKILL
- LANGUAGE: English / Spanish / French / Italian
- SUBJECT: work, travel, dating, shopping, health, social
- SITUATION: specific (asking for help, ordering food, complaining, etc.)
- SKILL: tone, politeness, pronunciation, pragmatics, assertiveness, etc.

FILENAME
- Format: language_subject_expression-short-context.mp4
- Lowercase only. Hyphens instead of spaces. No special characters. Keep expression short.

--------------------------------
IMPORTANT
--------------------------------
- All fields must be 100% in {lang.upper()}.
- Output ONLY the JSON object.
"""

# Default prompt for backward compatibility
METADATA_PROMPT = get_metadata_prompt("EXPRESSION", "English")
