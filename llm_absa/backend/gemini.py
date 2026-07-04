"""Gemini implementation of the LLMBackend protocol."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from llm_absa.backend.protocol import M


def _is_rate_limit_error(exc: BaseException) -> bool:
    return isinstance(exc, genai_errors.ClientError) and exc.code == 429


@dataclass
class RetryConfig:
    """Retry policy for rate-limit errors only; schema/parse failures always raise."""

    max_attempts: int = 5
    min_wait_seconds: float = 1.0
    max_wait_seconds: float = 60.0


class GeminiBackend:
    """LLMBackend implementation backed by the Gemini API."""

    def __init__(self, api_key: str, model: str, retry: RetryConfig | None = None) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._retry = retry or RetryConfig()

    async def agenerate(self, system: str, user: str, schema: type[M]) -> M:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._retry.max_attempts),
            wait=wait_exponential(
                min=self._retry.min_wait_seconds, max=self._retry.max_wait_seconds
            ),
            retry=retry_if_exception(_is_rate_limit_error),
            reraise=True,
        )
        async for attempt in retrying:
            with attempt:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=user,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
                if response.text is None:
                    raise ValueError("Gemini response contained no text")
                return schema.model_validate_json(response.text)
        raise AssertionError("unreachable")  # pragma: no cover

    def generate(self, system: str, user: str, schema: type[M]) -> M:
        return asyncio.run(self.agenerate(system, user, schema))
