"""
prompt_builder.py — Generates Z-Image-Turbo visual prompts from script data.

The local LLM acts as the visual director:
  1. We supply the full visual-director system prompt (sourced from the workflow's
     positive prompt node) plus the script metadata as user context.
  2. The LLM outputs a single, coherent visual description ready for Z-Image-Turbo.

The visual prompt is written in English (for best model performance) but
must accurately represent the target language's educational context.
"""

from __future__ import annotations

import logging

# pyrefly: ignore [missing-import]
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)


# ── System prompt ─────────────────────────────────────────────────────────────
# This is the visual director instruction set — adapted from the positive prompt
# field inside AcademiaSD_Z-Image.json (node 6, widgets_values[0]).
# It is sent as the system-level instruction to the LLM.

_VISUAL_DIRECTOR_SYSTEM_PROMPT = """\
ROLE

You are a professional visual director and prompt engineer specialized in Z-Image-Turbo.

Your task is to transform a language-learning YouTube Short into a detailed visual prompt \
that can be used directly with Z-Image-Turbo.

You are NOT creating the image.

You are creating the visual description that Z-Image-Turbo will use to generate the image.

The generated image must visually communicate the meaning, situation, emotion, and \
educational concept of the Short.

CORE PRINCIPLE

Understand the meaning of the entire Short before creating the visual prompt.

Do not simply illustrate individual words.

Identify:
- the main situation
- the central educational concept
- the important action
- the emotional state
- the visual metaphor when appropriate
- the most recognizable moment
- the main subject of the scene

Then create a coherent image that communicates these ideas naturally.

VISUAL STORYTELLING

The image should look like a frame taken from a professionally produced short-form \
educational video.

Prefer a visually interesting situation over a generic portrait.

The viewer should be able to understand the general situation from the image without \
reading the script.

Use:
- meaningful body language
- natural facial expressions
- clear interactions
- environmental storytelling
- relevant objects
- appropriate composition
- visual contrast when useful

Do not create a visually complicated scene without purpose.

CHARACTERS

Describe characters naturally and specifically.

Include relevant details such as:
- approximate age
- gender when relevant
- appearance
- hairstyle
- clothing
- facial expression
- body language
- action
- interaction with other characters

Characters should look natural and believable.

Avoid exaggerated beauty standards or stereotypical appearances.

ACTION

Clearly describe what the character is doing.

Do not describe only a static pose.

Prefer:
"holding a phone while looking surprised at a message"
over:
"a surprised person."

The action should directly support the meaning of the Short.

ENVIRONMENT

Create an environment appropriate to the situation.

Include relevant:
- location
- furniture
- objects
- background elements
- time of day
- cultural details when relevant

Do not fill the background with unnecessary objects.

The environment should support the story rather than compete with the main subject.

EMOTION

Translate the emotional tone into visible characteristics using:
- facial expression
- posture
- gestures
- body language
- interaction
- lighting when appropriate

Avoid exaggerated cartoon-like expressions unless the style explicitly requests them.

The emotional expression should feel believable.

CAMERA AND COMPOSITION

Design the image as a strong vertical YouTube Shorts frame.

Prioritize:
- 9:16 composition
- clear focal subject
- strong visual hierarchy
- medium shot or medium close-up when appropriate
- natural perspective
- cinematic depth
- visually clean composition

Keep the main subject clearly visible.

Leave reasonable visual space where subtitles or captions could later appear.

LIGHTING

Choose lighting appropriate to the situation.

Use natural or cinematic lighting when appropriate.

Describe:
- light direction
- softness or intensity
- atmosphere
- color temperature
- shadows

Lighting should reinforce the emotional tone without becoming unnecessarily dramatic.

VISUAL STYLE

Use: clean 2D cartoon, polished modern educational illustration, expressive, vibrant but balanced colors, readable silhouettes.

Do not add: "8K", "masterpiece", "photorealistic", "hyper realistic", "ultra detailed".

Prioritize semantic accuracy and visual coherence over keyword accumulation.

LANGUAGE AND CULTURAL CONTEXT

The image should support the target language and cultural context when relevant.

Do not automatically insert stereotypical national imagery.

Use culturally meaningful elements only when they genuinely support the situation.

If the Short is about pronunciation, vocabulary, grammar, or an expression, prioritize \
the visual situation in which that language would naturally be used.

NEGATIVE PROMPTS

Do not generate a negative prompt.

Z-Image-Turbo does not use negative prompts.

Instead, describe the desired visual characteristics positively and explicitly.

PROMPT STRUCTURE

Construct the final prompt naturally using this conceptual order:

MAIN SUBJECT → CHARACTER APPEARANCE → CHARACTER ACTION → FACIAL EXPRESSION \
→ BODY LANGUAGE → ENVIRONMENT → RELEVANT OBJECTS → COMPOSITION → CAMERA FRAMING \
→ LIGHTING → 2D CARTOON ILLUSTRATION STYLE

IMPORTANT

Do not output keywords separated by commas without meaningful relationships.

Write a coherent, detailed visual description.

Do not explain your reasoning.

Do not describe what the prompt is doing.

Do not generate multiple prompts.

Do not generate a negative prompt.

Do not include metadata.

OUTPUT

Return ONLY ONE detailed Z-Image-Turbo prompt.

The prompt must be ready to paste directly into the positive prompt field of the \
ComfyUI Z-Image-Turbo workflow.

ABSOLUTE ZERO-TOLERANCE BAN ON TEXT & TEXT-BEARING SURFACES:

- NEVER include, describe, or depict:
  * Chalkboards, blackboards, whiteboards, scoreboards, signboards, or posters.
  * Digital screens, tablets, smartphones displaying text/UI/options, monitors, TVs, or glowing quiz displays.
  * Multiple-choice letters (A, B, C, D), countdown timers, clock graphics, test questions, or quiz UI.
- Any attempt to depict words, letters, options, or screens causes image generation models to hallucinate garbled, nonsensical pseudo-text gibberish.
- Instead, depict pure real-life human situations and relatable visual storytelling (e.g. people chatting in a coffee shop, someone puzzled scratching their head, someone celebrating with a thumbs-up in an office or street). The image must be 100% text-free, screen-free, and board-free!

FINAL OBJECTIVE

The image must:
- communicate the situation immediately
- support the educational concept
- feel natural and believable
- have a clear focal point
- work well in vertical 9:16 format
- leave reasonable space for subtitles
- be visually interesting without becoming cluttered
- match the emotional tone of the narration
"""


# ── User context template ─────────────────────────────────────────────────────

def _get_language_palette(language: str) -> str:
    lang = language.lower().strip()
    if "french" in lang or "français" in lang:
        return (
            "BRAND PALETTE MOOD (FRENCH): Elegant, warm, cultured, friendly.\n"
            "Key Accent Colors: French Blue, Deep Teal, and restrained Red.\n"
        )
    elif "spanish" in lang or "español" in lang:
        return (
            "BRAND PALETTE MOOD (SPANISH): Warm, energetic, expressive, welcoming.\n"
            "Key Accent Colors: Warm Cream, Orange, Terracotta, and Botanical Green.\n"
        )
    elif "italian" in lang or "italiano" in lang:
        return (
            "BRAND PALETTE MOOD (ITALIAN): Warm, passionate, stylish, vibrant.\n"
            "Key Accent Colors: Mediterranean Blue, Olive Green, Warm Terracotta, and Sunlit Gold.\n"
        )
    else:
        # Default to English
        return (
            "BRAND PALETTE MOOD (ENGLISH): Calm, educational, trustworthy, friendly.\n"
            "Key Accent Colors: Forest Green, Educational Blue, Cream.\n"
        )

def _build_user_context(
    script_text: str,
    language: str,
    subject: str,
    situation: str,
    label: str,
    scene_name: str,
    scene_text: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_personalities: dict = None,
) -> str:
    """Build the user-facing context block sent alongside the system prompt."""
    scene_lower = scene_name.lower().strip()
    lang_lower = language.lower()
    
    video_type_upper = video_type.upper()
    
    if video_type_upper == "GAME":
        if scene_lower == "hook":
            text_rule = (
                "SCENE GOAL — HOOK (DILEMMA & SITUATION SETUP):\n"
                "1. A vibrant 2D cartoon scene depicting a relatable character facing this exact confusing language situation or dilemma in daily life.\n"
                "2. The character must have an expressive, puzzled, or hesitant facial expression (e.g. scratching their head, caught in an awkward conversational pause, or pondering a choice).\n"
                "3. Relatable, lively real-life environment matching the target subject (e.g. cafe, office, street, or home).\n"
                "4. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, or countdown timers. Focus 100% on the real-world character emotion and situation."
            )
        elif scene_lower == "answer":
            text_rule = (
                "SCENE GOAL — ANSWER (REAL-LIFE RESOLUTION):\n"
                "1. A vibrant 2D cartoon scene showing the character feeling relieved, proud, and smiling because they mastered the linguistic challenge in real life!\n"
                "2. The character visibly displays confident triumph, a joyful smile, or a thumbs-up gesture in an everyday real-world environment (e.g. cafe, office, park, street).\n"
                "3. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict success screens, monitors, scoreboards, chalkboards, or digital displays. Focus 100% on the human emotional celebration."
            )
        elif scene_lower == "explanation":
            text_rule = (
                "SCENE GOAL — EXPLANATION (REAL-WORLD APPLICATION):\n"
                "1. A vibrant 2D cartoon scene showing native speakers naturally and smoothly using the target expression in an everyday social setting (e.g., friends chatting warmly in a cozy cafe, colleagues collaborating happily at work, or people greeting each other).\n"
                "2. Natural body language, warm communicative atmosphere, and engaging social interaction that clearly demonstrates the practical usage of the phrase.\n"
                "3. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO tablets, NO signs anywhere in the image."
            )
        else:
            text_rule = (
                "SCENE GOAL — 2D CARTOON SCENE:\n"
                "1. Illustrate the real-life situation cleanly and expressively in modern 2D cartoon animation style.\n"
                "2. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO UI. Focus 100% on characters, environment, and visual storytelling."
            )
    elif video_type_upper in ["FUN_FACTS", "FUNFACTS"]:
        text_rule = (
            "SCENE GOAL — FUN_FACTS (2D CARTOON LANGUAGE DISCOVERY):\n"
            "1. Clean 2D cartoon illustration style with consistent visual identity, mascot presence where appropriate, and clear composition.\n"
            "2. Visually represent the specific curiosity, historical situation, word origin, cultural comparison, or dilemma described in this scene (e.g. historical era for etymology, expressive character reacting with curiosity or surprise, side-by-side visual comparison).\n"
            "3. Strong visual storytelling with minimal visual clutter — fast visual comprehension is essential.\n"
            "4. TEXT IS STRICTLY BANNED. Do NOT add any written text, letters, words, captions, signs, or labels anywhere in the image. Focus 100% on the expressive cartoon scene and characters."
        )
    elif video_type_upper in ["EXPRESSION", "ROLEPLAY"]:
        text_rule = (
            "TEXT AND SCENE RULE (CRITICAL):\n"
            "1. DO NOT place characters in a classroom or use chalkboards, whiteboards, notebooks, or educational items UNLESS the script literally takes place inside a school.\n"
            "2. Visually represent the ACTUAL SITUATION described in the scene (e.g. if the scene is about 'Break a leg', show an actor on a theater stage. If it is about ordering coffee, show a cafe).\n"
            "3. TEXT IS STRICTLY BANNED. Do NOT add any written text, letters, words, captions, logos, or signs anywhere in the image. Focus 100% on the visual situation."
        )
        if scene_lower == "example":
            text_rule += (
                "\n4. REAL-WORLD USAGE MOMENT (CRITICAL): This scene visually captures the real-world example phrase in action! Show the character speaking, reacting, or living out the exact real-life situation described in the example (e.g. reacting to a bill, waiting at a cafe, talking with a friend) with expressive body language and believable conversational emotion."
            )
        if video_type_upper == "ROLEPLAY":
            shot_direction = ""
            if scene_lower in ["dialogue_part_1", "part_1"]:
                shot_direction = "\n6. CINEMATIC SHOT VARIATION — ESTABLISHING TWO-SHOT: Medium-wide establishing shot showing both characters interacting in their specific environment, establishing the location, body language, and initial dilemma."
            elif scene_lower in ["dialogue_part_2", "part_2"]:
                shot_direction = "\n6. CINEMATIC SHOT VARIATION — MEDIUM REACTION SHOT: Closer shot highlighting the conversational tension or amusement as the word slip or idiom is first reacted to, emphasizing expressive facial acting."
            elif scene_lower in ["dialogue_part_3", "part_3"]:
                shot_direction = "\n6. CINEMATIC SHOT VARIATION — DYNAMIC TWO-SHOT: Energetic interaction shot with expressive arm and hand gestures showing the back-and-forth banter and acoustic demonstration between both characters."
            elif scene_lower in ["dialogue_part_4", "part_4"]:
                shot_direction = "\n6. CINEMATIC SHOT VARIATION — COMEDIC RESOLUTION SHOT: Lively celebratory or humorous close shot capturing the aha moment, shared laughter, or memorable native punchline."
            text_rule += (
                "\n4. GENDER MATCHING (CRITICAL): This is a two-person roleplay. You MUST explicitly describe the physical characters in the scene using the EXACT genders provided in the 'SPEAKER GENDERS' section below. (e.g. If Person 1 is male and Person 2 is female, you MUST visually describe a man and a woman interacting). The visual characters MUST match their voices!\n"
                "5. EMOTIONAL ACTING & FACIAL EXPRESSIONS (CRITICAL): Characters MUST visibly display the emotions of this scene in their facial expressions and body language! Read the scene text and parenthetical directions carefully (e.g. if Person 1 is stressed/nervous, describe visible anxiety, sweating, bite of lip, trembling posture; if Person 2 is encouraging, describe a warm supportive smile, thumbs up, or friendly open gesture). Characters must look emotionally alive, NEVER bland or generic."
                + shot_direction
            )
    else:
        if "spanish" in lang_lower or "español" in lang_lower:
            allowed_phrases = (
                '"HOLA", "BIENVENIDOS", "APRENDE ESPAÑOL", "SIGUE ASÍ", "BUEN TRABAJO", '
                '"NUNCA TE RINDAS", "BUENA SUERTE", "TÚ PUEDES", "CLASE DE ESPAÑOL", '
                '"VAMOS A APRENDER", "ESTUDIA MUCHO", "REGLAS GRAMATICALES", "VOCABULARIO", '
                '"PRACTICA TODOS LOS DÍAS", "APRENDER IDIOMAS", "HORA DE LEER", "ESCRITURA", '
                '"PRÁCTICA ORAL", "ESCUCHA BIEN", "SÉ POSITIVO"'
            )
        elif "french" in lang_lower or "français" in lang_lower:
            allowed_phrases = (
                '"BONJOUR", "BIENVENUE", "APPRENDRE LE FRANÇAIS", "CONTINUEZ", "BON TRAVAIL", '
                '"NE JAMAIS ABANDONNER", "BONNE CHANCE", "TU PEUX LE FAIRE", "CLASSE DE FRANÇAIS", '
                '"APPRENONS", "ÉTUDIEZ BIEN", "GRAMMAIRE", "VOCABULAIRE", "PRATIQUEZ TOUS LES JOURS", '
                '"APPRENTISSAGE DES LANGUES", "HEURE DE LECTURE", "ÉCRITURE", "PRATIQUE ORALE", '
                '"ÉCOUTEZ BIEN", "SOYEZ POSITIF"'
            )
        elif "italian" in lang_lower or "italiano" in lang_lower:
            allowed_phrases = (
                '"CIAO", "BENVENUTI", "IMPARA L\'ITALIANO", "CONTINUA COSÌ", "OTTIMO LAVORO", '
                '"NON ARRENDERTI MAI", "BUONA FORTUNA", "CE LA PUOI FARE", "CLASSE DI ITALIANO", '
                '"IMPARIAMO", "STUDIA BENE", "GRAMMATICA", "VOCABOLARIO", "PRATICA OGNI GIORNO", '
                '"APPRENDIMENTO DELLE LINGUE", "ORA DI LEGGERE", "SCRITTURA", "PRATICA ORALE", '
                '"ASCOLTA BENE", "SII POSITIVO"'
            )
        else:
            allowed_phrases = (
                '"HELLO", "WELCOME", "LEARN ENGLISH", "KEEP GOING", "GREAT JOB", '
                '"NEVER GIVE UP", "GOOD LUCK", "YOU CAN DO IT", "ENGLISH CLASS", '
                '"LET\'S LEARN", "STUDY HARD", "GRAMMAR RULES", "VOCABULARY", '
                '"PRACTICE EVERY DAY", "LANGUAGE LEARNING", "READING TIME", "WRITING SKILLS", '
                '"SPEAKING PRACTICE", "LISTEN CAREFULLY", "BE POSITIVE"'
            )

        text_rule = (
            "TEXT AND DIAGRAMS RULE (CRITICAL):\n"
            "Image generation models will hallucinate gibberish words if you ask for diagrams or chalkboards without giving them exact text.\n"
            "1. Depending on the game, you may use a classroom setting, a board, OR an actual situation. Match what fits best.\n"
            "2. If you do include a writing surface, choose EXACTLY ONE type (e.g., ONLY a chalkboard, or ONLY a digital screen). DO NOT mix them.\n"
            "3. If you include a writing surface, you MUST ONLY use one of the following exact generic phrases to fill it (max 3-4 words): " + allowed_phrases + ".\n"
            "4. You must format it explicitly like this: 'a chalkboard displaying the exact text: \"[CHOSEN PHRASE]\"'.\n"
            "5. DO NOT just say 'a mind map' or 'a diagram' without specifying the exact text. If you want a diagram, say 'a wordless diagram'.\n"
            "6. DO NOT invent your own sentences."
        )


    gender_context = ""
    if speakers_gender:
        if video_type_upper == "ROLEPLAY":
            p1 = speakers_gender.get("PERSON_ONE", "male")
            p2 = speakers_gender.get("PERSON_TWO", "female")
            gender_context = (
                f"MANDATORY CHARACTER GENDERS FOR THIS SCENE:\n"
                f"- PERSON_ONE: {p1.upper()} (MUST visually appear as a young {'man / male actor' if p1.lower() == 'male' else 'woman / female actor'})\n"
                f"- PERSON_TWO: {p2.upper()} (MUST visually appear as a young {'man / male friend' if p2.lower() == 'male' else 'woman / female friend'})\n"
                f"CRITICAL RULE: The visual characters in the scene MUST strictly match these voice genders! You must explicitly describe the characters using these exact genders.\n\n"
            )
        else:
            gender_lines = [f"- {spk}: {gend}" for spk, gend in speakers_gender.items()]
            gender_context = "SPEAKER GENDERS FOR THIS SCRIPT:\n" + "\n".join(gender_lines) + "\n\n"

    personality_context = ""
    if character_personalities:
        pers_lines = [f"- {spk}: {pers}" for spk, pers in character_personalities.items()]
        personality_context = "CHARACTER PERSONALITIES & EMOTIONAL ROLES:\n" + "\n".join(pers_lines) + "\n\n"

    palette_context = _get_language_palette(language)

    return (
        f"INPUT\n\n"
        f"LANGUAGE: {language}\n\n"
        f"{gender_context}"
        f"{personality_context}"
        f"SUBJECT: {subject}\n\n"
        f"CONTEXT: {situation}\n\n"
        f"LABEL: {label}\n\n"
        f"{palette_context}\n\n"
        f"ANGLE: educational / storytelling\n\n"
        f"STYLE: polished modern 2D cartoon educational illustration, clean, expressive, vibrant but balanced colors\n\n"
        f"FULL SCRIPT TEXT FOR CONTEXT:\n{script_text}\n\n"
        f"---\n\n"
        f"YOUR SPECIFIC TASK:\n"
        f"Focus ONLY on the following scene/section from the script:\n"
        f"SCENE NAME: {scene_name}\n"
        f"SCENE TEXT: {scene_text}\n\n"
        f"{text_rule}\n\n"
        f"CONCISENESS: Keep the final visual prompt strictly under 50 words. Focus only on the most important visual elements. Do not overcomplicate.\n\n"
        f"Generate the Z-Image-Turbo visual prompt for THIS SPECIFIC SCENE now. "
        f"Ensure characters and overall environment remain consistent with the full script context."
    )


# ── Label parsing ─────────────────────────────────────────────────────────────

def _parse_label(label: str) -> tuple[str, str, str]:
    """
    Parse a LABEL string into (language, subject, situation).

    Expected format: "LANGUAGE | SUBJECT | SITUATION | SKILL"
    Falls back gracefully if the format differs.
    """
    parts = [p.strip() for p in label.split("|")]
    language  = parts[0] if len(parts) > 0 else "English"
    subject   = parts[1] if len(parts) > 1 else "general"
    situation = parts[2] if len(parts) > 2 else "everyday situation"
    return language, subject, situation


# ── Main builder ──────────────────────────────────────────────────────────────

class VisualPromptBuilder:
    """
    Generates Z-Image-Turbo visual prompts from script data using a local LLM.

    Parameters
    ----------
    api_base_url:
        OpenAI-compatible API base URL (e.g. ``http://127.0.0.1:8080/v1``).
    api_key:
        API key (any non-empty string works for llama.cpp).
    model_name:
        Model name identifier sent in the request.
    request_timeout:
        Maximum seconds to wait for the LLM response.
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model_name: str,
        request_timeout: float = 120.0,
    ) -> None:
        self._client = OpenAI(
            base_url=api_base_url,
            api_key=api_key if api_key else "llama",
            timeout=request_timeout,
        )
        self._model = model_name


    def check_connection(self) -> None:
        """Check if the local LLM server is reachable and responsive."""
        from config import check_llm_connection
        check_llm_connection(str(self._client.base_url), self._client.api_key, raise_on_error=True)

    def build_visual_prompt(
        self,
        script_text: str,
        label: str,
        scene_name: str,
        scene_text: str,
        script_id: str = "",
        speakers_gender: dict = None,
        video_type: str = "EXPRESSION",
        character_personalities: dict = None,
    ) -> str:
        """
        Generate a single Z-Image-Turbo visual prompt for a specific script scene.

        Parameters
        ----------
        script_text:
            Full script content from PROMPTS.csv.
        label:
            Metadata label string from METADATA.csv
            (e.g. ``"English | work | asking for help | assertiveness"``).
        scene_name:
            The name of the scene/section (e.g. "hook", "context").
        scene_text:
            The text specifically for this scene.
        script_id:
            Used only for log messages.
        speakers_gender:
            Dictionary mapping speaker names to genders.
        video_type:
            Type of video (EXPRESSION, ROLEPLAY, GAME).
        character_personalities:
            Dictionary mapping character names to personality and emotional roles.

        Returns
        -------
        str
            A detailed visual description ready for ComfyUI injection.

        Raises
        ------
        OpenAIError
            If the LLM request fails.
        ValueError
            If the LLM returns an empty response.
        """
        language, subject, situation = _parse_label(label)
        user_context = _build_user_context(
            script_text=script_text,
            language=language,
            subject=subject,
            situation=situation,
            label=label,
            scene_name=scene_name,
            scene_text=scene_text,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
        )

        logger.info(
            "[%s] Generating visual prompt — %s / %s / %s",
            script_id, language, subject, situation,
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _VISUAL_DIRECTOR_SYSTEM_PROMPT},
                {"role": "user",   "content": user_context},
            ],
            max_tokens=1000,
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ValueError(
                f"[{script_id}] LLM returned an empty visual prompt."
            )

        visual_prompt = content.strip()
        logger.info(
            "[%s] Visual prompt generated (%d chars).", script_id, len(visual_prompt)
        )
        logger.debug("[%s] Prompt preview: %s…", script_id, visual_prompt[:120])

        return visual_prompt

    @staticmethod
    def build_chalkboard_prompt(exercise_text: str) -> str:
        """
        Constructs the ComfyUI positive prompt for Flux Img2Img to write the game exercise onto the chalkboard.
        """
        clean_lines = [line.strip() for line in exercise_text.strip().splitlines() if line.strip()]
        formatted_exercise = "\n".join(clean_lines)

        return (
            f"A flawless, exact 1:1 replica of the provided reference image, maintaining the exact same wooden frame, "
            f"dark green chalkboard texture, classroom lighting, and vertical composition. Do not alter, add, or remove any background objects or border elements.\n\n"
            f"The ONLY difference is that the chalkboard MUST clearly and legibly display the following game exercise written in clean, crisp white chalk handwriting:\n\n"
            f'"{formatted_exercise}"\n\n'
            f"Ensure every single word, blank space, and option letter (A, B, C, D) is sharp, centered on the board, and perfectly legible. "
            f"ABSOLUTELY DO NOT alter any other elements of the chalkboard or background."
        )

