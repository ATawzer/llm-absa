from __future__ import annotations

from llm_absa.discovery import DiscoveredPair, _DiscoveryBatchResult, canonicalize, discover_batch
from llm_absa.models import Taxonomy, TaxonomyCategory, TaxonomyFeature


async def test_discover_batch_returns_pairs_and_completion_flag(mock_backend_factory):
    response = _DiscoveryBatchResult(
        pairs=[DiscoveredPair(category="Performance", feature="load time")],
        taxonomy_complete=False,
    )
    backend = mock_backend_factory([response])

    pairs, complete = await discover_batch(["doc one"], None, backend)

    assert pairs == [DiscoveredPair(category="Performance", feature="load time")]
    assert complete is False


async def test_discover_batch_renders_accumulated_and_seeds(mock_backend_factory):
    response = _DiscoveryBatchResult(pairs=[], taxonomy_complete=True)
    backend = mock_backend_factory([response])
    accumulated = Taxonomy(
        categories=[
            TaxonomyCategory(
                name="Performance",
                is_seed=False,
                features=[TaxonomyFeature(canonical_name="load time", aliases=["load time"])],
            )
        ]
    )

    await discover_batch(["doc one"], accumulated, backend, seed_categories=["Performance"])

    system_prompt = backend.calls[0][0]
    assert "load time" in system_prompt
    assert "Performance" in system_prompt


async def test_discover_batch_omits_seed_bracket_when_no_seeds(mock_backend_factory):
    response = _DiscoveryBatchResult(pairs=[], taxonomy_complete=False)
    backend = mock_backend_factory([response])

    await discover_batch(["doc one"], None, backend)

    system_prompt = backend.calls[0][0]
    assert "[]" not in system_prompt


async def test_canonicalize_returns_taxonomy(mock_backend_factory):
    response = Taxonomy(
        categories=[
            TaxonomyCategory(
                name="Performance",
                is_seed=True,
                features=[
                    TaxonomyFeature(
                        canonical_name="load time", aliases=["load time", "loading speed"]
                    )
                ],
            )
        ]
    )
    backend = mock_backend_factory([response])

    taxonomy = await canonicalize(
        {"Performance": ["load time", "loading speed"]}, ["Performance"], backend
    )

    assert taxonomy == response
    user_prompt = backend.calls[0][1]
    assert "loading speed" in user_prompt
