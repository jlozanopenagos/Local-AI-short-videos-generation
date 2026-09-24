"""
core package — Central infrastructure for shorts_automation.

Exposes StateManager, ID resolution, and language/type maps.
Also maintains transparent backward compatibility for legacy imports
like 'import state_manager' or 'from state_manager import StateManager'.
"""
import sys
from pathlib import Path

# Ensure single identity for state_manager module whether imported via 'core.state_manager' or 'state_manager'
if "state_manager" in sys.modules:
    state_manager = sys.modules["state_manager"]
else:
    from . import state_manager
    sys.modules["state_manager"] = state_manager

from .state_manager import (
    StateManager,
    resolve_lang_and_type,
    LANG_MAP,
    TYPE_MAP,
)

from .expression_db import (
    ExpressionDB,
    get_expression_db,
    is_expression_done,
)

from .cli_prompt import (
    prompt_production_mode,
    prompt_group_range,
    prompt_fun_facts_mode,
    prompt_csv_list_mode,
    prompt_ready_scripts_mode,
    find_ready_scripts_csvs,
)

# Ensure core directory is also in sys.path for direct module discovery
_CORE_DIR = str(Path(__file__).parent.resolve())
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

# Extend path with stage-local core directories if they exist so namespace collisions are prevented
_MAIN_DIR = Path(__file__).resolve().parent.parent
for _sub_core in [
    _MAIN_DIR / "video_creation" / "_B_voice_generation" / "core",
    _MAIN_DIR / "video_creation" / "_C_image_generation" / "core",
]:
    if _sub_core.is_dir() and str(_sub_core) not in __path__:
        __path__.append(str(_sub_core))

__all__ = [
    "StateManager",
    "resolve_lang_and_type",
    "LANG_MAP",
    "TYPE_MAP",
    "ExpressionDB",
    "get_expression_db",
    "is_expression_done",
    "prompt_production_mode",
    "prompt_group_range",
    "prompt_fun_facts_mode",
    "prompt_csv_list_mode",
    "prompt_ready_scripts_mode",
    "find_ready_scripts_csvs",
]

