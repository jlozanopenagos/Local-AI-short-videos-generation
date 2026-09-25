"""OpenAI-compatible client for a local llama.cpp server with streaming watchdog and auto-recovery."""

from __future__ import annotations

import os
import sys
import time
from typing import Final

# pyrefly: ignore [missing-import]
import httpx
from openai import OpenAI

API_BASE_URL: Final[str] = os.getenv("LLM_API_BASE_URL", "http://127.0.0.1:8080/v1")
API_KEY: Final[str] = os.getenv("LLM_API_KEY", "llama")
MODEL_NAME: Final[str] = os.getenv("LLM_MODEL_NAME", "llama")
REQUEST_TIMEOUT_SECONDS: Final[float] = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "120"))
DEFAULT_CHUNK_TIMEOUT: Final[float] = float(os.getenv("LLM_CHUNK_TIMEOUT", "25.0"))
DEFAULT_WALL_TIMEOUT: Final[float] = float(os.getenv("LLM_WALL_TIMEOUT", "90.0"))
DEFAULT_MAX_TOKENS: Final[int] = int(os.getenv("LLM_MAX_TOKENS", "2048"))
DEFAULT_TEMPERATURE: Final[float] = float(os.getenv("LLM_TEMPERATURE", "0.7"))


def _safe_print(text: str, file=None, flush: bool = True) -> None:
    target = file or sys.stdout
    try:
        print(text, file=target, flush=flush)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), file=target, flush=flush)


def create_resilient_client(
    base_url: str = API_BASE_URL,
    api_key: str = API_KEY,
    chunk_timeout: float = DEFAULT_CHUNK_TIMEOUT,
) -> OpenAI:
    """Creates an OpenAI client with per-chunk socket read timeout."""
    timeout = httpx.Timeout(
        connect=10.0,
        read=chunk_timeout,
        write=15.0,
        pool=15.0,
    )
    return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)


client = create_resilient_client()


def check_connection() -> None:
    """Check if the local LLM server is reachable and responsive."""
    from config import check_llm_connection
    check_llm_connection(API_BASE_URL, API_KEY, raise_on_error=True)


def cooldown_between_calls(delay: float = 0.2) -> None:
    """Brief pause between calls to allow llama-server slot to return to idle."""
    if delay > 0:
        time.sleep(delay)


def generate_response(
    prompt: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    max_retries: int = 3,
    chunk_timeout: float = DEFAULT_CHUNK_TIMEOUT,
    wall_timeout: float = DEFAULT_WALL_TIMEOUT,
    show_progress: bool = True,
) -> str:
    """
    Send a prompt to the local llama.cpp server and return the assistant reply.
    Uses token streaming with an active watchdog to detect stalled slots, auto-aborts
    hung connections to free the slot, and retries seamlessly ("go ahead, don't stop").
    """
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt must not be empty")

    tokens_to_use = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
    temp_to_use = temperature if temperature is not None else DEFAULT_TEMPERATURE

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        stream = None
        start_t = time.time()
        last_heartbeat = start_t
        token_count = 0
        collected: list[str] = []

        try:
            # Recreate client with specified chunk_timeout if non-default
            active_client = (
                create_resilient_client(chunk_timeout=chunk_timeout)
                if chunk_timeout != DEFAULT_CHUNK_TIMEOUT
                else client
            )

            stream = active_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=tokens_to_use,
                temperature=temp_to_use,
                stream=True,
            )

            for chunk in stream:
                now = time.time()
                # Check overall generation wall-clock limit
                if now - start_t > wall_timeout:
                    raise TimeoutError(f"LLM generation exceeded wall timeout ({wall_timeout:.0f}s)")

                delta = chunk.choices[0].delta if chunk.choices else None
                content = delta.content if delta else None
                if content:
                    collected.append(content)
                    token_count += 1

                if show_progress and (now - last_heartbeat >= 4.0):
                    elapsed = int(now - start_t)
                    _safe_print(f"  [LLM] Generating... ({elapsed}s, {token_count} tokens)")
                    last_heartbeat = now

            full_text = "".join(collected).strip()
            if full_text:
                # Brief breather so slot returns cleanly to idle
                cooldown_between_calls(0.2)
                return full_text

            raise ValueError("Empty completion returned by LLM")

        except Exception as err:
            last_error = err
            # Force-close the stream to sever TCP connection and tell llama-server to abort the slot
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

            elapsed = int(time.time() - start_t)
            if attempt < max_retries:
                _safe_print(
                    f"[Watchdog] LLM stalled or interrupted ({err}) after {elapsed}s. "
                    f"Auto-resetting slot and retrying (attempt {attempt + 1}/{max_retries})... "
                    f"\"Go ahead, don't stop!\"",
                    file=sys.stderr,
                )
                # Pause to let llama-server acknowledge client disconnect and clear slot
                time.sleep(0.8 * attempt)
            else:
                _safe_print(
                    f"[Watchdog] LLM failed after {max_retries} attempts: {err}",
                    file=sys.stderr,
                )

    raise last_error or RuntimeError("Failed to generate LLM response")
