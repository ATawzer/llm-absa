# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is a simple Major.Minor
scheme: merging a PR bumps the minor version; major version bumps are a deliberate decision.

## [Unreleased]

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
