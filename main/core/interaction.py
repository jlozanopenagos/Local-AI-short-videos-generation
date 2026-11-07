"""
core/interaction.py — Injectable interaction layer for CLI and WebUI.

Decouples interactive terminal prompts (input(), countdown timers, msvcrt)
from core pipeline and stage execution logic.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class InteractionProvider(ABC):
    """Abstract interface for user interactions during workflow execution."""

    @abstractmethod
    def ask_choice(
        self,
        prompt: str,
        valid_choices: List[str],
        default: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Prompts for a choice from a list of valid choices."""
        ...

    @abstractmethod
    def ask_input(
        self,
        prompt: str,
        default: str = "",
        timeout: Optional[float] = None,
    ) -> str:
        """Prompts for free-form text input."""
        ...

    @abstractmethod
    def confirm(
        self,
        prompt: str,
        default: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """Prompts for a yes/no confirmation."""
        ...


class CliInteractionProvider(InteractionProvider):
    """Standard CLI interaction provider that delegates to console input / timed_input."""

    def ask_choice(
        self,
        prompt: str,
        valid_choices: List[str],
        default: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        from core.cli_prompt import timed_input
        default_val = default or (valid_choices[0] if valid_choices else "1")
        choices_hint = f"[{'/'.join(valid_choices)}]"
        display_prompt = f"{prompt} {choices_hint} (default: {default_val}): "
        raw = timed_input(prompt=display_prompt, timeout=timeout or 10.0, default=default_val).strip()
        return raw if raw in valid_choices else default_val

    def ask_input(
        self,
        prompt: str,
        default: str = "",
        timeout: Optional[float] = None,
    ) -> str:
        from core.cli_prompt import timed_input
        if timeout:
            return timed_input(prompt=prompt, timeout=timeout, default=default)
        try:
            val = input(prompt).strip()
            return val if val else default
        except (KeyboardInterrupt, EOFError):
            return default

    def confirm(
        self,
        prompt: str,
        default: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        hint = "[Y/n]" if default else "[y/N]"
        full_prompt = f"{prompt} {hint}: "
        ans = self.ask_input(full_prompt, default="y" if default else "n", timeout=timeout).strip().lower()
        if not ans:
            return default
        return ans in ("y", "yes")


class PresetInteractionProvider(InteractionProvider):
    """Non-interactive provider that resolves choices from predefined settings or defaults (for WebUI / automated jobs)."""

    def __init__(self, presets: Optional[Dict[str, Any]] = None, auto_default: bool = True):
        self.presets = presets or {}
        self.auto_default = auto_default

    def ask_choice(
        self,
        prompt: str,
        valid_choices: List[str],
        default: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        for k, v in self.presets.items():
            if k.lower() in prompt.lower() and str(v) in valid_choices:
                return str(v)
        if default and default in valid_choices:
            return default
        return valid_choices[0] if valid_choices else ""

    def ask_input(
        self,
        prompt: str,
        default: str = "",
        timeout: Optional[float] = None,
    ) -> str:
        for k, v in self.presets.items():
            if k.lower() in prompt.lower():
                return str(v)
        return default

    def confirm(
        self,
        prompt: str,
        default: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        for k, v in self.presets.items():
            if k.lower() in prompt.lower():
                return bool(v)
        return default


_GLOBAL_INTERACTION: InteractionProvider = CliInteractionProvider()


def get_interaction() -> InteractionProvider:
    """Returns current active interaction provider."""
    global _GLOBAL_INTERACTION
    return _GLOBAL_INTERACTION


def set_interaction(provider: InteractionProvider) -> None:
    """Sets active interaction provider."""
    global _GLOBAL_INTERACTION
    _GLOBAL_INTERACTION = provider

