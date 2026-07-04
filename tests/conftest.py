"""Shared test fixtures."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TypeVar

import pytest
from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


@dataclass
class MockBackend:
    """LLMBackend stand-in that returns pre-set responses in call order, no network."""

    responses: list[BaseModel]
    calls: list[tuple[str, str, type[BaseModel]]] = field(default_factory=list)

    async def agenerate(self, system: str, user: str, schema: type[M]) -> M:
        self.calls.append((system, user, schema))
        response = self.responses[len(self.calls) - 1]
        assert isinstance(response, schema)
        return response

    def generate(self, system: str, user: str, schema: type[M]) -> M:
        return asyncio.run(self.agenerate(system, user, schema))


@pytest.fixture
def mock_backend_factory():
    def _factory(responses: list[BaseModel]) -> MockBackend:
        return MockBackend(responses=list(responses))

    return _factory
