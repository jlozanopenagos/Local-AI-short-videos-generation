"""Layer 2: Integration Tests for Multi-Component Workflows and Mock Backends."""
import sys
from pathlib import Path

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))
