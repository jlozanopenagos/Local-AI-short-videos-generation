"""Test Layer Package for Shorts Automation Pipeline."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_DIR = REPO_ROOT / "main"
TEST_DIR = Path(__file__).resolve().parent

for p in [str(MAIN_DIR), str(REPO_ROOT), str(TEST_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)
