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

ANTI-CAFETERIA & NO LOCATION FLIPPING DIRECTIVE:
- NEVER default to a generic cafeteria, coffee shop, or cafe table unless the script explicitly and specifically mentions ordering coffee, a barista, or a cafe setting.
- ALL SCENES IN THIS SHORT MUST BELONG TO THE SAME COHESIVE PHYSICAL STORY WORLD. Do not randomly switch rooms or environments between scenes!

MANDATORY MULTI-CHARACTER GENDER SPECIFICATION (ZERO-AMBIGUITY RULE):
- Whenever MORE THAN ONE character appears in the image (in ROLEPLAY, EXPRESSION, GAME, or any video type):
  * The sex/gender of EACH character MUST be explicitly and unambiguously specified!
  * STRICTLY BAN collective, ambiguous, or generic gender-neutral words: NEVER say "the two teens", "two youthful teenage characters", "two colleagues", "two students", "two friends", "the characters", or "they".
  * ALWAYS explicitly describe each individual character: e.g. "one youthful 14-year-old teen boy with masculine features wearing [wardrobe] and one youthful 14-year-old teen girl with feminine features wearing [wardrobe]" (or "two youthful teen boys", or "two youthful teen girls").
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

2. ABSOLUTE CHARACTER APPEARANCE CONTINUITY (MANDATORY IN EVERY SCENE):
   - Diffusion models generate EACH scene image independently from scratch with zero memory of previous scenes!
   - To guarantee 100% character visual consistency (no shifting hair colors, no shifting clothes, no shifting ages):
     * EVERY SINGLE SCENE PROMPT MUST EXPLICITLY REPEAT THE EXACT SAME VISUAL TRAITS FOR EACH CHARACTER:
       - Exact demographic: e.g. "15-year-old high-school student girl", "15-year-old high-school student boy" (tall slender high school proportions, defined facial features).
       - Exact hair color AND exact hairstyle: e.g. "dark hair in a sleek bun", "textured dark-brown quiff hair" (NEVER change or omit hair color!).
       - Exact wardrobe and garment colors: e.g. "wearing her emerald velvet blazer over white shirt", "wearing his denim utility vest over charcoal long-sleeve" (NEVER change or omit wardrobe!).
       - Exact staging: Character 1 on the LEFT, Character 2 on the RIGHT.
     * NEVER omit the characters' hair color, hairstyle, or wardrobe in any scene prompt, otherwise the image generation model will randomly invent different hair and clothes!
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

5. CAMERA FRAMING PROGRESSION (WAIST-UP / CHEST-UP — NO DISTANT WIDE SHOTS):
   - In 9:16 vertical video, never use distant wide shots where characters shrink into tiny figures!
   - Keep characters comfortably waist-up or chest-up so their facial expressions and eyes remain large, clear, and detailed:
     * FOR EXPRESSION SHORTS:
       - Hook: Medium Shot (waist-up, focus on character's expressive face, opening dilemma, and visual metaphor).
       - Setup: Over-the-shoulder Two-Shot (waist-up conversational exchange, social contrast, or friction).
       - Discovery: Medium Action Shot (waist-up breakthrough moment, radiant eureka expression).
       - Example: Dynamic Medium Action Shot (waist-up active motion, dynamic verb/action demonstration).
       - Payoff: Medium Close-Up (chest-up, warm triumphant celebratory resolution).
     * FOR ROLEPLAY SHORTS (DYNAMIC 4-BEAT CINEMATIC PROGRESSION):
       - Hook: Scenario Establishing Shot (medium-wide framing, establishing opening dilemma, physical tension, and creative visual metaphor).
       - Dialogue_Part_2: Two-Shot or Over-The-Shoulder Shot focusing on the reaction and doubt/question in the dialogue.
       - Dialogue_Part_3: Kinetic Interaction & Demonstration Shot (active motion demonstrating the concept/prop, energetic body language).
       - Payoff: Triumphant Resolution Two-Shot (shared mastery, confident outro reflecting the resolution).
     * FOR GAME SHORTS:
       - Hook: Scenario Dilemma Shot (medium shot establishing the real-world dilemma / challenge).
       - Answer: Eureka Moment (character experiencing joyful breakthrough relief upon solving the puzzle).
       - Explanation: Real-World Application (characters applying the concept naturally in everyday life).
     * FOR FUN_FACTS SHORTS:
       - Hook: Curiosity Setup (medium shot establishing the bizarre question, myth, or intriguing fact).
       - Setup / Discovery: Dynamic Scene Progression (exploring the fascinating cultural/historical discovery in motion).
       - Payoff: Mind-Blown Resolution (warm, memorable celebratory outro).

6. CREATIVE VISUAL METAPHORS & GRAPHIC WORDPLAY (MANDATORY TO AVOID BORING IMAGES):
   - The visual image is the primary hook that attracts and retains the audience! Never produce boring, generic images of a character just looking stressed or staring at a paper/desk.
   - Embrace the GRAPHIC / LITERAL SENSE of words and expressions across the scenes to make them entertaining, memorable, and fun:
     * For 'a piece of cake': Visually play with a giant, colorful, towering multi-tiered cake or an ambitious baking challenge that is effortlessly mastered!
     * For 'break a leg': An opulent theater stage with dramatic velvet curtains, costume masks, and rehearsal props.
     * For 'PREsent vs preSENT': A grand banquet hall where a teen dramatically reveals an ornate ribbon-wrapped gift box.
     * For 'proJECT vs PROject': A rooftop film shoot with camera gear, director clapperboard, and megaphone.
     * For 'spill the beans': A vibrant artisan kitchen where a huge jar of colorful legumes has comically tipped over, revealing a secret discovery.
     * For 'cost an arm and a leg': A lavish high-end boutique with humorous exaggerated luxury displays.
   - We have creative license to play with words and visual metaphors across the scenes to make every image dynamic, eye-catching, and fun!

6. ZERO-TOLERANCE TEXT, SCREEN & INTERJECTION BAN (CRITICAL):
   - NEVER include words like 'aha', 'eureka', 'wow', 'oops', or any words inside quotation marks.
   - Text encoders (Qwen/Lumina) interpret quoted words and interjections as typography commands and literally paint the letters onto the image!
   - Describe purely visual facial expressions: 'eyes widening in breakthrough understanding', 'a bright smile of sudden clarity'.
   - NEVER depict chalkboards, blackboards, whiteboards with words, posters, screens displaying UI/text, tablets with text, monitors, timers, or letters (A, B, C, D).

7. MANDATORY 2D CARTOON ART STYLE (STRICT NO REALISM):
   - Every scene MUST look like a frame from a stylized 2D cartoon narrative illustration, hand-drawn 2D animation art style, with vibrant flat colors, clean lineart, and storybook charm.
   - ABSOLUTELY FORBIDDEN: Photorealism, realistic photos, 3D renders, CGI, real-life photography.

8. ANTI-CAFETERIA DIRECTIVE:
   - NEVER default to a generic cafeteria or cafe table unless the setting explicitly requires one.

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
      * ALWAYS explicitly describe each individual character: e.g. "one youthful 14-year-old teen boy with masculine features wearing [wardrobe] and one youthful 14-year-old teen girl with feminine features wearing [wardrobe]" (or "two youthful teen boys", or "two youthful teen girls").
      * For ROLEPLAY videos: You MUST strictly adhere to the exact assigned genders for PERSON_ONE and PERSON_TWO. NEVER swap their genders, and NEVER make them identical unless explicitly instructed!

OUTPUT FORMAT:
You MUST output ONLY a valid JSON object mapping each scene name (in lowercase, e.g. "hook", "setup", "discovery", "example", "payoff" or for roleplay: "hook", "dialogue_part_2", "dialogue_part_3", "payoff") to its final Z-Image-Turbo prompt string. Do not include markdown code block formatting or explanations outside the JSON object.
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
    (r'\b(park|garden|nature|tree|bench|flower|outdoor|trail)\b', "sunlit botanical park (featuring: walking promenade, garden pavilion, shaded wooden bench, flower lawn)"),
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
    """Detects if the script is about an idiom or figurative expression."""
    combined = f"{topic} {lexical_field} {scenario} {script_text}".lower()
    idiom_markers = [
        "idiom", "expression", "saying", "figurative", "slang", "proverb",
        "piece of cake", "break a leg", "bite the bullet", "spill the beans",
        "under the weather", "cost an arm and a leg", "burn the midnight oil",
        "hit the nail on the head", "once in a blue moon", "barking up the wrong tree",
        "cold feet", "see eye to eye", "ball is in your court", "cross that bridge",
        "call it a day", "cut corners", "easy as pie", "drop in the ocean",
        "rule of thumb", "through the grapevine", "pull someone's leg",
        "actions speak louder", "beat around the bush", "blessing in disguise",
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
        if "piece of cake" in combined_script or "easy as pie" in combined_script:
            return "chic modern social dining salon or studio lounge (featuring: central display table showcasing an elaborate towering multi-tier cake with a single slice removed, stylish seating lounge, sunlit terrace)"
        elif "break a leg" in combined_script:
            return "historic theater and performing arts center (featuring: dressing room with mirror, backstage wings with velvet curtains, rehearsal stage, grand auditorium)"
        elif "spill the beans" in combined_script:
            return "vibrant artisan kitchen and social pantry lounge (featuring: open prep counter with oversized ceramic bean jars, cozy banquette table, sunlit courtyard)"
        elif "under the weather" in combined_script:
            return "cozy sunlit living room and wellness study (featuring: comfortable sofa with warm knitted throw, herbal tea table, indoor botanical plants, reading window)"
        elif "burn the midnight oil" in combined_script:
            return "quiet late-night home study and creative library (featuring: vintage wooden desk with brass lamp, tall bookshelves, armchair, evening city skyline window)"
        elif "cost an arm and a leg" in combined_script:
            return "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"
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
        (r'\b(park|garden|nature|tree|bench|flower|outdoor|trail)\b', "sunlit botanical park (featuring: walking promenade, garden pavilion, shaded wooden bench, flower lawn)"),
        (r'\b(gym|workout|fitness|sport|athletic|exercise|dumbbells)\b', "dynamic modern athletic training gym (featuring: fitness floor, weights zone, training track, recovery lounge)"),
        (r'\b(market|store|boutique|seller|bazaar|craft)\b', "neighborhood artisan market boutique (featuring: craft display table, checkout counter, goods shelf, street awning)"),
        (r'\b(beach|sea|ocean|coastal|boat|sand|shore)\b', "sunlit coastal seaside promenade (featuring: ocean overlook deck, sand dunes path, beach pavilion)"),
        (r'\b(cafe|coffee|barista|latte|espresso)\b', "charming artisanal coffee bar (featuring: espresso counter, window high-top bar, cozy seating corner)"),
    ]

    for pattern, domain in keyword_domains:
        if re.search(pattern, combined_script):
            return domain

    # 4. Authentic modern everyday setting fallback (NON-cafeteria)
    return "sunlit modern apartment living room and creative study (featuring: focus work desk, conversation lounge, bookshelf, indoor botanical plants)"


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
) -> dict[str, str]:
    """
    Extracts and standardizes shared narrative context across single-scene and multi-scene storyboard builders:
    - Resolves anchor environment
    - Voiceover isolation notice
    - Character personalities
    - Mandatory speaker genders
    - Target language brand palette
    - Metadata topic/scenario/lexical context lines
    - Figurative idiom directive
    """
    video_type_upper = video_type.upper()
    if not anchor_environment:
        anchor_environment = resolve_anchor_environment(
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

    gender_context = ""
    if speakers_gender:
        if video_type_upper == "ROLEPLAY":
            p1 = speakers_gender.get("PERSON_ONE", "male")
            p2 = speakers_gender.get("PERSON_TWO", "female")
            p1_desc = "high school student boy (approx. 15-16 years old, tall slender build, stylish thematic attire)" if p1.lower() == "male" else "high school student girl (approx. 15-16 years old, tall slender build, stylish thematic attire)"
            p2_desc = "high school student boy (approx. 15-16 years old, tall slender build, stylish thematic attire)" if p2.lower() == "male" else "high school student girl (approx. 15-16 years old, tall slender build, stylish thematic attire)"
            gender_context = (
                f"MANDATORY CHARACTER GENDERS & DEMOGRAPHIC (HIGH SCHOOL PROTAGONISTS — 15-16 YEARS OLD):\n"
                f"- PERSON_ONE: {p1.upper()} (MUST visually appear as a {p1_desc})\n"
                f"- PERSON_TWO: {p2.upper()} (MUST visually appear as a {p2_desc})\n"
                f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! "
                f"NEVER use generic words like 'the two students', 'two friends', or 'the characters' without stating their individual sex (e.g. 'one high school student girl and one high school student boy').\n"
                f"CRITICAL RULE: Characters are 15-16 year old high school students (tall slender proportions) dressed appropriately for this specific setting. Strictly ban generic plain t-shirts/hoodies, and strictly ban middle-aged/mature adult wrinkles!\n\n"
            )
        else:
            narrator_gend = str(speakers_gender.get("NARRATOR") or speakers_gender.get("PERSON_ONE") or "male").lower()
            is_female = "f" in narrator_gend or "girl" in narrator_gend or "woman" in narrator_gend
            gender_word = "girl" if is_female else "boy"
            gender_desc = "high school student girl" if is_female else "high school student boy"
            gender_context = (
                f"MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (15-16 YEARS OLD):\n"
                f"- PROTAGONIST: MUST visually appear as an expressive high school student {gender_word.upper()} (approx. 15-16 years old {gender_desc}, tall slender proportions).\n"
                f"- WARDROBE: The {gender_word} MUST wear an authentic costume or attire explicitly matching the thematic setting (e.g. theater stage costume/vest, chef uniform, studio apron, lab coat). Strictly ban generic casual clothes (plain t-shirts/hoodies)!\n"
                f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! NEVER use generic words like 'two students' or 'friends'!\n"
                f"CRITICAL RULE: Character MUST be a {gender_word.upper()} ({gender_desc}). Strictly ban mature adult faces, wrinkles, and generic t-shirts!\n\n"
            )
    else:
        gender_context = (
            "MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (15-16 YEARS OLD):\n"
            "- PROTAGONIST: MUST visually appear as a high school student (approx. 15-16 years old, tall slender proportions) wearing an authentic costume or outfit explicitly matching the thematic setting. Strictly ban generic casual clothes (plain t-shirts/hoodies)!\n\n"
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
            "- Play with the graphic, visual sense of the expression across the scenes! Use the literal or visual imagery playfully to make the scenes entertaining and magnetic (e.g. giant towering multi-tiered cakes, ornate gift boxes, dramatic theatrical props, colorful spilled jars).\n"
            "- AVOID BORING IMAGES: Never just show someone staring at a desk or paper looking stressed. Make the visual world lively, imaginative, and fun!\n\n"
        )

    return {
        "anchor_environment": anchor_environment,
        "voiceover_notice": voiceover_notice,
        "personality_context": personality_context,
        "gender_context": gender_context,
        "palette_context": palette_context,
        "context_extra": context_extra,
        "idiom_rule": idiom_rule,
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
    )
    anchor_environment = ctx["anchor_environment"]

    # ── Video-Type Specific Situational Directions ───────────────────────────
    if video_type_upper == "GAME":
        if scene_lower == "hook":
            text_rule = (
                "SCENE GOAL — HOOK (DILEMMA & SITUATION SETUP):\n"
                "1. A vibrant 2D cartoon scene depicting a relatable character facing this exact confusing language dilemma or awkward choice in everyday life.\n"
                "2. The character must have an expressive, puzzled, or hesitant facial expression (e.g. scratching their head, caught in an awkward conversational pause, or pondering a decision).\n"
                "3. Relatable, lively real-life environment matching the locked anchor setting. Do NOT place them in a school, classroom, or generic cafe.\n"
                "4. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, or countdown timers. Focus 100% on the real-world character emotion and situation."
            )
        elif scene_lower == "answer":
            text_rule = (
                "SCENE GOAL — ANSWER (REAL-LIFE RESOLUTION):\n"
                "1. A vibrant 2D cartoon scene showing the character feeling relieved, proud, and smiling because they mastered the linguistic challenge in real life!\n"
                "2. The character visibly displays confident triumph, a joyful smile, or a thumbs-up gesture in the authentic environment.\n"
                "3. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict success screens, monitors, scoreboards, chalkboards, or digital displays. Focus 100% on the human emotional celebration."
            )
        elif scene_lower == "explanation":
            text_rule = (
                "SCENE GOAL — EXPLANATION (REAL-WORLD APPLICATION):\n"
                "1. A vibrant 2D cartoon scene showing native speakers naturally and smoothly using the target expression in the authentic real-world setting.\n"
                "2. Natural body language, warm communicative atmosphere, and engaging social interaction demonstrating practical usage.\n"
                "3. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO tablets, NO signs anywhere in the image."
            )
        else:
            text_rule = (
                "SCENE GOAL — 2D CARTOON SCENE:\n"
                "1. Illustrate the real-life situation cleanly and expressively in modern 2D cartoon animation style.\n"
                "2. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO UI. Focus 100% on characters, environment, and visual storytelling."
            )

    elif video_type_upper in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
        text_rule = (
            "SCENE GOAL — FUN_FACTS (2D CARTOON HISTORICAL & CULTURAL DISCOVERY):\n"
            "1. Clean modern 2D cartoon animation style with rich atmosphere, cinematic depth, and expressive characters.\n"
            "2. Visually depict the authentic historical era, cultural setting, or physical origin of the phrase or fact (e.g. Victorian London, ancient Roman forum, sailors on an 18th-century wooden ship deck, bustling medieval spice market, or a modern relatable person experiencing the fascinating quirk in real life).\n"
            "3. Strong visual environmental storytelling: include authentic architectural details, period attire, and evocative atmosphere.\n"
            "4. ZERO LECTURERS OR CLASSROOMS: Do NOT show a teacher or host lecturing in front of a whiteboard. Show the living world itself.\n"
            "5. TEXT IS STRICTLY BANNED. Do NOT add any written text, letters, words, captions, signs, or labels anywhere in the image."
        )

    elif video_type_upper == "ROLEPLAY":
        p1_g = (speakers_gender.get("PERSON_ONE", "male") if speakers_gender else "male").upper()
        p2_g = (speakers_gender.get("PERSON_TWO", "female") if speakers_gender else "female").upper()
        shot_direction = ""
        if scene_lower == "hook":
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SCENARIO ESTABLISHING SHOT: "
                f"Medium-wide establishing shot setting up the opening real-world dilemma and environment. "
                f"Both characters are visible in frame with explicit genders (PERSON_ONE as {p1_g}, PERSON_TWO as {p2_g}), "
                f"establishing their authentic outfits, physical location, and opening contrast."
            )
        elif scene_lower in ["dialogue_part_1", "part_1"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — OVER-THE-SHOULDER / PERSON_ONE FOCUS: "
                f"Over-the-shoulder shot angled squarely toward PERSON_ONE ({p1_g}), highlighting their expressive face, "
                f"nervous or questioning body language, and opening dilemma. "
                f"PERSON_TWO ({p2_g}) is visible in the foreground/shoulder listening attentively."
            )
        elif scene_lower in ["dialogue_part_2", "part_2"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — 180° REVERSE ANGLE / PERSON_TWO FOCUS: "
                f"Dramatic camera flip! Reverse angle over-the-shoulder shot focused squarely on PERSON_TWO ({p2_g}), "
                f"who gestures patiently and articulates the key linguistic insight/correction. "
                f"PERSON_ONE ({p1_g}) is seen reacting in the frame with confusion or curiosity."
            )
        elif scene_lower in ["dialogue_part_3", "part_3"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — KINETIC PROP & CONCEPT DEMONSTRATION ACTION: "
                f"Dynamic interactive two-shot with active physical motion! Both characters interact with the key physical prop "
                f"or engage in an energetic demonstration of the concept. "
                f"Explicitly describe both characters by sex: one {p1_g} and one {p2_g} in dynamic motion!"
            )
        elif scene_lower in ["dialogue_part_4", "part_4"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — BREAKTHROUGH REACTION CLOSE-UP: "
                f"Medium close-up shot capturing PERSON_ONE ({p1_g}) beaming with sudden clarity, relief, and confidence! "
                f"PERSON_TWO ({p2_g}) is in frame giving an encouraging nod, smile, or supportive gesture."
            )
        elif scene_lower in ["payoff", "resolution"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — CELEBRATORY TRIUMPH / DYNAMIC OUTRO: "
                f"Triumphant celebratory two-shot in a celebratory micro-zone! Both characters (one {p1_g} and one {p2_g}) "
                f"celebrate success (high-five, walking triumphantly together into the event, shared laughter, proudly holding the item)."
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
                "\n4. HOOK (REAL-WORLD DILEMMA & TENSION SETUP):\n"
                "Visually anchor the opening human dilemma, curiosity, or emotional tension in an individual focus micro-zone. Medium shot capturing the character's expressive face and body language reflecting the initial question or feeling, naturally rooted in the physical setting."
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
        f"THEMATIC STORY WORLD & SCENARIO CONTINUITY (MANDATORY):\n"
        f"The overarching real-world thematic setting is:\n"
        f">> {anchor_environment} <<\n"
        f"- MICRO-ZONE ROTATION: Each scene MUST occur in a different micro-zone (desk -> discussion lounge -> workbench -> action stage -> victory area)!\n"
        f"- PROP ROTATION: NEVER repeat the same focal prop across scenes!\n"
        f"- POSE DIVERSITY: Strictly ban repeating generic poses (no duplicate 'pointing' or 'gesturing at models')!\n"
        f"- ANTI-CAFETERIA RULE: Do NOT place characters in a generic cafe, cafeteria, or coffee shop unless the setting explicitly specifies one.\n"
        f"- MANDATORY THEMATIC WARDROBE: The character MUST wear clothing/costume that directly belongs to this setting ({anchor_environment}, e.g. theatrical stage costume/vest in theater, chef coat in kitchen, drafting vest in studio). NEVER use generic modern street clothes (no plain t-shirts/hoodies)!\n\n"
        f"{anti_rep_context}"
        f"{ctx['idiom_rule']}"
        f"{(f'OVERARCHING GENERAL PROMPT (MASTER STORY WORLD & CHARACTER ANCHOR):\n>> {general_prompt} <<\n\nCRITICAL CONTINUITY DIRECTIVE:\nInherit the exact physical environment, characters (exact ages, genders, positions, hairstyles, facial design), specific thematic wardrobes, and atmosphere established in this General Prompt!\n\n' if general_prompt else '')}"
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


def extract_or_build_character_anchors(
    general_prompt: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION"
) -> dict[str, str]:
    """
    Extracts or establishes consistent, locked character traits (hair color, hairstyle, wardrobe)
    from the General Prompt so they can be repeated verbatim in every scene prompt.
    Prevents character identity drift, hair color swapping, and age inconsistency.
    """
    speakers_gender = speakers_gender or {}
    video_type_upper = video_type.strip().upper()
    has_two_characters = (
        video_type_upper == "ROLEPLAY"
        or bool("PERSON_TWO" in speakers_gender)
    )

    p1 = str(speakers_gender.get("PERSON_ONE") or speakers_gender.get("NARRATOR") or "female").lower()
    p2 = str(speakers_gender.get("PERSON_TWO", "male")).lower()
    p1_is_female = "f" in p1 or "girl" in p1 or "woman" in p1
    p2_is_female = "f" in p2 or "girl" in p2 or "woman" in p2

    garments = r"(?:blazer|vest|coat|smock|apron|jacket|robe|dress|sweater|shirt|suit|cardigan|hoodie|uniform|tunic)"

    # 1. Search for hair specifications in general prompt
    hair_matches = re.findall(
        r"(\b(?:dark|jet-black|black|brown|chestnut|auburn|blonde|caramel|brunette|red)\s+[^,\.]{0,35}?\bhair\b[^,\.]*|\bshort\s+[^,\.]{0,30}?\bhair\b[^,\.]*)",
        general_prompt,
        re.IGNORECASE,
    )
    raw_h1 = hair_matches[0].strip() if len(hair_matches) >= 1 else ""
    raw_h2 = hair_matches[1].strip() if len(hair_matches) >= 2 else ""

    # Sanitize hair to guarantee strict gender-appropriate hairstyles
    char1_hair = sanitize_character_hair(raw_h1, is_female=p1_is_female, is_primary=True)
    char2_hair = sanitize_character_hair(raw_h2, is_female=p2_is_female, is_primary=False)

    # 2. Search for attire in general prompt
    attire_pattern = re.compile(rf"(?:in|wearing)\s+([^,\.]{{3,45}}?\b{garments}\b[^,\.]*?)", re.IGNORECASE)
    attire_matches = attire_pattern.findall(general_prompt)
    if len(attire_matches) >= 2:
        char1_attire = attire_matches[0].strip()
        char2_attire = attire_matches[1].strip()
    elif len(attire_matches) == 1:
        char1_attire = attire_matches[0].strip()
        char2_attire = "a complementary thematic designer vest"
    else:
        char1_attire = "an authentic thematic costume matching this setting"
        char2_attire = "a complementary thematic costume matching this setting"

    gender_word1 = "girl" if p1_is_female else "boy"
    gender_word2 = "girl" if p2_is_female else "boy"

    char1_desc = f"15-year-old high-school student {gender_word1} with {char1_hair} wearing {char1_attire}"
    char2_desc = f"15-year-old high-school student {gender_word2} with {char2_hair} wearing {char2_attire}"

    if has_two_characters:
        continuity_summary = (
            f"Character appearance continuity: Character 1 is a {char1_desc}; "
            f"Character 2 is a {char2_desc}."
        )
    else:
        continuity_summary = (
            f"Character appearance continuity: The protagonist is a {char1_desc}."
        )

    return {
        "has_two_characters": str(has_two_characters),
        "char1_desc": char1_desc,
        "char2_desc": char2_desc,
        "char1_hair": char1_hair,
        "char2_hair": char2_hair,
        "char1_attire": char1_attire,
        "char2_attire": char2_attire,
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
    )
    anchor_environment = ctx["anchor_environment"]

    general_prompt_block = ""
    if general_prompt:
        general_prompt_block = (
            "OVERARCHING GENERAL PROMPT (MASTER STORY WORLD & CHARACTER ANCHOR):\n"
            f">> {general_prompt} <<\n\n"
            "CRITICAL STORY WORLD & CHARACTER CONTINUITY DIRECTIVE:\n"
            "All scenes below MUST strictly inherit the exact physical environment, characters (exact ages, genders, "
            "positions, hairstyles, facial design), specific thematic costumes/wardrobes, and atmosphere established "
            "in this General Prompt!\n"
            "MANDATORY CONTINUITY REPETITION RULE: Diffusion models generate EACH scene image independently with zero memory of other scenes! "
            "Therefore, in EVERY single scene prompt below, you MUST explicitly repeat each character's exact hair color, "
            "exact hairstyle, and exact wardrobe (e.g. 'one 14-year-old adolescent teen girl with dark hair in a sleek bun wearing an emerald velvet blazer over white shirt', "
            "'one 15-year-old adolescent teen boy with textured brown quiff hair wearing a denim utility vest'). "
            "NEVER omit the hair color, hairstyle, or wardrobe from any scene prompt!\n\n"
        )

    formatted_scenes = []
    for sec_name, sec_text in sections.items():
        if sec_text.strip():
            formatted_scenes.append(f"[{sec_name.upper()}]: \"{sec_text.strip()}\"")
    scenes_block = "\n".join(formatted_scenes)

    video_type_upper = video_type.strip().upper()
    if video_type_upper == "ROLEPLAY":
        p1 = (speakers_gender.get("PERSON_ONE", "male") if speakers_gender else "male").upper()
        p2 = (speakers_gender.get("PERSON_TWO", "female") if speakers_gender else "female").upper()
        p1_word = "girl" if "F" in p1 else "boy"
        p2_word = "girl" if "F" in p2 else "boy"
        director_task = (
            f"DIRECTOR'S ROLEPLAY STORYBOARD TASK (CHRONOLOGICAL 4-SCENE PROGRESSION):\n"
            f"Transform this two-character roleplay dialogue into a dynamic, narrative-faithful 4-scene visual storyboard between PERSON_ONE ({p1}) and PERSON_TWO ({p2}).\n\n"
            f"CRITICAL DIRECTIVES FOR SCRIPT DIALOGUE ENACTMENT & SCENE PROGRESSION:\n"
            f"1. FAITHFUL DIALOGUE ENACTMENT (HIGHEST PRIORITY):\n"
            f"   Every scene MUST directly illustrate the specific spoken dialogue lines and emotional interaction of that scene:\n"
            f"   - HOOK: Illustrate the specific opening problem/stress in this line! Depict the characters' physical actions and facial expressions directly acting out the words (e.g. deadline tension, holding scenario props like scripts or clapperboards).\n"
            f"   - DIALOGUE_PART_2: Illustrate the exact doubt, question, or confusion spoken in this dialogue! Show the character's facial expression reacting with genuine puzzlement to the words being discussed.\n"
            f"   - DIALOGUE_PART_3: Illustrate the native explanation, rule demonstration, or solution spoken in this dialogue! Characters must physically demonstrate the concept using realistic scenario props (pointing to text, showing physical actions). STRICTLY BAN surreal fantasy effects (NO glowing energy beams from chest, NO floating graphics).\n"
            f"   - PAYOFF: Illustrate the triumphant resolution of this specific story! Show genuine relief, confidence, and mastery directly reflecting the final lines of the dialogue (DO NOT default to generic high-fives unless the dialogue calls for it).\n"
            f"2. MANDATORY CHARACTER APPEARANCE REPETITION (ZERO-DRIFT IDENTITY):\n"
            f"   In EVERY scene prompt, explicitly describe BOTH characters using their exact locked traits from the General Prompt:\n"
            f"   - Restate Character 1: 15-year-old high-school student {p1_word} (tall slender proportions), exact hair color, exact hairstyle, and exact wardrobe!\n"
            f"   - Restate Character 2: 15-year-old high-school student {p2_word} (tall slender proportions), exact hair color, exact hairstyle, and exact wardrobe!\n"
            f"   - NEVER omit hair color, hairstyle, or wardrobe in any scene prompt!\n"
            f"3. AVOID REPETITIVE TWO-SHOTS: Vary camera angles (medium, over-the-shoulder, reaction shot, two-shot) and distinct character poses across scenes.\n"
            f"4. ZERO-AMBIGUITY MULTI-CHARACTER GENDER RULE: Explicitly specify the sex of EACH character (e.g. 'one adolescent 14-year-old teen {p1_word}' and 'one adolescent 15-year-old teen {p2_word}'). Strictly ban generic words like 'two teens', 'two friends', or 'the characters'!\n"
            f"5. LENGTH: Around 70-110 words per scene prompt (rich enough to include the full character continuity description, action, props, and setting).\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, dialogue_part_2, dialogue_part_3, payoff) to its final prompt string."
        )
    elif video_type_upper == "GAME":
        director_task = (
            f"DIRECTOR'S GAME STORYBOARD TASK (CHALLENGE TO TRIUMPH PROGRESSION):\n"
            f"Transform this game quiz into a cohesive storyboard where each scene faithfully depicts the specific question, answer, and explanation:\n"
            f"1. FAITHFUL SCRIPT ENACTMENT:\n"
            f"   - HOOK: Illustrate the real-world dilemma or question presented in the Hook text.\n"
            f"   - ANSWER: Illustrate the eureka breakthrough relief and joyful reaction upon identifying the correct answer.\n"
            f"   - EXPLANATION: Illustrate the practical real-world demonstration of the concept in everyday life as spoken in the explanation.\n"
            f"2. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Strictly ban generic words like 'two teens'.\n"
            f"3. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact high school student demographic (15-16yo, tall slender proportions), hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"4. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
        )
    elif video_type_upper in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
        director_task = (
            f"DIRECTOR'S FUN FACTS STORYBOARD TASK (CURIOSITY & DISCOVERY PROGRESSION):\n"
            f"Transform this curiosity script into a visually stunning, narrative-faithful storyboard:\n"
            f"1. FAITHFUL SCRIPT ENACTMENT:\n"
            f"   - HOOK: Illustrate the intriguing mystery or bizarre myth described in the Hook text.\n"
            f"   - SETUP / DISCOVERY / FACTS: Illustrate the fascinating real-world discovery being unveiled in dynamic motion.\n"
            f"   - PAYOFF: Illustrate the mind-blown reaction, awe, and memorable resolution.\n"
            f"2. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Strictly ban generic words like 'two teens'.\n"
            f"3. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact high school student demographic (15-16yo, tall slender proportions), hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"4. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
        )
    else:
        director_task = (
            f"DIRECTOR'S EXPRESSION STORYBOARD TASK (CHRONOLOGICAL 5-BEAT PROGRESSION):\n"
            f"Create a cohesive 5-scene visual storyboard where EVERY scene faithfully visualizes the specific narrative beat and spoken script text of that scene in CHRONOLOGICAL ORDER:\n"
            f"1. FAITHFUL SCRIPT ENACTMENT (HIGHEST PRIORITY):\n"
            f"   Every scene MUST directly depict the specific words and meaning from that scene's text:\n"
            f"   - HOOK: Illustrate the opening dilemma, curiosity, or visual metaphor described in the Hook text.\n"
            f"   - SETUP: Illustrate the conversational friction, misunderstanding, or tricky distinction spoken in this beat.\n"
            f"   - DISCOVERY: Illustrate the eureka turning point — wide joyful eyes, sudden breakthrough clarity, reacting directly to the native rule being explained.\n"
            f"   - EXAMPLE: ACTIVELY DEPICT THE EXACT EXAMPLE SENTENCE FROM THE SCRIPT IN DYNAMIC MOTION! Show the character living out the specific action or situation described in the narration.\n"
            f"   - PAYOFF: Illustrate the triumphant real-world resolution and confidence of mastering this expression.\n"
            f"2. ZERO-DUPLICATE PROPS & REALISTIC ACTION: Give each scene distinct physical postures and unique focal objects. Strictly ban surreal fantasy magic effects.\n"
            f"3. CAMERA SHOTS (WAIST-UP / CHEST-UP ONLY): Keep characters comfortably close to camera so their faces remain large and detailed.\n"
            f"4. MULTI-CHARACTER GENDER SPECIFICATION: If more than 1 character is depicted, explicitly specify the sex of EACH character (e.g. 'one teen boy and one companion teen girl'). Strictly ban generic phrases like 'two teens'.\n"
            f"5. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact high school student demographic (15-16yo, tall slender proportions), hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"6. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
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
        f"{ctx['idiom_rule']}"
        f"OVERARCHING THEMATIC BASE SETTING:\n"
        f">> {anchor_environment} <<\n\n"
        f"{general_prompt_block}"
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
        r"\bwith\s+[^,\.]{0,45}?\b(?:tied in a (?:sleek\s+)?bun|in a (?:sleek\s+)?bun|sleek bun|hair bun|in a bob|in a ponytail|chignon)\b",
        "with short textured dark hair and a neat side-part",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(boy|man|male(?:\s+teen|\s+student)?)\b([^,\.]{0,40}?)\b(?:tied in a (?:sleek\s+)?bun|in a (?:sleek\s+)?bun|sleek bun|hair bun|in a bob|in a ponytail|chignon)\b",
        r"\1\2with short textured dark hair and neat side-part",
        text,
        flags=re.IGNORECASE,
    )
    # 3c. Ensure female characters NEVER have masculine haircuts (quiffs, buzz cuts, crew cuts)
    text = re.sub(
        r"\bwith\s+[^,\.]{0,45}?\b(?:quiff hair|quiff|buzz-?cut|crew-?cut)\b",
        "with textured caramel-brown hair styled in soft shoulder-length waves",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(girl|woman|female(?:\s+teen|\s+student)?)\b([^,\.]{0,40}?)\b(?:quiff hair|quiff|buzz-?cut|crew-?cut)\b",
        r"\1\2with soft wavy hair resting over shoulders",
        text,
        flags=re.IGNORECASE,
    )

    # 4. Mandatory High School Student Demographic & Thematic Wardrobe Upgrades
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:man|actor|gentleman)\b", "a 15-year-old high-school student boy", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:woman|actress|lady)\b", "a 15-year-old high-school student girl", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:performer|enthusiast|student|person|scholar|professional|individual|character)\b", "a 15-year-old high-school student protagonist", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\bNO\s)(?<!\bmiddle-aged\s)(?<!\bolder\s)\b(adult|grown-?up)s?\b", "high-school students", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\bNO\s)\ban adult\b", "a high-school student", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:8|9|10|11|12|13|14)-year-old\b", "15-year-old", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:wearing\s+)?normal clothing\b", "wearing thematically authentic scene costume", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:smart\s+)?casual attire\b", "thematic scene-specific wardrobe", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcasual clothes\b", "thematic scene-specific costume", text, flags=re.IGNORECASE)

    # 5. Mandatory 2D Cartoon Style Anchor with High School Proportions & Safe Exclusions
    style_mandate = (
        "Clean modern 2D cartoon narrative illustration, stylized 2D animation art style, "
        "vibrant flat colors, bold outlines, expressive high-school student character design (approx. 15-16 years old, tall slender proportions), "
        "large clear cartoon eyes with visible white sclera and specular pupil highlights, "
        "thematically authentic scene-specific wardrobe matching the environment (NO generic modern street clothes, NO plain t-shirts/hoodies), "
        "rich detailed environmental interior background with depth and warm atmospheric lighting. "
        "(high-school student protagonist, thematic costume, NO mature adult wrinkles, NO elderly, "
        "NO generic casual t-shirts, NO plain hoodies, NO dot eyes, NO minimalist faces, NO blank backgrounds, "
        "NO 3D render, NO photorealism, NO photograph, NO text, NO watermark)."
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
        if not general_prompt and anchor_environment and len(anchor_environment) > 80:
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
        if not general_prompt:
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
        )

        final_prompts: dict[str, str] = {}
        for sec_key, raw_prompt in storyboard_dict.items():
            prompt_str = raw_prompt.strip()
            # Verify if character hair and wardrobe continuity tokens are present
            c1_words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', anchors["char1_attire"].lower()) if w not in {"with", "wear", "wearing", "over", "into"}]
            has_c1_attire = any(w in prompt_str.lower() for w in c1_words) if c1_words else True
            has_c1_hair = any(w in prompt_str.lower() for w in ["hair", "bun", "ponytail", "quiff", "bob", "undercut", "curls"])

            if not (has_c1_attire and has_c1_hair):
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
            or bool(speakers_gender and "PERSON_TWO" in speakers_gender)
        )
        if has_two_characters:
            p1_g = speakers_gender.get("PERSON_ONE", "female") if speakers_gender else "female"
            p2_g = speakers_gender.get("PERSON_TWO", "male") if speakers_gender else "male"
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
                f"2. Dual Lead Characters (MANDATORY EXACT GENDER-ACCURATE HAIR & THEMATIC WARDROBE CONTINUITY):\n"
                f"   - Character 1 (Left Position): An expressive 15-year-old high-school student {p1_word} (tall slender build) positioned on the LEFT side of the frame.\n"
                f"     * Hair: Explicitly specify hair color and hairstyle (e.g. '{c1_hair_example}')!\n"
                f"     * Wardrobe: Explicitly specify authentic thematic costume garments and colors MATCHING THIS SPECIFIC SETTING ({anchor_environment}) — NEVER plain t-shirts/hoodies, and NEVER copy unrelated clothing!\n"
                f"   - Character 2 (Right Position): An energetic 15-year-old high-school student {p2_word} (tall slender build) positioned on the RIGHT side of the frame.\n"
                f"     * Hair: Explicitly specify contrasting hair color and hairstyle (e.g. '{c2_hair_example}')!\n"
                f"     * Wardrobe: Explicitly specify complementary authentic thematic costume garments and colors matching this setting!\n"
                f"   CRITICAL GENDER-ACCURATE HAIRSTYLE RULE:\n"
                f"   - For MALE characters: ALWAYS use short, distinctly masculine hairstyles (short textured side-part, neat tapered sides, crew-cut). STRICTLY FORBIDDEN FOR MALES: NO buns, NO chignons, NO bobs, NO ponytails, NO feminine long hair!\n"
                f"   - For FEMALE characters: ALWAYS use stylish feminine hairstyles (ponytails, soft shoulder-length waves, bobs with bangs). STRICTLY FORBIDDEN FOR FEMALES: NO masculine quiffs or buzz cuts!\n"
                f"   CRITICAL MULTI-CHARACTER RULE: You MUST explicitly describe the sex, hair color, and wardrobe of BOTH characters! Strictly ban generic words like 'two teens' or 'the characters'!"
            )
        else:
            p_gend = speakers_gender.get("NARRATOR") or speakers_gender.get("PERSON_ONE") or "male" if speakers_gender else "male"
            is_female = "f" in str(p_gend).lower() or "girl" in str(p_gend).lower()
            gender_desc = "high-school student girl (approx. 15-16 years old, tall slender build)" if is_female else "high-school student boy (approx. 15-16 years old, tall slender build)"
            protagonist_hair = (
                "dark wavy hair tied in an elegant ponytail or chic shoulder-length bob"
                if is_female
                else "short textured dark hair with clean tapered sides and a neat side-part (NEVER buns or long hair for boys!)"
            )
            character_directive = (
                f"2. Protagonist (MANDATORY EXACT HAIR & WARDROBE CONTINUITY):\n"
                f"   - Primary Character: An expressive {gender_desc} with explicitly specified hair color and hairstyle (e.g. '{protagonist_hair}'), and an authentic thematic costume/wardrobe explicitly matching this setting (describe specific colors and garment types — NEVER plain generic t-shirts/hoodies).\n"
                f"   - Staging & Companion Rule: If any secondary character, peer, or companion appears, Character 1 is on the LEFT and Character 2 is on the RIGHT, each with explicitly specified sex, hair color, and distinct thematic costumes (NEVER plain t-shirts/hoodies)!"
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
            "(e.g., for 'a piece of cake', feature an elaborate multi-tiered cake on the display table; for 'PREsent vs preSENT', an ornate ribbon-wrapped gift box; "
            "for 'proJECT vs PROject', camera tripods, clapperboard, and megaphone on the film shoot set).\n"
            "4. Atmosphere & Style: Vibrant color palette, rich cinematic lighting, clean modern 2D cartoon narrative illustration, "
            "stylized 2D animation art style, vibrant flat colors, bold outlines, expressive facial design, large cartoon eyes with visible sclera and specular highlights, rich interior depth.\n"
            "5. STATIC STAGE SETUP ONLY (NO MOMENTARY DIALOGUE ACTIONS):\n"
            "   Describe the physical stage, setting props, and characters standing ready on set in their thematic costumes and Left/Right positions.\n"
            "   DO NOT describe temporary dialogue actions (such as shouting, covering ears, arguing, or gesturing) in this General Prompt! Temporary actions belong strictly to individual scene prompts.\n"
            "6. Keep the description rich, concrete, vivid, and around 110-180 words (detailed enough to establish specific character clothing, positions, and environmental props).\n"
            "7. Return ONLY the visual prompt text. No markdown formatting, no commentary."
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


