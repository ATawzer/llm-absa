# Discovery & canonicalization

Before you can classify documents, you need a taxonomy — the set of categories and features
you're going to sort aspects into. Discovery builds that taxonomy for you from a sample of your
own documents, in two steps:

1. **Discover** — read the documents in batches and pull out every `(category, feature)` pair
   mentioned, e.g. `("Performance", "load time")`. Batches run one after another, each one told
   what's already been found, so later batches only surface genuinely new pairs instead of
   repeating themselves.
2. **Canonicalize** — take everything discovered across all batches and collapse the near-
   duplicates (`"load time"`, `"loading speed"`, `"page load"`) into one canonical taxonomy,
   where each feature has a single name and a list of the raw phrasings that map to it.

The result is a `Taxonomy` you pass into classification. If you already have a fixed taxonomy —
your own category list, or one from a previous run — you don't need this step at all; go
straight to classification with that taxonomy. Discovery exists to give you a reasonable
starting point when you don't have one, built from what's actually in your documents rather than
guessed up front.

Two async functions, in `llm_absa/discovery.py`, do this work.

## `discover_batch`

```python
async def discover_batch(
    documents: list[str],
    accumulated: Taxonomy | None,
    backend: LLMBackend,
    *,
    seed_categories: list[str] | None = None,
) -> tuple[list[DiscoveredPair], bool]: ...
```

Extracts raw `(category, feature)` pairs from one batch of document text.

**Bring:**
- `documents` — plain text, `list[str]`. No ids needed.
- `accumulated` — the `Taxonomy` discovered from earlier batches, so the model only reports
  genuinely new pairs. Pass `None` on the first call.
- `backend` — anything implementing `LLMBackend` (e.g. `GeminiBackend`).
- `seed_categories` — category names to prefer reusing over inventing new ones. Optional.

**Get back:**
- `list[DiscoveredPair]` — the new `(category, feature)` pairs found in this batch.
- `bool` — `taxonomy_complete`, `True` once further batches are unlikely to add anything new.

## `canonicalize`

```python
async def canonicalize(
    raw_pairs: dict[str, list[str]],
    seed_categories: list[str],
    backend: LLMBackend,
) -> Taxonomy: ...
```

Collapses raw pairs — including duplicates and near-duplicates — into a canonical `Taxonomy`.

**Bring:**
- `raw_pairs` — `{category: [raw feature strings]}`, accumulated across all discovery batches.
- `seed_categories` — category names to prefer over inventing new ones.
- `backend` — same as above.

**Get back:**
- A `Taxonomy`: each feature has one canonical name plus every raw alias that maps to it, and
  each category is flagged `is_seed` if it matches a seed category exactly.

## Example

```python
import asyncio

from llm_absa.backend.gemini import GeminiBackend
from llm_absa.discovery import canonicalize, discover_batch
from llm_absa.models import Taxonomy, TaxonomyCategory, TaxonomyFeature

async def discover(documents: list[str], seed_categories: list[str] | None = None) -> Taxonomy:
    backend = GeminiBackend(api_key="...", model="gemini-2.5-flash")
    seed_categories = seed_categories or []
    batch_size = 10

    raw_pairs: dict[str, list[str]] = {}
    accumulated: Taxonomy | None = None

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        pairs, complete = await discover_batch(
            batch, accumulated, backend, seed_categories=seed_categories
        )
        for pair in pairs:
            raw_pairs.setdefault(pair.category, []).append(pair.feature)

        accumulated = Taxonomy(
            categories=[
                TaxonomyCategory(
                    name=category,
                    is_seed=category in seed_categories,
                    features=[
                        TaxonomyFeature(canonical_name=f, aliases=[f]) for f in set(features)
                    ],
                )
                for category, features in raw_pairs.items()
            ]
        )

        if complete:
            break

    return await canonicalize(raw_pairs, seed_categories, backend)

taxonomy = asyncio.run(discover(my_documents, seed_categories=["Performance", "Support"]))
```

## Saving and loading

```python
taxonomy.save("taxonomy.json")
taxonomy = Taxonomy.load("taxonomy.json")
```
