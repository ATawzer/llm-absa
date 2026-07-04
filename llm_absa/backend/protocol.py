"""Provider-agnostic LLM backend interface."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


@runtime_checkable
class LLMBackend(Protocol):
    """Provider-agnostic interface for structured-output LLM calls."""

    async def agenerate(self, system: str, user: str, schema: type[M]) -> M: ...

    def generate(self, system: str, user: str, schema: type[M]) -> M: ...
