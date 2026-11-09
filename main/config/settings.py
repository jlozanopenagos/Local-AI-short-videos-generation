import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Base directories
# In config/settings.py, parent.parent is the main application root directory
BASE_DIR = Path(__file__).parent.parent.resolve()
CORE_DIR = BASE_DIR / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))
STATE_DIR = BASE_DIR / "state"

# Load environment variables from .env (checks main/.env, repo root .env, and current working directory)
for _env_candidate in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if _env_candidate.exists():
        load_dotenv(_env_candidate)
load_dotenv()


def _resolve_local_path(raw_path: Optional[str], base_dir: Path = BASE_DIR) -> Optional[Path]:
    """Resolves an environment variable path (relative to base_dir if not absolute)."""
    if not raw_path or not raw_path.strip():
        return None
    p = Path(raw_path.strip())
    if not p.is_absolute():
        p = base_dir / p
    return p.resolve()


# Output directories (configurable via OUTPUT_DIR in .env, defaults to sibling output/ or BASE_DIR/output)
_resolved_output = _resolve_local_path(os.getenv("OUTPUT_DIR"), BASE_DIR)
if _resolved_output:
    OUTPUT_DIR = _resolved_output
elif (BASE_DIR.parents[1] / "output").exists():
    OUTPUT_DIR = (BASE_DIR.parents[1] / "output").resolve()
elif (BASE_DIR.parent / "output").exists():
    OUTPUT_DIR = (BASE_DIR.parent / "output").resolve()
else:
    OUTPUT_DIR = (BASE_DIR / "output").resolve()

VIDEO_ASSETS_DIR = OUTPUT_DIR / "video_assets"
SCRIPTS_TO_SEE_DIR = OUTPUT_DIR / "scripts_to_see"
BANK_MUSIC_DIR = OUTPUT_DIR / "bank_music"

# Database directories
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "expressions.db"

# Unified Input directories
INPUT_DIR = BASE_DIR / "input"
INPUT_CSV_DIR = INPUT_DIR / "csv"
if not INPUT_CSV_DIR.exists():
    INPUT_CSV_DIR = INPUT_DIR  # fallback to flat input directory

INPUT_IMAGES_DIR = INPUT_DIR / "images"
GAME_IMAGES_DIR = INPUT_IMAGES_DIR / "game_images"
OPENING_CLOSURE_DIR = INPUT_IMAGES_DIR / "openning_closure_images"
if not OPENING_CLOSURE_DIR.exists() and (INPUT_IMAGES_DIR / "opening_closure_images").exists():
    OPENING_CLOSURE_DIR = INPUT_IMAGES_DIR / "opening_closure_images"

WATERMARK_DIR = INPUT_IMAGES_DIR / "watermark"
THUMBNAIL_MODELS_DIR = INPUT_IMAGES_DIR / "thumbnail_models"

# API Keys (Loaded from .env)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ComfyUI Configuration (auto-discovers sibling ComfyUI_windows_portable relative to project root or via .env)
COMFY_API_URL = os.getenv("COMFY_API_URL", "http://127.0.0.1:8188")
_resolved_comfy = _resolve_local_path(os.getenv("COMFY_DIR"), BASE_DIR)
if _resolved_comfy and _resolved_comfy.exists():
    COMFY_DIR = _resolved_comfy
elif (BASE_DIR.parents[1] / "ComfyUI_windows_portable").exists():
    COMFY_DIR = (BASE_DIR.parents[1] / "ComfyUI_windows_portable").resolve()
elif (BASE_DIR.parent / "ComfyUI_windows_portable").exists():
    COMFY_DIR = (BASE_DIR.parent / "ComfyUI_windows_portable").resolve()
elif (BASE_DIR / "ComfyUI_windows_portable").exists():
    COMFY_DIR = (BASE_DIR / "ComfyUI_windows_portable").resolve()
else:
    COMFY_DIR = (_resolved_comfy or (BASE_DIR.parents[1] / "ComfyUI_windows_portable")).resolve()

COMFY_OUTPUT_DIR = _resolve_local_path(os.getenv("COMFY_OUTPUT_DIR"), BASE_DIR) or (COMFY_DIR / "ComfyUI" / "output")
COMFY_INPUT_DIR = _resolve_local_path(os.getenv("COMFY_INPUT_DIR"), BASE_DIR) or (COMFY_DIR / "ComfyUI" / "input")

# Workflow directories
WORKFLOWS_DIR = BASE_DIR / "video_creation" / "workflows"

# Image config
IMAGE_DEFAULT_STEPS = 6
IMAGE_DEFAULT_WIDTH = 576
IMAGE_DEFAULT_HEIGHT = 1024
IMAGE_STALL_TIMEOUT = int(os.getenv("IMAGE_STALL_TIMEOUT", "600"))
IMAGE_WORKFLOW_PATH = WORKFLOWS_DIR / "AcademiaSD_Z-Image_v05.json"

# Voice config
OPEN_SWARA_DIR = _resolve_local_path(os.getenv("OPEN_SWARA_DIR"), BASE_DIR) or (COMFY_DIR / "open-swara" / "voices")
VOICE_WORKFLOW_PATH = WORKFLOWS_DIR / "Qwen3-TTS Voice.json"

NARRATOR_VOICES = {
    ("english", "male"): [
        "english/male/english_male_kokoro_golden_narrator.wav",
        "english/male/english_male_kokoro_golden_char1.wav",
        "english/male/english_male_kokoro_golden_char2.wav",
        "english/male/english_male_open_swara_149.wav",
        "english/male/english_male_open_swara_113.wav",
        "english/male/english_male_open_swara_027.wav",
    ],
    ("english", "female"): [
        "english/female/english_female_kokoro_golden_narrator.wav",
        "english/female/english_female_kokoro_golden_char1.wav",
        "english/female/english_female_kokoro_golden_char2.wav",
        "english/female/english_female_open_swara_035.wav",
        "english/female/english_female_open_swara_065.wav",
        "english/female/english_female_open_swara_190.wav",
    ],
    ("french", "male"): [
        "french/male/french_male_kokoro_golden_narrator.wav",
        "french/male/french_male_kokoro_golden_baritone.wav",
        "french/male/french_male_kokoro_golden_tenor.wav",
        "french/male/french_male_kokoro_golden_bass.wav",
    ],
    ("french", "female"): [
        "french/female/french_female_kokoro_golden_narrator.wav",
        "french/female/french_female_kokoro_golden_alto.wav",
        "french/female/french_female_kokoro_golden_mezzo.wav",
    ],
    ("spanish", "male"): [
        "spanish/male/spanish_male_kokoro_golden_narrator.wav",
        "spanish/male/spanish_male_kokoro_golden_baritone.wav",
        "spanish/male/spanish_male_kokoro_golden_tenor.wav",
        "spanish/male/spanish_male_kokoro_golden_bass.wav",
    ],
    ("spanish", "female"): [
        "spanish/female/spanish_female_kokoro_golden_narrator.wav",
        "spanish/female/spanish_female_kokoro_golden_alto.wav",
        "spanish/female/spanish_female_kokoro_golden_mezzo.wav",
    ],
    ("italian", "male"): [
        "italian/male/italian_male_kokoro_golden_narrator.wav",
        "italian/male/italian_male_kokoro_golden_baritone.wav",
        "italian/male/italian_male_kokoro_golden_tenor.wav",
        "italian/male/italian_male_kokoro_golden_bass.wav",
    ],
    ("italian", "female"): [
        "italian/female/italian_female_kokoro_golden_narrator.wav",
        "italian/female/italian_female_kokoro_golden_alto.wav",
        "italian/female/italian_female_kokoro_golden_mezzo.wav",
    ]
}

# Qwen3-TTS Cloning Quality Settings
QWEN3_USE_ICL = os.getenv("QWEN3_USE_ICL", "true").strip().lower() in ("1", "true", "yes")
QWEN3_LOCALIZE_INSTRUCT = os.getenv("QWEN3_LOCALIZE_INSTRUCT", "true").strip().lower() in ("1", "true", "yes")
REF_TRANSCRIPTS_PATH = OUTPUT_DIR / "voice_quality" / "audit" / "ref_transcripts.json"

DEFAULT_PAUSES = {
    "section_gap": 0.35,           # Natural transition between major sections (Hook -> Dialogue, Dialogue -> Payoff)
    "dialogue_section_gap": 0.20,  # Natural transition between consecutive dialogue parts (Part 1 -> Part 2)
    "dialogue_gap": 0.15,          # Natural human conversational turn latching between speakers (150ms)
    "paragraph_gap": 0.20,         # Crisp paragraph pause for narration
    "pressure_gap": 2.20,          # Suspenseful countdown pause for GAME videos (between pressure and answer)
}

# Static Narrator Personality (Dynamic YouTube Shorts Creator, not a boring book reader)
STATIC_NARRATOR_PERSONALITY = "Charismatic, witty, and high-energy YouTube Shorts storyteller and viral language mentor. Speaks with a magnetic hook, vibrant dynamic intonation, warm humor, and fast compelling cadence that instantly grabs attention."

# Video config
VIDEO_WIDTH = 576
VIDEO_HEIGHT = 1024

def resolve_script_language(script_data: dict) -> str:
    """Extracts the standardized language name ('english', 'french', 'spanish') from script state."""
    if not isinstance(script_data, dict):
        return "english"
    
    # Check ID prefix first (e.g. FE01 -> french, SE01 -> spanish, EE01 -> english)
    script_id = str(script_data.get("id", "")).strip().upper()
    if len(script_id) >= 2 and script_id[1] in ("E", "G", "R", "F"):
        if script_id[0] == "F":
            return "french"
        elif script_id[0] == "S":
            return "spanish"
        elif script_id[0] == "I":
            return "italian"
        elif script_id[0] == "E":
            return "english"

    raw_lang = (
        script_data.get("prompt_params", {}).get("TARGET_LANGUAGE")
        or script_data.get("content_metadata", {}).get("language")
        or script_data.get("metadata", {}).get("LABEL")
        or "english"
    )
    clean = str(raw_lang).split("|")[0].strip().lower()
    if "french" in clean or "français" in clean:
        return "french"
    elif "spanish" in clean or "español" in clean:
        return "spanish"
    elif "italian" in clean or "italiano" in clean:
        return "italian"
    return "english"

def resolve_script_video_type(script_data: dict) -> str:
    """Extracts the standardized video type ('expression', 'game', 'roleplay', 'fun_facts') from script state."""
    if not isinstance(script_data, dict):
        return "expression"

    script_id = str(script_data.get("id", "")).strip().upper()
    if len(script_id) >= 2 and script_id[1] in ("E", "G", "R", "F"):
        if script_id[1] == "E":
            return "expression"
        elif script_id[1] == "G":
            return "game"
        elif script_id[1] == "R":
            return "roleplay"
        elif script_id[1] == "F":
            return "fun_facts"

    raw_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or script_data.get("metadata", {}).get("VIDEO_TYPE")
        or ""
    )
    clean = str(raw_type).strip().upper()
    if "GAME" in clean:
        return "game"
    elif "ROLEPLAY" in clean:
        return "roleplay"
    elif "FUN_FACTS" in clean or "FUNFACTS" in clean or "FACTS" in clean:
        return "fun_facts"
    return "expression"

def _find_image_in_dir(directory: Path, keywords: List[str] = None, exclude_keywords: List[str] = None) -> Optional[Path]:
    if not directory or not directory.exists() or not directory.is_dir():
        return None
    valid_exts = {".png", ".jfif", ".jpg", ".jpeg", ".webp"}
    candidates = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
    if not candidates:
        return None
    
    if keywords:
        for kw in keywords:
            kw_clean = kw.lower()
            matched = [f for f in candidates if kw_clean in f.stem.lower()]
            if matched:
                return matched[0]
                
    if exclude_keywords:
        filtered = [f for f in candidates if not any(ex.lower() in f.stem.lower() for ex in exclude_keywords)]
        if filtered:
            return filtered[0]
            
    return candidates[0]

def resolve_opening_closure_paths(
    script_data: dict,
    base_dir: Path = None,
    opening_closure_dir: Path = None,
    dialect: Optional[str] = None,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Resolves the opening and closure image paths for a script based on video type and language.
    - If video_type is FUN_FACTS:
        Pulls from <root>/fun_facts/openning/<lang> and <root>/fun_facts/closure/<lang>.
        Performs dialect detection or uses explicit dialect selection for:
          - English: 'american' vs 'british'
          - Spanish: 'latin_american' vs 'spain'
        Falls back to normal_videos if an image is not present in fun_facts.
    - If video_type is NORMAL (EXPRESSION, GAME, ROLE_PLAY):
        Pulls from <root>/normal_videos/openning/<lang> and <root>/normal_videos/closure/<lang>.
    """
    root = opening_closure_dir or OPENING_CLOSURE_DIR
    if base_dir and not opening_closure_dir:
        candidate_root = base_dir / "input" / "images" / "openning_closure_images"
        if candidate_root.exists():
            root = candidate_root

    video_type = resolve_script_video_type(script_data)
    is_fun_facts = (video_type == "fun_facts")
    lang = resolve_script_language(script_data)

    def _get_category_folder(cat_name: str) -> Optional[Path]:
        cat_dir = root / cat_name
        if cat_dir.exists():
            return cat_dir
        return None

    def _locate_subfolder(cat_dir: Path, subfolder_names: List[str]) -> Optional[Path]:
        for name in subfolder_names:
            sub = cat_dir / name
            if sub.exists():
                return sub
        return None

    # Context analysis for accent/dialect detection
    text_corpus = []
    if isinstance(script_data, dict):
        for k in ("prompt_params", "content_metadata", "metadata"):
            obj = script_data.get(k)
            if isinstance(obj, dict):
                for val in obj.values():
                    if isinstance(val, str):
                        text_corpus.append(val.lower())
                    elif isinstance(val, (list, tuple)):
                        text_corpus.extend(str(v).lower() for v in val)
        if "script_text" in script_data and isinstance(script_data["script_text"], str):
            text_corpus.append(script_data["script_text"].lower())
    combined_text = " ".join(text_corpus)

    english_dialect = "american"
    spanish_dialect = "latin_american"

    if dialect:
        d_clean = dialect.strip().lower()
        if lang == "english":
            if any(k in d_clean for k in ("brit", "uk", "england", "london")):
                english_dialect = "british"
            elif any(k in d_clean for k in ("amer", "us", "usa")):
                english_dialect = "american"
            else:
                english_dialect = d_clean
        elif lang == "spanish":
            if any(k in d_clean for k in ("spain", "españ", "cast", "penin")):
                spanish_dialect = "spain"
            elif any(k in d_clean for k in ("latin", "latam", "amer", "mex", "col")):
                spanish_dialect = "latin_american"
            else:
                spanish_dialect = d_clean
    else:
        if any(k in combined_text for k in ("british", "uk accent", "united kingdom", "england", "queen's english", "in the uk", "london")):
            english_dialect = "british"

        if any(k in combined_text for k in ("spain", "españa", "castellano", "castilian", "rae", "real academia", "peninsular")):
            spanish_dialect = "spain"

    def _resolve_for_category(cat_name: str) -> Tuple[Optional[Path], Optional[Path]]:
        cat_dir = _get_category_folder(cat_name)
        if not cat_dir:
            return None, None

        open_parent = _locate_subfolder(cat_dir, ["openning", "opening"])
        close_parent = _locate_subfolder(cat_dir, ["closure", "closing"])

        open_path = None
        close_path = None

        if open_parent:
            open_lang_dir = open_parent / lang
            if cat_name == "fun_facts":
                if lang == "english":
                    kw_list = ["american", "us", "usa"] if english_dialect == "american" else ["british", "uk", "britain"]
                    open_path = _find_image_in_dir(open_lang_dir, keywords=kw_list)
                elif lang == "spanish":
                    kw_list = ["latin_american", "latam", "latin"] if spanish_dialect == "latin_american" else ["spain", "españa", "espana", "castellano", "peninsular"]
                    open_path = _find_image_in_dir(open_lang_dir, keywords=kw_list)
                else:
                    open_path = _find_image_in_dir(open_lang_dir)
            else:
                open_path = _find_image_in_dir(open_lang_dir, keywords=[f"openning_{lang}", f"opening_{lang}", "open", "oppen"])

        if close_parent:
            close_lang_dir = close_parent / lang
            if cat_name == "fun_facts":
                if lang == "english":
                    kw_list = ["american", "us", "usa"] if english_dialect == "american" else ["british", "uk", "britain"]
                    close_path = _find_image_in_dir(close_lang_dir, keywords=kw_list)
                elif lang == "spanish":
                    kw_list = ["latin_american", "latam", "latin"] if spanish_dialect == "latin_american" else ["spain", "españa", "espana", "castellano", "peninsular"]
                    close_path = _find_image_in_dir(close_lang_dir, keywords=kw_list)
                else:
                    close_path = _find_image_in_dir(close_lang_dir)
            else:
                close_path = _find_image_in_dir(close_lang_dir, keywords=[f"closure_{lang}", "closure", "close"])

        return open_path, close_path

    if is_fun_facts:
        opening_path, closure_path = _resolve_for_category("fun_facts")
        # Fallback to normal_videos if fun_facts cards are missing
        if not opening_path or not closure_path:
            norm_open, norm_close = _resolve_for_category("normal_videos")
            if not opening_path:
                opening_path = norm_open
            if not closure_path:
                closure_path = norm_close
    else:
        opening_path, closure_path = _resolve_for_category("normal_videos")

    return opening_path, closure_path

def get_script_output_dir(script_id: str, language: str = None, base_dir: Path = None, video_type: str = None) -> Path:
    """
    Returns the language- and video-type-namespaced output directory for a script:
    base_dir / "output" / "video_assets" / <language> / <video_type> / f"script_{script_id}"
    If language or video_type is not specified, resolves via canonical script_id or defaults.
    Maintains backward compatibility by finding existing folders in video_assets or legacy output/.
    """
    if base_dir is None or base_dir == BASE_DIR:
        out_root = VIDEO_ASSETS_DIR
        legacy_root = OUTPUT_DIR
    else:
        out_root = base_dir / "output" / "video_assets"
        legacy_root = base_dir / "output"

    clean_lang = None
    if language:
        clean = str(language).split("|")[0].strip().lower()
        if "french" in clean or "français" in clean:
            clean_lang = "french"
        elif "spanish" in clean or "español" in clean:
            clean_lang = "spanish"
        elif "italian" in clean or "italiano" in clean:
            clean_lang = "italian"
        elif "english" in clean:
            clean_lang = "english"
        else:
            clean_lang = clean

    clean_type = None
    if video_type:
        vt_clean = str(video_type).strip().lower()
        if "game" in vt_clean:
            clean_type = "game"
        elif "roleplay" in vt_clean:
            clean_type = "roleplay"
        elif "fun_facts" in vt_clean or "funfacts" in vt_clean or "facts" in vt_clean:
            clean_type = "fun_facts"
        elif "expression" in vt_clean:
            clean_type = "expression"
        else:
            clean_type = vt_clean

    sid = str(script_id).strip().upper()
    if len(sid) >= 2 and sid[1] in ("E", "G", "R", "F"):
        if not clean_lang:
            if sid[0] == "F":
                clean_lang = "french"
            elif sid[0] == "S":
                clean_lang = "spanish"
            elif sid[0] == "I":
                clean_lang = "italian"
            elif sid[0] == "E":
                clean_lang = "english"
        if not clean_type:
            if sid[1] == "E":
                clean_type = "expression"
            elif sid[1] == "G":
                clean_type = "game"
            elif sid[1] == "R":
                clean_type = "roleplay"
            elif sid[1] == "F":
                clean_type = "fun_facts"


    clean_lang = clean_lang or "english"
    clean_type = clean_type or "expression"

    canonical_target = out_root / clean_lang / clean_type / f"script_{script_id}"
    if canonical_target.exists():
        return canonical_target

    # Check if existing output folder exists in configured out_root
    if out_root.exists():
        legacy_lang_target = out_root / clean_lang / f"script_{script_id}"
        if legacy_lang_target.exists():
            return legacy_lang_target
        for found in out_root.rglob(f"script_{script_id}"):
            if found.is_dir():
                return found

    # Fallback: check workspace local BASE_DIR / "output" if different from out_root
    local_out_root = BASE_DIR / "output" / "video_assets"
    if local_out_root.exists() and local_out_root != out_root:
        for found in local_out_root.rglob(f"script_{script_id}"):
            if found.is_dir():
                return found

    # Backward compatibility: check if existing output folder exists in legacy output/
    if legacy_root.exists():
        legacy_path = legacy_root / clean_lang / clean_type / f"script_{script_id}"
        if legacy_path.exists():
            return legacy_path
        for found in legacy_root.rglob(f"script_{script_id}"):
            if (
                found.is_dir()
                and "video_assets" not in found.parts
                and "scripts_to_see" not in found.parts
            ):
                return found

    return canonical_target

# Ensure core directories exist
STATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
SCRIPTS_TO_SEE_DIR.mkdir(parents=True, exist_ok=True)
BANK_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
