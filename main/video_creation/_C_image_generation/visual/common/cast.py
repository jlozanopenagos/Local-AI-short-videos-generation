"""
visual/common/cast.py — Character gender lookup, hairstyle sanitization, and character anchor extraction.
"""
from __future__ import annotations

import re

FEMALE_HAIRSTYLE_TERMS = [
    "bun", "bob", "ponytail", "pigtail", "braid", "braided", "chignon",
    "hairband", "headband", "flowing", "shoulder-length", "hair clip"
]
MALE_HAIRSTYLE_TERMS = [
    "quiff", "buzz", "crew-cut", "crew cut", "fade", "pompadour",
    "sideburns", "flat-top", "undercut"
]


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
            c2_desc = character_anchors.get("char2_desc") or (c2_text if c2_text else f"14-16-year-old high-school teenage {gender_word2} (natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child)")
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
                "char2_desc": parsed.get("char2_desc", f"14-16-year-old high-school teenage {gender_word2} (natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child)"),
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
        char1_desc = f"14-16-year-old high-school teenage {gender_word1} (natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child) with {char1_hair} wearing {char1_attire}"

    if c2_text:
        char2_desc = c2_text
    else:
        char2_desc = f"14-16-year-old high-school teenage {gender_word2} (natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child)"

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
