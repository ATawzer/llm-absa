"""Async-first orchestration: discovery, concurrent classification, and end-to-end runs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from aiolimiter import AsyncLimiter

from llm_absa.backend.protocol import LLMBackend
from llm_absa.classify import classify_document
from llm_absa.discovery import canonicalize, discover_batch
from llm_absa.models import DocumentResult, RunResult, Taxonomy, TaxonomyCategory, TaxonomyFeature

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    seed_categories: list[str] = field(default_factory=list)
    discovery_sample_size: int = 50
    discovery_batch_size: int = 10
    max_chars: int = 2000
    concurrency: int = 10
    requests_per_minute: int = 60
    on_progress: Callable[[DocumentResult], None] | None = None
    discovery_context: str | None = None
    canonicalize_context: str | None = None
    classify_context: str | None = None


def _taxonomy_from_raw_pairs(
    raw_pairs: dict[str, list[str]], seed_categories: list[str]
) -> Taxonomy:
    """Cheap local rebuild of a Taxonomy from raw pairs, for prompting only — no LLM call."""
    return Taxonomy(
        categories=[
            TaxonomyCategory(
                name=category,
                is_seed=category in seed_categories,
                features=[
                    TaxonomyFeature(canonical_name=feature, aliases=[feature])
                    for feature in features
                ],
            )
            for category, features in raw_pairs.items()
        ]
    )


class Pipeline:
    def __init__(self, backend: LLMBackend, config: PipelineConfig | None = None) -> None:
        self.backend = backend
        self.config = config or PipelineConfig()

    async def adiscover(self, documents: list[str]) -> Taxonomy:
        sample = documents[: self.config.discovery_sample_size]
        batch_size = self.config.discovery_batch_size
        batches = [sample[i : i + batch_size] for i in range(0, len(sample), batch_size)]

        raw_pairs: dict[str, list[str]] = {}
        accumulated: Taxonomy | None = None
        for batch in batches:
            pairs, complete = await discover_batch(
                batch,
                accumulated,
                self.backend,
                seed_categories=self.config.seed_categories,
                context=self.config.discovery_context,
            )
            for pair in pairs:
                features = raw_pairs.setdefault(pair.category, [])
                if pair.feature not in features:
                    features.append(pair.feature)
            accumulated = _taxonomy_from_raw_pairs(raw_pairs, self.config.seed_categories)
            if complete:
                break

        return await canonicalize(
            raw_pairs,
            self.config.seed_categories,
            self.backend,
            context=self.config.canonicalize_context,
        )

    async def aclassify(
        self,
        documents: list[str | tuple[str | int, str]],
        taxonomy: Taxonomy,
        already_processed: set[str | int] | None = None,
    ) -> list[DocumentResult]:
        already_processed = already_processed or set()
        normalized = _normalize_documents(documents)
        pending = [(doc_id, text) for doc_id, text in normalized if doc_id not in already_processed]

        semaphore = asyncio.Semaphore(self.config.concurrency)
        limiter = AsyncLimiter(self.config.requests_per_minute, 60)

        async def _run_one(doc_id: str | int, text: str) -> DocumentResult:
            async with semaphore, limiter:
                aspects = await classify_document(
                    text,
                    taxonomy,
                    self.backend,
                    max_chars=self.config.max_chars,
                    context=self.config.classify_context,
                )
            return DocumentResult(document_id=doc_id, aspects=aspects)

        outcomes = await asyncio.gather(
            *(_run_one(doc_id, text) for doc_id, text in pending), return_exceptions=True
        )

        results: list[DocumentResult] = []
        for (doc_id, _text), outcome in zip(pending, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                logger.warning("classification failed for document %r: %s", doc_id, outcome)
                continue
            results.append(outcome)
            if self.config.on_progress is not None:
                self.config.on_progress(outcome)

        return results

    async def arun(self, documents: list[str | tuple[str | int, str]]) -> RunResult:
        normalized = _normalize_documents(documents)
        taxonomy = await self.adiscover([text for _, text in normalized])
        results = await self.aclassify(documents, taxonomy)
        stats = {
            "processed": len(results),
            "failed": len(normalized) - len(results),
            "skipped": 0,
        }
        return RunResult(taxonomy=taxonomy, results=results, stats=stats)

    def discover(self, documents: list[str]) -> Taxonomy:
        return asyncio.run(self.adiscover(documents))

    def classify(
        self,
        documents: list[str | tuple[str | int, str]],
        taxonomy: Taxonomy,
        already_processed: set[str | int] | None = None,
    ) -> list[DocumentResult]:
        return asyncio.run(self.aclassify(documents, taxonomy, already_processed))

    def run(self, documents: list[str | tuple[str | int, str]]) -> RunResult:
        return asyncio.run(self.arun(documents))


def _normalize_documents(
    documents: list[str | tuple[str | int, str]],
) -> list[tuple[str | int, str]]:
    return [doc if isinstance(doc, tuple) else (index, doc) for index, doc in enumerate(documents)]
