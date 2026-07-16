from __future__ import annotations

from llm_absa.classify import _ClassifyResult, classify_document
from llm_absa.models import Aspect, Taxonomy, TaxonomyCategory, TaxonomyFeature


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


async def test_classify_document_returns_aspects(mock_backend_factory):
    response = _ClassifyResult(
        aspects=[
            Aspect(
                category="Performance",
                feature="load time",
                sentiment="Negative",
                rationale="User complained about slow loading.",
            )
        ]
    )
    backend = mock_backend_factory([response])

    aspects = await classify_document("the app is slow to load", _taxonomy(), backend)

    assert aspects == response.aspects


async def test_classify_document_renders_taxonomy(mock_backend_factory):
    response = _ClassifyResult(aspects=[])
    backend = mock_backend_factory([response])

    await classify_document("doc text", _taxonomy(), backend)

    system_prompt = backend.calls[0][0]
    assert "Performance" in system_prompt
    assert "load time" in system_prompt


async def test_classify_document_renders_context(mock_backend_factory):
    response = _ClassifyResult(aspects=[])
    backend = mock_backend_factory([response])

    await classify_document(
        "doc text", _taxonomy(), backend, context="These are Steam game reviews."
    )

    system_prompt = backend.calls[0][0]
    assert "These are Steam game reviews." in system_prompt


async def test_classify_document_truncates_to_max_chars(mock_backend_factory):
    response = _ClassifyResult(aspects=[])
    backend = mock_backend_factory([response])

    await classify_document("abcdefghij", _taxonomy(), backend, max_chars=5)

    user_prompt = backend.calls[0][1]
    assert "abcde" in user_prompt
    assert "fghij" not in user_prompt
