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

MANDATORY YOUTHFUL TEEN PROTAGONIST DIRECTIVE (12–15 YEARS OLD — SITUATION-APPROPRIATE ATTIRE):
- ALL main characters across EVERY scene MUST be youthful 2D cartoon TEENS (approx. 12–15 years old, young teen boys or girls).
- STRICT PROHIBITION ON CHILDISH ELEMENTS:
  * Do NOT depict them as little children, kids, or toddlers.
  * NO childish clothing (e.g. dungarees, toddler bibs, oversized cartoon tees, childish hats).
  * NO toys, childish backpacks, or toddler accessories unless explicitly required by the script.
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
- approximate age (youthful teen, 13-15 years old)
- gender when relevant
- appearance
- hairstyle
- situation-appropriate clothing (thematic costume/wardrobe matching the scene, NO plain street clothes, NO childish clothes)
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

CRITICAL DIRECTIVES FOR COMPLETE SCENE UNIQUENESS & ZERO REPETITION:

1. THEMATIC MACRO-WORLD WITH MICRO-ZONE DIVERSITY:
   All scenes share the same overarching real-world thematic setting (e.g. creative innovation agency, music production studio, curiosity archives).
   HOWEVER, EVERY SCENE MUST OCCUR IN A DIFFERENT MICRO-ZONE within that world:
   - Hook: An individual focus station, private desk, or reflective corner.
   - Setup: A collaborative discussion area, lounge, or meeting space.
   - Discovery: An active demonstration bench, specimen cabinet, or discovery workbench.
   - Example: THE ACTION STAGE — actively living out the specific example sentence in full dynamic motion!
   - Payoff: A celebration area, exit lounge, or victory space.

2. PROP ROTATION (STRICT ZERO-DUPLICATE RULE):
   - NEVER repeat the same focal prop across scenes!
   - If Scene 1 features a notebook/tablet, Scene 2 CANNOT have a notebook/tablet.
   - If Scene 3 features a miniature model or tool, Scene 4 CANNOT have that model or tool, and Scene 5 CANNOT have it!
   - Every single scene MUST have a unique, identifiable physical object or visual center of attention.

3. KINETIC ENERGY & POSE DIVERSITY (STRICT BAN ON CLICHE POSES):
   - ABSOLUTELY DO NOT repeat generic gestures like 'pointing', 'gesturing emphatically', or 'leaning over a desk' across scenes!
   - Enforce distinct postures across the story arc:
     * Hook: Still, reflective curiosity, touching chin, tilted head, questioning facial expression.
     * Setup: Two-character dynamic interaction, conversational banter, expressive facial exchange.
     * Discovery: Sudden breakthrough clarity, wide joyful eyes, holding up the breakthrough discovery.
     * Example: DYNAMIC PHYSICAL MOTION depicting the exact verb/action from the narration (e.g. projecting a luminous light beam, assembling, running, demonstrating)!
     * Payoff: Confident victory, high-five, relaxed celebratory posture, bright warm smile.

4. CAMERA FRAMING PROGRESSION (MEDIUM SHOTS ONLY - NO DISTANT WIDE SHOTS):
   - In 9:16 vertical video, never use distant wide shots where characters shrink into tiny figures, causing their facial details and eyes to turn into dots!
   - Every scene must be framed comfortably waist-up or chest-up so the character's face is prominent, expressive, and detailed:
     * FOR EXPRESSION SHORTS:
       - Hook: Medium Shot (waist-up, focus on character's expressive face and opening dilemma).
       - Setup: Over-the-shoulder Two-Shot (waist-up conversational exchange, expressive acting).
       - Discovery: Medium Action Shot (waist-up breakthrough moment, radiant expression).
       - Example: Dynamic Medium Action Shot (waist-up active motion, dynamic verb demonstration).
       - Payoff: Medium Close-Up (chest-up, warm triumphant celebratory resolution).
     * FOR ROLEPLAY SHORTS (DYNAMIC 4-BEAT CINEMATIC PROGRESSION — NEVER REPEAT IDENTICAL TWO-SHOTS):
       - Hook: Scenario Establishing Shot (medium-wide, setting up the dilemma, environment, and physical tension; visually establishes opening dilemma and problem).
       - Dialogue_Part_2: 180° Reverse Angle Over-The-Shoulder / Focus on PERSON_TWO mentoring and explaining the correction.
       - Dialogue_Part_3: Kinetic Interaction & Prop Demonstration Shot (active motion demonstrating the concept/prop, energetic body language).
       - Payoff: Celebratory Resolution Two-Shot (shared triumph, high-five, walking triumphantly into event, confident outro).

5. FIGURATIVE IDIOM DUAL-LAYER RULE:
   - When the Short is about an idiom or figurative expression (e.g. 'piece of cake', 'break a leg', 'spill the beans'):
     * The Hook and Setup may playfully nod to the literal curiosity.
     * The Example and Payoff MUST depict the REAL-WORLD FIGURATIVE ACHIEVEMENT (e.g. an everyday person effortlessly fixing a bicycle, effortlessly parallel parking, or solving a puzzle in 3 seconds).
     * STRICT BAN: DO NOT depict people eating/baking cake or repeating literal props in the Example or Payoff! Focus on real-life accomplishment!

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

11. MANDATORY YOUTHFUL TEEN DEMOGRAPHIC & THEMATIC WARDROBE:
    - All main characters across every scene MUST be youthful 2D cartoon teens (approx. 12–15 years old, young teen boys and girls).
    - STRICTLY FORBIDDEN: Childish clothes (dungarees, bibs, oversized cartoon tees), toys, or toddler appearances. Also STRICTLY FORBIDDEN: Middle-aged adults, elderly faces, or mature wrinkles.
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
    "produce": "sunlit organic farmstead and rustic market barn (featuring: harvest sorting tables, wooden crate stalls, farm kitchen counter, open-air pergola)",
    "content": "warm personal library and literary study (featuring: tall mahogany bookshelves, reading armchair by the window, fireplace hearth, writing desk)",
    "minute": "precision watchmaking and mechanical atelier (featuring: magnifying loupe workbench, clockwork gear cabinet, calibration table, display showcase)",
    "close": "bespoke tailoring boutique and fashion design atelier (featuring: cutting table with measuring shears, mannequin fitting area, fabric bolt wall, dressing lounge)",
    "clothe": "bespoke tailoring boutique and fashion design atelier (featuring: cutting table with measuring shears, mannequin fitting area, fabric bolt wall, dressing lounge)",
    "rice": "artisan culinary kitchen and gourmet dining space (featuring: wooden preparation counter, cookware rack, dining table, garden terrace)",
    "rise": "sunlit artisan bakery and dawn terrace (featuring: wooden kneading table, baker oven alcove, cafe terrace overlooking horizon)",
    "dice": "classic tabletop gaming parlor (featuring: wooden gaming table, board game library shelves, warm hearth, players lounge)",
    "dies": "artisan metal craft foundry and engraving atelier (featuring: hand forge anvil, drafting table, metal tool rack, assembly bench)",
    "ice": "alpine winter lodge and mountain lookout (featuring: frosted bay window, stone fireplace, ski gear rack, scenic snowy overlook)",
    "eyes": "scenic mountain lookout observatory (featuring: panoramic telescope deck, wooden railing, alpine trail bench)",
    "fan": "sunlit sports stadium arena and pavilion (featuring: grandstand seating, team dugout, concession concourse, athletic field)",
    "fun": "vibrant outdoor carnival park (featuring: festival lawn, creative game stalls, decorative lantern path, open pavilion)",
    "cat": "warm sunlit apartment living room and botanical study (featuring: comfortable sofa, sunny window sill, bookshelf, indoor house plants)",
    "cut": "creative woodworking and craft atelier (featuring: artisan workbench, hand tool wall, material storage racks, design counter)",
    "hat": "charming bespoke millinery boutique (featuring: wooden hat stands, display mirrors, haberdashery counter, dressing lounge)",
    "hot": "sun-drenched coastal beach promenade (featuring: boardwalk railing, shade cabana, open-air terrace, ocean view)",
    "winner": "city athletic marathon finish plaza (featuring: finish line gantry, celebration podium, spectator grandstand, winner enclosure)",
    "wiener": "sunny park community picnic lawn (featuring: rustic picnic benches, barbecue pavilion, festive bunting, open grassy field)",
    "peace": "peaceful botanical garden courtyard (featuring: stone water fountain, lush pergola, stone walking path, shaded marble bench)",
    "peas": "sunlit heirloom vegetable garden allotment (featuring: raised wooden garden beds, potting shed, harvest baskets, garden path)",
    "leaf": "autumn deciduous park boulevard (featuring: golden tree canopy, cobblestone path, wooden park bench, historic lamppost)",
    "leave": "scenic train station departure platform (featuring: classic iron canopy, passenger benches, vintage station clock, luggage cart)",
    "life": "lively historic city boulevard (featuring: pedestrian sidewalk, tree-lined avenue, shop facades, public fountain plaza)",
    "live": "acoustic music club stage (featuring: warm stage spotlights, wooden floorboards, instrument stands, intimate audience tables)",
}


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

    # 1. Check known heteronym / word stress domain mappings
    for word_key, domain in HETERONYM_DOMAINS.items():
        if re.search(r'\b' + re.escape(word_key) + r'\b', combined_meta) or re.search(r'\b' + re.escape(word_key) + r'\b', topic.lower()):
            return domain

    # 2. Check for figurative idioms (Prevents the 'Literal Cake/Bakery Trap')
    if is_figurative_idiom(topic, lexical_field, scenario, script_text):
        if "piece of cake" in combined_script or "easy as pie" in combined_script:
            return "modern creative maker studio or living room workspace (featuring: DIY assembly workbench, puzzle table, comfortable reading nook, sunlit terrace)"
        elif "break a leg" in combined_script:
            return "historic theater and performing arts center (featuring: dressing room with mirror, backstage wings with velvet curtains, rehearsal stage, grand auditorium)"
        elif "spill the beans" in combined_script:
            return "vibrant community center and social living room (featuring: cozy seating circle, game table, sunlit courtyard, coffee counter)"
        elif "under the weather" in combined_script:
            return "cozy sunlit living room and wellness study (featuring: comfortable sofa with warm knitted throw, herbal tea table, indoor botanical plants, reading window)"
        elif "burn the midnight oil" in combined_script:
            return "quiet late-night home study and creative library (featuring: vintage wooden desk with brass lamp, tall bookshelves, armchair, evening city skyline window)"
        elif "cost an arm and a leg" in combined_script:
            return "chic metropolitan shopping promenade and artisan boutique (featuring: elegant storefront display, artisan counter, shopping boulevard, terrace)"
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
            p1_desc = "youthful cartoon teen boy (approx. 13-15 years old, stylish situation-appropriate attire)" if p1.lower() == "male" else "youthful cartoon teen girl (approx. 13-15 years old, stylish situation-appropriate attire)"
            p2_desc = "youthful cartoon teen boy (approx. 13-15 years old, stylish situation-appropriate attire)" if p2.lower() == "male" else "youthful cartoon teen girl (approx. 13-15 years old, stylish situation-appropriate attire)"
            gender_context = (
                f"MANDATORY CHARACTER GENDERS & AGE (YOUTHFUL TEEN PROTAGONISTS — 13-15 YEARS OLD):\n"
                f"- PERSON_ONE: {p1.upper()} (MUST visually appear as a {p1_desc})\n"
                f"- PERSON_TWO: {p2.upper()} (MUST visually appear as a {p2_desc})\n"
                f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! "
                f"NEVER use generic words like 'the two teens', 'two friends', or 'the characters' without stating their individual sex (e.g. 'one teen girl and one teen boy').\n"
                f"CRITICAL RULE: Characters are youthful 13-15 year old teens dressed appropriately for this specific setting. Strictly ban childish clothes/toys, and strictly ban middle-aged/mature adult faces!\n\n"
            )
        else:
            narrator_gend = str(speakers_gender.get("NARRATOR") or speakers_gender.get("PERSON_ONE") or "male").lower()
            is_female = "f" in narrator_gend or "girl" in narrator_gend or "woman" in narrator_gend
            gender_word = "girl" if is_female else "boy"
            gender_desc = "young teen girl" if is_female else "young teen boy"
            gender_context = (
                f"MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (13-15 YEARS OLD):\n"
                f"- PROTAGONIST: MUST visually appear as an expressive youthful cartoon teen {gender_word.upper()} (approx. 13-15 years old {gender_desc}).\n"
                f"- WARDROBE: The {gender_word} MUST wear an authentic costume or attire explicitly matching the thematic setting (e.g. theater stage costume/vest, chef uniform, studio apron, lab coat). Strictly ban generic casual clothes (plain t-shirts/hoodies) and childish clothes!\n"
                f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! NEVER use generic words like 'two teens' or 'friends'!\n"
                f"CRITICAL RULE: Character MUST be a {gender_word.upper()} ({gender_desc}). Strictly ban adults, mature faces, wrinkles, and little-kid clothes!\n\n"
            )
    else:
        gender_context = (
            "MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (13-15 YEARS OLD):\n"
            "- PROTAGONIST: MUST visually appear as a youthful 2D cartoon teen (approx. 13-15 years old) wearing an authentic costume or outfit explicitly matching the thematic setting. Strictly ban generic casual clothes (plain t-shirts/hoodies) and childish clothes!\n\n"
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
            "FIGURATIVE IDIOM DIRECTIVE (CRITICAL):\n"
            f"This Short is about an idiom / figurative phrase ('{topic}').\n"
            "- In Hook/Setup: You may playfully nod to the literal curiosity or confusing wording.\n"
            "- In EXAMPLE and PAYOFF: You MUST depict the REAL-WORLD FIGURATIVE ACHIEVEMENT (e.g. someone effortlessly fixing a bike, assembling sleek DIY furniture, or solving a puzzle in 3 seconds).\n"
            "- STRICT BAN: DO NOT place the literal object (e.g. cake, beans, bullet) in the Example or Payoff scenes! Depict the real-life triumph!\n\n"
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
        f"STYLE: polished modern 2D cartoon narrative illustration, clean, expressive, youthful teen protagonist (approx. 13-15 years old, stylish situation-appropriate attire, NO childish clothes, NO mature adults), vibrant but balanced colors, rich cinematic atmosphere\n\n"
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
        f"CONCISENESS: Keep the final visual prompt strictly under 50 words. Focus only on the most important visual elements (character, facial expression, physical action, authentic setting, cinematic lighting). Do not overcomplicate.\n\n"
        f"Generate the Z-Image-Turbo visual prompt for this scene now. Ensure visual style, environment, and character remain 100% consistent with the story while showing this distinct scene action."
    )


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
) -> str:
    """Build the prompt for generating a complete, non-repetitive 5-scene visual storyboard in JSON."""
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
            f"DIRECTOR'S ROLEPLAY STORYBOARD TASK (DYNAMIC 4-BEAT CINEMATIC PROGRESSION):\n"
            f"Transform this two-character roleplay dialogue into a dynamic, highly varied 4-scene visual storyboard between PERSON_ONE ({p1}) and PERSON_TWO ({p2}).\n\n"
            f"CRITICAL DIRECTIVES FOR COMPLETE SCENE UNIQUENESS & ZERO REPETITION:\n"
            f"1. AVOID REPETITIVE TWO-SHOTS (MANDATORY): DO NOT generate identical two-shots where both characters simply stand side-by-side in the same room in slightly different poses! You MUST vary the camera angle, perspective, distance, and focal character across the 4-beat sequence:\n"
            f"   - HOOK: Scenario Establishing Shot (medium-wide, setting up the dilemma, environment, and physical tension; visually establishes opening problem and premise).\n"
            f"   - DIALOGUE_PART_2: 180° Reverse Angle Over-The-Shoulder / Focus on PERSON_TWO ({p2}) mentoring and explaining the correction.\n"
            f"   - DIALOGUE_PART_3: Kinetic Interaction & Prop Demonstration Shot (active motion demonstrating the concept/prop, energetic body language).\n"
            f"   - PAYOFF: Celebratory Resolution Two-Shot (shared triumph, high-five, walking triumphantly into event, confident outro).\n"
            f"2. ZERO-AMBIGUITY MULTI-CHARACTER GENDER RULE (MANDATORY): Whenever MORE THAN ONE character appears in a scene, the sex of EACH character MUST be explicitly specified (e.g. 'one youthful 14-year-old teen {p1_word} and one youthful 14-year-old teen {p2_word}'). NEVER use generic words like 'the two teens', 'two friends', 'the characters', or 'they'!\n"
            f"3. ZERO-DUPLICATE POSES: Banish repetitive standing or pointing. Each scene must feature distinct physical postures (dilemma posture -> patient explanation -> active prop interaction -> triumphant celebration).\n"
            f"4. HIGH-FIDELITY TEEN DEMOGRAPHIC & THEMATIC WARDROBE: Both characters must be youthful cartoon teens (approx. 13-15 years old) with distinct, consistent thematic wardrobes matching this specific setting, large expressive cartoon eyes with visible sclera, and rich background depth.\n"
            f"5. CONCISENESS: Keep each visual prompt strictly under 50 words.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, dialogue_part_2, dialogue_part_3, payoff) to its final prompt string."
        )
    else:
        director_task = (
            f"DIRECTOR'S STORYBOARD TASK:\n"
            f"Create a cohesive 5-scene visual storyboard where EVERY scene is completely unique and visually captivating:\n"
            f"1. MICRO-ZONE ROTATION: Each scene takes place in a different micro-zone of the setting above (e.g. personal focus desk -> collaborative meeting area -> active demonstration workbench -> presentation action stage -> celebratory lounge).\n"
            f"2. ZERO-DUPLICATE PROPS: Never repeat the same focal prop across scenes! Give every scene a distinct visual focal object.\n"
            f"3. ZERO-DUPLICATE POSES: Banish repetitive 'pointing' or 'gesturing at blueprints'. Vary character poses (pondering -> conversational dynamic -> breakthrough clarity -> active kinetic motion -> proud celebration).\n"
            f"4. EXAMPLE SCENE: Must actively depict the physical action/verb from the example narration in dynamic motion!\n"
            f"5. CAMERA SHOTS (WAIST-UP / CHEST-UP ONLY): Keep characters comfortably close to camera so their faces remain large and detailed (Hook = Medium Shot, Setup = Over-the-shoulder Two-Shot, Discovery = Medium Action Shot, Example = Dynamic Medium Action Shot, Payoff = Medium Close-Up). NEVER use distant wide shots where characters become tiny!\n"
            f"6. MULTI-CHARACTER GENDER SPECIFICATION: If more than 1 character is depicted, explicitly specify the sex of EACH character (e.g. 'one teen boy and one companion teen girl'). Strictly ban generic phrases like 'two teens'.\n"
            f"7. CHARACTER DETAIL PARITY, TEEN DEMOGRAPHIC & THEMATIC WARDROBE: Every character across all scenes MUST be a youthful 2D cartoon teen (approx. 13-15 years old) wearing authentic thematic scene costume/wardrobe matching the setting (e.g. theatrical stage costume/vest in theater, chef coat in kitchen, drafting smock in design studio; STRICTLY BAN generic modern street clothes, plain t-shirts/hoodies, and childish clothes) with high animation fidelity — large clear expressive cartoon eyes with visible white sclera and specular highlights, expressive eyebrows, and clean line art. Strictly ban dot eyes or minimalist faces!\n"
            f"8. BACKGROUND DETAIL PARITY: Every single scene MUST describe the physical interior environment (furniture, textured walls, shelves, tools, atmospheric indoor lighting, depth). NEVER leave the background empty or flat solid color!\n"
            f"9. CONCISENESS: Keep each visual prompt strictly under 50 words.\n\n"
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
        f"OVERARCHING THEMATIC STORY WORLD:\n"
        f">> {anchor_environment} <<\n\n"
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

    # 4. Mandatory Youthful Teen Protagonist Enforcement & Thematic Wardrobe Upgrades
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:man|actor|gentleman)\b", "a young teen boy (13-15 years old)", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:woman|actress|lady)\b", "a young teen girl (13-15 years old)", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:performer|enthusiast|student|person|scholar|professional|individual|character)\b", "a youthful teen protagonist (13-15 years old)", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba (?:child|little kid|toddler)\b", "a youthful teen (13-15 years old)", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(adult|grown-?up)s?\b", "young teens", text, flags=re.IGNORECASE)
    text = re.sub(r"\ban adult\b", "a young teen", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:8|9|10|11)-year-old\b", "14-year-old", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:wearing\s+)?normal clothing\b", "wearing thematically authentic scene costume", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:smart\s+)?casual attire\b", "thematic scene-specific wardrobe", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcasual clothes\b", "thematic scene-specific costume", text, flags=re.IGNORECASE)

    # 5. Mandatory 2D Cartoon Style Anchor with Thematic Wardrobe Mandate
    style_mandate = (
        "Clean modern 2D cartoon narrative illustration, stylized 2D animation art style, "
        "vibrant flat colors, bold outlines, expressive youthful teen character design (approx. 13-15 years old), "
        "large clear cartoon eyes with visible white sclera and specular pupil highlights, "
        "thematically authentic scene-specific wardrobe matching the environment (NO generic modern street clothes, NO plain t-shirts/hoodies), "
        "rich detailed environmental interior background with depth and warm atmospheric lighting. "
        "(youthful teen protagonist, thematic costume, NO generic clothes, NO childish clothes, NO toys, NO toddlers, "
        "NO middle-aged adults, NO elderly, NO wrinkles, NO dot eyes, NO minimalist faces, NO blank backgrounds, "
        "NO 3D, NO realism, NO photograph, NO text)."
    )

    text_lower = text.lower()
    if "thematically authentic" not in text_lower or "white sclera" not in text_lower or "2d cartoon" not in text_lower:
        # Strip older style mandate if present
        text = re.sub(r"\.?\s*Clean modern 2D cartoon narrative illustration.*?\(.*?\)\.?", "", text, flags=re.IGNORECASE).strip()
        text = f"{text}. {style_mandate}"
    elif "no generic clothes" not in text_lower:
        text = f"{text}. (youthful teen protagonist, thematic costume, NO generic clothes, NO childish clothes, NO toys, NO toddlers, NO middle-aged adults, NO elderly, NO wrinkles, NO dot eyes, NO minimalist faces, NO blank backgrounds, NO 3D, NO realism, NO photograph, NO text)."

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
                    max_tokens=1000,
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
        5. Figurative real-world accomplishment for idioms (no repeated literal props).
        """
        language, subject, situation = _parse_label(label)
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
                    max_tokens=2500,
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
                    "[%s] Scene '%s' missing from storyboard. Generating individually with anti-repetition memory...",
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
                    )
                    storyboard_dict[sec_lower] = single_prompt
                except Exception as exc:
                    logger.error("[%s] Failed fallback prompt for %s: %s", script_id, sec_name, exc)

        return {
            k: sanitize_and_style_prompt(v)
            for k, v in storyboard_dict.items()
        }

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

        if video_type.upper() == "ROLEPLAY":
            p1_g = speakers_gender.get("PERSON_ONE", "female") if speakers_gender else "female"
            p2_g = speakers_gender.get("PERSON_TWO", "male") if speakers_gender else "male"
            p1_word = "girl" if "f" in str(p1_g).lower() else "boy"
            p2_word = "girl" if "f" in str(p2_g).lower() else "boy"
            character_directive = (
                f"2. Dual Lead Characters (Roleplay Duo):\n"
                f"   - Character 1 (PERSON_ONE): An expressive youthful cartoon teen {p1_word} (approx. 13-15 years old) wearing authentic thematic scene costume matching this setting.\n"
                f"   - Character 2 (PERSON_TWO): An energetic youthful cartoon teen {p2_word} (approx. 13-15 years old) wearing complementary authentic thematic costume matching this setting.\n"
                f"   CRITICAL MULTI-CHARACTER RULE: The sex of BOTH characters MUST be explicitly specified! Strictly ban generic ambiguous words like 'two teens' or 'the characters'!"
            )
        else:
            gender_desc = "youthful cartoon teen boy (approx. 13-15 years old)"
            if speakers_gender:
                principal_key = "PERSON_ONE" if video_type.upper() == "ROLEPLAY" else "NARRATOR"
                p_gend = speakers_gender.get(principal_key) or speakers_gender.get("NARRATOR") or speakers_gender.get("PERSON_ONE") or "male"
                if "f" in str(p_gend).lower():
                    gender_desc = "youthful cartoon teen girl (approx. 13-15 years old)"
                else:
                    gender_desc = "youthful cartoon teen boy (approx. 13-15 years old)"
            character_directive = (
                f"2. Protagonist: A {gender_desc} wearing authentic thematic costume/wardrobe explicitly matching this setting. "
                f"If any companion or secondary character appears, their sex MUST also be explicitly stated (never just 'two teens')!"
            )

        system_prompt = (
            "You are a professional visual director for language-learning animated YouTube Shorts.\n"
            "Your task is to establish the overarching General Visual Prompt / Story World Anchor that will define "
            "the visual context, thematic environment, character appearance, and atmosphere for ALL scenes of this video.\n\n"
            "MANDATORY DIRECTIVES:\n"
            "1. Macro-Setting & Micro-Zones: Describe a rich, authentic physical setting with multiple distinct micro-zones "
            "(e.g., technical workbench, observation booth, collaboration desk, demonstration area).\n"
            f"{character_directive}\n"
            "   Strictly ban generic modern street clothes (plain t-shirts/hoodies), childish clothes, and mature adults.\n"
            "3. Atmosphere & Style: Vibrant color palette, rich cinematic lighting, clean modern 2D cartoon narrative illustration, "
            "stylized 2D animation art style, vibrant flat colors, bold outlines, expressive facial design.\n"
            "4. Keep the description vivid, concrete, and strictly under 85 words.\n"
            "5. Return ONLY the visual prompt text. No markdown formatting, no commentary."
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
                    max_tokens=800,
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


