# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is a simple Major.Minor
scheme: merging a PR bumps the minor version; major version bumps are a deliberate decision.

## [Unreleased]

## [0.1] - 2026-07-02

### Added

- Initial package scaffold (`pyproject.toml`, `src/llm_absa` layout, `uv` dependency management).
- Core Pydantic models: `Aspect`, `Taxonomy`, `TaxonomyCategory`, `TaxonomyFeature`,
  `DocumentResult`, `RunResult`.
- Pre-commit quality gates: ruff (lint + format), mypy, bandit on commit; pytest with a 90%
  coverage gate on push.
