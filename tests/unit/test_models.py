from llm_absa.models import (
    Aspect,
    DocumentResult,
    RunResult,
    Taxonomy,
    TaxonomyCategory,
    TaxonomyFeature,
)


def make_taxonomy() -> Taxonomy:
    return Taxonomy(
        categories=[
            TaxonomyCategory(
                name="Performance",
                is_seed=True,
                features=[
                    TaxonomyFeature(canonical_name="Load Times", aliases=["loading", "load speed"]),
                    TaxonomyFeature(canonical_name="Frame Rate", aliases=["fps", "framerate"]),
                ],
            ),
            TaxonomyCategory(
                name="Story",
                is_seed=False,
                features=[
                    TaxonomyFeature(canonical_name="Plot", aliases=["narrative"]),
                ],
            ),
        ]
    )


def test_aspect_json_roundtrip():
    aspect = Aspect(
        category="Performance",
        feature="Frame Rate",
        sentiment="Negative",
        rationale="Frequent stuttering during combat.",
    )
    assert Aspect.model_validate_json(aspect.model_dump_json()) == aspect


def test_taxonomy_json_roundtrip():
    taxonomy = make_taxonomy()
    assert Taxonomy.model_validate_json(taxonomy.model_dump_json()) == taxonomy


def test_taxonomy_to_dict():
    taxonomy = make_taxonomy()
    assert taxonomy.to_dict() == {
        "Performance": ["Load Times", "Frame Rate"],
        "Story": ["Plot"],
    }


def test_taxonomy_save_load_roundtrip(tmp_path):
    taxonomy = make_taxonomy()
    path = tmp_path / "taxonomy.json"

    taxonomy.save(path)
    loaded = Taxonomy.load(path)

    assert loaded == taxonomy


def test_document_result_json_roundtrip():
    result = DocumentResult(
        document_id="doc-1",
        aspects=[
            Aspect(
                category="Performance",
                feature="Load Times",
                sentiment="Positive",
                rationale="Loads in under a second.",
            )
        ],
    )
    assert DocumentResult.model_validate_json(result.model_dump_json()) == result


def test_run_result_json_roundtrip():
    run_result = RunResult(
        taxonomy=make_taxonomy(),
        results=[DocumentResult(document_id=1, aspects=[])],
        stats={"processed": 1, "skipped": 0, "failed": 0},
    )
    assert RunResult.model_validate_json(run_result.model_dump_json()) == run_result
