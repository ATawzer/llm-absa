"""Async aspect extraction for a single document against a taxonomy."""

from __future__ import annotations

from pydantic import BaseModel

from llm_absa.backend.protocol import LLMBackend
from llm_absa.models import Aspect, Taxonomy
from llm_absa.prompts import render


class _ClassifyResult(BaseModel):
    aspects: list[Aspect]


async def classify_document(
    text: str,
    taxonomy: Taxonomy,
    backend: LLMBackend,
    *,
    max_chars: int = 2000,
) -> list[Aspect]:
    """Extract aspects from one document, constrained to the given taxonomy."""
    system = render("classify/system.jinja2", taxonomy=taxonomy.to_dict())
    user = render("classify/user.jinja2", document_text=text[:max_chars])
    result = await backend.agenerate(system, user, _ClassifyResult)
    return result.aspects
