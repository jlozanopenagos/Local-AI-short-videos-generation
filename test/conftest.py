"""
test_layer/conftest.py — Shared test fixtures, mock helpers, and isolated workspace utilities.
Compatible with both pytest (via fixtures) and standard unittest (via helper functions/classes).
"""
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator

# Add repository root, main project, and test directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_DIR = REPO_ROOT / "main"
TEST_DIR = Path(__file__).resolve().parent
for p in [str(REPO_ROOT), str(MAIN_DIR), str(TEST_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    # pyrefly: ignore [missing-import]
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class WorkspaceHelper:
    """Helper for managing temporary isolated test workspaces."""
    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name).resolve()
        self._setup_structure()

    def _setup_structure(self):
        (self.path / "state").mkdir(parents=True, exist_ok=True)
        (self.path / "database").mkdir(parents=True, exist_ok=True)
        (self.path / "output").mkdir(parents=True, exist_ok=True)
        (self.path / "input" / "csv" / "english" / "expressions_list").mkdir(parents=True, exist_ok=True)
        (self.path / "input" / "images").mkdir(parents=True, exist_ok=True)

    def cleanup(self):
        self.temp_dir.cleanup()


SAMPLE_EXPRESSION_SCRIPT = {
    "title": "Why Break a Leg Actually Means Good Luck",
    "hook": "Ever wondered why saying good luck to an actor is considered a total disaster?",
    "setup": "Old theatrical superstition claimed evil spirits would flip your words, so wishing success guaranteed failure.",
    "discovery": "In reality, to break a leg meant bending your knees during an encore curtain call.",
    "example": "Before heading onstage tonight, Sarah whispered: break a leg, you've got this!",
    "payoff": "Superstitions are wild, but true stage presence never fails. Drop your favorite backstage idiom below!"
}

SAMPLE_ROLEPLAY_SCRIPT = {
    "title": "The Flight Gate Drama",
    "hook": "Running through terminal three with five minutes to departure never goes smoothly.",
    "DIALOGUE_PART_1": "PERSON_ONE (Panicked): We only have four minutes before they shut the jet bridge!\nPERSON_TWO (Calm): Take a breath, they're still boarding group one. Keep your shirt on.",
    "DIALOGUE_PART_2": "PERSON_ONE (Confused): Keep my shirt on? Why would I take my clothes off in the airport?\nPERSON_TWO (Amused): It means don't lose your temper or panic when there's still time.",
    "DIALOGUE_PART_3": "PERSON_ONE (Relieved): Right, I was about to drop my carry-on and sprint like an Olympian.\nPERSON_TWO (Playful): Exactly, save that speed for sprinting through security next time.",
    "DIALOGUE_PART_4": "PERSON_ONE (Laughing): Deal, let me grab my boarding pass before they call final boarding.\nPERSON_TWO (Smirking): See? We're the first ones in the jet bridge queue.",
    "PAYOFF": "Airport sprints test everyone's patience. What's your funniest gate rush story? Tell us in the comments!"
}

SAMPLE_GAME_SCRIPT = {
    "title": "Acoustic Ear Test: Break a Leg",
    "hook": "Think your ears are tuned to real spoken English? Let's test your reflexes.",
    "challenge": "Both actors signed the employment CONtract yesterday. Did you hear A: CONtract, or B: conTRACT?",
    "pressure": "Lock in your choice before the timer runs out.",
    "answer": "Option A takes the win! The noun takes the stress on the first syllable: CONtract.",
    "explanation": "Nouns place stress on the first beat, while verbs push it to the second beat.",
    "chalkboard_exercise": "Both actors signed the employment ___ yesterday.\nA) CONtract\nB) conTRACT"
}

SAMPLE_FUN_FACTS_SCRIPT = {
    "title": "Why English Has a Silent K in Knight and Knee",
    "hook": "Ever wonder why you write a K in knight, knee, and knife, but never pronounce it?",
    "discovery": "In Old English and Germanic ancestors, that K was fully pronounced like 'k-nee' and 'k-nicht'.",
    "payoff": "Spelling froze when printing presses arrived, but speech kept moving fast. Which silent letter confuses you most?"
}


if HAS_PYTEST:
    @pytest.fixture
    def isolated_workspace() -> Generator[WorkspaceHelper, None, None]:
        helper = WorkspaceHelper()
        yield helper
        helper.cleanup()

    @pytest.fixture
    def sample_expression() -> Dict[str, Any]:
        return SAMPLE_EXPRESSION_SCRIPT.copy()

    @pytest.fixture
    def sample_roleplay() -> Dict[str, Any]:
        return SAMPLE_ROLEPLAY_SCRIPT.copy()

    @pytest.fixture
    def sample_game() -> Dict[str, Any]:
        return SAMPLE_GAME_SCRIPT.copy()
