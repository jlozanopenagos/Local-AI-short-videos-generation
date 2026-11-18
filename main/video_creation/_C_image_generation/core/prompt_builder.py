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

import json
import logging
import re
import time
from typing import Optional, Dict, Any, Tuple

# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
from openai import OpenAI

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

The generated image must visually communicate the real-world situation, human emotion, \
narrative action, and core story moment of the Short.

CORE PRINCIPLE

Understand the meaning of the entire Short before creating the visual prompt.

Do not simply illustrate individual words.

Identify:
- the main real-world situation
- the authentic human stakes and dilemma
- the important action
- the emotional state
- the visual metaphor when appropriate
- the most recognizable moment
- the main subject of the scene

Then create a coherent image that communicates these ideas naturally.

VISUAL STORYTELLING

The image should look like a frame taken from a vibrant, professionally animated \
short-form visual story.

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

Describe characters naturally, specifically, and charmingly.

MANDATORY HIGH SCHOOL PROTAGONIST DIRECTIVE (15–16 YEARS OLD — SITUATION-APPROPRIATE ATTIRE):
- ALL main characters across EVERY scene MUST be stylish 2D cartoon high school students (approx. 15–16 years old, tall slender proportions, expressive youthful features).
- STRICT PROHIBITION ON MATURE ADULTS:
  * NEVER depict middle-aged people, elderly individuals, mature grown-ups, or weathered adult faces with wrinkles.
- MANDATORY THEMATIC WARDROBE (CLOTHING MUST BE EXPLICITLY THEMED TO THE SCENE):
  * The character's clothing MUST visibly and unmistakably match the specific thematic setting and narrative scene. NEVER use generic modern street clothes!
    - In theater / performing arts (e.g. EE01): theatrical stage costume, dramatic performance wear, ornate stage vest, performer capelet/waistcoat, or theatrical rehearsal outfit with costume accessories. NEVER plain street clothes or generic casual hoodies/t-shirts!
    - In culinary / kitchen: authentic crisp chef coat or artisan cooking apron with rolled sleeves and neckerchief.
    - In architecture / design studio: technical drafting vest, designer workshop smock with mechanical pencils in pocket, or sleek architect studio coat.
    - In science / lab / research: crisp student laboratory coat, researcher vest, or academic field smock.
    - In music / audio studio: vintage sound technician jacket, musician stage vest, headphones draped around neck.
    - In artisan / craft workshop: heavy leather maker apron, tool harness, sturdy craftsman workwear.
  * STRICT BAN ON GENERIC CLOTHES: Strictly ban plain modern t-shirts, plain hoodies, jeans, and nondescript street clothes when an authentic setting is established! The wardrobe must visually reinforce the theme!

Include relevant details such as:
- approximate age (high school student, 15-16 years old, tall slender build)
- gender when relevant
- appearance
- hairstyle
- situation-appropriate clothing (thematic costume/wardrobe matching the scene, NO plain street clothes)
- facial expression
- body language
- action
- interaction with other characters

Characters should look natural, expressive, and believable in 2D animation.

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

Use: clean modern 2D cartoon animation style, polished narrative illustration, expressive characters with large clear eyes (visible white sclera and specular pupil highlights), rich detailed interior background environment with depth, vibrant atmospheric lighting, readable silhouettes. Strictly ban dot eyes, minimalist faces, and solid color backgrounds.

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
- Instead, depict pure real-life human situations and relatable visual storytelling (e.g. someone examining a curious artifact, someone gesturing during an active demonstration, someone celebrating with a proud smile in their environment). The image must be 100% text-free, screen-free, and board-free!

ANTI-CLICHÉ & ANTI-CAFETERIA DIRECTIVE:
- NEVER default to a generic cafeteria, coffee shop, or cafe table unless the script explicitly and specifically mentions ordering coffee, a barista, or a cafe setting.
- STRICTLY BAN OVERUSED AI CLICHÉS: NO greenhouses, NO conservatories, NO plant nurseries, NO generic classrooms, NO school lecture rooms, NO generic flower shops, NO pottery/ceramic studios.
- ALL SCENES IN THIS SHORT MUST BELONG TO THE SAME COHESIVE PHYSICAL STORY WORLD. Do not randomly switch rooms or environments between scenes!

MANDATORY MULTI-CHARACTER GENDER SPECIFICATION (ZERO-AMBIGUITY RULE):
- Whenever MORE THAN ONE character appears in the image (in ROLEPLAY, EXPRESSION, GAME, or any video type):
  * The sex/gender of EACH character MUST be explicitly and unambiguously specified!
  * STRICTLY BAN collective, ambiguous, or generic gender-neutral words: NEVER say "the two teens", "two youthful teenage characters", "two colleagues", "two students", "two friends", "the characters", or "they".
  * ALWAYS explicitly describe each individual character: e.g. "one youthful 15-year-old teen boy with masculine features wearing [wardrobe] and one youthful 15-year-old teen girl with feminine features wearing [wardrobe]" (or "two youthful teen boys", or "two youthful teen girls").
  * For ROLEPLAY videos: You MUST strictly adhere to the exact assigned genders for PERSON_ONE and PERSON_TWO. NEVER swap their genders, and NEVER make them identical unless explicitly instructed!

FINAL OBJECTIVE

The image must:
- communicate the situation immediately
- visually ground the action in its authentic real-world environment
- feel natural and believable
- have a clear focal point
- work well in vertical 9:16 format
- leave reasonable space for subtitles
- be visually interesting without becoming cluttered
- match the emotional tone of the narration
"""


# ── Storyboard Director System Prompt ─────────────────────────────────────────

_STORYBOARD_DIRECTOR_SYSTEM_PROMPT = """\
ROLE

You are the Lead Visual Storyboard Director and Concept Artist for an elite YouTube Shorts animation channel.
Your task is to transform a complete language-learning video script into a fully realized, 5-scene visual storyboard.

For each scene of the Short, you will produce one distinct, rich, positive Z-Image-Turbo prompt.

CRITICAL DIRECTIVES FOR COMPLETE SCENE UNIQUENESS & FAITHFUL SCRIPT ENACTMENT:

1. NARRATIVE FAITHFULNESS TO THE SCRIPT TEXT & DIALOGUE (HIGHEST PRIORITY):
   - Every single scene prompt MUST directly visualize the specific dialogue lines, narrative beat, and emotional meaning occurring in that scene's text!
   - Read what the characters are actually saying and doing in each scene:
     * What is the specific question, confusion, native explanation, or example in this beat?
     * Depict physical, tangible actions using realistic props from the setting (e.g. holding a script, pointing to text/schedule, demonstrating with tools or equipment, reacting with expressive eyes and body language).
     * STRICTLY BAN SURREAL / ABSTRACT FANTASY EFFECTS: Do NOT invent glowing energy beams from chests, floating sound wave graphics, glowing magic auras, or abstract fantasy elements unless the script is explicitly fantasy/sci-fi! Keep every action authentic, tangible, and believable in the established story world.
     * STRICTLY BAN BOILERPLATE CLICHES: Do NOT default to generic hand gestures, "explaining a concept" without showing what they are discussing, or automatic high-fives in every scene. The action must be uniquely tied to that scene's dialogue!

2. ABSOLUTE STORY WORLD, ENVIRONMENT & CHARACTER CONTINUITY (MANDATORY IN EVERY SCENE):
   - Diffusion models generate EACH scene image independently from scratch with zero memory of previous scenes!
   - ABSOLUTE PHYSICAL ENVIRONMENT CONTINUITY (CRITICAL PRECEDENCE):
     * The master setting, physical location, architecture, background props, and atmosphere established in the OVERARCHING GENERAL PROMPT / MASTER STORY WORLD anchor MUST be strictly maintained across EVERY single scene prompt!
     * NEVER change or relocate the scene to a different environment (e.g. if the story world is a vintage park skate plaza, ALL scenes MUST remain in that skate plaza/park; NEVER switch the scene to a kitchen, school, or other room, even if food or another subject is mentioned in the dialogue).
     * Micro-zone diversity within that established setting is strongly encouraged (e.g. moving naturally from the concrete skate bowl to the park bench, to the rails), but the overarching location is 100% locked.
   - To guarantee 100% character visual consistency (no shifting hair colors, no shifting clothes, no shifting skin tones, no shifting ages):
     * EVERY SINGLE SCENE PROMPT MUST EXPLICITLY REPEAT THE EXACT SAME VISUAL TRAITS FOR EACH CHARACTER:
       - Exact demographic & skin tone: e.g. "15-year-old high-school student girl with fair peach skin", "15-year-old high-school student boy with warm tan skin" (tall slender high school proportions, defined facial features). NEVER omit skin tone, otherwise camera angle changes (like close-up hooks) will drift into a completely different ethnicity!
       - Exact eye color: e.g. "expressive dark brown cartoon eyes", "warm hazel cartoon eyes".
       - Exact hair color AND exact hairstyle: e.g. "dark hair in a sleek bun", "textured dark-brown quiff hair with clean tapered sides" (NEVER change or omit hair color or styling!).
       - Exact wardrobe and garment colors: e.g. "wearing her emerald velvet blazer over white shirt", "wearing his denim utility vest over charcoal long-sleeve" (NEVER change or omit wardrobe!).
       - Exact staging: Character 1 on the LEFT, Character 2 on the RIGHT.
     * NEVER omit the characters' skin tone, eye color, hair color, hairstyle, or wardrobe in any scene prompt, otherwise the image generation model will randomly invent different ethnicities, hair, and clothes!
   - Natural staging variations: Characters move naturally across the set (e.g. from the drafting table to the camera rig, to the terrace railing overlook) without artificially teleporting to incompatible rooms.

3. PROP INTERACTION & PHYSICAL RELEVANCE:
   - Use physical objects and props that naturally belong to this scenario and reinforce the dialogue of that specific scene.
   - Rotate focal interaction across scenes so each scene features a distinct, identifiable physical action or visual center of attention.

4. EXPRESSIVE FACIAL ACTING & DIVERSE POSTURES:
   - Convey the exact emotional arc from the script through expressive facial design:
     * Hook: Opening tension, stress, urgent inquiry, or intrigued curiosity reflecting the opening problem.
     * Setup: Puzzled, questioning, or amused exchange, comparing concepts or reacting to doubt.
     * Discovery / Demonstration: Eureka clarity, wide joyful eyes, active physical demonstration of the native rule.
     * Example: Full kinetic motion depicting the exact verb or example situation from the narration.
     * Payoff: Confident mastery, warm satisfaction, triumphant conclusion of the scenario.

5. ARCHETYPE VISUAL GRAMMAR & CAMERA FRAMING (MANDATORY FORMAT FINGERPRINT):
   - In 9:16 vertical video, never use distant wide shots where characters shrink into tiny figures! Keep characters comfortably waist-up or chest-up so their facial expressions and eyes remain large, clear, and detailed.
   - You MUST strictly apply the unique Archetype Visual Grammar tailored to each video type:

     * FOR GAME SHORTS (SYMMETRICAL DILEMMA & TENSION PROGRESSION):
       - Hook [THE LIVELY DILEMMA]: Dynamic 3/4 eye-level medium shot with warm cinematic depth. The 16yo student protagonist has a natural healthy athletic build and is caught in an active, energetic moment of clever curiosity and playful dilemma, weighing two choices with engaging personality. Lively expressive face with an amused raised eyebrow, slight thinking smile, head tilted curiously, and warm animated eyes full of life and spark (NEVER wide bug eyes, NEVER staring, NEVER unexpressive deadpan face).
       - Answer [THE EUREKA BREAKTHROUGH]: Dynamic asymmetrical breakthrough moment! Protagonist radiates joyful relief, confident smile, and forward kinetic momentum in the authentic setting.
       - Explanation: Real-world application showing natural confident usage.

     * FOR EXPRESSION SHORTS (LAYERED DEPTH & INSIDER REVELATION PROGRESSION):
       - Hook [THE INSIDER GUIDE]: 35mm angled foreground-and-background depth composition (Rule of Thirds). The 15yo student protagonist occupies the foreground left or right (35-40%), turned 3/4 toward the viewer with an engaging, playful knowing smile and warm animated cartoon eyes, sharing an insider secret with natural relaxed facial acting (subtle amused smirk, lively curious gaze, NEVER bulging eyes, NEVER staring rounded eyes) breaking the fourth wall. The luminous midground and deep background (60%) reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.
       - Setup [SOCIAL CONTRAST]: Two-shot profile angle across a table/counter demonstrating the conversational friction or literal misunderstanding.
       - Discovery [EUREKA BREAKTHROUGH]: Medium action shot at a demonstration station. Radiant smile of sudden clarity and understanding.
       - Example [LIVING KINETIC MOTION]: Dynamic wide action shot actively demonstrating the exact verb or example situation in full motion.
       - Payoff [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment.

     * FOR ROLEPLAY SHORTS (DYNAMIC 6-BEAT CINEMATIC DIALOGUE PROGRESSION):
       - Hook [SCENARIO THRESHOLD TWO-SHOT]: Medium-wide 35mm diagonal shot crossing a physical threshold (archway, curtain edge, counter). STRICTLY ZERO FOURTH-WALL EYE CONTACT. Characters interact exclusively with each other in situational tension.
       - Dialogue_Part_1 [SOLO TIGHT CLOSE-UP ON PERSON_ONE]: 85mm portrait lens, shallow depth of field, dramatic key lighting, expressive facial acting on PERSON_ONE showing dilemma or questioning (PERSON_TWO is strictly off-camera).
       - Dialogue_Part_2 [SOLO 180° REVERSE-ANGLE CLOSE-UP ON PERSON_TWO]: 85mm portrait lens, 180° reverse angle, warm fill light, calm reassuring mentorship and guidance on PERSON_TWO (PERSON_ONE is strictly off-camera).
       - Dialogue_Part_3 [90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION]: 50mm lens. The camera shifts 90° to a side-profile or high-angle table overview showing BOTH characters actively examining or manipulating an authentic physical prop from the setting. Breaks the solo close-up sequence with collaborative interaction.
       - Dialogue_Part_4 [SOLO WAIST-UP DYNAMIC ACTION ON PERSON_ONE]: 28mm/50mm lens. Distinct waist-up dynamic action framing (completely different camera distance and physical stance from the tight close-up in Part 1) capturing PERSON_ONE gesturing with clarity, confidence, and determination (PERSON_TWO is strictly off-camera).
       - Payoff [CELEBRATORY TWO-SHOT]: 28mm wide cinematic lens, dramatic backlighting, shared celebratory triumph in motion.

     * FOR FUN_FACTS SHORTS (SCALE OF WONDER PROGRESSION):
       - Hook [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking up from floor level. Protagonist in lower third looking upward in jaw-dropped awe at an imposing, towering cultural anomaly or historic marvel. Upward gaze, volumetric lighting shafts, monumental scale contrast.
       - Setup / Discovery: Collaborative inspection and dynamic reveal of the fascinating historical discovery in motion.
       - Payoff: Mind-blown celebratory outro celebrating trivia mastery.

6. CREATIVE VISUAL METAPHORS & GRAPHIC WORDPLAY (MANDATORY TO AVOID BORING IMAGES):
   - The visual image is the primary hook that attracts and retains the audience! Never produce boring, generic images of a character just looking stressed or staring at a paper/desk.
   - Embrace the GRAPHIC / LITERAL SENSE of words and expressions across the scenes to make them entertaining, memorable, and fun:
     * For 'a piece of cake': Visually play with a giant, colorful, towering multi-tiered cake or an ambitious baking challenge that is effortlessly mastered!
     * For 'break a leg': An opulent theater stage with dramatic velvet curtains, costume masks, and rehearsal props.
     * For 'PREsent vs preSENT': A grand banquet hall where a teen dramatically reveals an ornate ribbon-wrapped gift box (strictly permitted ONLY for the heteronym 'present').
     * For 'proJECT vs PROject': A rooftop film shoot with camera gear, director clapperboard, and megaphone.
     * For 'spill the beans': A vibrant artisan kitchen where a huge jar of colorful legumes has comically tipped over, revealing a secret discovery.
     * For 'cost an arm and a leg': A lavish high-end boutique with humorous exaggerated luxury displays.
   - We have creative license to play with words and visual metaphors across the scenes to make every image dynamic, eye-catching, and fun!
   - STRICT BAN ON LAZY PROP CLICHÉS: NEVER use generic ribbon-wrapped gift boxes, mystery boxes, or present parcels as a lazy fallback prop! Gift boxes are strictly reserved for the heteronym 'present'. In all other videos, characters must interact with authentic physical objects naturally found in that setting (e.g. luggage/tickets for travel, cookware/platters for culinary, blueprints/tablets for design, instruments/records for music).

6. ZERO-TOLERANCE TEXT, LETTER, SCREEN & INTERJECTION BAN (CRITICAL):
   - NEVER include words like 'aha', 'eureka', 'wow', 'oops', or any words inside quotation marks.
   - NEVER mention the target words, foreign phrases, minimal pair terms (e.g. NEVER write 'anno and ano', 'break a leg'), spelling, or alphabet letters (e.g. NEVER write 'the letter N', 'double N', 'holding letter A') in any scene prompt!
   - Text encoders in diffusion models interpret quoted words, foreign phrases, and letter names as literal typography commands and will paint garbled pseudo-text onto the characters' clothing, faces, props, or background!
   - Describe purely visual physical acting, natural prop interactions from the setting, and facial expressions: e.g. 'eyes widening in breakthrough understanding', 'a bright smile of sudden clarity', 'gesturing dynamically near an authentic prop'.
   - NEVER depict chalkboards, blackboards, whiteboards with words, posters, screens displaying UI/text, tablets with text, monitors, timers, or letters (A, B, C, D). Image must be 100% text-free and letter-free!

7. MANDATORY 2D CARTOON ART STYLE (STRICT NO REALISM):
   - Every scene MUST look like a frame from a stylized 2D cartoon narrative illustration, hand-drawn 2D animation art style, with vibrant flat colors, clean lineart, and storybook charm.
   - ABSOLUTELY FORBIDDEN: Photorealism, realistic photos, 3D renders, CGI, real-life photography.

8. STRICT ANTI-CLICHÉ & ANTI-GENERIC BAN (CRITICAL):
   - ABSOLUTELY BANNED SCENARIOS: Strictly DO NOT generate or default to the following overused AI clichés:
     * NO greenhouses, conservatories, glasshouses, plant nurseries, or rooms filled with potted plants (unless the script is explicitly about gardening or botany).
     * NO generic empty classrooms, school desks, teacher blackboards, or academic lecture rooms (unless the script explicitly describes a school lesson).
     * NO generic flower shops, pottery/ceramic workshops, or random flea markets.
     * NO generic modern coffee shops, cafe tables, or barista counters (unless the script explicitly mentions ordering coffee or a cafe setting).
   - AUTHENTIC REAL-WORLD DIVERSITY: Always ground the setting directly in the authentic cultural, vocational, or narrative domain established in the Master Story World / General Prompt!

9. HIGH-FIDELITY CHARACTER FACIAL QUALITY (STRICT BAN ON DOT EYES / MINIMALIST FACES):
   - Characters across ALL scenes must maintain consistent, high-end 2D cartoon animation fidelity.
   - Every character must have large, clearly defined anime-cartoon eyes with visible white sclera and specular pupil highlights, expressive eyebrows, and clean line art.
   - ABSOLUTELY FORBIDDEN: Dot eyes, bead eyes, button eyes, flat minimalist stick faces, or featureless faces! Every character across every scene must look as polished and expressive as a modern 2D animated feature film.

10. ENVIRONMENTAL BACKGROUND RICHNESS (STRICT BAN ON SOLID COLOR / EMPTY BACKDROPS):
   - Every scene prompt MUST describe the physical background interior environment:
     * Architecture, furniture (e.g. wooden drafting desk, tool workbench, books on shelves), indoor depth, textured walls, atmospheric ambient lighting, and soft cast shadows.
   - ABSOLUTELY FORBIDDEN: Solid color backgrounds, plain white voids, flat empty backdrops, or isolated characters on blank walls! Even close-up shots MUST have rich background room depth.

11. MANDATORY HIGH SCHOOL DEMOGRAPHIC & THEMATIC WARDROBE:
    - All main characters across every scene MUST be stylish 2D cartoon high school students (approx. 15–16 years old, tall slender proportions).
    - STRICTLY FORBIDDEN: Middle-aged adults, elderly faces, or mature adult wrinkles.
    - THEMATIC COSTUME & WARDROBE: The character's clothing MUST explicitly match the physical environment (e.g. theater stage costume/waistcoat in theater, chef coat in kitchen, drafting smock in studio, lab coat in science). NEVER depict plain generic modern street clothes (plain t-shirts/hoodies)!

12. MANDATORY MULTI-CHARACTER GENDER SPECIFICATION (ZERO-AMBIGUITY RULE):
    - Whenever MORE THAN ONE character appears in any scene (in ROLEPLAY, EXPRESSION, GAME, or any video type):
      * The sex/gender of EACH character MUST be explicitly and unambiguously specified!
      * STRICTLY BAN collective, ambiguous, or generic gender-neutral words: NEVER say "the two teens", "two youthful teenage characters", "two colleagues", "two students", "two friends", "the characters", or "they".
      * ALWAYS explicitly describe each individual character: e.g. "one youthful 15-year-old teen boy with masculine features wearing [wardrobe] and one youthful 15-year-old teen girl with feminine features wearing [wardrobe]" (or "two youthful teen boys", or "two youthful teen girls").
      * For ROLEPLAY videos: You MUST strictly adhere to the exact assigned genders for PERSON_ONE and PERSON_TWO. NEVER swap their genders, and NEVER make them identical unless explicitly instructed!

OUTPUT FORMAT:
You MUST output ONLY a valid JSON object mapping each scene name (in lowercase, e.g. "hook", "setup", "discovery", "example", "payoff" or for roleplay: "hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff") to its final Z-Image-Turbo prompt string. Do not include markdown code block formatting or explanations outside the JSON object.
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
            "BRAND PALETTE MOOD (ENGLISH): Warm, vibrant, natural, cinematic.\n"
            "Key Accent Colors: Forest Green, Warm Ochre, Rich Amber, Slate Blue, Cream.\n"
        )

HETERONYM_DOMAINS = {
    "record": "acoustic music recording studio and audio production facility (featuring: sound control board, vocal tracking booth, live acoustic instrument room, vinyl listening lounge)",
    "permit": "metropolitan transit center and security checkpoint (featuring: vehicle entry barrier, administrative security desk, transit concourse, credential booth)",
    "project": "modern creative design and architectural innovation agency (featuring: drafting workstation, collaborative conference lounge, fabrication workbench, luminous presentation space)",
    "present": "festive celebration banquet hall or elegant reception venue (featuring: banquet dining table, presentation stage, gift alcove, outdoor terrace)",
    "object": "curiosity archives and historical appraisal chamber (featuring: specimen display cabinets, study desk, appraisal reference library, gallery room)",
    "contract": "executive law library or dynamic sports management facility (featuring: consultation desk, document archive, client lounge, athletic training arena)",
    "conduct": "symphony concert hall or scientific physics laboratory (featuring: orchestra podium, acoustic seating, research workstation, demonstration table)",
    "desert": "golden sand dune expedition camp (featuring: canvas safari tent, navigational map table, shaded campfire circle, desert overlook)",
    "increase": "bustling commercial logistics center or tech analytics trading office (featuring: dispatch floor, analytics whiteboard, trading station, logistics overview deck)",
    "decrease": "energy conservation laboratory or quiet evening study (featuring: efficiency monitoring workstation, resource optimization desk, quiet reading area)",
    "import": "international cargo shipping port and freight terminal (featuring: harbor viewing deck, customs office desk, container loading dock, logistics lounge)",
    "export": "international cargo shipping port and freight terminal (featuring: logistics dispatch desk, maritime harbor overlook, cargo staging area, freight gate)",
    "protest": "historic civic community hall or public city plaza (featuring: assembly stage, creative banner workshop, public steps, town hall courtyard)",
    "refuse": "sustainable design workshop and upcycling studio (featuring: material sorting station, fabrication bench, upcycled product gallery, design desk)",
    "rebel": "vintage printmaking atelier or underground creative studio (featuring: mechanical printing press, paper drafting table, typeset drawer wall, studio lounge)",
    "address": "formal conference auditorium or classic epistolary study (featuring: podium stage, library writing desk, correspondence cabinet, reading alcove)",
}

EXPLICIT_SCENARIO_DOMAINS = [
    (r'\b(animation studio|animator|animation desk|storyboard room)\b', "creative modern animation studio at night (featuring: animator drawing desks with digital pen displays, animation lightboxes, pencil sketches pinned to corkboards, glowing monitors with timeline tracks, comfortable studio chairs, warm desk lamps against dark ambient room)"),
    (r'\b(rooftop cinema|cinema shoot|film shoot|movie set|film set)\b', "architectural rooftop cinema shoot at dusk (featuring: director clapperboards, brass megaphone, camera tripods, blueprint rolls, warm amber string lights, twilight skyline)"),
    (r'\b(bakery|bake|baker|pastry)\b', "warm artisan culinary bakery (featuring: rustic wooden prep counter, baker oven alcove, flour dusting on table, cooling racks)"),
    (r'\b(theater|theatre|stage|acting|backstage|curtain|actor|show|rehearsal)\b', "historic theater and performing arts center (featuring: backstage wings, rehearsal stage, dressing room with mirror, grand auditorium)"),
    (r'\b(kitchen|cook|chef|dessert|ingredient|dish|oven)\b', "warm artisan culinary kitchen (featuring: rustic wooden prep counter, cookware rack, dining table, pantry alcove)"),
    (r'\b(library|exam|study|student|homework|grade|assignment|textbook)\b', "university academic library (featuring: individual study carrel, collaborative reference desk, book stacks, reading lounge)"),
    (r'\b(airport|flight|plane|airplane|travel|suitcase|boarding|luggage)\b', "modern international airport terminal (featuring: panoramic tarmac lounge, check-in concourse, boarding gate, baggage reclaim)"),
    (r'\b(train|station|subway|metro|platform|railway)\b', "scenic railway station (featuring: passenger platform, ticketing hall, waiting concourse, vintage trackside bench)"),
    (r'\b(hospital|doctor|clinic|medical|patient|nurse|consultation)\b', "bright modern wellness and medical consultation clinic (featuring: examination room, consultation desk, waiting lounge)"),
    (r'\b(street|city|avenue|plaza|sidewalk|urban|crosswalk|boulevard)\b', "bustling historic city avenue (featuring: pedestrian sidewalk, brick storefronts, street corner plaza, park bench)"),
    (r'\b(park|garden|nature|tree|bench|flower|outdoor|trail)\b', "sunlit municipal park promenade (featuring: walking promenade, historic stone balustrade, shaded wooden bench, open lawn)"),
    (r'\b(gym|workout|fitness|sport|athletic|exercise|dumbbells)\b', "dynamic modern athletic training gym (featuring: fitness floor, weights zone, training track, recovery lounge)"),
    (r'\b(market|store|boutique|seller|bazaar|craft)\b', "neighborhood artisan market boutique (featuring: craft display table, checkout counter, goods shelf, street awning)"),
    (r'\b(beach|sea|ocean|coastal|boat|sand|shore)\b', "sunlit coastal seaside promenade (featuring: ocean overlook deck, sand dunes path, beach pavilion)"),
    (r'\b(cafe|coffee|barista|latte|espresso)\b', "charming artisanal coffee bar (featuring: espresso counter, window high-top bar, cozy seating corner)"),
]


def is_figurative_idiom(
    topic: str = "",
    lexical_field: str = "",
    scenario: str = "",
    script_text: str = "",
) -> bool:
    """Detects if the script is about an idiom or figurative expression across languages."""
    combined = f"{topic} {lexical_field} {scenario} {script_text}".lower()
    idiom_markers = [
        "idiom", "saying", "figurative", "slang", "proverb",
        "dicho", "modismo", "idiotismo", "refrán", "locución idiomática",
        "idiomatic expression", "expression idiomatique", "expresión idiomática",
        "piece of cake", "break a leg", "bite the bullet", "spill the beans",
        "under the weather", "cost an arm and a leg", "burn the midnight oil",
        "hit the nail on the head", "once in a blue moon", "barking up the wrong tree",
        "cold feet", "see eye to eye", "ball is in your court", "cross that bridge",
        "call it a day", "cut corners", "easy as pie", "drop in the ocean",
        "rule of thumb", "through the grapevine", "pull someone's leg",
        "actions speak louder", "beat around the bush", "blessing in disguise",
        # Multilingual Idioms
        "poser un lapin", "yeux de la tête", "coup de foudre", "dans les pommes", "du gâteau",
        "costar un ojo", "ojo de la cara", "tomar el pelo", "en las nubes", "pan comido",
        "in bocca al lupo", "occhio della testa", "mani bucate", "lucciole per lanterne",
    ]
    return any(marker in combined for marker in idiom_markers)


def resolve_anchor_environment(
    script_text: str,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    label: str = "",
    video_type: str = "EXPRESSION"
) -> str:
    """
    Deduces a vivid, concrete, and consistent physical anchor environment for the script.
    Prevents the LLM from falling back to generic cafeterias or flipping locations between scenes.
    """
    combined_meta = f"{topic} {scenario} {lexical_field} {label}".lower()
    combined_script = f"{combined_meta} {script_text}".lower()

    # 1. Check explicit scenario / setting keywords first (highest priority)
    for pattern, domain in EXPLICIT_SCENARIO_DOMAINS:
        if scenario and re.search(pattern, scenario.lower()):
            return domain
        if topic and re.search(pattern, topic.lower()):
            return domain

    # 2. Check known heteronym / word stress domain mappings (only if topic is specifically that heteronym)
    for word_key, domain in HETERONYM_DOMAINS.items():
        if re.search(r'\b' + re.escape(word_key) + r'\b', topic.lower()):
            return domain

    # 2. Check for figurative idioms (Allows creative graphic visual metaphors)
    if is_figurative_idiom(topic, lexical_field, scenario, script_text):
        if any(w in combined_script for w in ("piece of cake", "easy as pie", "pan comido", "du gâteau")):
            return "chic modern social dining salon or studio lounge (featuring: central display table showcasing an elaborate towering multi-tier cake with a single slice removed, stylish seating lounge, sunlit terrace)"
        elif any(w in combined_script for w in ("break a leg", "in bocca al lupo")):
            return "historic theater and performing arts center (featuring: dressing room with mirror, backstage wings with velvet curtains, rehearsal stage, grand auditorium)"
        elif "spill the beans" in combined_script:
            return "vibrant artisan kitchen and social pantry lounge (featuring: open prep counter with oversized ceramic bean jars, cozy banquette table, sunlit courtyard)"
        elif any(w in combined_script for w in ("under the weather", "dans les pommes")):
            return "cozy sunlit living room and wellness study (featuring: comfortable sofa with warm knitted throw, warm ceramic tea mugs on a low wooden table, soft reading window, warm fireplace mantle)"
        elif "burn the midnight oil" in combined_script:
            return "quiet late-night home study and creative library (featuring: vintage wooden desk with brass lamp, tall bookshelves, armchair, evening city skyline window)"
        elif any(w in combined_script for w in ("cost an arm and a leg", "ojo de la cara", "yeux de la tête", "occhio della testa")):
            return "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"
        elif "poser un lapin" in combined_script:
            return "charming historic bistro exterior and clock tower plaza (featuring: outdoor cafe table with an untouched cup, historic clock face showing late time, cobblestone promenade)"
        return "vibrant modern creative studio and everyday living space (featuring: focus work area, collaborative lounge, demonstration bench, sunlit terrace)"

    # 3. Check for explicit keyword domains in script text and metadata
    keyword_domains = [
        (r'\b(theater|theatre|stage|acting|backstage|curtain|actor|show|rehearsal)\b', "historic theater and performing arts center (featuring: backstage wings, rehearsal stage, dressing room, auditorium)"),
        (r'\b(kitchen|cook|bake|recipe|chef|dessert|ingredient|dish|oven)\b', "warm artisan culinary kitchen (featuring: rustic wooden prep counter, cookware rack, dining table, pantry alcove)"),
        (r'\b(library|exam|study|student|homework|grade|assignment|textbook)\b', "university academic library (featuring: individual study carrel, collaborative reference desk, book stacks, reading lounge)"),
        (r'\b(office|workplace|colleague|coworker|meeting|boss|presentation|company|corporate)\b', "modern corporate creative studio (featuring: brainstorming desk, glass conference room, presentation hall, office lounge)"),
        (r'\b(airport|flight|plane|airplane|travel|suitcase|boarding|luggage)\b', "modern international airport terminal (featuring: panoramic tarmac lounge, check-in concourse, boarding gate, baggage reclaim)"),
        (r'\b(train|station|subway|metro|platform|railway)\b', "scenic railway station (featuring: passenger platform, ticketing hall, waiting concourse, vintage trackside bench)"),
        (r'\b(hospital|doctor|clinic|medical|patient|nurse|consultation)\b', "bright modern wellness and medical consultation clinic (featuring: examination room, consultation desk, waiting lounge)"),
        (r'\b(street|city|avenue|plaza|sidewalk|urban|crosswalk|boulevard)\b', "bustling historic city avenue (featuring: pedestrian sidewalk, brick storefronts, street corner plaza, park bench)"),
        (r'\b(park|garden|nature|tree|bench|flower|outdoor|trail)\b', "sunlit municipal park promenade (featuring: walking promenade, historic stone balustrade, shaded wooden bench, open lawn)"),
        (r'\b(gym|workout|fitness|sport|athletic|exercise|dumbbells)\b', "dynamic modern athletic training gym (featuring: fitness floor, weights zone, training track, recovery lounge)"),
        (r'\b(market|store|boutique|seller|bazaar|craft)\b', "neighborhood artisan market boutique (featuring: craft display table, checkout counter, goods shelf, street awning)"),
        (r'\b(beach|sea|ocean|coastal|boat|sand|shore)\b', "sunlit coastal seaside promenade (featuring: ocean overlook deck, sand dunes path, beach pavilion)"),
        (r'\b(cafe|coffee|barista|latte|espresso)\b', "charming artisanal coffee bar (featuring: espresso counter, window high-top bar, cozy seating corner)"),
    ]

    for pattern, domain in keyword_domains:
        if re.search(pattern, combined_script):
            return domain

    # 4. Authentic modern everyday setting fallback (NON-cafeteria, NON-classroom, NON-greenhouse)
    return "vibrant modern creative studio and cultural study lounge (featuring: collaborative work table, conversation lounge, reference bookshelf, architectural drafting desk, sunlit terrace window)"


def get_speaker_gender_safe(speakers_gender: dict, role: str, default: str = "") -> str:
    """
    Safely retrieves a speaker's gender from speakers_gender dictionary
    handling any case variations (e.g. 'Narrator', 'NARRATOR', 'narrator',
    'PERSON_ONE', 'person_one', 'Person_1', etc.) or named speakers.
    """
    if not speakers_gender or not isinstance(speakers_gender, dict):
        return default

    # 1. Exact match
    if role in speakers_gender and speakers_gender[role]:
        return str(speakers_gender[role]).strip()

    role_norm = role.lower().replace(" ", "").replace("_", "")

    # 2. Case-insensitive / normalized match
    for k, v in speakers_gender.items():
        if not v:
            continue
        k_norm = str(k).lower().replace(" ", "").replace("_", "")
        if k_norm == role_norm:
            return str(v).strip()

    # 3. Fuzzy role matching
    if role_norm in ("narrator", "personone", "person1", "p1", "protagonist"):
        for k, v in speakers_gender.items():
            if not v:
                continue
            k_lower = str(k).lower()
            if "narrator" in k_lower or "one" in k_lower or k_lower in ("p1", "lead"):
                return str(v).strip()
        # Single-speaker fallback: if exactly 1 speaker exists, use it
        if len(speakers_gender) == 1:
            return str(next(iter(speakers_gender.values()))).strip()
        if speakers_gender:
            return str(next(iter(speakers_gender.values()))).strip()

    elif role_norm in ("persontwo", "person2", "p2", "counterpart", "companion"):
        for k, v in speakers_gender.items():
            if not v:
                continue
            k_lower = str(k).lower()
            if "two" in k_lower or k_lower in ("p2", "companion", "peer"):
                return str(v).strip()
        # If there are 2 or more speakers, return the second speaker's gender
        if len(speakers_gender) >= 2:
            vals = list(speakers_gender.values())
            return str(vals[1]).strip()

    return default


def _extract_shared_story_context(
    script_text: str,
    language: str,
    label: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_personalities: dict = None,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    anchor_environment: str = "",
    general_prompt: str = "",
    character_anchors: dict = None,
) -> dict[str, Any]:
    """
    Extracts and standardizes shared narrative context across single-scene and multi-scene storyboard builders:
    - Resolves anchor environment
    - Voiceover isolation notice
    - Character personalities
    - Mandatory speaker genders (authoritatively anchored to General Prompt / character anchors)
    - Target language brand palette
    - Metadata topic/scenario/lexical context lines
    - Figurative idiom directive
    """
    video_type_upper = video_type.upper()
    if not anchor_environment:
        anchor_environment = general_prompt or resolve_anchor_environment(
            script_text=script_text,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            label=label,
            video_type=video_type,
        )

    voiceover_notice = ""
    personality_context = ""
    if video_type_upper == "ROLEPLAY":
        if character_personalities:
            pers_lines = [f"- {spk}: {pers}" for spk, pers in character_personalities.items() if spk != "Narrator"]
            if pers_lines:
                personality_context = "ACTING CHARACTERS IN SCENE:\n" + "\n".join(pers_lines) + "\n\n"
    else:
        voiceover_notice = (
            "VOICEOVER ISOLATION (MANDATORY):\n"
            "The Narrator is strictly an OFF-SCREEN AUDIO VOICEOVER. Do NOT illustrate a narrator, "
            "host, teacher, mentor, presenter, creator, or lecturer talking to the camera! "
            "Instead, the visual scene MUST depict real everyday human characters actively living out "
            "the authentic real-world situation described in the scene.\n\n"
        )
        if character_personalities:
            acting_chars = [f"- {spk}: {pers}" for spk, pers in character_personalities.items() if spk != "Narrator"]
            if acting_chars:
                personality_context = "ACTING CHARACTERS IN SCENE:\n" + "\n".join(acting_chars) + "\n\n"

    # Authoritative character anchors resolution (General Prompt is single source of truth)
    char_anchors = extract_or_build_character_anchors(
        general_prompt=general_prompt or anchor_environment,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_anchors=character_anchors,
    )
    p1_is_female = char_anchors.get("p1_is_female", False)
    p2_is_female = char_anchors.get("p2_is_female", not p1_is_female)
    p1_word = char_anchors.get("gender_word1") or ("girl" if p1_is_female else "boy")
    p2_word = char_anchors.get("gender_word2") or ("girl" if p2_is_female else "boy")
    has_two = char_anchors.get("has_two_characters") in (True, "True") or video_type_upper == "ROLEPLAY"

    if has_two:
        p1_desc = f"high school student {p1_word} (approx. 15-16 years old, tall slender build, stylish thematic attire)"
        p2_desc = f"high school student {p2_word} (approx. 15-16 years old, tall slender build, stylish thematic attire)"
        gender_context = (
            f"MANDATORY CHARACTER GENDERS & DEMOGRAPHIC (HIGH SCHOOL PROTAGONISTS — 15-16 YEARS OLD):\n"
            f"- PERSON_ONE: {p1_word.upper()} (MUST visually appear as a {p1_desc})\n"
            f"- PERSON_TWO: {p2_word.upper()} (MUST visually appear as a {p2_desc})\n"
            f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! "
            f"NEVER use generic words like 'the two students', 'two friends', or 'the characters' without stating their individual sex (e.g. 'one high school student {p1_word} and one high school student {p2_word}').\n"
            f"CRITICAL RULE: Characters are 15-16 year old high school students (tall slender proportions) dressed appropriately for this specific setting. Strictly ban generic plain t-shirts/hoodies, and strictly ban middle-aged/mature adult wrinkles!\n\n"
        )
    else:
        gender_word = p1_word
        gender_desc = f"high school student {gender_word}"
        gender_context = (
            f"MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (15-16 YEARS OLD):\n"
            f"- PROTAGONIST: MUST visually appear as an expressive high school student {gender_word.upper()} (approx. 15-16 years old {gender_desc}, tall slender proportions).\n"
            f"- WARDROBE: The {gender_word} MUST wear an authentic costume or attire explicitly matching the thematic setting (e.g. theater stage costume/vest, chef uniform, studio apron, lab coat). Strictly ban generic casual clothes (plain t-shirts/hoodies)!\n"
            f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! NEVER use generic words like 'two students' or 'friends'!\n"
            f"CRITICAL RULE: Character MUST be a {gender_word.upper()} ({gender_desc}). Strictly ban mature adult faces, wrinkles, and generic t-shirts!\n\n"
        )

    palette_context = _get_language_palette(language)

    context_lines = []
    if topic:
        context_lines.append(f"TOPIC / TARGET PHRASE: {topic}")
    if scenario:
        context_lines.append(f"SCENARIO / REAL-WORLD SETTING: {scenario}")
    if lexical_field:
        context_lines.append(f"LEXICAL FIELD: {lexical_field}")
    context_extra = "\n".join(context_lines) + "\n\n" if context_lines else ""

    idiom_rule = ""
    if is_figurative_idiom(topic, lexical_field, scenario, script_text):
        idiom_rule = (
            "CREATIVE VISUAL METAPHOR & GRAPHIC WORDPLAY DIRECTIVE:\n"
            f"This Short is about an idiom / figurative phrase ('{topic}').\n"
            "- Play with the graphic, visual sense of the expression across the scenes! Use the literal or visual imagery playfully to make the scenes entertaining and magnetic (e.g. giant towering multi-tiered cakes, dramatic theatrical props, colorful spilled jars, vintage travel luggage, hourglass timers, botanical planters).\n"
            "- AVOID BORING IMAGES: Never just show someone staring at a desk or paper looking stressed. Make the visual world lively, imaginative, and fun!\n"
            "- STRICT PROP RELEVANCE (ANTI-GIFT-BOX BAN): Ground props strictly in the environment and actual subject. NEVER use generic gift boxes, ribbon-wrapped packages, or mystery boxes as fallback props!\n\n"
        )

    return {
        "anchor_environment": anchor_environment,
        "voiceover_notice": voiceover_notice,
        "personality_context": personality_context,
        "gender_context": gender_context,
        "palette_context": palette_context,
        "context_extra": context_extra,
        "idiom_rule": idiom_rule,
        "char_anchors": char_anchors,
    }


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
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    anchor_environment: str = "",
    existing_scene_prompts: dict = None,
    general_prompt: str = "",
) -> str:
    """Build the user-facing context block sent alongside the system prompt."""
    scene_lower = scene_name.lower().strip()
    video_type_upper = video_type.upper()

    ctx = _extract_shared_story_context(
        script_text=script_text,
        language=language,
        label=label,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_personalities=character_personalities,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        anchor_environment=anchor_environment,
        general_prompt=general_prompt,
    )
    anchor_environment = ctx["anchor_environment"]
    char_anchors = ctx.get("char_anchors", {})
    p1_word = char_anchors.get("gender_word1") or ("girl" if char_anchors.get("p1_is_female") else "boy")
    p2_word = char_anchors.get("gender_word2") or ("girl" if char_anchors.get("p2_is_female") else "boy")
    p1_g = p1_word.upper()
    p2_g = p2_word.upper()

    # ── Video-Type Specific Situational Directions ───────────────────────────
    if video_type_upper == "GAME":
        if scene_lower == "hook":
            text_rule = (
                "SCENE GOAL — HOOK (THE FRONTAL DILEMMA):\n"
                "1. CAMERA & STAGING: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo 16yo student protagonist has a natural healthy athletic build and is centered, weighing two choices with engaging personality (solo character, no companion in hook).\n"
                "2. FOURTH-WALL GAZE: 100% DIRECT FOURTH-WALL EYE CONTACT WITH THE CAMERA LENS! The protagonist looks straight into the camera at the viewer, breaking the fourth wall to confront the audience with the quiz dilemma!\n"
                "3. EXPRESSIVE ACTING: Lively animated dilemma face with an amused raised eyebrow, slight thinking dilemma smirk, head tilted inquisitively, and warm expressive cartoon eyes full of life and spark (NEVER wide bug eyes, NEVER unexpressive deadpan stare).\n"
                "4. Relatable, lively real-life environment matching the locked anchor setting. Do NOT place them in a school, classroom, or generic cafe.\n"
                "5. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Focus 100% on the human character dilemma and authentic setting."
            )
        elif scene_lower == "answer":
            text_rule = (
                "SCENE GOAL — ANSWER (THE ASYMMETRICAL BREAKTHROUGH):\n"
                "1. CAMERA & STAGING: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum. The character breaks free from the dilemma with radiant eureka relief, joyful smile, and forward momentum in the authentic setting!\n"
                "2. The character visibly displays confident triumph, a joyful smile, or a thumbs-up gesture, joyfully holding or gesturing toward the correct choice.\n"
                "3. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict success screens, monitors, scoreboards, chalkboards, or digital displays. Focus 100% on the human emotional celebration."
            )
        elif scene_lower == "explanation":
            text_rule = (
                "SCENE GOAL — EXPLANATION (REAL-WORLD APPLICATION):\n"
                "1. CAMERA & STAGING: Real-world narrative medium-wide shot (35mm wide lens) showing native speakers naturally and smoothly using the target expression in the authentic real-world setting.\n"
                "2. FOURTH-WALL GAZE: STRICTLY 0% EYE CONTACT WITH THE CAMERA! 100% in-scene narrative immersion (looking at the environment, peers, or task).\n"
                "3. Natural body language, warm communicative atmosphere, and engaging social interaction demonstrating practical usage.\n"
                "4. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO tablets, NO signs anywhere in the image."
            )
        else:
            text_rule = (
                "SCENE GOAL — 2D CARTOON SCENE:\n"
                "1. Illustrate the real-life situation cleanly and expressively in modern 2D cartoon animation style.\n"
                "2. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO UI. Focus 100% on characters, environment, and visual storytelling."
            )

    elif video_type_upper in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
        text_rule = (
            "SCENE GOAL — FUN_FACTS (THE SCALE OF WONDER):\n"
            "1. CAMERA & STAGING: Dramatic low-angle heroic 24mm wide shot looking up from low elevation. The 15yo student protagonist is framed in the lower third, tilting their head upward in jaw-dropped awe at an imposing, towering cultural anomaly, ancient clockwork, or historic marvel.\n"
            "2. FOURTH-WALL GAZE: The character does NOT look at the camera; their eyes are locked upward on the central wonder/artifact in fascination.\n"
            "3. LIGHTING: Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating monumental scale contrast.\n"
            "4. Visually depict the authentic historical era, cultural setting, or physical origin of the phrase or fact.\n"
            "5. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or whiteboards."
        )

    elif video_type_upper == "ROLEPLAY":
        shot_direction = ""
        if scene_lower == "hook":
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SCENARIO THRESHOLD TWO-SHOT (35mm LENS): "
                f"Dynamic 3/4 over-the-shoulder (OTS) diagonal shot crossing a physical threshold (archway, curtain edge, counter, or doorway). "
                f"Both characters are visible in frame with explicit genders (PERSON_ONE as {p1_g}, PERSON_TWO as {p2_g}). "
                f"STRICTLY ZERO FOURTH-WALL EYE CONTACT: Characters lock eyes exclusively with each other in pre-performance tension. "
                f"Directional side-key lighting, dramatic chiaroscuro shadows across the authentic setting."
            )
        elif scene_lower in ["dialogue_part_1", "part_1"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SOLO MEDIUM CLOSE-UP ON PERSON_ONE (85mm PORTRAIT LENS): "
                f"Single-character solo medium close-up shot focused ENTIRELY on PERSON_ONE ({p1_g}). "
                f"Dramatic key lighting, shallow depth of field with softly blurred background. "
                f"Highlighting their intense facial acting, nervous or questioning body language, and opening dilemma. "
                f"PERSON_TWO is strictly off-camera / NOT visible in this frame."
            )
        elif scene_lower in ["dialogue_part_2", "part_2"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SOLO 180° REVERSE-ANGLE ON PERSON_TWO (85mm PORTRAIT LENS): "
                f"Dramatic 180° reverse-angle camera switch! Single-character solo medium close-up focused ENTIRELY on PERSON_TWO ({p2_g}). "
                f"Warm fill light, shallow depth of field. Highlighting their calm, confident, reassuring facial expression, "
                f"smirking or gesturing smoothly as they mentor and articulate the explanation. "
                f"PERSON_ONE is strictly off-camera / NOT visible in this frame."
            )
        elif scene_lower in ["dialogue_part_3", "part_3"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — 90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION (50mm LENS): "
                f"Camera shifts 90° to a dynamic side profile or high-angle table overview! "
                f"Both characters (one {p1_g} and one {p2_g}) are visible actively examining or interacting with an authentic physical prop "
                f"(pointing to details, examining an item, interacting with objects on table/counter). "
                f"This breaks the solo close-up sequence with collaborative environmental interaction."
            )
        elif scene_lower in ["dialogue_part_4", "part_4"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SOLO WAIST-UP DYNAMIC ACTION ON PERSON_ONE (28mm/50mm LENS): "
                f"Single-character solo waist-up dynamic action shot focused ENTIRELY on PERSON_ONE ({p1_g}). "
                f"Completely different camera distance, body posture, and scale from the tight close-up in Part 1! "
                f"Medium-wide framing capturing PERSON_ONE standing or gesturing with clarity and newfound confidence! "
                f"PERSON_TWO is strictly off-camera / NOT visible in this frame."
            )
        elif scene_lower in ["payoff", "resolution"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — CELEBRATORY TRIUMPH TWO-SHOT (28mm WIDE CINEMATIC LENS): "
                f"Dynamic celebratory two-shot in motion! Both characters (one {p1_g} and one {p2_g}) "
                f"celebrate success with dynamic movement and dramatic stage backlighting (high-five, walking triumphantly into the event/stage together)."
            )

        text_rule = (
            "SCENE GOAL — ROLEPLAY CONVERSATIONAL SCENARIO:\n"
            "1. Visually represent the EXACT REAL-WORLD SCENARIO described in the script (e.g. bakery counter, airport baggage claim, taxi cab, restaurant table, train station, doctor's office). Do NOT place characters in a classroom or school UNLESS the scenario is explicitly a school setting.\n"
            f"2. GENDER MATCHING & MULTI-CHARACTER RULE (CRITICAL): This is a two-person roleplay. You MUST explicitly describe the physical characters in the scene using the EXACT genders provided: PERSON_ONE is {p1_g} and PERSON_TWO is {p2_g}. If both characters appear in the image, NEVER use generic words like 'two teens' or 'the characters' without specifying their individual sex!\n"
            "3. EMOTIONAL ACTING & FACIAL EXPRESSIONS (CRITICAL): Characters MUST visibly display the emotions of this scene in their facial expressions and body language (e.g. nervous anxiety, friendly open gesture, amused smile, shock). Characters must look emotionally alive!\n"
            "4. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or screens."
            + shot_direction
        )

    else:
        # Default / EXPRESSION (and Idioms, Vocabulary, Pronunciation)
        base_rule = (
            "SCENE GOAL — REAL-WORLD SITUATIONAL STORYTELLING:\n"
            "1. AUTHENTIC SITUATION ONLY: Visually represent the ACTUAL REAL-WORLD SITUATION described in the script. Do NOT place characters in a classroom, school, or presentation studio.\n"
            "2. REAL HUMAN CHARACTERS: Depict everyday characters experiencing the situation with genuine emotions, expressive faces, and natural body language.\n"
            "3. TEXT IS STRICTLY BANNED: NO written text, letters, words, captions, logos, chalkboards, whiteboards, or screens anywhere in the image. Focus 100% on characters and environmental storytelling."
        )

        if scene_lower == "hook":
            scene_specific = (
                "\n4. HOOK (THE INSIDER GUIDE — LAYERED DEPTH):\n"
                "CAMERA & COMPOSITION: Angled foreground-and-background depth composition with a 35mm cinematic lens (Rule of Thirds). "
                "In the foreground left or right occupying 35-40% of the frame, the 15yo student protagonist turns 3/4 toward the viewer with an engaging, playful knowing smile and natural relaxed cartoon eyes, sharing an insider secret with friendly confidence (subtle amused smirk, lively spark in the eyes, NEVER bulging or wide bug eyes) breaking the fourth wall. "
                "In the luminous midground and deep background (60%), the authentic story setting extends in rich perspective, showcasing the oversized thematic visual metaphor in atmospheric ambient lighting. "
                "Zero text, zero speech bubbles, zero signs with words."
            )
        elif scene_lower == "setup":
            scene_specific = (
                "\n4. SETUP (SOCIAL CONTEXT & CONTRAST):\n"
                "Depict the social friction, contrasting expectations, or conversational exchange between characters in a collaborative micro-zone. Two-shot or over-the-shoulder shot with expressive body language highlighting the misunderstanding, contrast, or tricky distinction."
            )
        elif scene_lower == "discovery":
            scene_specific = (
                "\n4. DISCOVERY (THE BREAKTHROUGH / TURNING POINT MOMENT):\n"
                "Show the breakthrough moment of realization happening naturally at a demonstration workbench or discovery station! Medium action shot: a companion or friend introduces the key insight or native touch, sparking a radiant smile of sudden clarity, relief, or confident realization on the character's face."
            )
        elif scene_lower == "example":
            scene_specific = (
                "\n4. EXAMPLE (REAL-WORLD USAGE MOMENT IN FULL ACTION):\n"
                "This scene visually captures the real-world example phrase in active motion! Dynamic wide or active motion shot showing the characters actively living out the specific example sentence in the story environment with believable, dynamic body language. Illustrate the specific physical verb/action from the narration!"
            )
        elif scene_lower == "payoff":
            scene_specific = (
                "\n4. PAYOFF (CONFIDENT REAL-WORLD RESOLUTION):\n"
                "Show triumphant mastery, confident relief, or warm shared celebration in the celebration lounge or exit area. Medium close-up or celebratory shot: characters radiate success, comfort, and natural confidence."
            )
        else:
            scene_specific = (
                "\n4. VIBRANT NARRATIVE MOMENT: Illustrate the specific real-life action and emotion described in the scene text cleanly and expressively within the story setting."
            )

        text_rule = base_rule + scene_specific

    anti_rep_context = ""
    if existing_scene_prompts:
        other_scenes = [
            f"- {k.upper()}: \"{v}\""
            for k, v in existing_scene_prompts.items()
            if k.lower() != scene_lower and v
        ]
        if other_scenes:
            anti_rep_context = (
                "ANTI-REPETITION CONSTRAINT (CRITICAL):\n"
                "The other scenes in this Short already depict:\n"
                + "\n".join(other_scenes) + "\n\n"
                "- STRICT PROHIBITION: DO NOT repeat any of the focal props, character poses, micro-locations, or actions used in the scenes above!\n"
                "- Ensure this scene has a completely unique focal object, distinct physical action, and fresh camera perspective!\n\n"
            )

    if general_prompt:
        anchor_block = (
            "MASTER STORY WORLD, PHYSICAL SETTING & CHARACTER ANCHOR (FROM GENERAL PROMPT):\n"
            f">> {general_prompt} <<\n\n"
            "CRITICAL CONTINUITY DIRECTIVE (ABSOLUTE PRECEDENCE):\n"
            "All scenes MUST take place in this exact physical story world and setting! Inherit the exact characters (ages, genders, hair colors, hairstyles, specific thematic wardrobes), and atmosphere established in this General Prompt!\n\n"
        )
    else:
        anchor_block = (
            "THEMATIC STORY WORLD & SCENARIO CONTINUITY (MANDATORY):\n"
            f"The overarching real-world thematic setting is:\n>> {anchor_environment} <<\n"
            "- MICRO-ZONE ROTATION: Each scene MUST occur in a different micro-zone (desk -> discussion lounge -> workbench -> action stage -> victory area)!\n"
            "- PROP ROTATION: NEVER repeat the same focal prop across scenes!\n"
            "- POSE DIVERSITY: Strictly ban repeating generic poses (no duplicate 'pointing' or 'gesturing at models')!\n"
            "- ANTI-CAFETERIA RULE: Do NOT place characters in a generic cafe, cafeteria, or coffee shop unless the setting explicitly specifies one.\n"
            f"- MANDATORY THEMATIC WARDROBE: The character MUST wear clothing/costume that directly belongs to this setting ({anchor_environment}).\n\n"
        )

    return (
        f"INPUT\n\n"
        f"LANGUAGE: {language}\n\n"
        f"{ctx['gender_context']}"
        f"{ctx['personality_context']}"
        f"{ctx['voiceover_notice']}"
        f"SUBJECT: {subject}\n\n"
        f"CONTEXT: {situation}\n\n"
        f"{ctx['context_extra']}"
        f"LABEL: {label}\n\n"
        f"{ctx['palette_context']}\n\n"
        f"ANGLE: visual storytelling / authentic situation\n\n"
        f"STYLE: polished modern 2D cartoon narrative illustration, clean, expressive high-school student protagonist (approx. 15-16 years old, tall slender build, stylish situation-appropriate attire, NO mature adults), vibrant but balanced colors, rich cinematic atmosphere\n\n"
        f"FULL SCRIPT TEXT FOR CONTEXT (THE STORY):\n{script_text}\n\n"
        f"---\n\n"
        f"{anchor_block}"
        f"{anti_rep_context}"
        f"{ctx['idiom_rule']}"
        f"---\n\n"
        f"YOUR SPECIFIC TASK FOR THIS SCENE:\n"
        f"Illustrate this specific moment: SCENE [{scene_name.upper()}]:\n"
        f"SCENE TEXT: \"{scene_text}\"\n\n"
        f"DISTINCT SCENE PROGRESSION (CRITICAL — PREVENT IDENTICAL DUPLICATES):\n"
        f"While all scenes share the story world above, EACH scene must depict a UNIQUE narrative beat, distinct physical action, and varied camera shot:\n"
        f"- HOOK: Medium shot. Opening dilemma or curiosity with an intrigued or questioning expression.\n"
        f"- SETUP: Two-shot or over-the-shoulder shot. Conversational exchange or physical contrast.\n"
        f"- DISCOVERY: Medium action shot. Sudden breakthrough realization and physical gesture.\n"
        f"- EXAMPLE: Dynamic wide or active motion shot. Character actively demonstrating the specific phrase in motion.\n"
        f"- PAYOFF: Medium close-up or celebratory shot. Triumphant mastery, confident relief, warm accomplishment.\n\n"
        f"{text_rule}\n\n"
        f"CONCISENESS: Keep the final visual prompt strictly under 75 words. Focus only on the most important visual elements (character, facial expression, physical action, authentic setting, cinematic lighting). Do not overcomplicate.\n\n"
        f"Generate the Z-Image-Turbo visual prompt for this scene now. Ensure visual style, environment, and character remain 100% consistent with the story while showing this distinct scene action."
    )


FEMALE_HAIRSTYLE_TERMS = [
    "bun", "bob", "ponytail", "pigtail", "braid", "braided", "chignon",
    "hairband", "headband", "flowing", "shoulder-length", "hair clip"
]
MALE_HAIRSTYLE_TERMS = [
    "quiff", "buzz", "crew-cut", "crew cut", "fade", "pompadour",
    "sideburns", "flat-top", "undercut"
]

def sanitize_character_hair(raw_hair: str, is_female: bool, is_primary: bool = True) -> str:
    """
    Enforces 100% gender-accurate hairstyles.
    Prevents male characters from receiving feminine hairstyles (buns, bobs, ponytails, chignons)
    and female characters from receiving masculine haircuts (quiffs, buzz cuts).
    """
    hair_lower = raw_hair.lower().strip()

    if not is_female:  # MALE CHARACTER
        # If male was assigned ANY feminine hairstyle or empty:
        if any(trig in hair_lower for trig in FEMALE_HAIRSTYLE_TERMS) or not hair_lower:
            if is_primary or "dark" in hair_lower or "black" in hair_lower:
                return "short textured dark hair with clean tapered sides and a neat side-part"
            else:
                return "short textured chestnut-brown hair with clean-cut neckline and defined sideburns"
        # Guarantee "short" is present so diffusion models never draw long hair on boys
        if "short" not in hair_lower and "tapered" not in hair_lower and "crew" not in hair_lower:
            return f"short {raw_hair.strip()}"
        return raw_hair.strip()

    else:  # FEMALE CHARACTER
        # If female was assigned ANY masculine hairstyle or empty:
        if any(trig in hair_lower for trig in MALE_HAIRSTYLE_TERMS) or not hair_lower:
            if is_primary or "dark" in hair_lower or "black" in hair_lower:
                return "dark wavy hair tied in an elegant high ponytail with soft face-framing strands"
            else:
                return "textured caramel-brown hair styled in soft shoulder-length waves"
        return raw_hair.strip()


def _split_sentences_safe(text: str) -> list[str]:
    """Splits text into sentences while protecting abbreviations (approx., e.g., i.e., vs.)."""
    protected = re.sub(r'\b(approx|e\.g|i\.e|vs)\.', r'\1_DOT_', text, flags=re.IGNORECASE)
    parts = re.split(r'(?<=[.!?])\s+', protected)
    return [p.replace('_DOT_', '.').strip() for p in parts if p.strip()]


def _clean_character_clause(text: str) -> str:
    """Strips negative prompt shields and style boilerplate from a character clause."""
    t = re.sub(r'\(.*?(?:no\s+|thematic\s+setting|high-school\s+student\s+protagonist|explicit\s+footwear).*?\)', '', text, flags=re.IGNORECASE)
    t = re.sub(r'\bclean modern 2d cartoon narrative illustration.*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bstylized 2d animation art style.*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip(' ,.;')
    return t


def extract_or_build_character_anchors(
    general_prompt: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_anchors: dict = None,
) -> dict[str, str]:
    """
    Extracts or establishes consistent, locked character traits (hair color, hairstyle, wardrobe)
    from the General Prompt or structured character anchors so they can be repeated verbatim
    in every scene prompt. Prevents character identity drift, hair swapping, and wardrobe changes.

    CRITICAL RULE: The General Prompt is the authoritative visual source of truth for character gender,
    hair, and wardrobe. Speakers_gender is only a secondary fallback when the General Prompt is silent.
    """
    speakers_gender = speakers_gender or {}
    video_type_upper = video_type.strip().upper()
    has_two_characters = (
        video_type_upper in ("ROLEPLAY", "ROLE_PLAY")
        or bool(re.search(r'\b(companion|peer|friend|two characters|both characters|char_2|person_two|counterpart|on the right stands)\b', general_prompt, re.I))
        or bool(isinstance(speakers_gender, dict) and any("two" in str(k).lower() for k in speakers_gender))
    )

    sents = _split_sentences_safe(general_prompt)

    # 1. Identify Character 1 and Character 2 sentences directly from the General Prompt
    HUMAN_WORDS = [
        'student', 'boy', 'girl', 'protagonist', 'character', 'peer', 'companion', 'teen',
        '15-year', '16-year', '15yo', '16yo', 'young man', 'young woman', 'chico', 'chica',
        'hombre', 'mujer', 'muchacho', 'muchacha', 'char_1', 'char_2'
    ]
    CLOTHING_WORDS = [
        'wears', 'wearing', 'dressed', 'attire', 'shoes', 'vest', 'jacket', 'shirt', 'pants',
        'chinos', 'jeans', 'apron', 'coat', 'suit', 'uniform', 'boots', 'sneakers', 'hoodie',
        'sweater', 'outfit', 'costume', 'lleva', 'pantalones', 'falda', 'vestido'
    ]

    c1_sents: list[str] = []
    c2_sents: list[str] = []

    for idx, s in enumerate(sents):
        s_clean = _clean_character_clause(s)
        s_low = s_clean.lower()
        if not any(h in s_low for h in HUMAN_WORDS):
            continue

        if any(w in s_low for w in ['companion', 'peer', 'char_2', 'counterpart', 'on the right stands', 'second character']):
            c2_sents.append(s_clean)
            if idx + 1 < len(sents):
                next_clean = _clean_character_clause(sents[idx + 1])
                if any(w in next_clean.lower() for w in CLOTHING_WORDS):
                    c2_sents.append(next_clean)
        else:
            if not c1_sents:
                c1_sents.append(s_clean)
                if idx + 1 < len(sents):
                    next_clean = _clean_character_clause(sents[idx + 1])
                    if any(w in next_clean.lower() for w in CLOTHING_WORDS):
                        c1_sents.append(next_clean)

    c1_text = ' '.join(c1_sents).strip()
    c2_text = ' '.join(c2_sents).strip()

    # 2. Authoritative Gender Detection (General Prompt > speakers_gender fallback)
    search_target_c1 = c1_text or general_prompt
    c1_male_score = len(re.findall(
        r'\b(boy|male|guy|young man|man|chico|muchacho|hombre|he wears|he stands|his hair|his build)\b',
        search_target_c1.lower()
    ))
    c1_female_score = len(re.findall(
        r'\b(girl|female|young woman|woman|lady|chica|muchacha|mujer|she wears|she stands|her hair|her build)\b',
        search_target_c1.lower()
    ))

    if c1_male_score > c1_female_score:
        p1_is_female = False
    elif c1_female_score > c1_male_score:
        p1_is_female = True
    else:
        # Fallback to speakers_gender case-insensitively
        p1_raw = (
            get_speaker_gender_safe(speakers_gender, "PERSON_ONE", "")
            or get_speaker_gender_safe(speakers_gender, "NARRATOR", "")
        ).lower()
        p1_is_female = "f" in p1_raw or "girl" in p1_raw or "woman" in p1_raw

    gender_word1 = "girl" if p1_is_female else "boy"

    # Gender detection for Character 2
    search_target_c2 = c2_text or general_prompt
    c2_male_score = len(re.findall(
        r'\b(boy|male|guy|young man|man|chico|muchacho|hombre|he wears|he stands|his hair|his build)\b',
        search_target_c2.lower()
    ))
    c2_female_score = len(re.findall(
        r'\b(girl|female|young woman|woman|lady|chica|muchacha|mujer|she wears|she stands|her hair|her build)\b',
        search_target_c2.lower()
    ))

    if c2_male_score > c2_female_score:
        p2_is_female = False
    elif c2_female_score > c2_male_score:
        p2_is_female = True
    else:
        p2_raw = get_speaker_gender_safe(speakers_gender, "PERSON_TWO", "").lower()
        if p2_raw:
            p2_is_female = "f" in p2_raw or "girl" in p2_raw or "woman" in p2_raw
        else:
            p2_is_female = not p1_is_female

    gender_word2 = "girl" if p2_is_female else "boy"

    # 3. Use pre-extracted structured character anchors ONLY IF consistent with General Prompt
    if isinstance(character_anchors, dict) and character_anchors.get("char1_desc"):
        c1_desc = character_anchors["char1_desc"]
        c1_desc_lower = c1_desc.lower()
        anchor_is_female = bool(re.search(r'\b(girl|female|woman|chica|muchacha|mujer)\b', c1_desc_lower))
        # If anchors are consistent with the General Prompt's gender, use them
        if anchor_is_female == p1_is_female:
            c2_desc = character_anchors.get("char2_desc") or (c2_text if c2_text else f"16-year-old high-school teenage {gender_word2} (tall slender proportions, mature teenage features, NOT a child)")
            cont_summary = character_anchors.get("continuity_summary") or (
                f"Character appearance continuity: Character 1 is a {c1_desc}; Character 2 is a {c2_desc}."
                if has_two_characters else f"Character appearance continuity: The protagonist is a {c1_desc}."
            )
            return {
                "has_two_characters": str(has_two_characters),
                "char1_desc": c1_desc,
                "char2_desc": c2_desc,
                "char1_hair": character_anchors.get("char1_hair", ""),
                "char2_hair": character_anchors.get("char2_hair", ""),
                "char1_attire": character_anchors.get("char1_attire", ""),
                "char2_attire": character_anchors.get("char2_attire", ""),
                "gender_word1": gender_word1,
                "gender_word2": gender_word2,
                "p1_is_female": p1_is_female,
                "p2_is_female": p2_is_female,
                "continuity_summary": cont_summary,
            }

    # 4. Check for [CHARACTER_ANCHORS] block embedded inside general_prompt
    anchor_block_match = re.search(r'\[CHARACTER_ANCHORS\](.*?)\[/CHARACTER_ANCHORS\]', general_prompt, re.DOTALL | re.IGNORECASE)
    if anchor_block_match:
        # pyrefly: ignore[missing-import]
        from core.gemini_auditor import extract_character_anchors_from_output
        _, parsed = extract_character_anchors_from_output(general_prompt)
        if parsed and parsed.get("char1_desc"):
            return {
                "has_two_characters": str(has_two_characters),
                "char1_desc": parsed["char1_desc"],
                "char2_desc": parsed.get("char2_desc", f"16-year-old high-school teenage {gender_word2} (tall slender proportions, mature teenage features, NOT a child)"),
                "char1_hair": parsed.get("char1_hair", ""),
                "char2_hair": parsed.get("char2_hair", ""),
                "char1_attire": parsed.get("char1_attire", ""),
                "char2_attire": parsed.get("char2_attire", ""),
                "gender_word1": gender_word1,
                "gender_word2": gender_word2,
                "p1_is_female": p1_is_female,
                "p2_is_female": p2_is_female,
                "continuity_summary": parsed.get("continuity_summary", ""),
            }

    # 5. Build coherent character description directly from General Prompt prose
    if c1_text:
        char1_desc = c1_text
    else:
        garments = r"(?:blazer|vest|coat|smock|apron|jacket|robe|dress|sweater|shirt|suit|cardigan|hoodie|uniform|tunic|jersey|overshirt|jeans|trousers|sneakers|boots|loafers)"
        hair_matches = re.findall(
            r"(\b(?:dark|jet-black|black|brown|chestnut|auburn|blonde|caramel|brunette|red|copper|amber)?\s*[^,\.]{0,25}?\b(?:hair|curls|fade|bob|undercut|braid|braided|ponytail|quiff|buzz)\b[^,\.]*)",
            general_prompt,
            re.IGNORECASE,
        )
        raw_h1 = hair_matches[0].strip() if len(hair_matches) >= 1 else ""
        char1_hair = sanitize_character_hair(raw_h1, is_female=p1_is_female, is_primary=True)

        attire_pattern = re.compile(rf"(?:in|wearing|wears|dressed in)\s+([^,\.]{{3,50}}?\b{garments}\b[^,\.]*?)", re.IGNORECASE)
        attire_matches = attire_pattern.findall(general_prompt)
        char1_attire = attire_matches[0].strip() if attire_matches else "an authentic thematic costume matching this setting"
        if not p1_is_female:
            char1_attire = re.sub(r"\b(?:bodice|corset|kirtle|skirt|gown|dress)\b", "doublet and tailored trousers", char1_attire, flags=re.IGNORECASE)
        char1_desc = f"16-year-old high-school teenage {gender_word1} (tall slender proportions, mature teenage features, NOT a child) with {char1_hair} wearing {char1_attire}"

    if c2_text:
        char2_desc = c2_text
    else:
        char2_desc = f"16-year-old high-school teenage {gender_word2} (tall slender proportions, mature teenage features, NOT a child)"

    if has_two_characters:
        continuity_summary = (
            f"Character appearance continuity: Character 1 is {char1_desc}; "
            f"Character 2 is {char2_desc}."
        )
    else:
        continuity_summary = (
            f"Character appearance continuity: The protagonist is {char1_desc}."
        )

    return {
        "has_two_characters": str(has_two_characters),
        "char1_desc": char1_desc,
        "char2_desc": char2_desc,
        "char1_hair": "",
        "char2_hair": "",
        "char1_attire": "",
        "char2_attire": "",
        "gender_word1": gender_word1,
        "gender_word2": gender_word2,
        "p1_is_female": p1_is_female,
        "p2_is_female": p2_is_female,
        "continuity_summary": continuity_summary,
    }


def _build_storyboard_context(
    script_text: str,
    sections: dict[str, str],
    language: str,
    subject: str,
    situation: str,
    label: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_personalities: dict = None,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    anchor_environment: str = "",
    general_prompt: str = "",
    character_anchors: dict = None,
) -> str:
    """Build the prompt for generating a complete, non-repetitive visual storyboard in JSON."""
    ctx = _extract_shared_story_context(
        script_text=script_text,
        language=language,
        label=label,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_personalities=character_personalities,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        anchor_environment=anchor_environment,
        general_prompt=general_prompt,
    )
    anchor_environment = ctx["anchor_environment"]
    char_anchors = ctx.get("char_anchors", {})
    p1_word = char_anchors.get("gender_word1") or ("girl" if char_anchors.get("p1_is_female") else "boy")
    p2_word = char_anchors.get("gender_word2") or ("girl" if char_anchors.get("p2_is_female") else "boy")
    p1_g = p1_word.upper()
    p2_g = p2_word.upper()

    char_anchors = extract_or_build_character_anchors(
        general_prompt=general_prompt,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_anchors=character_anchors,
    )

    general_prompt_block = ""
    if general_prompt:
        general_prompt_block = (
            "MASTER STORY WORLD, PHYSICAL SETTING & CHARACTER ANCHOR (FROM GENERAL PROMPT):\n"
            f">> {general_prompt} <<\n\n"
            "CRITICAL STORY WORLD, SETTING & CHARACTER CONTINUITY DIRECTIVE (ABSOLUTE PRECEDENCE):\n"
            "1. MANDATORY PHYSICAL SETTING: All scenes below MUST strictly take place inside the exact physical setting "
            "established in this General Prompt! Micro-zones, props, architecture, and lighting must belong to this specific story world. "
            "NEVER relocate scenes to a different or unrelated location (e.g. if General Prompt establishes a sunny vintage park skate plaza, "
            "every scene MUST take place in that skate plaza or adjacent park area; NEVER switch the environment to a kitchen, restaurant, or classroom).\n"
            "2. MANDATORY CHARACTER CONTINUITY:\n"
            f"   - Character 1 (Protagonist): {char_anchors['char1_desc']}\n"
            f"   - Character 2 (Counterpart): {char_anchors['char2_desc']}\n"
            "Diffusion models generate EACH scene image independently with zero memory of other scenes! "
            "Therefore, in EVERY single scene prompt below, you MUST explicitly repeat the featured character's exact demographic (15-16yo high-school student), "
            "exact hair color, exact hairstyle, and exact wardrobe specified above. "
            "NEVER invent different clothing or different hairstyles across scenes!\n\n"
        )

    formatted_scenes = []
    for sec_name, sec_text in sections.items():
        if sec_text.strip():
            formatted_scenes.append(f"[{sec_name.upper()}]: \"{sec_text.strip()}\"")
    scenes_block = "\n".join(formatted_scenes)

    video_type_upper = video_type.strip().upper()
    if video_type_upper == "ROLEPLAY":
        p1_word = char_anchors.get("gender_word1") or ("girl" if char_anchors.get("p1_is_female") else "boy")
        p2_word = char_anchors.get("gender_word2") or ("girl" if char_anchors.get("p2_is_female") else "boy")
        p1 = p1_word.upper()
        p2 = p2_word.upper()
        director_task = (
            f"DIRECTOR'S ROLEPLAY STORYBOARD TASK (6-BEAT CINEMATIC PROGRESSION):\n"
            f"Transform this two-character roleplay dialogue into a dynamic, 6-scene visual storyboard between PERSON_ONE ({p1}) and PERSON_TWO ({p2}).\n\n"
            f"CRITICAL DIRECTIVES FOR CINEMATIC COVERAGE & ZERO REPETITION (MANDATORY):\n"
            f"To guarantee that no two images ever look like copies of each other, you MUST strictly follow this shot-by-shot coverage and camera matrix:\n\n"
            f"1. SCENE-BY-SCENE SUBJECT & CAMERA MATRIX (STRICTLY ENFORCED):\n"
            f"   - HOOK [ESTABLISHING TWO-SHOT (35mm LENS)]: Both characters in frame. Medium-wide 35mm establishing shot setting up the opening dilemma, spatial relationship, and environment. Both {p1_word} and {p2_word} are visible engaged in dialogue across the table, counter, or threshold. STRICTLY ZERO FOURTH-WALL EYE CONTACT.\n"
            f"   - DIALOGUE_PART_1 [SOLO TIGHT CLOSE-UP ON PERSON_ONE (85mm LENS)]: ONLY PERSON_ONE ({p1_word}) is in frame. 85mm portrait lens, shallow depth of field, dramatic key lighting, chest-up tight framing. Expressive facial acting showing opening questioning or dilemma. PERSON_TWO is strictly off-camera!\n"
            f"   - DIALOGUE_PART_2 [SOLO 180° REVERSE-ANGLE CLOSE-UP ON PERSON_TWO (85mm LENS)]: ONLY PERSON_TWO ({p2_word}) is in frame. 180° reverse-angle 85mm portrait lens, chest-up medium close-up, warm fill light. Focus entirely on PERSON_TWO's calm, reassuring expression as they mentor and explain. PERSON_ONE is strictly off-camera!\n"
            f"   - DIALOGUE_PART_3 [90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION (50mm LENS)]: Both characters in frame! Camera shifts 90° to a dynamic side profile or high-angle table overview. Both {p1_word} and {p2_word} are visible actively examining or manipulating an authentic physical prop (menu, map, book, tool, coffee cup, document with cartoon doodles). NOT another solo close-up!\n"
            f"   - DIALOGUE_PART_4 [SOLO WAIST-UP DYNAMIC ACTION ON PERSON_ONE (28mm/50mm LENS)]: ONLY PERSON_ONE ({p1_word}) is in frame. Completely different camera distance and physical stance from Part 1: waist-up medium-wide framing showing {p1_word} standing or gesturing dynamically with clarity and confidence. PERSON_TWO is strictly off-camera!\n"
            f"   - PAYOFF [CELEBRATORY ACTION TWO-SHOT (28mm LENS)]: Both characters in dynamic motion. 28mm wide cinematic lens, dramatic backlighting, shared celebratory mastery.\n\n"
            f"2. ZERO-AMBIGUITY CHARACTER DESCRIPTION & CONTINUITY:\n"
            f"   - For solo shots (dialogue_part_1, dialogue_part_2, dialogue_part_4): Explicitly describe ONLY the single featured character with their locked traits. State: 'Single character solo shot. The other character is off-camera.'\n"
            f"   - For two-shots (hook, dialogue_part_3, payoff): Explicitly specify the sex of EACH character (e.g. 'one 15-year-old teen {p1_word}' and 'one 15-year-old teen {p2_word}'). Strictly ban generic words like 'the characters'!\n\n"
            f"3. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping all 6 scene names in lowercase (hook, dialogue_part_1, dialogue_part_2, dialogue_part_3, dialogue_part_4, payoff) to their final prompt string."
        )
    elif video_type_upper == "GAME":
        director_task = (
            f"DIRECTOR'S GAME STORYBOARD TASK (FRONTAL DILEMMA TO ASYMMETRICAL TRIUMPH PROGRESSION):\n"
            f"Transform this game quiz into a cohesive storyboard where each scene faithfully depicts the specific question, answer, and explanation with exact camera geometry:\n"
            f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
            f"   - HOOK [THE FRONTAL DILEMMA]: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo 16yo student protagonist {p1_word} has a natural healthy athletic build and is centered, weighing two choices with engaging personality. FOURTH-WALL GAZE: 100% direct fourth-wall eye contact with the camera lens, confronting the viewer with the quiz dilemma! EXPRESSIVE ACTING: Lively animated dilemma face with an amused raised eyebrow, slight thinking dilemma smirk, head tilted inquisitively, and warm animated cartoon eyes (NEVER wide bug eyes, NEVER staring, NEVER unexpressive deadpan stare). Solo {p1_word} only (no companion in hook)!\n"
            f"   - ANSWER [THE ASYMMETRICAL BREAKTHROUGH]: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum! Protagonist {p1_word} breaks free from the dilemma with radiant relief, a triumphant eureka smile, and forward kinetic energy, joyfully celebrating the winning choice in the setting.\n"
            f"   - EXPLANATION [REAL-WORLD IMMERSION]: Real-world narrative medium-wide shot (35mm wide lens) with deep spatial environment. Protagonist {p1_word} actively engages in the authentic cultural practice, ritual, or real-life application. FOURTH-WALL GAZE: STRICTLY 0% EYE CONTACT WITH THE CAMERA (100% in-scene narrative immersion).\n"
            f"2. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Completely ban all written words, letters, phrases, and quotes. If documents or papers appear, describe them strictly as containing abstract wavy cartoon doodle lines, 0% legible text. Focus 100% on the human character dilemma and authentic setting.\n"
            f"3. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Character 1 protagonist MUST be a {p1_word.upper()}. Strictly ban generic words like 'two teens'.\n"
            f"4. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 16-year-old high-school student {p1_word} demographic (tall slender proportions, mature teenage features, NOT a child), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"5. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, answer, explanation) to its final prompt string."
        )
    elif video_type_upper in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
        director_task = (
            f"DIRECTOR'S FUN FACTS STORYBOARD TASK (SCALE OF WONDER & DISCOVERY PROGRESSION):\n"
            f"Transform this curiosity script into a visually stunning, narrative-faithful storyboard:\n"
            f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
            f"   - HOOK [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking up from floor level. Protagonist {p1_word} in lower third looking upward in jaw-dropped awe at an imposing, towering cultural anomaly or historic marvel. Upward gaze, volumetric lighting shafts, monumental scale contrast.\n"
            f"   - SETUP / DISCOVERY / FACTS: Collaborative inspection and dynamic reveal of the fascinating historical discovery in motion.\n"
            f"   - PAYOFF: Mind-blown celebratory outro celebrating trivia mastery.\n"
            f"2. ZERO-TOLERANCE TEXT BAN: Do NOT include words, quotes, letters, phrases, vocabulary words, or complete sentences in the visual prompt! If scrolls, books, parchment, signs, or artifacts are depicted, describe them strictly as containing 'abstract wavy cartoon scribble lines, graphic doodle curves, or decorative geometric diagrams representing text, completely devoid of legible alphabet letters, words, or typography'.\n"
            f"3. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Character 1 protagonist MUST be a {p1_word.upper()}. Strictly ban generic words like 'two teens'.\n"
            f"4. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 16-year-old high-school student {p1_word} demographic (tall slender proportions, mature teenage features, NOT a child), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"5. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
        )
    else:
        director_task = (
            f"DIRECTOR'S EXPRESSION STORYBOARD TASK (LAYERED DEPTH CHRONOLOGICAL 5-BEAT PROGRESSION):\n"
            f"Create a cohesive 5-scene visual storyboard where EVERY scene faithfully visualizes the specific narrative beat and spoken script text of that scene in CHRONOLOGICAL ORDER:\n"
            f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
            f"   - HOOK [THE INSIDER GUIDE]: 35mm angled foreground-and-background depth composition (Rule of Thirds). The 15yo student protagonist {p1_word} occupies the foreground left or right (35-40%), turned 3/4 toward the viewer with an engaging, playful knowing smile and warm animated cartoon eyes, sharing an insider secret with natural relaxed facial acting (subtle amused smirk, lively curious gaze, NEVER bulging eyes, NEVER staring rounded eyes) breaking the fourth wall. The luminous midground and deep background (60%) reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.\n"
            f"   - SETUP [SOCIAL CONTRAST]: Two-shot profile angle across a table/counter demonstrating the conversational friction or literal misunderstanding spoken in this beat.\n"
            f"   - DISCOVERY [EUREKA BREAKTHROUGH]: Medium action shot at a demonstration station. Wide joyful eyes, sudden breakthrough clarity, reacting directly to the native rule being explained.\n"
            f"   - EXAMPLE [LIVING KINETIC MOTION]: ACTIVELY DEPICT THE EXACT EXAMPLE SENTENCE FROM THE SCRIPT IN DYNAMIC MOTION! Show the {p1_word} living out the specific action or situation described in the narration.\n"
            f"   - PAYOFF [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment.\n"
            f"2. ZERO-DUPLICATE PROPS & REALISTIC ACTION: Give each scene distinct physical postures and unique focal objects. Strictly ban surreal fantasy magic effects.\n"
            f"3. CAMERA SHOTS (WAIST-UP / CHEST-UP ONLY): Keep characters comfortably close to camera so their faces remain large and detailed.\n"
            f"4. MULTI-CHARACTER GENDER SPECIFICATION: If more than 1 character is depicted, explicitly specify the sex of EACH character (e.g. 'one teen {p1_word} and one companion teen {p2_word}'). Strictly ban generic phrases like 'two teens'.\n"
            f"5. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact high school student {p1_word} demographic (15-16yo, tall slender proportions), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"6. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
        )

    if general_prompt:
        story_setting_block = general_prompt_block
    else:
        story_setting_block = f"OVERARCHING THEMATIC BASE SETTING:\n>> {anchor_environment} <<\n\n"

    return (
        f"INPUT\n\n"
        f"LANGUAGE: {language}\n\n"
        f"{ctx['gender_context']}"
        f"{ctx['personality_context']}"
        f"{ctx['voiceover_notice']}"
        f"SUBJECT: {subject}\n\n"
        f"CONTEXT: {situation}\n\n"
        f"{ctx['context_extra']}"
        f"LABEL: {label}\n\n"
        f"{ctx['palette_context']}\n\n"
        f"{ctx['idiom_rule']}"
        f"{story_setting_block}"
        f"FULL SCRIPT TEXT (THE COMPLETE STORY):\n{script_text}\n\n"
        f"---\n\n"
        f"SCENES TO STORYBOARD:\n"
        f"{scenes_block}\n\n"
        f"---\n\n"
        f"{director_task}"
    )



def _extract_json_payload(raw_text: str) -> dict:
    """Extracts a JSON dictionary from LLM response text robustly."""
    cleaned = raw_text.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except Exception:
            pass

    brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except Exception:
            pass

    return {}


def sanitize_and_style_prompt(prompt: str) -> str:
    """
    Sanitizes visual prompts and enforces strict 2D cartoon narrative illustration styling.

    1. Removes any interjections or quote words like 'aha', 'eureka', 'wow', 'oops'.
    2. Strips quotes around words (e.g. 'project', 'cake') which trigger text/OCR rendering in Qwen/Lumina.
    3. Guarantees that the prompt has explicit, high-priority 2D cartoon illustration tokens
       and anti-photorealism directives.
    """
    if not prompt or not isinstance(prompt, str):
        return ""

    text = prompt.strip()

    # 1. Clean out interjections that cause diffusion models to paint letters onto the image
    text = re.sub(r"['\"]?\baha!?['\"]?", "sudden breakthrough clarity", text, flags=re.IGNORECASE)
    text = re.sub(r"['\"]?\beureka!?['\"]?", "sudden discovery", text, flags=re.IGNORECASE)
    text = re.sub(r"['\"]?\bwow!?['\"]?", "amazed expression", text, flags=re.IGNORECASE)
    text = re.sub(r"['\"]?\boops!?['\"]?", "surprised reaction", text, flags=re.IGNORECASE)

    # 2. Strip single or double quotes around words which trigger typography rendering
    text = re.sub(r"['\"]([a-zA-Z0-9_\-\s]{1,30})['\"]", r"\1", text)

    # 3. Strip any residual stray quotes
    text = text.replace('"', '').replace("'", "")
    text = re.sub(r"\s+", " ", text).strip()

    # 3b. Ensure male characters NEVER have feminine hairstyles (buns, bobs, ponytails, chignons)
    text = re.sub(
        r"\b(boy|man|male(?:\s+teen|\s+student|\s+protagonist)?)\b([^,\.]{0,40}?)\b(?:tied in a (?:sleek\s+)?bun|in a (?:sleek\s+)?bun|sleek bun|hair bun|in a bob|in a ponytail|chignon)\b",
        r"\1\2with short textured dark hair and neat side-part",
        text,
        flags=re.IGNORECASE,
    )
    # Ensure male characters NEVER wear female garments (bodices, corsets, kirtles, skirts, dresses, gowns)
    text = re.sub(
        r"\b(boy|man|male(?:\s+teen|\s+student|\s+protagonist)?)\b([^,\.]{0,50}?)\b(?:bodice|corset|kirtle|skirt|gown|dress)\b",
        r"\1\2theatrical doublet and tailored trousers",
        text,
        flags=re.IGNORECASE,
    )
    # 3c. Ensure female characters NEVER have masculine haircuts (quiffs, buzz cuts, crew cuts)
    text = re.sub(
        r"\b(girl|woman|female(?:\s+teen|\s+student|\s+protagonist)?)\b([^,\.]{0,40}?)\b(?:quiff hair|quiff|buzz-?cut|crew-?cut)\b",
        r"\1\2with soft wavy hair resting over shoulders",
        text,
        flags=re.IGNORECASE,
    )

    # 3d. Absolute text, quote, speech, and typography scrubbing to prevent diffusion models from painting text onto images
    # Scrub all text inside quotes: "...", '...', “...”, ‘...’, «...»
    text = re.sub(r'["“«][^"”»]{1,60}["”»]', "expressive dialogue", text)
    text = re.sub(r"['‘][^'’]{1,60}['’]", "expressive dialogue", text)

    # Scrub verbs of speaking followed by words/phrases
    text = re.sub(r"\b(?:whispering|saying|speaking|mouthing|shouting|calling|reading|repeating)\s+(?:the\s+words?|the\s+phrase)?\s*[^,\.]{1,40}", "speaking expressively", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwith\s+the\s+words?\s+[^,\.]{1,40}", "with expressive visual details", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthe\s+words?\s+[^,\.]{1,30}", "expressive dialogue", text, flags=re.IGNORECASE)

    # Scrub document / scroll / paper / parchment text references and replace with cartoon graphic doodles
    text = re.sub(
        r"\b(?:revealing|reveals?|displaying|inscribed\s+with|containing|featuring)\s+(?:the\s+)?(?:two-word\s+|three-word\s+)?\b(?:statement|phrase|sentence|words?|text|quote)\b\s*[^,\.]{0,60}",
        "featuring abstract wavy cartoon doodle lines and geometric graphical diagrams representing text, completely devoid of legible letters or words",
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r"\b(?:scroll|parchment|book|manuscript|document|page|slate|paper)\s+that\s+reveals?\s+[^,\.]{0,60}",
        "blank parchment scroll adorned only with decorative wavy graphic scribble lines and zero text",
        text,
        flags=re.IGNORECASE
    )

    # Scrub signs, posters, screens, boards with text
    text = re.sub(r"\b(?:labeled|inscribed\s+with|reading|displaying\s+(?:the\s+text)?)\s+[^,\.]{1,40}", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:a\s+)?(?:sign|poster|banner|board|screen|tablet|t-shirt|shirt|hoodie)\s+(?:with|showing|saying|displaying)\s+[^,\.]{1,40}", "thematic decor", text, flags=re.IGNORECASE)

    # Scrub letter / alphabet mentions
    text = re.sub(r"\b(?:holding|waving|showing|with|displaying)\s+(?:a\s+)?(?:large,?\s+)?(?:stylized\s+)?(?:prop|sign|card|banner|object)?\s*representing\s+(?:the\s+)?letters?\s+[A-Za-z0-9_\-]+\b", "gesturing with an expressive physical prop", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:the\s+)?letters?\s+[A-Z]\b", "an expressive thematic prop", text)
    text = re.sub(r"\bdouble\s+[A-Za-z]\b", "expressive vocal inflection", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:double\s+)?ene\b", "vocal resonance", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:difference|distinction|contrast)\s+between\s+[A-Za-zÀ-ÿ0-9_\-]+\s+and\s+[A-Za-zÀ-ÿ0-9_\-]+\b", "subtle vocal nuance", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:distinguishing|differentiating)\s+between\s+[A-Za-zÀ-ÿ0-9_\-]+\s+and\s+[A-Za-zÀ-ÿ0-9_\-]+\b", "subtle vocal demonstration", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpronunciation\s+of\s+[^,\.]{1,50}", "subtle vocal delivery", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsound\s+of\s+[A-Za-zÀ-ÿ0-9_\-]+", "vocal resonance", text, flags=re.IGNORECASE)

    # 4. Mandatory High School Student Demographic & Thematic Wardrobe Upgrades (16yo, tall slender proportions, NOT a child)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:man|actor|gentleman)\b", "a 16-year-old high-school teenage boy", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:woman|actress|lady)\b", "a 16-year-old high-school teenage girl", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:performer|enthusiast|student|person|scholar|professional|individual|character)\b", "a 16-year-old high-school teenage protagonist", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\bNO\s)(?<!\bmiddle-aged\s)(?<!\bolder\s)\b(adult|grown-?up)s?\b", "high-school teenagers", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\bNO\s)\ban adult\b", "a high-school teenager", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:8|9|10|11|12|13|14|15)-year-old\b", "16-year-old", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:kid|child|children)\b", "teenager", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:wearing\s+)?normal clothing\b", "wearing thematically authentic scene costume", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:smart\s+)?casual attire\b", "thematic scene-specific wardrobe", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcasual clothes\b", "thematic scene-specific costume", text, flags=re.IGNORECASE)

    # 4b. Scrub deadpan, bug-eye, and stick-figure triggers while PRESERVING front-facing camera & 100% fourth-wall eye contact!
    text = re.sub(r"\(Wes Anderson-style\s+central\s+balance\)", "with clean vertical balance", text, flags=re.IGNORECASE)
    text = re.sub(r"\bWes Anderson[- ]style(?: central balance)?\b", "clean vertical balance", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfrozen at a(?:n organic)? physical crossroads\b", "weighing two choices in an active thinking pose", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:with\s+)?(?:big|wide),?\s+puzzled eyes,?\s+", "with an amused raised eyebrow and lively expressive cartoon eyes, ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:big|wide),?\s+puzzled eyes\b", "expressive cartoon eyes full of animated curiosity", text, flags=re.IGNORECASE)
    text = re.sub(r"\btall slender proportions\b", "natural balanced teenage proportions", text, flags=re.IGNORECASE)
    text = re.sub(r"\btall slender build\b", "natural healthy athletic build", text, flags=re.IGNORECASE)

    # 4c. Scrub conspiratorial glance / arched eyebrow triggers that cause weird rounded bug-eyes
    text = re.sub(
        r"\b(?:with\s+an?\s+)?expressive,?\s+conspiratorial\s+glance\s*(?:\([^)]*\)|and\s+an?\s+arched\s+eyebrow)?",
        "with an engaging, playful knowing smile and natural animated cartoon eyes",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bconspiratorial\s+glance\b",
        "playful, knowing expression",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bconspiratorial\b",
        "insider",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\barched\s+eyebrow\b",
        "subtle thinking smile",
        text,
        flags=re.IGNORECASE,
    )

    # 4d. Scrub lazy repetitive gift box props from prompts (except when genuinely teaching 'present')
    text = re.sub(
        r"\b(?:a\s+)?(?:large,?\s+|giant\s+oversized,?\s+|vintage,?\s+|single\s+perfectly\s+wrapped\s+|stylized\s+graphic\s+prop\s+of\s+an?\s+|stylized\s+ornate\s+golden\s+)?ornate,?\s+(?:ribbon-wrapped\s+|golden\s+)?gift\s+box\b",
        "an authentic thematic prop from the setting",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:a\s+)?(?:large,?\s+|small,?\s+|massive,?\s+)?(?:ornate,?\s+)?ribbon-wrapped\s+gift\s+box(?:es)?\b",
        "an authentic setting prop",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bstack\s+of\s+ornate,?\s+(?:ribbon-wrapped\s+)?gift\s+boxes\b",
        "authentic setting props and tools",
        text,
        flags=re.IGNORECASE,
    )

    # 5. Mandatory 2D Cartoon Style Anchor with High School Proportions & Safe Exclusions
    style_mandate = (
        "Clean modern 2D cartoon narrative illustration, stylized 2D animation art style, "
        "vibrant flat colors, bold outlines, expressive high-school student character design (approx. 16 years old, natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child), "
        "expressive stylized cartoon eyes with natural lively shape and warm gaze, "
        "thematically authentic scene-specific wardrobe matching the environment (NO generic modern street clothes, NO plain t-shirts/hoodies), "
        "rich detailed environmental interior background with depth and warm atmospheric lighting. "
        "(high-school student protagonist, thematic costume, NO mature adult wrinkles, NO elderly, "
        "NO young children, NO elementary kids, NO childish proportions, "
        "NO generic casual t-shirts, NO plain hoodies, NO dot eyes, NO minimalist faces, NO blank backgrounds, "
        "NO bulging eyes, NO bug eyes, NO staring unblinking eyes, NO excessively open rounded eyes, NO unnatural wide eyes, NO deadpan blank face, NO emotionless expression, NO stiff mannequin pose, NO gaunt, NO emaciated, NO stick-figure proportions, "
        "NO 3D render, NO photorealism, NO photograph, NO text, NO words, NO letters, NO quotes, NO signs with text, NO subtitles, NO typography, NO watermark)."
    )

    if "(high-school student protagonist, thematic costume" not in text:
        text = re.sub(r"\.\s*Clean modern 2D cartoon narrative illustration.*$", "", text, flags=re.DOTALL)
        text = f"{text.rstrip('. ')}. {style_mandate}"

    return text.strip()


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
        chunk_timeout: float = 25.0,
    ) -> None:
        timeout = httpx.Timeout(
            connect=10.0,
            read=chunk_timeout,
            write=15.0,
            pool=15.0,
        )
        self._client = OpenAI(
            base_url=api_base_url,
            api_key=api_key if api_key else "llama",
            timeout=timeout,
        )
        self._model = model_name
        self._chunk_timeout = chunk_timeout
        self._wall_timeout = request_timeout


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
        topic: str = "",
        scenario: str = "",
        lexical_field: str = "",
        anchor_environment: str = "",
        existing_scene_prompts: dict = None,
        general_prompt: str = "",
        temperature: float = 0.75,
        max_retries: int = 3,
    ) -> str:
        """
        Generate a single Z-Image-Turbo visual prompt for a specific script scene.
        Uses token streaming with an active watchdog to prevent stalls and auto-recovers
        if the LLM server or slot gets stuck ("go ahead, don't stop").

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
        topic:
            Optional specific topic or expression string.
        scenario:
            Optional specific roleplay or situational setting.
        lexical_field:
            Optional lexical category / field (e.g. "Performance & Theater", "Cooking").
        anchor_environment:
            Optional locked physical story environment across all scenes of this script.
        existing_scene_prompts:
            Optional dictionary of other scene prompts in this script, used as anti-repetition memory.
        general_prompt:
            Optional overarching master visual prompt anchor.
        max_retries:
            Maximum number of retry attempts on stall or timeout.

        Returns
        -------
        str
            A detailed visual description ready for ComfyUI injection.

        Raises
        ------
        OpenAIError / RuntimeError
            If the LLM request fails after retries.
        """
        language, subject, situation = _parse_label(label)
        if general_prompt:
            anchor_environment = general_prompt
        elif not general_prompt and anchor_environment and len(anchor_environment) > 80:
            general_prompt = anchor_environment

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
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            anchor_environment=anchor_environment,
            existing_scene_prompts=existing_scene_prompts,
            general_prompt=general_prompt,
        )

        logger.info(
            "[%s] Generating visual prompt — %s / %s / %s",
            script_id, language, subject, situation,
        )

        last_error = None
        for attempt in range(1, max_retries + 1):
            stream = None
            start_t = time.time()
            collected: list[str] = []
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": _VISUAL_DIRECTOR_SYSTEM_PROMPT},
                        {"role": "user",   "content": user_context},
                    ],
                    max_tokens=2000,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if time.time() - start_t > self._wall_timeout:
                        raise TimeoutError(
                            f"LLM visual prompt exceeded wall timeout ({self._wall_timeout:.0f}s)"
                        )

                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = delta.content if delta else None
                    if content:
                        collected.append(content)

                visual_prompt = "".join(collected).strip()
                if not visual_prompt:
                    raise ValueError(f"[{script_id}] LLM returned an empty visual prompt.")

                logger.info(
                    "[%s] Visual prompt generated (%d chars).", script_id, len(visual_prompt)
                )
                logger.debug("[%s] Prompt preview: %s…", script_id, visual_prompt[:120])
                time.sleep(0.2)  # Slot cooldown
                return sanitize_and_style_prompt(visual_prompt)

            except Exception as exc:
                last_error = exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

                elapsed = int(time.time() - start_t)
                if attempt < max_retries:
                    logger.warning(
                        "[%s] LLM generation stalled/failed (%s) after %ds. "
                        "Auto-recovering slot and retrying (attempt %d/%d)... Go ahead, don't stop!",
                        script_id, exc, elapsed, attempt + 1, max_retries,
                    )
                    time.sleep(0.8 * attempt)
                else:
                    logger.error(
                        "[%s] Failed to generate visual prompt for %s after %d attempts: %s",
                        script_id, scene_name, max_retries, exc,
                    )

        raise last_error or RuntimeError(f"[{script_id}] Failed to generate visual prompt.")

    def build_storyboard_prompts(
        self,
        script_text: str,
        label: str,
        sections: dict[str, str],
        script_id: str = "",
        speakers_gender: dict = None,
        video_type: str = "EXPRESSION",
        character_personalities: dict = None,
        topic: str = "",
        scenario: str = "",
        lexical_field: str = "",
        anchor_environment: str = "",
        general_prompt: str = "",
        character_anchors: dict = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> dict[str, str]:
        """
        Generates a cohesive, non-repetitive visual storyboard for all scenes of a Short in a single pass.
        Guarantees:
        1. Micro-zone diversity within the thematic macro-environment.
        2. Zero repeated focal props across scenes.
        3. Varied camera framing across all scenes.
        4. Active depiction of the example sentence action.
        5. Creative visual metaphors and graphic wordplay across scenes.
        """
        language, subject, situation = _parse_label(label)
        if general_prompt:
            anchor_environment = general_prompt
        else:
            logger.info("[%s] General prompt anchor not provided; establishing master visual anchor first...", script_id)
            try:
                general_prompt = self.build_general_prompt(
                    script_text=script_text,
                    label=label,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic,
                    scenario=scenario,
                    lexical_field=lexical_field,
                    anchor_environment=anchor_environment,
                    temperature=temperature,
                )
                anchor_environment = general_prompt
            except Exception as exc:
                logger.warning("[%s] Failed to build general prompt for storyboard: %s", script_id, exc)
                general_prompt = anchor_environment

        storyboard_context = _build_storyboard_context(
            script_text=script_text,
            sections=sections,
            language=language,
            subject=subject,
            situation=situation,
            label=label,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            anchor_environment=anchor_environment,
            general_prompt=general_prompt,
            character_anchors=character_anchors,
        )

        logger.info(
            "[%s] Generating complete visual storyboard — %s / %s / %s",
            script_id, language, subject, situation,
        )

        last_error = None
        storyboard_dict: dict[str, str] = {}
        for attempt in range(1, max_retries + 1):
            stream = None
            start_t = time.time()
            collected: list[str] = []
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": _STORYBOARD_DIRECTOR_SYSTEM_PROMPT},
                        {"role": "user",   "content": storyboard_context},
                    ],
                    max_tokens=3500,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if time.time() - start_t > self._wall_timeout * 1.5:
                        raise TimeoutError(
                            f"LLM storyboard prompt exceeded wall timeout ({self._wall_timeout * 1.5:.0f}s)"
                        )

                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = delta.content if delta else None
                    if content:
                        collected.append(content)

                full_response = "".join(collected).strip()
                if not full_response:
                    raise ValueError(f"[{script_id}] LLM returned an empty storyboard response.")

                parsed = _extract_json_payload(full_response)
                if parsed and isinstance(parsed, dict):
                    storyboard_dict = {
                        k.strip().lower(): str(v).strip()
                        for k, v in parsed.items()
                        if isinstance(v, (str, int, float)) and str(v).strip()
                    }
                    if storyboard_dict:
                        logger.info(
                            "[%s] Successfully parsed %d storyboard scene prompt(s) from JSON.",
                            script_id, len(storyboard_dict),
                        )
                        break

                logger.warning(
                    "[%s] Could not parse valid JSON storyboard from LLM response (attempt %d/%d). Retrying...",
                    script_id, attempt, max_retries,
                )
            except Exception as exc:
                last_error = exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                elapsed = int(time.time() - start_t)
                logger.warning(
                    "[%s] Storyboard generation error (%s) after %ds. Retrying attempt %d/%d...",
                    script_id, exc, elapsed, attempt + 1, max_retries,
                )
                time.sleep(1.0 * attempt)

        # Validate that all requested active sections exist in storyboard_dict; auto-fill missing
        for sec_name, sec_text in sections.items():
            sec_lower = sec_name.strip().lower()
            if not sec_text.strip():
                continue
            if sec_lower not in storyboard_dict or not storyboard_dict[sec_lower]:
                logger.info(
                    "[%s] Scene '%s' missing from storyboard. Generating individually with general prompt anchor...",
                    script_id, sec_name,
                )
                try:
                    single_prompt = self.build_visual_prompt(
                        script_text=script_text,
                        label=label,
                        scene_name=sec_name,
                        scene_text=sec_text,
                        script_id=script_id,
                        speakers_gender=speakers_gender,
                        video_type=video_type,
                        character_personalities=character_personalities,
                        topic=topic,
                        scenario=scenario,
                        lexical_field=lexical_field,
                        anchor_environment=anchor_environment,
                        existing_scene_prompts=storyboard_dict,
                        general_prompt=general_prompt,
                    )
                    storyboard_dict[sec_lower] = single_prompt
                except Exception as exc:
                    logger.error("[%s] Failed fallback prompt for %s: %s", script_id, sec_name, exc)

        anchors = extract_or_build_character_anchors(
            general_prompt=general_prompt,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_anchors=character_anchors,
        )

        final_prompts: dict[str, str] = {}
        for sec_key, raw_prompt in storyboard_dict.items():
            prompt_str = raw_prompt.strip()
            # Only append continuity summary if prompt completely lacks character description
            has_character = any(w in prompt_str.lower() for w in ["student", "teen", "protagonist", "character", "girl", "boy", "actor", "actress", "man", "woman"])
            if not has_character and anchors.get("continuity_summary"):
                prompt_str = f"{prompt_str.rstrip('. ')}. {anchors['continuity_summary']}"

            final_prompts[sec_key] = sanitize_and_style_prompt(prompt_str)

        return final_prompts

    def build_general_prompt(
        self,
        script_text: str,
        label: str,
        script_id: str = "",
        speakers_gender: dict = None,
        video_type: str = "EXPRESSION",
        character_personalities: dict = None,
        topic: str = "",
        scenario: str = "",
        lexical_field: str = "",
        anchor_environment: str = "",
        guidance: str = "",
        temperature: float = 0.75,
        max_retries: int = 3,
    ) -> str:
        """
        Generates an overarching General Visual Prompt / Story World Anchor that defines
        the visual environment, thematic setting, protagonist demographic/wardrobe, and aesthetic
        for all scenes in this video.
        """
        language, subject, situation = _parse_label(label)
        if not anchor_environment:
            anchor_environment = resolve_anchor_environment(
                script_text=script_text,
                topic=topic,
                scenario=scenario,
                lexical_field=lexical_field,
                label=label,
                video_type=video_type,
            )

        has_two_characters = (
            video_type.upper() == "ROLEPLAY"
            or bool(speakers_gender and any("two" in str(k).lower() for k in speakers_gender))
        )
        if has_two_characters:
            p1_g = get_speaker_gender_safe(speakers_gender, "PERSON_ONE", "female")
            p2_g = get_speaker_gender_safe(speakers_gender, "PERSON_TWO", "male")
            p1_is_female = "f" in str(p1_g).lower() or "girl" in str(p1_g).lower()
            p2_is_female = "f" in str(p2_g).lower() or "girl" in str(p2_g).lower()
            p1_word = "girl" if p1_is_female else "boy"
            p2_word = "girl" if p2_is_female else "boy"

            c1_hair_example = (
                "dark wavy hair tied in an elegant ponytail or soft shoulder-length bob"
                if p1_is_female
                else "short textured dark hair with clean tapered sides and a neat side-part (NEVER buns, bobs, or ponytails for boys!)"
            )
            c2_hair_example = (
                "textured caramel-brown hair styled in soft shoulder-length waves or graceful braid"
                if p2_is_female
                else "short textured chestnut-brown hair with clean-cut neckline and defined sideburns (NEVER buns, bobs, or ponytails for boys!)"
            )

            character_directive = (
                f"2. Dual Lead Characters (MANDATORY EXACT SKIN TONE, EYE COLOR, GENDER-ACCURATE HAIR & THEMATIC WARDROBE CONTINUITY):\n"
                f"   - Character 1 (Left Position): An expressive 15-year-old high-school student {p1_word} (tall slender build) positioned on the LEFT side of the frame.\n"
                f"     * Complexion & Eyes: Explicitly specify skin tone and eye color (e.g. 'warm tan skin, expressive dark brown cartoon eyes' or 'fair peach skin, lively green cartoon eyes')! NEVER omit skin tone!\n"
                f"     * Hair: Explicitly specify hair color and hairstyle (e.g. '{c1_hair_example}')!\n"
                f"     * Wardrobe: Explicitly specify authentic thematic costume garments and colors MATCHING THIS SPECIFIC SETTING ({anchor_environment}) — NEVER plain t-shirts/hoodies, and NEVER copy unrelated clothing!\n"
                f"   - Character 2 (Right Position): An energetic 15-year-old high-school student {p2_word} (tall slender build) positioned on the RIGHT side of the frame.\n"
                f"     * Complexion & Eyes: Explicitly specify skin tone and eye color (e.g. 'fair peach skin, clear blue cartoon eyes' or 'warm olive skin, expressive dark hazel cartoon eyes')!\n"
                f"     * Hair: Explicitly specify contrasting hair color and hairstyle (e.g. '{c2_hair_example}')!\n"
                f"     * Wardrobe: Explicitly specify complementary authentic thematic costume garments and colors matching this setting!\n"
                f"   CRITICAL GENDER-ACCURATE HAIRSTYLE RULE:\n"
                f"   - For MALE characters: ALWAYS use short, distinctly masculine hairstyles (short textured side-part, neat tapered sides, crew-cut). STRICTLY FORBIDDEN FOR MALES: NO buns, NO chignons, NO bobs, NO ponytails, NO feminine long hair!\n"
                f"   - For FEMALE characters: ALWAYS use stylish feminine hairstyles (ponytails, soft shoulder-length waves, bobs with bangs). STRICTLY FORBIDDEN FOR FEMALES: NO masculine quiffs or buzz cuts!\n"
                f"   CRITICAL MULTI-CHARACTER RULE: You MUST explicitly describe the sex, skin tone, hair color, and wardrobe of BOTH characters! Strictly ban generic words like 'two teens' or 'the characters'!"
            )
        else:
            p_gend = get_speaker_gender_safe(speakers_gender, "NARRATOR", "") or get_speaker_gender_safe(speakers_gender, "PERSON_ONE", "male")
            is_female = "f" in str(p_gend).lower() or "girl" in str(p_gend).lower()
            gender_desc = "high-school student girl (approx. 15-16 years old, tall slender build)" if is_female else "high-school student boy (approx. 15-16 years old, tall slender build)"
            protagonist_hair = (
                "dark wavy hair tied in an elegant ponytail or chic shoulder-length bob"
                if is_female
                else "short textured dark hair with clean tapered sides and a neat side-part (NEVER buns or long hair for boys!)"
            )
            character_directive = (
                f"2. Protagonist (MANDATORY EXACT SKIN TONE, EYE COLOR, HAIR & WARDROBE CONTINUITY):\n"
                f"   - Primary Character: An expressive {gender_desc} with explicitly specified skin tone (e.g. 'warm tan skin' or 'fair peach skin'), eye color (e.g. 'dark brown cartoon eyes'), hair color and hairstyle (e.g. '{protagonist_hair}'), and an authentic thematic costume/wardrobe explicitly matching this setting (describe specific colors and garment types — NEVER plain generic t-shirts/hoodies).\n"
                f"   - Staging & Companion Rule: If any secondary character, peer, or companion appears, Character 1 is on the LEFT and Character 2 is on the RIGHT, each with explicitly specified sex, skin tone, hair color, and distinct thematic costumes (NEVER plain t-shirts/hoodies)!"
            )

        video_type_clean = (video_type or "EXPRESSION").strip().upper()
        if video_type_clean == "GAME":
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (GAME — FRONTAL DILEMMA & FOURTH-WALL EYE CONTACT):\n"
                "   - Hook Scene: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo teen protagonist centered, making 100% direct fourth-wall eye contact into the camera lens with an expressive, animated dilemma expression.\n"
                "   - Answer Scene: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum, celebrating eureka victory.\n"
                "   - Explanation Scene: Real-world narrative medium-wide shot (35mm lens) with deep spatial environment and 0% eye contact with camera (100% in-scene immersion).\n"
                "   - Crisp cast shadows on the floorboards, high focus on the dilemma."
            )
        elif video_type_clean in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (FUN_FACTS — MONUMENTAL SCALE OF WONDER):\n"
                "   - Establish a dramatic low-angle heroic perspective looking upward from low elevation.\n"
                "   - The teen protagonist is positioned in the lower third of the frame, head tilted upward in awe at a towering, imposing cultural anomaly, ancient clockwork, or giant historic relic.\n"
                "   - Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating a striking scale contrast between the student and the wonder."
            )
        elif video_type_clean == "ROLEPLAY":
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (ROLEPLAY — CINEMATIC THRESHOLD DIALOGUE):\n"
                "   - Establish a dynamic diagonal trajectory across a physical boundary (doorframe, table edge, counter, or curtain line).\n"
                "   - Characters are positioned across an active physical divide, engaged in close conversational drama. STRICTLY ZERO eye contact with camera (100% fourth-wall barrier).\n"
                "   - Directional cinematic side-key lighting, dramatic chiaroscuro shadows across faces, authentic interpersonal narrative tension."
            )
        else:  # EXPRESSION
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (EXPRESSION — LAYERED DEPTH INSIDER GUIDE):\n"
                "   - Establish an angled foreground-and-background depth composition (35mm wide lens with layered Rule-of-Thirds depth planes).\n"
                "   - The foreground zone (occupying 35-40% of the frame, left or right) is reserved for the expressive teen guide, while the luminous midground and background (60%) showcase the expansive storybook setting and the oversized thematic visual metaphor in atmospheric depth.\n"
                "   - Warm atmospheric lighting with distinct depth separation between foreground and background."
            )

        system_prompt = (
            "You are a professional visual director for language-learning animated YouTube Shorts.\n"
            "Your task is to establish the overarching General Visual Prompt / Story World Anchor that will define "
            "the visual context, thematic environment, character appearance, and atmosphere for ALL scenes of this video.\n\n"
            "MANDATORY DIRECTIVES:\n"
            "1. Macro-Setting & Architecture: Describe a rich, authentic physical setting with architectural details, indoor depth, "
            "furniture, ambient props, atmospheric lighting, and soft cast shadows.\n"
            f"{character_directive}\n"
            "   Strictly ban generic modern street clothes (plain t-shirts/hoodies) and mature adults.\n"
            "3. Creative Visual Metaphor & Graphic Props in Environment:\n"
            "   Embrace the GRAPHIC / LITERAL SENSE of the expression or topic by placing relevant physical props naturally in the setting to make the world visually magnetic and fun "
            "(e.g., for 'a piece of cake', feature an elaborate multi-tiered cake on the display table; "
            "for 'proJECT vs PROject', camera tripods, clapperboard, and megaphone on the film shoot set; for travel/visiting, vintage luggage, train timetables, and architectural maps).\n"
            "   STRICT BAN ON GENERIC PROP CLICHÉS: NEVER use generic ribbon-wrapped gift boxes, mystery boxes, or present parcels unless the topic literally and explicitly discusses gifts or birthdays.\n"
            "4. Atmosphere & Style: Vibrant color palette, rich cinematic lighting, clean modern 2D cartoon narrative illustration, "
            "stylized 2D animation art style, vibrant flat colors, bold outlines, expressive facial design, large cartoon eyes with visible sclera and specular highlights, rich interior depth.\n"
            f"{format_staging_directive}\n"
            "6. STATIC STAGE SETUP ONLY (NO MOMENTARY DIALOGUE ACTIONS):\n"
            "   Describe the physical stage, setting props, and characters standing ready on set in their thematic costumes and positions matching the format staging above.\n"
            "   DO NOT describe temporary dialogue actions (such as shouting, covering ears, arguing, or gesturing) in this General Prompt! Temporary actions belong strictly to individual scene prompts.\n"
            "7. Keep the description rich, concrete, vivid, and around 110-180 words (detailed enough to establish specific character clothing, positions, and environmental props).\n"
            "8. ANTI-CLICHÉ BAN: Strictly DO NOT use generic AI clichés: BANNED are generic greenhouses or plant nurseries, plain empty classrooms/schools, pottery/ceramic workshops, flower shops, or generic coffee shops. Ground the setting authentically in the dialogue domain.\n"
            "9. Return ONLY the visual prompt text. No markdown formatting, no commentary."
        )

        user_content = (
            f"LANGUAGE / SUBJECT: {language} / {subject}\n"
            f"CONTEXT: {situation}\n"
            f"VIDEO TYPE: {video_type}\n"
            f"TOPIC: {topic}\n"
            f"SCENARIO: {scenario}\n"
            f"LEXICAL FIELD: {lexical_field}\n"
            f"THEMATIC BASE SETTING: {anchor_environment}\n\n"
            f"FULL SCRIPT TEXT (THE COMPLETE STORY):\n{script_text}\n\n"
        )
        if guidance:
            user_content += f"SPECIAL DIRECTOR GUIDANCE NOTES:\n{guidance}\n\n"
        user_content += "Create the overarching General Visual Prompt now:"

        logger.info("[%s] Generating general visual prompt — %s / %s", script_id, language, subject)

        last_error = None
        for attempt in range(1, max_retries + 1):
            stream = None
            start_t = time.time()
            collected: list[str] = []
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_content},
                    ],
                    max_tokens=2500,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if time.time() - start_t > self._wall_timeout:
                        raise TimeoutError(f"LLM general prompt exceeded wall timeout ({self._wall_timeout:.0f}s)")
                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = delta.content if delta else None
                    if content:
                        collected.append(content)

                general_prompt = "".join(collected).strip()
                if not general_prompt:
                    raise ValueError(f"[{script_id}] LLM returned an empty general prompt.")

                logger.info("[%s] General visual prompt generated (%d chars).", script_id, len(general_prompt))
                time.sleep(0.2)
                return sanitize_and_style_prompt(general_prompt)

            except Exception as exc:
                last_error = exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                elapsed = int(time.time() - start_t)
                if attempt < max_retries:
                    logger.warning(
                        "[%s] General prompt generation failed (%s) after %ds. Retrying attempt %d/%d...",
                        script_id, exc, elapsed, attempt + 1, max_retries,
                    )
                    time.sleep(0.8 * attempt)
                else:
                    logger.error("[%s] Failed to generate general prompt after %d attempts: %s", script_id, max_retries, exc)

        if anchor_environment:
            logger.warning("[%s] Falling back to default anchor_environment: %s", script_id, anchor_environment)
            return sanitize_and_style_prompt(anchor_environment)

        raise last_error or RuntimeError(f"[{script_id}] Failed to generate general prompt.")


