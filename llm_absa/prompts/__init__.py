"""Shared Jinja2 environment for rendering prompt templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Templates render plain-text LLM prompts, not HTML; escaping would corrupt document text.
_env = Environment(loader=FileSystemLoader(Path(__file__).parent), autoescape=False)  # nosec B701


def render(template_name: str, **context: object) -> str:
    return _env.get_template(template_name).render(**context)
