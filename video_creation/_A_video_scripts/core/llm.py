"""OpenAI-compatible client for a local llama.cpp server."""

from __future__ import annotations

import os
from typing import Final

# pyrefly: ignore [missing-import]
from openai import OpenAI

API_BASE_URL: Final[str] = os.getenv("LLM_API_BASE_URL", "http://127.0.0.1:8080/v1")
API_KEY: Final[str] = os.getenv("LLM_API_KEY", "llama")
MODEL_NAME: Final[str] = os.getenv("LLM_MODEL_NAME", "llama")
REQUEST_TIMEOUT_SECONDS: Final[float] = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "120"))
DEFAULT_MAX_TOKENS: Final[int] = int(os.getenv("LLM_MAX_TOKENS", "2048"))
DEFAULT_TEMPERATURE: Final[float] = float(os.getenv("LLM_TEMPERATURE", "0.7"))

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
    timeout=REQUEST_TIMEOUT_SECONDS,
)


def check_connection() -> None:
    """Check if the local LLM server is reachable and responsive."""
    from config import check_llm_connection
    check_llm_connection(API_BASE_URL, API_KEY, raise_on_error=True)


def generate_response(
    prompt: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    max_retries: int = 2,
) -> str:
    """Send a prompt to the local llama.cpp server and return the assistant reply."""
    import time
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt must not be empty")

    tokens_to_use = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
    temp_to_use = temperature if temperature is not None else DEFAULT_TEMPERATURE

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=tokens_to_use,
                temperature=temp_to_use,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
            raise ValueError("Empty completion returned by LLM")
        except Exception as err:
            last_error = err
            if attempt < max_retries:
                time.sleep(1.5 * attempt)

    raise last_error or RuntimeError("Failed to generate LLM response")
