# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is a simple Major.Minor
scheme: merging a PR bumps the minor version; major version bumps are a deliberate decision.

## [Unreleased]

### Added

- `classify_document` (`llm_absa/classify.py`) — extracts aspects for a single document,
  constrained to a canonical `Taxonomy`, with `max_chars` truncation.
- `classify` Jinja2 prompt templates under `llm_absa/prompts/classify/`, completing the set of
  six templates (discovery, canonicalization, classification).

## [0.4] - 2026-07-08

### Added

- `discover_batch` and `canonicalize` (`llm_absa/discovery.py`) — sequential per-batch
  `(category, feature)` pair extraction, accumulated against prior batches, collapsed into a
  canonical `Taxonomy` via a final canonicalization pass.
- Jinja2 prompt templates for discovery and canonicalization under `llm_absa/prompts/`, rendered
  through a shared environment helper (`llm_absa/prompts/__init__.py`).
- `docs/discovery.md` documenting the discovery pipeline and a worked example.

### Fixed

- Integration tests read `GEMINI_API_KEY` instead of `GOOGLE_API_KEY`, matching the env var the
  maintainer actually sets (`google-genai` supports both, preferring `GOOGLE_API_KEY` if both are
  present).

## [0.3] - 2026-07-04

### Added

- `LLMBackend` Protocol (`llm_absa/backend/protocol.py`) — provider-agnostic
  async/sync interface for structured-output LLM calls.
- `GeminiBackend` and `RetryConfig` (`llm_absa/backend/gemini.py`) — Gemini
  implementation using native `response_schema` structured output, with
  tenacity-based retry scoped to rate-limit (429) errors only.
- `MockBackend` fixture in `tests/conftest.py` for network-free unit testing
  of downstream pipeline logic.

## [0.2] - 2026-07-04

### Changed

- Flattened package layout from `src/llm_absa` to a top-level `llm_absa` package; updated
  hatchling and coverage config accordingly.

### Fixed

- Corrected pre-commit's `mypy` and `bandit` hook entries, which still referenced the old
  `src` path.

## [0.1] - 2026-07-02

### Added

- Initial package scaffold (`pyproject.toml`, `src/llm_absa` layout, `uv` dependency management).
- Core Pydantic models: `Aspect`, `Taxonomy`, `TaxonomyCategory`, `TaxonomyFeature`,
  `DocumentResult`, `RunResult`.
- Pre-commit quality gates: ruff (lint + format), mypy, bandit on commit; pytest with a 90%
  coverage gate on push.
