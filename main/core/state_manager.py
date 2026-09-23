import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

LANG_MAP = {
    "E": "english",
    "F": "french",
    "S": "spanish",
    "I": "italian",
}

TYPE_MAP = {
    "E": "expression",
    "G": "game",
    "R": "roleplay",
    "F": "fun_facts",
}

def resolve_lang_and_type(script_id: str, state: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Resolves (language, video_type) from canonical script_id or state dict.
    Returns lowercase pairs like ('english', 'expression'), ('french', 'game'), ('italian', 'roleplay'), ('spanish', 'fun_facts').
    """
    sid = str(script_id).strip().upper()
    lang = None
    vtype = None

    # 1. Canonical ID prefix check (e.g. EE01, FG02, IR01, SE03, EF01, FF01)
    if len(sid) >= 2 and sid[0] in LANG_MAP and sid[1] in TYPE_MAP:
        lang = LANG_MAP[sid[0]]
        vtype = TYPE_MAP[sid[1]]

    # 2. Extract from state if not found or incomplete
    if state and isinstance(state, dict):
        if not lang:
            raw_lang = (
                state.get("prompt_params", {}).get("TARGET_LANGUAGE")
                or state.get("content_metadata", {}).get("language")
                or state.get("metadata", {}).get("LABEL")
                or ""
            )
            clean_l = str(raw_lang).split("|")[0].strip().lower()
            if "french" in clean_l or "français" in clean_l:
                lang = "french"
            elif "spanish" in clean_l or "español" in clean_l:
                lang = "spanish"
            elif "italian" in clean_l or "italiano" in clean_l:
                lang = "italian"
            elif "english" in clean_l:
                lang = "english"

        if not vtype:
            raw_type = (
                state.get("content_metadata", {}).get("video_type")
                or state.get("prompt_params", {}).get("VIDEO_TYPE")
                or state.get("metadata", {}).get("VIDEO_TYPE")
                or ""
            )
            clean_t = str(raw_type).strip().upper()
            if "GAME" in clean_t:
                vtype = "game"
            elif "ROLEPLAY" in clean_t:
                vtype = "roleplay"
            elif "FUN_FACTS" in clean_t or "FUNFACTS" in clean_t or "FACTS" in clean_t:
                vtype = "fun_facts"
            elif "EXPRESSION" in clean_t:
                vtype = "expression"

    return lang or "english", vtype or "expression"


class StateManager:
    def __init__(self, base_dir: Path):
        self.state_dir = base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_script_path(self, script_id: str, state: Optional[Dict[str, Any]] = None) -> Path:
        """Returns the path for a script JSON.
        Target format: state/<language>/<video_type>/script_<script_id>.json
        Includes fallback checks across subdirectories and legacy flat state.
        """
        lang, vtype = resolve_lang_and_type(script_id, state)
        canonical_path = self.state_dir / lang / vtype / f"script_{script_id}.json"
        if canonical_path.exists():
            return canonical_path

        # Backward compatibility search across existing directories
        if self.state_dir.exists():
            # Check state/<language>/script_<id>.json
            lang_path = self.state_dir / lang / f"script_{script_id}.json"
            if lang_path.exists():
                return lang_path
            # Check flat state/script_<id>.json
            flat_path = self.state_dir / f"script_{script_id}.json"
            if flat_path.exists():
                return flat_path
            # Check any nested match
            for match in self.state_dir.rglob(f"script_{script_id}.json"):
                if match.is_file():
                    return match

        return canonical_path
        
    def script_exists(self, script_id: str) -> bool:
        """Returns True if the script's state JSON file exists on disk."""
        return self._get_script_path(script_id).exists()

    def get_script_state(self, script_id: str) -> Dict[str, Any]:
        path = self._get_script_path(script_id)
        if not path.exists():
            return {
                "id": script_id,
                "status": {
                    "script_generation": "pending",
                    "voice_generation": "pending",
                    "image_generation": "pending",
                    "thumbnail_generation": "pending",
                    "video_assembly": "pending"
                },
                "assets": {}
            }
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if "status" in data and isinstance(data["status"], dict):
                default_stages = [
                    "script_generation",
                    "voice_generation",
                    "image_generation",
                    "thumbnail_generation",
                    "video_assembly"
                ]
                for stage in default_stages:
                    if stage not in data["status"]:
                        data["status"][stage] = "pending"
            return data
            
    def save_script_state(self, script_id: str, state: Dict[str, Any]) -> None:
        lang, vtype = resolve_lang_and_type(script_id, state)
        target_path = self.state_dir / lang / vtype / f"script_{script_id}.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

        # Clean up legacy flat or unpartitioned files if they exist
        legacy_flat = self.state_dir / f"script_{script_id}.json"
        if legacy_flat.exists() and legacy_flat.resolve() != target_path.resolve():
            try:
                legacy_flat.unlink()
            except Exception:
                pass

        legacy_lang = self.state_dir / lang / f"script_{script_id}.json"
        if legacy_lang.exists() and legacy_lang.resolve() != target_path.resolve():
            try:
                legacy_lang.unlink()
            except Exception:
                pass

        # Real-time synchronization with state/pipeline_status.csv
        try:
            from core.status_tracker import get_status_tracker
            tracker = get_status_tracker(self.state_dir.parent)
            statuses = state.get("status", {})
            for stage_name, status_val in statuses.items():
                tracker.update_script_stage_status(script_id, stage_name, str(status_val))
        except Exception:
            pass
            
    def get_all_scripts(self) -> List[Dict[str, Any]]:
        scripts = []
        seen_ids = set()
        for file_path in sorted(self.state_dir.rglob("script_*.json")):
            if file_path.is_file() and ".sample" not in file_path.name.lower() and "sample" not in file_path.name.lower():
                try:
                    with file_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        sid = data.get("id") or file_path.stem.replace("script_", "")
                        if sid not in seen_ids:
                            seen_ids.add(sid)
                            scripts.append(data)
                except Exception:
                    continue
        return scripts
