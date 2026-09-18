import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import BASE_DIR, get_script_output_dir
from core.state_manager import StateManager, resolve_lang_and_type
from core.status_tracker import get_status_tracker

SENTENCE_TERMINATORS = ('.', '!', '?', '"', "'", '»', '”', '…', ')')
ILLEGAL_SCRIPT_KEYS = {
    "total_word_count", "word_count", "related_content", "difficulty",
    "target_expression", "learning_objective", "category", "subcategory",
    "video_type", "language", "tags", "hashtags"
}

class ScriptHealthAuditor:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or BASE_DIR).resolve()
        self.state_dir = self.base_dir / "state"
        self.state_mgr = StateManager(self.base_dir)
        self.status_tracker = get_status_tracker(self.base_dir)

    def audit_script(self, state_file: Path) -> Tuple[str, Dict[str, Any], List[str]]:
        """
        Audits a single state JSON file.
        Returns (script_id, state_data, list_of_error_messages).
        """
        errors = []
        state_data = {}
        sid = state_file.stem.replace("script_", "").strip().upper()

        # 1. JSON Syntax Check
        try:
            with state_file.open("r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception as exc:
            return sid, {}, [f"Corrupted or invalid JSON syntax: {exc}"]

        if not isinstance(state_data, dict):
            return sid, {}, ["Root state element is not a JSON object/dict"]

        # 2. Basic Root Schema
        if "id" not in state_data or not str(state_data["id"]).strip():
            errors.append("Missing or empty root 'id' field")
        elif state_data["id"].strip().upper() != sid:
            errors.append(f"State ID mismatch: file says '{sid}', JSON says '{state_data['id']}'")

        status = state_data.get("status")
        if not status or not isinstance(status, dict):
            errors.append("Missing or invalid 'status' dictionary")
            return sid, state_data, errors

        prompt_params = state_data.get("prompt_params")
        if not prompt_params or not isinstance(prompt_params, dict):
            errors.append("Missing or invalid 'prompt_params' dictionary")

        # 3. Script Generation Integrity (if marked done)
        if status.get("script_generation") == "done":
            script_text = state_data.get("script_text")
            if not script_text or not str(script_text).strip():
                errors.append("Marked 'done' but 'script_text' is empty or missing")

            content_meta = state_data.get("content_metadata")
            if not content_meta or not isinstance(content_meta, dict):
                errors.append("Missing or invalid 'content_metadata' dictionary")
            else:
                script_dict = content_meta.get("script")
                if not script_dict or not isinstance(script_dict, dict):
                    errors.append("Missing or invalid 'content_metadata.script' dictionary")
                else:
                    sections = [k for k in script_dict.keys() if k.lower() != "title"]
                    if not sections:
                        errors.append("No spoken script sections found inside 'content_metadata.script'")
                    else:
                        # Check illegal non-spoken keys placed inside script dict
                        found_illegal = [k for k in script_dict.keys() if k.lower() in ILLEGAL_SCRIPT_KEYS]
                        if found_illegal:
                            errors.append(f"Non-spoken metadata fields found inside script: {', '.join(found_illegal)}")

                        # Check for empty sections
                        empty_secs = [k for k in sections if not str(script_dict[k]).strip()]
                        if empty_secs:
                            errors.append(f"Empty spoken text in sections: {', '.join(empty_secs)}")

                        # Check for abrupt cut-off / truncation in the final spoken section
                        last_sec = sections[-1]
                        last_val = str(script_dict[last_sec]).strip()
                        if last_val and not any(last_val.endswith(t) for t in SENTENCE_TERMINATORS):
                            errors.append(f"Final section '{last_sec}' appears truncated/cut-off: ...{last_val[-35:]}")

                        # Check word count
                        spoken_words = sum(len(str(script_dict[k]).split()) for k in sections if k.lower() not in ILLEGAL_SCRIPT_KEYS)
                        vtype = (prompt_params.get("VIDEO_TYPE") if prompt_params else "").upper()
                        if not vtype:
                            vtype = (content_meta.get("video_type") or "EXPRESSION").upper()

                        if vtype == "EXPRESSION" and spoken_words < 45:
                            errors.append(f"Unusually low word count: {spoken_words} words (expected 70-90 for EXPRESSION)")
                        elif vtype == "ROLEPLAY" and spoken_words < 80:
                            errors.append(f"Unusually low word count: {spoken_words} words (expected 120-140 for ROLEPLAY)")
                        elif vtype == "GAME" and spoken_words < 50:
                            errors.append(f"Unusually low word count: {spoken_words} words (expected 75-95 for GAME)")
                        elif vtype in ("FUN_FACTS", "FUNFACTS") and spoken_words < 60:
                            errors.append(f"Unusually low word count: {spoken_words} words (expected 95-135 for FUN_FACTS)")

                        # Format-specific structural validation
                        if vtype == "GAME":
                            has_challenge = any("challenge" in k.lower() for k in script_dict)
                            has_answer = any("answer" in k.lower() for k in script_dict)
                            chalkboard = content_meta.get("chalkboard_exercise")
                            if not has_challenge or not has_answer:
                                errors.append("GAME script missing mandatory 'challenge' or 'answer' sections")
                            if chalkboard is not None:
                                if not isinstance(chalkboard, (str, dict)) or (isinstance(chalkboard, str) and not chalkboard.strip()):
                                    errors.append("GAME script has invalid or empty 'chalkboard_exercise'")
                            elif not has_challenge:
                                errors.append("GAME script missing 'chalkboard_exercise' and 'challenge' fallback")

                        elif vtype == "ROLEPLAY":
                            dialogue_parts = [k for k in script_dict if "dialogue" in k.lower()]
                            if len(dialogue_parts) < 2:
                                errors.append("ROLEPLAY script missing required multi-turn dialogue sections")
                            personalities = content_meta.get("character_personalities")
                            if not personalities or not isinstance(personalities, dict):
                                errors.append("ROLEPLAY script missing 'character_personalities' definitions")

                        elif vtype in ("FUN_FACTS", "FUNFACTS"):
                            has_hook = any("hook" in k.lower() for k in script_dict)
                            has_payoff = any("payoff" in k.lower() for k in script_dict)
                            if not has_hook or not has_payoff:
                                errors.append("FUN_FACTS script missing mandatory 'hook' or 'payoff' sections")

            # Metadata Object Check
            meta = state_data.get("metadata")
            if not meta or not isinstance(meta, dict):
                errors.append("Missing or invalid 'metadata' dictionary")
            else:
                has_title = any(k.lower() == "title" for k in meta)
                has_desc = any("desc" in k.lower() for k in meta)
                has_tags = any(k.lower() == "tags" for k in meta)
                if not has_title:
                    errors.append("Metadata is missing 'title' field")
                if not has_desc:
                    errors.append("Metadata is missing 'description' field")
                if not has_tags:
                    errors.append("Metadata is missing 'tags' field")

        # 4. Downstream Asset Verification (if marked done)
        lang, vtype = resolve_lang_and_type(sid, state_data)
        out_dir = get_script_output_dir(sid, lang, self.base_dir)

        if status.get("voice_generation") == "done":
            audio_path_str = state_data.get("assets", {}).get("audio_path")
            audio_path = Path(audio_path_str) if audio_path_str else out_dir / f"script_{sid}_master.wav"
            if not audio_path.exists() or audio_path.stat().st_size < 1000:
                errors.append(f"Voice is marked 'done', but master audio file is missing or 0 bytes: {audio_path.name}")

        if status.get("video_assembly") == "done":
            video_path = out_dir / f"script_{sid}_final.mp4"
            if not video_path.exists():
                video_path = out_dir / f"script_{sid}.mp4"
            if not video_path.exists() or video_path.stat().st_size < 5000:
                errors.append(f"Video assembly is marked 'done', but final MP4 is missing in {out_dir.name}")

        return sid, state_data, errors

    def reset_script_to_pending(self, script_id: str, state_file: Path, state_data: Dict[str, Any]) -> bool:
        """Resets a script's status to pending and clears downstream artifacts."""
        try:
            if not state_data:
                state_data = self.state_mgr.get_script_state(script_id)

            status = state_data.setdefault("status", {})
            status["script_generation"] = "pending"
            status["voice_generation"] = "pending"
            status["image_generation"] = "pending"
            status["thumbnail_generation"] = "pending"
            status["video_assembly"] = "pending"

            self.state_mgr.save_script_state(script_id, state_data)
            self.status_tracker.update_script_stage_status(script_id, "script_generation", "pending")
            return True
        except Exception as exc:
            print(f"Error resetting {script_id}: {exc}", file=sys.stderr)
            return False

    def regenerate_script_now(self, script_id: str, state_data: Dict[str, Any]) -> bool:
        """Immediately re-generates the script using local LLM."""
        try:
            from video_creation._A_video_scripts.main import handle_prompt
            params = state_data.get("prompt_params")
            if not params:
                print(f"Cannot regenerate {script_id}: missing prompt_params in state.")
                return False

            print(f"Regenerating script for {script_id} with local LLM...")
            # Temporarily set script_generation to pending so handle_prompt doesn't skip it
            state_data.setdefault("status", {})["script_generation"] = "pending"
            self.state_mgr.save_script_state(script_id, state_data)

            res = handle_prompt(self.state_mgr, script_id, params, 1, 1, auto=True)
            if res == 0:
                self.status_tracker.update_script_stage_status(script_id, "script_generation", "done")
                return True
            return False
        except Exception as exc:
            print(f"Regeneration failed for {script_id}: {exc}", file=sys.stderr)
            return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LingoVerse JSON Health Checker: Audits state JSONs for corruption, truncation, missing sections, and broken assets."
    )
    parser.add_argument("--script-id", type=str, default=None, help="Check a specific script ID (e.g. SE01, EE03)")
    parser.add_argument("--language", type=str, default=None, help="Filter audit by language (english, french, spanish, italian)")
    parser.add_argument("--type", type=str, default=None, help="Filter audit by video type (expression, game, roleplay, fun_facts)")
    parser.add_argument("--auto-reset", action="store_true", help="Automatically reset all problematic scripts to pending without prompting")
    parser.add_argument("--dry-run", action="store_true", help="Only audit and report issues; do not prompt to fix or modify files")
    args = parser.parse_args()

    auditor = ScriptHealthAuditor()
    state_dir = auditor.state_dir

    if not state_dir.exists():
        print(f"No state directory found at {state_dir}.")
        return 0

    # Collect candidate files
    if args.script_id:
        target_path = auditor.state_mgr._get_script_path(args.script_id)
        if not target_path.exists():
            print(f"No state file found for script ID: {args.script_id}")
            return 1
        state_files = [target_path]
    else:
        state_files = sorted(state_dir.rglob("script_*.json"))

    if args.language:
        l_filter = args.language.lower()
        state_files = [f for f in state_files if l_filter in str(f).lower()]
    if args.type:
        t_filter = args.type.lower()
        state_files = [f for f in state_files if t_filter in str(f).lower()]

    print("\n" + "=" * 76)
    print("           LINGOVERSE JSON HEALTH CHECKER & REPAIR TOOL")
    print("=" * 76)
    print(f"Scanning {len(state_files)} state JSON files across state/ ...")
    print("-" * 76)

    healthy_count = 0
    problematic_scripts = []

    for sf in state_files:
        sid, data, errors = auditor.audit_script(sf)
        if not errors:
            healthy_count += 1
        else:
            problematic_scripts.append((sid, sf, data, errors))

    print(f"Scan complete: {healthy_count} healthy script(s), {len(problematic_scripts)} issue(s) detected.\n")

    if not problematic_scripts:
        print("✓ All scanned state JSONs are 100% healthy, valid, and fully formed!")
        print("=" * 76 + "\n")
        return 0

    print("=" * 76)
    print(f"DETECTED {len(problematic_scripts)} PROBLEMATIC SCRIPT(S):")
    print("=" * 76)

    for i, (sid, sf, data, errors) in enumerate(problematic_scripts, start=1):
        rel_path = sf.relative_to(auditor.base_dir) if auditor.base_dir in sf.parents else sf
        lang = data.get("prompt_params", {}).get("TARGET_LANGUAGE") or "Unknown"
        vtype = data.get("prompt_params", {}).get("VIDEO_TYPE") or "Unknown"
        expr = (
            data.get("prompt_params", {}).get("EXPRESSION")
            or data.get("prompt_params", {}).get("TOPIC")
            or data.get("prompt_params", {}).get("ROLEPLAY_SCENARIO")
            or ""
        )

        print(f"\n[{i}/{len(problematic_scripts)}] ⚠️ SCRIPT ISSUE: {sid} ({lang} / {vtype})")
        if expr:
            print(f"  Topic/Expression: {expr}")
        print(f"  File: {rel_path}")
        print("  Issues:")
        for err in errors:
            print(f"    • {err}")
        print("-" * 76)

        if args.dry_run:
            continue

        if args.auto_reset:
            if auditor.reset_script_to_pending(sid, sf, data):
                print(f"  ✓ [Auto-Reset] Script {sid} reset to 'pending'.")
            continue

        # Interactive resolution prompt
        if sys.stdin.isatty():
            print("  Choose an action:")
            print("    [1] Reset script to 'pending' (recommended: will be re-generated on next run)")
            print("    [2] Re-generate script right now with local LLM")
            print("    [3] Skip / Leave as is")
            try:
                choice = input("  Enter choice [1/2/3] (default: 1): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAudit interrupted by user.")
                return 0

            if choice in ("", "1"):
                if auditor.reset_script_to_pending(sid, sf, data):
                    print(f"  ✓ Script {sid} successfully reset to 'pending'.")
            elif choice == "2":
                if auditor.regenerate_script_now(sid, data):
                    print(f"  ✓ Script {sid} successfully re-generated!")
                else:
                    print(f"  ✗ Re-generation failed for {sid}. Resetting to 'pending' instead.")
                    auditor.reset_script_to_pending(sid, sf, data)
            else:
                print(f"  Skipped {sid}.")

    print("\n" + "=" * 76)
    print("Health check completed.")
    print("=" * 76 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
