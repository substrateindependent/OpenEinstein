"""Versioned template registry with backend-specific mappings."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field


_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class BackendTemplate(BaseModel):
    backend: str
    body: str


class ComputeTemplate(BaseModel):
    template_id: str
    version: str
    description: str = ""
    backends: list[BackendTemplate] = Field(default_factory=list)

    def body_for_backend(self, backend: str) -> str:
        for item in self.backends:
            if item.backend == backend:
                return item.body
        raise KeyError(f"Backend '{backend}' not configured for template '{self.template_id}'")


class TemplateDocument(BaseModel):
    template: ComputeTemplate


class TemplateRegistry:
    """Stores validated templates and renders them for target backends."""

    def __init__(self) -> None:
        self._templates: dict[str, ComputeTemplate] = {}

    def register(self, template: ComputeTemplate) -> None:
        for backend in template.backends:
            self.validate_syntax(backend.body)
        self._templates[template.template_id] = template

    def load_directory(self, directory: str | Path) -> int:
        root = Path(directory)
        if not root.exists():
            return 0
        loaded = 0
        for path in sorted([*root.rglob("*.yaml"), *root.rglob("*.yml")]):
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            document = TemplateDocument.model_validate(payload)
            self.register(document.template)
            loaded += 1
        return loaded

    def get(self, template_id: str) -> ComputeTemplate:
        if template_id not in self._templates:
            raise KeyError(f"Unknown template_id: {template_id}")
        return self._templates[template_id]

    def render(
        self,
        *,
        template_id: str,
        backend: str,
        variables: dict[str, Any],
    ) -> str:
        template = self.get(template_id)
        body = template.body_for_backend(backend)
        return self._fill(body, variables)

    def available_backends(self, template_id: str) -> list[str]:
        template = self.get(template_id)
        return [item.backend for item in template.backends]

    @staticmethod
    def validate_syntax(template_body: str) -> None:
        opens = template_body.count("{{")
        closes = template_body.count("}}")
        if opens != closes:
            raise ValueError("Unbalanced template braces")
        # Reject dangling single brace markers.
        if re.search(r"(?<!\{)\{(?!\{)", template_body):
            raise ValueError("Invalid template syntax: single '{' found")
        if re.search(r"(?<!\})\}(?!\})", template_body):
            raise ValueError("Invalid template syntax: single '}' found")

    @staticmethod
    def _fill(template_body: str, variables: dict[str, Any]) -> str:
        missing: list[str] = []

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                missing.append(key)
                return match.group(0)
            return str(variables[key])

        rendered = _PLACEHOLDER_PATTERN.sub(replace, template_body)
        if missing:
            raise KeyError(f"Missing template variables: {', '.join(sorted(set(missing)))}")
        return rendered
