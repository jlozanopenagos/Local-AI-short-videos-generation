"""
visual/common/sanitizer.py — Prompt sanitizer, text/quote scrubber, and 2D cartoon style enforcer.

Phase 3 Upgrades:
- Idempotent age/child scrubbing (Q11: preserves `NOT a child`, preserves `14-year-old`, `15-year-old`, `16-year-old`, `14-16-year-old` per Q3).
- Gift-box exception (`allow_gift_box=True` or topic='present' per Q5).
"""
from __future__ import annotations

import re


def is_present_heteronym_topic(topic: str = "", label: str = "") -> bool:
    """Returns True when the script specifically teaches the English heteronym 'present' (PREsent vs preSENT)."""
    combined = f"{topic} {label}".lower()
    return bool(re.search(r"\bpresent\b", combined))


def sanitize_and_style_prompt(prompt: str, allow_gift_box: bool = False) -> str:
    """
    Sanitizes visual prompts and enforces strict 2D cartoon narrative illustration styling.

    1. Removes any interjections or quote words like 'aha', 'eureka', 'wow', 'oops'.
    2. Strips quotes around words (e.g. 'project', 'cake') which trigger text/OCR rendering in Qwen/Lumina.
    3. Guarantees that the prompt has explicit, high-priority 2D cartoon illustration tokens
       and anti-photorealism directives, and is 100% idempotent when applied multiple times.
    """
    if not prompt or not isinstance(prompt, str):
        return ""

    text = prompt.strip()

    # Strip existing appended style_mandate tail first so re-running sanitizer never corrupts negative exclusions
    text = re.sub(
        r"\.?\s*Clean modern 2D cartoon narrative illustration, stylized 2D animation art style.*?\(high-school student protagonist, thematic costume.*?\)\.?\s*$",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Strip echoed rubric headers or general prompt prefixes at the start of the string
    text = re.sub(
        r"^(?:General\s+Visual\s+Prompt\s*:\s*|(?:HOOK|SETUP|DISCOVERY|EXAMPLE|PAYOFF|ANSWER|EXPLANATION|CHALLENGE|PRESSURE|DIALOGUE_PART_\d)\s*\[[^\]]+\]\s*:\s*)+",
        "",
        text,
        flags=re.IGNORECASE,
    )

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

    # 3b. Ensure male characters NEVER have feminine hairstyles (buns, bobs, ponytails, chignons, long wavy hair)
    text = re.sub(
        r"\b(boy|man|male(?:\s+teen|\s+student|\s+protagonist)?)\b([^,\.]{0,80}?)\b(?:(?:with\s+|and\s+)?(?:long,?\s+)?(?:dark\s+|black\s+|brown\s+|auburn\s+|wavy\s+|long\s+)*hair\s+(?:tied\s+)?in\s+an?\s+(?:sleek\s+|high\s+|elegant\s+)?(?:bun|ponytail|bob|braid|chignon)|(?:with\s+|and\s+)long,?\s+(?:wavy\s+|flowing\s+)?(?:dark\s+|auburn\s+|brown\s+|black\s+)*hair|tied in a (?:sleek\s+|high\s+)?(?:bun|ponytail)|in a (?:sleek\s+|high\s+)?(?:bun|ponytail|bob|braid)|sleek (?:bun|ponytail)|hair bun|in a bob|in a ponytail|chignon)\b",
        r"\1\2with short textured dark hair and neat side-part",
        text,
        flags=re.IGNORECASE,
    )
    # Ensure male characters NEVER wear female garments (bodices, corsets, kirtles, skirts, dresses, gowns)
    text = re.sub(
        r"\b(boy|man|male(?:\s+teen|\s+student|\s+protagonist)?)\b([^,\.]{0,60}?)\b(?:bodice|corset|kirtle|skirt|gown|dress)\b",
        r"\1\2theatrical doublet and tailored trousers",
        text,
        flags=re.IGNORECASE,
    )
    # 3c. Ensure female characters NEVER have masculine haircuts or sideburns (quiffs, buzz cuts, crew cuts, sideburns)
    text = re.sub(
        r"\b(girl|woman|female(?:\s+teen|\s+student|\s+protagonist)?)\b([^,\.]{0,80}?)\b(?:(?:sporting\s+|with\s+)?short\s+textured\s+[^,\.]{0,30}?\bsideburns|with\s+clean-?cut\s+sideburns|quiff hair|quiff|buzz-?cut|crew-?cut)\b",
        r"\1\2with soft wavy hair resting over shoulders",
        text,
        flags=re.IGNORECASE,
    )

    # 3d. Absolute text, quote, speech, and typography scrubbing to prevent diffusion models from painting text onto images
    # Scrub all text inside quotes: "...", '...', “...”, ‘...’, «...»
    text = re.sub(r'["“«][^"”»]{1,60}["”»]', "expressive dialogue", text)
    text = re.sub(r"['‘][^'’]{1,60}['’]", "expressive dialogue", text)

    # Scrub verbs of speaking followed by words/phrases (always terminate on a word boundary \b so words are never sliced mid-token)
    text = re.sub(r"\bspeaking\s+expressively[a-z]+\b", "speaking expressively", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:whispering|saying|speaking|mouthing|shouting|calling|reading|repeating)\s+(?:the\s+words?|the\s+phrase)?\s*[^,\.]{1,40}\b", "speaking expressively", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwith\s+the\s+words?\s+[^,\.]{1,40}\b", "with expressive visual details", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthe\s+words?\s+[^,\.]{1,30}\b", "expressive dialogue", text, flags=re.IGNORECASE)

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

    # Scrub signs, posters, screens, boards with text (preserve shirts/hoodies with clothing details like sleeves/scarf!)
    text = re.sub(r"\b(?:labeled|inscribed\s+with|reading|displaying\s+(?:the\s+text)?)\s+[^,\.]{1,40}", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:a\s+)?(?:sign|poster|banner|board|screen|tablet|chalkboard|blackboard|whiteboard)\s+(?:with|showing|saying|displaying|covered\s+in|(?:subtly\s+)?referencing)\s+[^,\.]{1,50}",
        "thematic decor",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:a\s+)?(?:t-shirt|shirt|hoodie)\s+(?:saying|reading|inscribed\s+with|(?:with|showing|displaying)\s+(?:the\s+)?(?:text|words?|letters?|phrase|quote|slogan|logo))\s*[^,\.]{0,40}",
        "thematic garment",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:a\s+|an\s+)?(?:large,?\s+|small,?\s+)?(?:ornate,?\s+)?(?:metallic\s+)?(?:sign|placard|price\s+tag|framed\s+quote)\s+(?:with\s+(?:exaggerated\s+)?numbers|(?:subtly\s+)?referencing\s+[^,\.]{1,40}|about\s+[^,\.]{1,40})",
        "an authentic decorative setting prop",
        text,
        flags=re.IGNORECASE,
    )

    # Scrub letter / alphabet / word-card / phonetic symbol mentions
    text = re.sub(r"\b(?:oversized,?\s+)?(?:stylized\s+)?letters?\s*\(\s*like\s+[^)]+\)", "stylized abstract geometric emblems", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:oversized,?\s+)?(?:stylized\s+)?word-?cards?(?:\s+and\s+phonetic\s+symbols?)?\b", "stylized abstract graphic emblems", text, flags=re.IGNORECASE)
    text = re.sub(r"\bphonetic\s+symbols?\b", "abstract acoustic wave emblems", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:oversized,?\s+)?(?:glowing\s+)?(?:\d+\s+)?individual\s+letters?\b", "glowing circular emblems", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:holding|waving|showing|with|displaying)\s+(?:a\s+)?(?:large,?\s+)?(?:stylized\s+)?(?:prop|sign|card|banner|object)?\s*representing\s+(?:the\s+)?letters?\s+[A-Za-z0-9_\-]+\b", "gesturing with an expressive physical prop", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:the\s+)?letters?\s+[A-Z]\b", "an expressive thematic prop", text)
    text = re.sub(r"\bdouble\s+[A-Za-z]\b", "expressive vocal inflection", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:double\s+)?ene\b", "vocal resonance", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:difference|distinction|contrast)\s+between\s+[A-Za-zÀ-ÿ0-9_\-]+\s+and\s+[A-Za-zÀ-ÿ0-9_\-]+\b", "subtle vocal nuance", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:distinguishing|differentiating)\s+between\s+[A-Za-zÀ-ÿ0-9_\-]+\s+and\s+[A-Za-zÀ-ÿ0-9_\-]+\b", "subtle vocal demonstration", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpronunciation\s+of\s+[^,\.]{1,50}", "subtle vocal delivery", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsound\s+of\s+[A-Za-zÀ-ÿ0-9_\-]+", "vocal resonance", text, flags=re.IGNORECASE)

    # 4. Mandatory High School Student Demographic & Thematic Wardrobe Upgrades (14-16yo teenagers, NOT a child)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:man|actor|gentleman)\b", "a 16-year-old high-school teenage boy", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:woman|actress|lady)\b", "a 16-year-old high-school teenage girl", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba young(?:\s+[a-zA-Z]+)?\s+(?:performer|enthusiast|student|person|scholar|professional|individual|character)\b", "a 16-year-old high-school teenage protagonist", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\bNO\s)(?<!\bmiddle-aged\s)(?<!\bolder\s)\b(adult|grown-?up)s?\b", "high-school teenagers", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\bNO\s)\ban adult\b", "a high-school teenager", text, flags=re.IGNORECASE)
    # Q3: Teenagers are 14-16 years old; only upgrade younger child ages (8-13) to 14-16-year-old
    text = re.sub(r"\b(?:8|9|10|11|12|13)-year-old\b", "15-year-old", text, flags=re.IGNORECASE)
    # Q11: Do not corrupt negative exclusions like "NOT a child" or "NO young children"
    text = re.sub(r"(?<!\bNOT\s)(?<!\bnot\s)(?<!\ba\sNOT\s)(?<!\bNO\s)(?<!\byoung\s)\b(?:kid|child|children)\b", "teenager", text)
    text = re.sub(r"\bNOT a teenager\b", "NOT a child", text, flags=re.IGNORECASE)
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

    # 4d. Scrub lazy repetitive gift box props from prompts (Q5: except when genuinely teaching 'present')
    if not allow_gift_box:
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
        "vibrant flat colors, bold outlines, expressive high-school student character design (approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child), "
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
