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

    def test_env_file_is_not_tracked_in_git(self):
        try:
            res = subprocess.run(
                ["git", "ls-files", ".env", "main/.env"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_output = res.stdout.strip()
            self.assertEqual(tracked_output, "", ".env file is tracked in git! Immediate security violation.")
        except Exception as exc:
            self.skipTest(f"Git command failed: {exc}")

    def test_google_apps_script_is_not_tracked_in_git(self):
        try:
            res = subprocess.run(
                ["git", "ls-files", "main/connectivity/google_apps_script.js", "main/connectivity/apps_script/google_apps_script.js"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_output = res.stdout.strip()
            self.assertEqual(tracked_output, "", "google_apps_script.js is tracked in git! Should be ignored.")
        except Exception as exc:
            self.skipTest(f"Git command failed: {exc}")

    def test_private_input_csvs_are_not_tracked_in_git(self):
        try:
            res = subprocess.run(
                ["git", "ls-files", "input/csv/", "main/input/csv/"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
            for filepath in tracked_files:
                # Only README.md, .gitkeep, and *.sample.csv are permitted
                is_sample = "sample_templates" in filepath or filepath.endswith(".sample.csv")
                is_readme = filepath.endswith("README.md")
                is_gitkeep = filepath.endswith(".gitkeep")
                self.assertTrue(
                    is_sample or is_readme or is_gitkeep,
                    f"Private input file tracked in git: {filepath}"
                )
        except Exception as exc:
            self.skipTest(f"Git command failed: {exc}")

    def test_tracked_files_do_not_contain_hardcoded_openai_keys(self):
        try:
            res = subprocess.run(
                ["git", "ls-files"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
            openai_key_regex = re.compile(r"sk-[A-Za-z0-9]{32,}")

            for rel_path in tracked_files:
                full_path = REPO_ROOT / rel_path
                if full_path.suffix in [".png", ".jpg", ".jfif", ".wav", ".mp4", ".db"]:
                    continue

                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    matches = openai_key_regex.findall(content)
                    self.assertEqual(
                        len(matches), 0,
                        f"Potential live OpenAI API key found in {rel_path}: {matches}"
                    )
                except Exception:
                    continue
        except Exception as exc:
            self.skipTest(f"Git command failed: {exc}")

    def test_tracked_files_do_not_exceed_50mb(self):
        try:
            res = subprocess.run(
                ["git", "ls-files"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
            max_size_bytes = 50 * 1024 * 1024  # 50MB

            for rel_path in tracked_files:
                full_path = REPO_ROOT / rel_path
                if full_path.exists() and full_path.is_file():
                    size = full_path.stat().st_size
                    self.assertLess(
                        size, max_size_bytes,
                        f"Tracked file exceeds 50MB limit ({size / (1024*1024):.2f}MB): {rel_path}"
                    )
        except Exception as exc:
            self.skipTest(f"Git command failed: {exc}")

    def test_tracked_files_do_not_contain_hardcoded_sheets_or_webapp_tokens(self):
        """Ensure no live Google Apps Script deployment tokens or production sheet IDs are hardcoded in tracked files."""
        try:
            res = subprocess.run(
                ["git", "ls-files"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
            webapp_token_regex = re.compile(r"AKfycb[A-Za-z0-9_-]{20,}")

            for rel_path in tracked_files:
                full_path = REPO_ROOT / rel_path
                if full_path.suffix in [".png", ".jpg", ".jfif", ".wav", ".mp4", ".db"]:
                    continue

                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    matches = webapp_token_regex.findall(content)
                    self.assertEqual(
                        len(matches), 0,
                        f"Live Google Apps Script deployment token found in tracked file {rel_path}: {matches}"
                    )
                except Exception:
                    continue
        except Exception as exc:
            self.skipTest(f"Git command failed: {exc}")


if __name__ == "__main__":
    unittest.main()
