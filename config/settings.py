import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from .env file at project root
load_dotenv()

# Base directories
# In config/settings.py, parent.parent is the project root directory
BASE_DIR = Path(__file__).parent.parent.resolve()
CORE_DIR = BASE_DIR / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))
STATE_DIR = BASE_DIR / "state"

# Output directories (configurable via OUTPUT_DIR in .env, defaults to D:/AI/output if present, otherwise BASE_DIR / output)
_env_output = os.getenv("OUTPUT_DIR")
if _env_output:
    OUTPUT_DIR = Path(_env_output).resolve()
elif Path("D:/AI/output").exists():
    OUTPUT_DIR = Path("D:/AI/output").resolve()
else:
    OUTPUT_DIR = (BASE_DIR / "output").resolve()

VIDEO_ASSETS_DIR = OUTPUT_DIR / "video_assets"
SCRIPTS_TO_SEE_DIR = OUTPUT_DIR / "scripts_to_see"
BANK_MUSIC_DIR = OUTPUT_DIR / "bank_music"

# Database directories
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "expressions.db"
DB_CSV_PATH = DATABASE_DIR / "expressions.csv"

# Unified Input directories
INPUT_DIR = BASE_DIR / "input"
INPUT_CSV_DIR = INPUT_DIR / "csv"
if not INPUT_CSV_DIR.exists():
    INPUT_CSV_DIR = INPUT_DIR  # fallback to flat input directory

INPUT_IMAGES_DIR = INPUT_DIR / "images"
if not INPUT_IMAGES_DIR.exists() and (BASE_DIR / "input_images").exists():
    INPUT_IMAGES_DIR = BASE_DIR / "input_images"

GAME_IMAGES_DIR = INPUT_IMAGES_DIR / "game_images"
if not GAME_IMAGES_DIR.exists() and (INPUT_DIR / "game_images").exists():
    GAME_IMAGES_DIR = INPUT_DIR / "game_images"
elif not GAME_IMAGES_DIR.exists() and (BASE_DIR / "game_images").exists():
    GAME_IMAGES_DIR = BASE_DIR / "game_images"

OPENING_CLOSURE_DIR = INPUT_IMAGES_DIR / "openning_closure_images"
if not OPENING_CLOSURE_DIR.exists() and (INPUT_DIR / "openning_closure_images").exists():
    OPENING_CLOSURE_DIR = INPUT_DIR / "openning_closure_images"
elif not OPENING_CLOSURE_DIR.exists() and (BASE_DIR / "openning_closure_images").exists():
    OPENING_CLOSURE_DIR = BASE_DIR / "openning_closure_images"
if not OPENING_CLOSURE_DIR.exists():
    if (INPUT_IMAGES_DIR / "opening_closure_images").exists():
        OPENING_CLOSURE_DIR = INPUT_IMAGES_DIR / "opening_closure_images"
    elif (INPUT_DIR / "opening_closure_images").exists():
        OPENING_CLOSURE_DIR = INPUT_DIR / "opening_closure_images"
    elif (BASE_DIR / "opening_closure_images").exists():
        OPENING_CLOSURE_DIR = BASE_DIR / "opening_closure_images"

WATERMARK_DIR = INPUT_IMAGES_DIR / "watermark"
if not WATERMARK_DIR.exists() and (BASE_DIR / "watermark_image").exists():
    WATERMARK_DIR = BASE_DIR / "watermark_image"

THUMBNAIL_MODELS_DIR = INPUT_IMAGES_DIR / "thumbnail_models"
if not THUMBNAIL_MODELS_DIR.exists():
    legacy_thumb_dir = BASE_DIR / "video_creation" / "_F_thumbnail_image_generation" / "input_images"
    if legacy_thumb_dir.exists():
        THUMBNAIL_MODELS_DIR = legacy_thumb_dir

# API Keys (Loaded from .env)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3")

# ComfyUI Configuration
COMFY_API_URL = os.getenv("COMFY_API_URL", "http://127.0.0.1:8188")
COMFY_DIR = Path(os.getenv("COMFY_DIR", "C:/AI/ComfyUI_windows_portable"))
COMFY_OUTPUT_DIR = Path(os.getenv("COMFY_OUTPUT_DIR", str(COMFY_DIR / "ComfyUI" / "output")))
COMFY_INPUT_DIR = Path(os.getenv("COMFY_INPUT_DIR", str(COMFY_DIR / "ComfyUI" / "input")))

# Workflow directories
WORKFLOWS_DIR = BASE_DIR / "video_creation" / "workflows"

# Image config
IMAGE_DEFAULT_STEPS = 6
IMAGE_DEFAULT_WIDTH = 576
IMAGE_DEFAULT_HEIGHT = 1024
IMAGE_WORKFLOW_PATH = WORKFLOWS_DIR / "AcademiaSD_Z-Image_v05.json"
if not IMAGE_WORKFLOW_PATH.exists() and (BASE_DIR / "AcademiaSD_Z-Image_v05.json").exists():
    IMAGE_WORKFLOW_PATH = BASE_DIR / "AcademiaSD_Z-Image_v05.json"

# Voice config
OPEN_SWARA_DIR = Path(os.getenv("OPEN_SWARA_DIR", str(COMFY_DIR / "open-swara" / "voices")))
VOICE_WORKFLOW_PATH = WORKFLOWS_DIR / "Qwen3-TTS Voice.json"
if not VOICE_WORKFLOW_PATH.exists() and (BASE_DIR / "Qwen3-TTS Voice.json").exists():
    VOICE_WORKFLOW_PATH = BASE_DIR / "Qwen3-TTS Voice.json"

# Thumbnail workflow config
THUMBNAIL_WORKFLOW_PATH = WORKFLOWS_DIR / "flux1_dev_uso_reference_image_gen.json"
if not THUMBNAIL_WORKFLOW_PATH.exists() and (BASE_DIR / "flux1_dev_uso_reference_image_gen.json").exists():
    THUMBNAIL_WORKFLOW_PATH = BASE_DIR / "flux1_dev_uso_reference_image_gen.json"

SPEAKER_GENDER_MAP = {
    "amigo": "male",
    "amiga": "female",
}

NARRATOR_VOICES = {
    ("english", "male"): [
        "english/male/english_male_open_swara_130.wav",
        "english/male/english_male_open_swara_134.wav",
        "english/male/english_male_open_swara_135.wav",
        "english/male/english_male_open_swara_144.wav"
    ],
    ("english", "female"): [
        "english/female/english_female_open_swara_080.wav",
        "english/female/english_female_open_swara_085.wav",
        "english/female/english_female_open_swara_096.wav",
        "english/female/english_female_open_swara_125.wav",
        "english/female/english_female_open_swara_127.wav"
    ],
    ("french", "male"): [
        "french/male/french_male_open_swara_009.wav",
        "french/male/french_male_open_swara_011.wav",
        "french/male/french_male_open_swara_050.wav"
    ],
    ("french", "female"): [
        "french/female/french_female_open_swara_001.wav",
        "french/female/french_female_open_swara_026.wav",
        "french/female/french_female_open_swara_074.wav"
    ],
    ("spanish", "male"): [
        "spanish/male/spanish_male_open_swara_001.wav",
        "spanish/male/spanish_male_open_swara_004.wav"
    ],
    ("spanish", "female"): [
        "spanish/female/spanish_female_open_swara_003.wav",
        "spanish/female/spanish_female_open_swara_006.wav",
        "spanish/female/spanish_female_open_swara_008.wav"
    ],
    ("italian", "male"): [
        "italian/male/italian_male_open_swara_001.wav",
        "italian/male/italian_male_open_swara_002.wav"
    ],
    ("italian", "female"): [
        "italian/female/italian_female_open_swara_001.wav",
        "italian/female/italian_female_open_swara_002.wav"
    ]
}

DEFAULT_PAUSES = {
    "section_gap": 0.40,
    "dialogue_gap": 0.20,
    "paragraph_gap": 0.30,
    "pressure_gap": 2.20,  # Suspenseful countdown pause for GAME videos (between pressure and answer)
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
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Resolves the opening and closure image paths for a script based on video type and language.
    - If video_type is FUN_FACTS:
        Pulls from <root>/fun_facts/openning/<lang> and <root>/fun_facts/closure/<lang>.
        Performs dialect detection for English (american vs british) and Spanish (latin_american vs spain).
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
    if any(k in combined_text for k in ("british", "uk accent", "united kingdom", "england", "queen's english", "in the uk", "london")):
        english_dialect = "british"

    spanish_dialect = "latin_american"
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
                    open_path = _find_image_in_dir(open_lang_dir, keywords=[english_dialect])
                else:
                    open_path = _find_image_in_dir(open_lang_dir)
            else:
                open_path = _find_image_in_dir(open_lang_dir, keywords=[f"openning_{lang}", f"opening_{lang}", "open", "oppen"])

        if close_parent:
            close_lang_dir = close_parent / lang
            if cat_name == "fun_facts":
                if lang == "english":
                    close_path = _find_image_in_dir(close_lang_dir, keywords=[english_dialect])
                elif lang == "spanish":
                    close_path = _find_image_in_dir(close_lang_dir, keywords=[spanish_dialect])
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

