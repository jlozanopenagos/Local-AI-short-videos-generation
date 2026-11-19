"""assembly/types/__init__.py — Re-exports AssemblyProfile registry and helpers."""
from .base import AssemblyProfile
from .registry import (
    AssemblyProfileRegistry,
    get_assembly_profile,
    is_legacy_assembly_engine_enabled,
)

__all__ = [
    "AssemblyProfile",
    "AssemblyProfileRegistry",
    "get_assembly_profile",
    "is_legacy_assembly_engine_enabled",
]
