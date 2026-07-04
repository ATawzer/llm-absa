"""Typed data models for the llm-absa pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class Aspect(BaseModel):
    category: str
    feature: str
    sentiment: Literal["Positive", "Negative", "Mixed", "Neutral"]
    rationale: str


class TaxonomyFeature(BaseModel):
    canonical_name: str
    aliases: list[str]


class TaxonomyCategory(BaseModel):
    name: str
    is_seed: bool
    features: list[TaxonomyFeature]


class Taxonomy(BaseModel):
    categories: list[TaxonomyCategory]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            category.name: [feature.canonical_name for feature in category.features]
            for category in self.categories
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: str | Path) -> Taxonomy:
        return cls.model_validate(json.loads(Path(path).read_text()))


class DocumentResult(BaseModel):
    document_id: str | int
    aspects: list[Aspect]


class RunResult(BaseModel):
    taxonomy: Taxonomy
    results: list[DocumentResult]
    stats: dict[str, int]
