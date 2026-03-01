"""Unit tests for template registry validation and rendering."""

from __future__ import annotations

import pytest

from openeinstein.campaigns import BackendTemplate, ComputeTemplate, TemplateRegistry


def test_template_registry_placeholder_fill_and_backend_mapping() -> None:
    registry = TemplateRegistry()
    registry.register(
        ComputeTemplate(
            template_id="kinetic",
            version="1.0.0",
            description="Kinetic template",
            backends=[
                BackendTemplate(backend="sympy", body="f({{x}}) + {{y}}"),
                BackendTemplate(backend="mathematica", body="f[{{x}}] + {{y}}"),
            ],
        )
    )

    sympy_rendered = registry.render(
        template_id="kinetic",
        backend="sympy",
        variables={"x": 2, "y": 3},
    )
    math_rendered = registry.render(
        template_id="kinetic",
        backend="mathematica",
        variables={"x": 2, "y": 3},
    )
    assert sympy_rendered == "f(2) + 3"
    assert math_rendered == "f[2] + 3"
    assert registry.available_backends("kinetic") == ["sympy", "mathematica"]


def test_template_syntax_validation_and_missing_variables() -> None:
    registry = TemplateRegistry()
    with pytest.raises(ValueError):
        registry.register(
            ComputeTemplate(
                template_id="bad",
                version="1.0.0",
                backends=[BackendTemplate(backend="sympy", body="f({{x}) + {{y}}")],
            )
        )

    registry.register(
        ComputeTemplate(
            template_id="ok",
            version="1.0.0",
            backends=[BackendTemplate(backend="sympy", body="f({{x}}) + {{y}}")],
        )
    )
    with pytest.raises(KeyError):
        registry.render(template_id="ok", backend="sympy", variables={"x": 1})
