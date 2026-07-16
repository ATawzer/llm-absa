# Pipeline

`Pipeline` ties discovery and classification together into one object: build a taxonomy from a
sample of your documents, then classify the full corpus into it. It's async-first — every
method has an `a`-prefixed coroutine and a synchronous wrapper that runs it with `asyncio.run`.

```python
from llm_absa.backend.gemini import GeminiBackend
from llm_absa.pipeline import Pipeline, PipelineConfig

backend = GeminiBackend(api_key="...", model="gemini-2.5-flash")
pipeline = Pipeline(backend, PipelineConfig(seed_categories=["Performance", "Support"]))

result = pipeline.run(documents)
```

`documents` is a `list[str]`, or a `list[tuple[str | int, str]]` if you want to supply your own
document ids — plain strings are auto-assigned an id equal to their index in the list.

## `PipelineConfig`

```python
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
```

- `seed_categories` — category names discovery should prefer reusing over inventing new ones.
- `discovery_sample_size` — how many documents discovery samples from the corpus. It doesn't need
  to see every document to find a representative taxonomy.
- `discovery_batch_size` — how many of those sampled documents go into each discovery call.
- `max_chars` — documents are truncated to this length before being sent to classification.
- `concurrency` — max simultaneous in-flight `classify` calls.
- `requests_per_minute` — a hard cap on classification call rate, independent of `concurrency`.
- `on_progress` — called with each document's `DocumentResult` as soon as it finishes classifying,
  in whatever order results land — useful for progress bars or persisting results incrementally.
- `discovery_context` / `canonicalize_context` / `classify_context` — free text spliced as-is into
  that stage's system prompt. Each is independent, so you can set one, all three, or none — use
  them to describe the corpus ("these are Steam game reviews") or give direct instructions
  ("ignore mentions of price").

## `adiscover` / `discover`

```python
async def adiscover(self, documents: list[str]) -> Taxonomy: ...
def discover(self, documents: list[str]) -> Taxonomy: ...
```

Runs discovery end to end: samples `discovery_sample_size` documents, splits them into batches of
`discovery_batch_size`, and calls `discover_batch` on each in sequence — each batch is told what
the previous batches already found, so later batches only surface genuinely new pairs. Discovery
stops early if a batch reports the taxonomy is complete. The accumulated raw pairs are then
collapsed into a canonical `Taxonomy` via `canonicalize`.

Batches run sequentially, not concurrently — each one depends on the accumulated taxonomy from
the one before it.

## `aclassify` / `classify`

```python
async def aclassify(
    self,
    documents: list[str | tuple[str | int, str]],
    taxonomy: Taxonomy,
    already_processed: set[str | int] | None = None,
) -> list[DocumentResult]: ...
```

Classifies every document against `taxonomy`, skipping any document whose id is in
`already_processed`. Unlike discovery, classification calls have no dependency on each other, so
they run concurrently — bounded by `concurrency` and `requests_per_minute` from `PipelineConfig` —
via `asyncio.gather`.

A single document failing (a schema parse error, an exhausted retry) doesn't take down the batch:
failures are caught, logged, and excluded from the returned results rather than raised. If you
need to know how many failed, use `arun`/`run`, which reports it in `RunResult.stats["failed"]`.

## `arun` / `run`

```python
async def arun(self, documents: list[str | tuple[str | int, str]]) -> RunResult: ...
```

Runs discovery followed by classification over the same document set and returns a `RunResult`:

```python
class RunResult(BaseModel):
    taxonomy: Taxonomy
    results: list[DocumentResult]
    stats: dict[str, int]  # processed / skipped / failed
```

Use this when you don't already have a taxonomy. If you do — your own category list, or one
saved from a previous `discover()` call — skip straight to `classify()` with it instead of paying
for discovery again.

## Example

```python
import asyncio

from llm_absa.backend.gemini import GeminiBackend
from llm_absa.pipeline import Pipeline, PipelineConfig

async def main() -> None:
    backend = GeminiBackend(api_key="...", model="gemini-2.5-flash")
    pipeline = Pipeline(
        backend,
        PipelineConfig(
            seed_categories=["Performance", "Support"],
            concurrency=5,
            requests_per_minute=30,
            on_progress=lambda r: print(f"done: {r.document_id} ({len(r.aspects)} aspects)"),
            discovery_context="These are Steam game reviews.",
            classify_context="These are Steam game reviews.",
        ),
    )

    result = await pipeline.arun(reviews)  # list[str] or list[tuple[id, str]]

    print(result.stats)
    result.taxonomy.save("taxonomy.json")

asyncio.run(main())
```

Or without async, for scripts that don't need it:

```python
pipeline = Pipeline(backend, PipelineConfig(seed_categories=["Performance", "Support"]))
taxonomy = pipeline.discover(reviews)
results = pipeline.classify(reviews, taxonomy)
```
