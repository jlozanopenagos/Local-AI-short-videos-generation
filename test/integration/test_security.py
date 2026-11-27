"""
test/integration/test_security.py — Automated security audit preventing leaks of secrets, personal paths, and private data.
"""

from __future__ import annotations

import unittest
import subprocess
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestSecurityAndPrivacy(unittest.TestCase):
    """Ensure no secrets, API keys, credentials, or private files are tracked or exposed."""

    def setUp(self):
        self.gitignore_path = REPO_ROOT / ".gitignore"

    def test_gitignore_contains_critical_privacy_rules(self):
        self.assertTrue(self.gitignore_path.exists())
        content = self.gitignore_path.read_text(encoding="utf-8")

        critical_rules = [
            ".env",
            "database/*.db",
            "database/*.csv",
            "!database/*.sample.csv",
            "input/csv/**/*.csv",
            "!input/csv/**/*.sample.csv",
            "state/**/*.json",
            "!state/script_state.sample.json",
            "output/",
            "ffmpeg.exe",
            "ffprobe.exe",
            "google_apps_script.js",
            "!**/connectivity/google_apps_script.sample.js",
        ]
        for rule in critical_rules:
            with self.subTest(rule=rule):
                self.assertIn(rule, content, f"Rule '{rule}' missing from .gitignore")

    def tracked_files(self, *patterns):
        result = subprocess.run(
            ["git", "-c", f"safe.directory={REPO_ROOT.as_posix()}", "ls-files", "-z", "--", *patterns],
            cwd=REPO_ROOT, capture_output=True, check=True, timeout=15,
        )
        return [REPO_ROOT / path for path in result.stdout.decode("utf-8").split("\0") if path]

    def test_env_file_is_not_tracked_in_git(self):
        self.assertFalse(self.tracked_files(".env", "main/.env"))

    def test_google_apps_script_is_not_tracked_in_git(self):
        self.assertFalse(self.tracked_files(
            "main/connectivity/google_apps_script.js", "main/connectivity/apps_script/google_apps_script.js",
        ))

    def test_private_input_csvs_are_not_tracked_in_git(self):
        for path in self.tracked_files("input/csv/", "main/input/csv/"):
            self.assertTrue(
                "sample_templates" in path.parts or path.name.endswith(".sample.csv") or
                path.name in ("README.md", ".gitkeep"),
                f"Private input file tracked: {path.relative_to(REPO_ROOT)}",
            )

    def test_tracked_files_do_not_exceed_50mb(self):
        for path in self.tracked_files():
            if path.is_file():
                self.assertLess(path.stat().st_size, 50 * 1024 * 1024, f"Tracked file exceeds 50 MiB: {path.name}")

    def assert_no_match_in_tracked_text(self, pattern):
        matches = []
        for path in self.tracked_files():
            if not path.is_file() or path == Path(__file__).resolve():
                continue
            content = path.read_bytes()
            if b"\0" in content:
                continue
            if pattern.search(content.decode("utf-8", errors="replace")):
                matches.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertFalse(matches, f"Sensitive pattern matched in: {', '.join(matches)}")

    def test_tracked_files_do_not_contain_hardcoded_openai_keys(self):
        self.assert_no_match_in_tracked_text(re.compile(r"sk-[A-Za-z0-9]{32,}"))

    def test_tracked_files_do_not_contain_hardcoded_elevenlabs_or_gemini_keys(self):
        self.assert_no_match_in_tracked_text(re.compile(r"\bsk_[0-9a-f]{32,}\b"))
        self.assert_no_match_in_tracked_text(re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"))
        self.assert_no_match_in_tracked_text(re.compile(r"BEGIN (?:RSA )?PRIVATE KEY"))

    def test_tracked_files_do_not_contain_hardcoded_sheets_or_webapp_tokens(self):
        self.assert_no_match_in_tracked_text(re.compile(r"AKfycb[A-Za-z0-9_-]{20,}"))

    def test_tracked_production_sources_do_not_contain_personal_paths(self):
        pattern = re.compile(r"(?:[CD]:[/\\]+(?:AI|AI_video_generation|Users)[/\\]|july_)", re.IGNORECASE)
        matches = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in self.tracked_files()
            if path.is_file()
            and path != Path(__file__).resolve()
            and b"\0" not in path.read_bytes()
            and pattern.search(path.read_text(encoding="utf-8", errors="replace"))
        ]
        self.assertFalse(matches, f"Personal path matched in tracked file(s): {', '.join(matches)}")


if __name__ == "__main__":
    unittest.main()
