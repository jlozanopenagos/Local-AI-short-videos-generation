"""
assembly/languages/base.py — Base AssemblyLanguageProfile dataclass.
Languages share video-type assembly rules by default, while keeping isolated per-language hooks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AssemblyLanguageProfile:
    """Language-level optional overrides for font, vertical margin offset, and BGM volume scaling."""

    code: str
    name: str
    font_override: Optional[str] = None
    margin_v_offset: int = 0
    bgm_volume_scale: float = 1.0
