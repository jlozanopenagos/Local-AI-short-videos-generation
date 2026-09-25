# core package
from pathlib import Path

# Extend core package path with main/core so central modules (status_tracker, expression_db, cli_prompt, state_manager) are always discoverable
_curr = Path(__file__).resolve().parent
while _curr.name != "main" and _curr.parent != _curr:
    _curr = _curr.parent
_MAIN_CORE = _curr / "core"
if _MAIN_CORE.is_dir() and str(_MAIN_CORE) not in __path__:
    __path__.append(str(_MAIN_CORE))
