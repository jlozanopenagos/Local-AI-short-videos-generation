"""
llm_client.py — Standard access to the streaming LLM client for domain engines.
Directly binds to core.llm to guarantee identical runtime state, patches, and watchdogs.
"""

from __future__ import annotations

from ..core.llm import (
    API_BASE_URL,
    API_KEY,
    MODEL_NAME,
    REQUEST_TIMEOUT_SECONDS,
    DEFAULT_CHUNK_TIMEOUT,
    DEFAULT_WALL_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    create_resilient_client,
    client,
    check_connection,
    cooldown_between_calls,
    generate_response,
)

__all__ = [
    "API_BASE_URL",
    "API_KEY",
    "MODEL_NAME",
    "REQUEST_TIMEOUT_SECONDS",
    "DEFAULT_CHUNK_TIMEOUT",
    "DEFAULT_WALL_TIMEOUT",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_TEMPERATURE",
    "create_resilient_client",
    "client",
    "check_connection",
    "cooldown_between_calls",
    "generate_response",
]
