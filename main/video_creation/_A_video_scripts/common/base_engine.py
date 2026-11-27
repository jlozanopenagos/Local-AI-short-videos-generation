"""
base_engine.py — Standard contract and lifecycle for all script type domain engines.
Provides abstract validation, prompt building, sanitization, and structured generation lifecycle.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .text_utils import count_spoken_words, extract_json_from_llm_response

logger = logging.getLogger("script_engine")


@dataclass
class ValidationResult:
    """Encapsulates validation outcome, errors, warnings, and word count metrics."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    spoken_words: int = 0

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


@dataclass
class ScriptGenerationResult:
    """Unified result container returned by all domain script engines."""
    script_id: str
    script_type: str
    script: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    spoken_words: int = 0
    raw_response: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    retry_count: int = 0


class BaseScriptEngine(ABC):
    """
    Abstract base class for all script engines.
    Subclasses (GameEngine, RoleplayEngine, ExpressionEngine, FunFactsEngine)
    implement their domain-specific prompt construction, sanitization, and rules.
    """

    script_type: str = "base"
    type_codes: List[str] = []

    def __init__(self, llm_callable: Optional[Callable[..., str]] = None):
        """
        Args:
            llm_callable: Optional LLM generator function. If None, lazily binds to common.llm_client.
        """
        self._llm_callable = llm_callable

    def _get_llm_callable(self) -> Callable[..., str]:
        if self._llm_callable is not None:
            return self._llm_callable
        from .llm_client import generate_response
        return generate_response

    @abstractmethod
    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        """Constructs the domain-specific prompt for this script type."""
        pass

    @abstractmethod
    def validate(self, script_dict: Dict[str, Any], input_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validates domain-specific schema, keys, word counts, and structural rules."""
        pass

    def sanitize(self, script_dict: Dict[str, Any], input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Normalizes, cleans, and strips unwanted artifacts (e.g. narrator prefixes).
        Default implementation returns a shallow copy. Domain engines can override.
        """
        return dict(script_dict)

    def build_retry_prompt(
        self,
        original_prompt: str,
        script_dict: Dict[str, Any],
        validation: ValidationResult,
    ) -> str:
        """
        Constructs an explicit targeted correction prompt when initial validation fails.
        """
        errs = "\n- ".join(validation.errors)
        advice = []
        for e in validation.errors:
            e_lower = e.lower()
            if "spoken word count too high" in e_lower:
                advice.append(
                    "ACTION REQUIRED: Your previous script was TOO LONG! You MUST trim dialogues and make lines significantly more concise."
                )
            elif "spoken word count too low" in e_lower:
                advice.append(
                    "ACTION REQUIRED: Your previous script was TOO SHORT! Add more natural dialogue turns or richer detail."
                )
            elif "not found in the script" in e_lower or "not found in the game" in e_lower:
                advice.append(
                    "ACTION REQUIRED: You MUST explicitly include and focus on the required target expression/contrast!"
                )
            elif "language mismatch" in e_lower:
                advice.append(
                    "ACTION REQUIRED: LANGUAGE MISMATCH! You MUST write the ENTIRE script 100% in the TARGET LANGUAGE! Do NOT write in English!"
                )
            elif "not spoken in any dialogue part" in e_lower:
                advice.append(
                    "ACTION REQUIRED: One of the characters MUST naturally speak the TARGET EXPRESSION during the dialogue!"
                )

        advice_block = ("\n" + "\n".join(advice)) if advice else ""
        return (
            f"{original_prompt}\n\n"
            f"=== CORRECTION REQUIRED ===\n"
            f"Your previous attempt violated the following strict requirements:\n"
            f"- {errs}{advice_block}\n\n"
            f"Please generate the complete, corrected JSON strictly adhering to all rules."
        )

    def generate(
        self,
        input_data: Dict[str, Any],
        on_token: Optional[Callable[[str], None]] = None,
        max_retries: int = 2,
    ) -> ScriptGenerationResult:
        """
        Standard generation lifecycle:
        1. Build domain prompt.
        2. Stream tokens via LLM client (forwarding to on_token callback if provided).
        3. Parse JSON from response.
        4. Sanitize script dictionary.
        5. Validate against domain rules.
        6. If invalid, attempt targeted correction retries up to max_retries.
        7. Return structured ScriptGenerationResult.
        """
        script_id = input_data.get("SCRIPT_ID") or input_data.get("script_id") or "UNKNOWN"
        prompt = self.build_prompt(input_data)
        llm_fn = self._get_llm_callable()

        raw_response = ""
        current_script: Dict[str, Any] = {}
        validation = ValidationResult()
        retry_count = 0

        current_prompt = prompt

        for attempt in range(max_retries + 1):
            try:
                # LLM Call
                raw_response = llm_fn(current_prompt)
                parsed = extract_json_from_llm_response(raw_response)
                sanitized = self.sanitize(parsed, input_data)
                val_result = self.validate(sanitized, input_data)

                if val_result.is_valid:
                    current_script = sanitized
                    validation = val_result
                    break

                # Invalid attempt
                retry_count = attempt + 1
                logger.warning(
                    f"[{script_id}] Validation failed (attempt {attempt + 1}/{max_retries + 1}): {val_result.errors}"
                )
                current_script = sanitized
                validation = val_result

                if attempt < max_retries:
                    current_prompt = self.build_retry_prompt(prompt, sanitized, val_result)

            except Exception as exc:
                logger.error(f"[{script_id}] Generation attempt {attempt + 1} raised error: {exc}")
                validation.add_error(str(exc))
                if attempt == max_retries:
                    break

        words = count_spoken_words(current_script) if current_script else 0

        return ScriptGenerationResult(
            script_id=script_id,
            script_type=self.script_type,
            script=current_script,
            spoken_words=words,
            raw_response=raw_response,
            is_valid=validation.is_valid,
            validation_errors=validation.errors,
            retry_count=retry_count,
        )

