from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from llm_absa.classify import _ClassifyResult
from llm_absa.discovery import DiscoveredPair, _DiscoveryBatchResult
from llm_absa.models import DocumentResult, Taxonomy, TaxonomyCategory, TaxonomyFeature
from llm_absa.pipeline import Pipeline, PipelineConfig


def _taxonomy() -> Taxonomy:
    return Taxonomy(
        categories=[
            TaxonomyCategory(
                name="Performance",
                is_seed=True,
                features=[TaxonomyFeature(canonical_name="load time", aliases=["load time"])],
            )
        ]
    )


@dataclass
class KeyedBackend:
    """LLMBackend stand-in that dispatches by a substring found in the user prompt.

    Order-independent, unlike MockBackend, so it's safe against concurrent aclassify calls.
    """

    by_marker: dict[str, object]
    calls: list[tuple[str, str, type]] = field(default_factory=list)

    async def agenerate(self, system, user, schema):
        self.calls.append((system, user, schema))
        for marker, outcome in self.by_marker.items():
            if marker in user:
                if isinstance(outcome, BaseException):
                    raise outcome
                assert isinstance(outcome, schema)
                return outcome
        raise AssertionError(f"no response configured for prompt: {user!r}")

    def generate(self, system, user, schema):
        return asyncio.run(self.agenerate(system, user, schema))


async def test_adiscover_batches_sequentially_and_canonicalizes(mock_backend_factory):
    batch1 = _DiscoveryBatchResult(
        pairs=[DiscoveredPair(category="Performance", feature="load time")],
        taxonomy_complete=False,
    )
    batch2 = _DiscoveryBatchResult(
        pairs=[DiscoveredPair(category="Performance", feature="crash rate")],
        taxonomy_complete=False,
    )
    final_taxonomy = _taxonomy()
    backend = mock_backend_factory([batch1, batch2, final_taxonomy])
    pipeline = Pipeline(backend, PipelineConfig(discovery_batch_size=1, discovery_sample_size=2))

    taxonomy = await pipeline.adiscover(["doc one", "doc two"])

    assert taxonomy == final_taxonomy
    assert len(backend.calls) == 3
    assert "load time" in backend.calls[1][0]


async def test_adiscover_stops_early_on_taxonomy_complete(mock_backend_factory):
    batch1 = _DiscoveryBatchResult(
        pairs=[DiscoveredPair(category="Performance", feature="load time")],
        taxonomy_complete=True,
    )
    final_taxonomy = _taxonomy()
    backend = mock_backend_factory([batch1, final_taxonomy])
    pipeline = Pipeline(backend, PipelineConfig(discovery_batch_size=1, discovery_sample_size=3))

    await pipeline.adiscover(["doc one", "doc two", "doc three"])

    assert len(backend.calls) == 2


async def test_adiscover_only_samples_discovery_sample_size(mock_backend_factory):
    batch = _DiscoveryBatchResult(pairs=[], taxonomy_complete=False)
    final_taxonomy = Taxonomy(categories=[])
    backend = mock_backend_factory([batch, final_taxonomy])
    pipeline = Pipeline(backend, PipelineConfig(discovery_batch_size=5, discovery_sample_size=1))

    await pipeline.adiscover(["doc one", "doc two", "doc three"])

    assert len(backend.calls) == 2
    assert "doc two" not in backend.calls[0][1]


async def test_adiscover_threads_context_per_stage(mock_backend_factory):
    batch = _DiscoveryBatchResult(pairs=[], taxonomy_complete=True)
    final_taxonomy = _taxonomy()
    backend = mock_backend_factory([batch, final_taxonomy])
    pipeline = Pipeline(
        backend,
        PipelineConfig(
            discovery_context="discovery instructions",
            canonicalize_context="canonicalize instructions",
        ),
    )

    await pipeline.adiscover(["doc one"])

    discover_system, canonicalize_system = backend.calls[0][0], backend.calls[1][0]
    assert "discovery instructions" in discover_system
    assert "canonicalize instructions" not in discover_system
    assert "canonicalize instructions" in canonicalize_system
    assert "discovery instructions" not in canonicalize_system


async def test_aclassify_threads_classify_context():
    response = _ClassifyResult(aspects=[])
    backend = KeyedBackend({"doc one": response})
    pipeline = Pipeline(backend, PipelineConfig(classify_context="classify instructions"))

    await pipeline.aclassify(["doc one"], _taxonomy())

    assert "classify instructions" in backend.calls[0][0]


async def test_aclassify_returns_results_for_all_documents():
    response = _ClassifyResult(aspects=[])
    backend = KeyedBackend({"doc one": response, "doc two": response})
    pipeline = Pipeline(backend)

    results = await pipeline.aclassify(["doc one", "doc two"], _taxonomy())

    assert {r.document_id for r in results} == {0, 1}


async def test_aclassify_skips_already_processed():
    response = _ClassifyResult(aspects=[])
    backend = KeyedBackend({"doc two": response})
    pipeline = Pipeline(backend)

    results = await pipeline.aclassify(
        [("a", "doc one"), ("b", "doc two")], _taxonomy(), already_processed={"a"}
    )

    assert [r.document_id for r in results] == ["b"]
    assert len(backend.calls) == 1


async def test_aclassify_isolates_failures():
    ok = _ClassifyResult(aspects=[])
    backend = KeyedBackend({"good doc": ok, "bad doc": RuntimeError("boom")})
    pipeline = Pipeline(backend)

    results = await pipeline.aclassify([("good", "good doc"), ("bad", "bad doc")], _taxonomy())

    assert [r.document_id for r in results] == ["good"]


async def test_aclassify_calls_on_progress_per_document():
    response = _ClassifyResult(aspects=[])
    backend = KeyedBackend({"doc one": response})
    seen: list[DocumentResult] = []
    pipeline = Pipeline(backend, PipelineConfig(on_progress=seen.append))

    await pipeline.aclassify(["doc one"], _taxonomy())

    assert len(seen) == 1
    assert seen[0].document_id == 0


async def test_arun_shape_and_stats(mock_backend_factory):
    batch = _DiscoveryBatchResult(
        pairs=[DiscoveredPair(category="Performance", feature="load time")],
        taxonomy_complete=True,
    )
    taxonomy = _taxonomy()
    classify_response = _ClassifyResult(aspects=[])
    backend = mock_backend_factory([batch, taxonomy, classify_response, classify_response])
    pipeline = Pipeline(backend, PipelineConfig(discovery_sample_size=2, discovery_batch_size=2))

    result = await pipeline.arun(["doc one", "doc two"])

    assert result.taxonomy == taxonomy
    assert result.stats == {"processed": 2, "failed": 0, "skipped": 0}
    assert {r.document_id for r in result.results} == {0, 1}


def test_discover_sync_wrapper(mock_backend_factory):
    batch = _DiscoveryBatchResult(pairs=[], taxonomy_complete=True)
    taxonomy = Taxonomy(categories=[])
    backend = mock_backend_factory([batch, taxonomy])

    result = Pipeline(backend).discover(["only doc"])

    assert result == taxonomy


def test_classify_sync_wrapper():
    response = _ClassifyResult(aspects=[])
    backend = KeyedBackend({"doc one": response})

    results = Pipeline(backend).classify(["doc one"], _taxonomy())

    assert [r.document_id for r in results] == [0]


def test_run_sync_wrapper(mock_backend_factory):
    batch = _DiscoveryBatchResult(pairs=[], taxonomy_complete=True)
    taxonomy = Taxonomy(categories=[])
    classify_response = _ClassifyResult(aspects=[])
    backend = mock_backend_factory([batch, taxonomy, classify_response])

    result = Pipeline(backend).run(["only doc"])

    assert result.taxonomy == taxonomy
    assert result.stats["processed"] == 1
