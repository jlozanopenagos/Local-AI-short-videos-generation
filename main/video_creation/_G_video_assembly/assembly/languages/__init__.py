"""assembly/languages/__init__.py — Re-exports language assembly profiles and resolver."""
from .base import AssemblyLanguageProfile
from .english import ENGLISH_ASSEMBLY_PROFILE
from .french import FRENCH_ASSEMBLY_PROFILE
from .italian import ITALIAN_ASSEMBLY_PROFILE
from .registry import get_assembly_language_profile
from .spanish import SPANISH_ASSEMBLY_PROFILE

__all__ = [
    "AssemblyLanguageProfile",
    "ENGLISH_ASSEMBLY_PROFILE",
    "FRENCH_ASSEMBLY_PROFILE",
    "SPANISH_ASSEMBLY_PROFILE",
    "ITALIAN_ASSEMBLY_PROFILE",
    "get_assembly_language_profile",
]
