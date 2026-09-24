# Init package
from pathlib import Path
_MAIN_CORE = Path(__file__).resolve().parents[2] / "core"
if _MAIN_CORE.is_dir() and str(_MAIN_CORE) not in __path__:
    __path__.append(str(_MAIN_CORE))
