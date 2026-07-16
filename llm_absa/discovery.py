"""Async taxonomy discovery: raw pair extraction per batch, then canonicalization."""

from __future__ import annotations

from pydantic import BaseModel

from llm_absa.backend.protocol import LLMBackend
from llm_absa.models import Taxonomy
from llm_absa.prompts import render


class DiscoveredPair(BaseModel):
    category: str
    feature: str


class _DiscoveryBatchResult(BaseModel):
    pairs: list[DiscoveredPair]
    taxonomy_complete: bool


async def discover_batch(
    documents: list[str],
    accumulated: Taxonomy | None,
    backend: LLMBackend,
    *,
    seed_categories: list[str] | None = None,
    context: str | None = None,
) -> tuple[list[DiscoveredPair], bool]:
    """Extract new (category, feature) pairs from one batch of documents."""
    system = render(
        "discover_batch/system.jinja2",
        seed_categories=seed_categories or [],
        accumulated=accumulated.to_dict() if accumulated else None,
        context=context,
    )
    user = render("discover_batch/user.jinja2", documents=documents)
    result = await backend.agenerate(system, user, _DiscoveryBatchResult)
    return result.pairs, result.taxonomy_complete


async def canonicalize(
    raw_pairs: dict[str, list[str]],
    seed_categories: list[str],
    backend: LLMBackend,
    *,
    context: str | None = None,
) -> Taxonomy:
    """Collapse raw discovered pairs into a canonical taxonomy."""
    system = render("canonicalize/system.jinja2", seed_categories=seed_categories, context=context)
    user = render("canonicalize/user.jinja2", raw_pairs=raw_pairs)
    return await backend.agenerate(system, user, Taxonomy)
