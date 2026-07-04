"""Live-API tests for GeminiBackend. Requires GOOGLE_API_KEY."""

import os

import pytest
from pydantic import BaseModel

from llm_absa.backend import GeminiBackend

pytestmark = pytest.mark.integration

_MODEL = os.environ.get("GEMINI_TEST_MODEL", "gemini-2.5-flash")


class _Answer(BaseModel):
    answer: str


@pytest.fixture
def backend() -> GeminiBackend:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set")
    return GeminiBackend(api_key=api_key, model=_MODEL)


async def test_agenerate_returns_schema_from_live_api(backend: GeminiBackend):
    result = await backend.agenerate(
        system="Answer in one word.",
        user="What color is a clear daytime sky?",
        schema=_Answer,
    )

    assert isinstance(result, _Answer)
    assert result.answer


def test_generate_sync_returns_schema_from_live_api(backend: GeminiBackend):
    result = backend.generate(
        system="Answer with only the numeral.",
        user="What is 2 + 2?",
        schema=_Answer,
    )

    assert isinstance(result, _Answer)
    assert result.answer
