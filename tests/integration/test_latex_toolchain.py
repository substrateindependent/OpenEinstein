"""Integration tests for LaTeX compile/clean workflow and CLI wiring."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from conftest import requires_latex
from openeinstein.cli.main import app
from openeinstein.tools import LatexToolchain


@requires_latex
def test_latex_compile_and_clean_workflow(tmp_path: Path) -> None:
    toolchain = LatexToolchain()
    tex_path = toolchain.generate_skeleton(
        title="OpenEinstein Draft",
        author="OpenEinstein Team",
        abstract="A generated abstract.",
        output_file=tmp_path / "draft.tex",
    )

    result = toolchain.compile(tex_path, timeout_seconds=120)
    assert result.success
    assert result.pdf_path is not None
    assert Path(result.pdf_path).exists()

    cleaned = toolchain.clean(tex_path, timeout_seconds=60)
    assert cleaned


@requires_latex
def test_latex_cli_commands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    skeleton = runner.invoke(
        app,
        [
            "latex",
            "skeleton",
            "--title",
            "CLI Draft",
            "--author",
            "OpenEinstein",
            "--abstract",
            "CLI generated abstract",
            "--output",
            "cli-paper.tex",
        ],
    )
    assert skeleton.exit_code == 0
    assert (tmp_path / "cli-paper.tex").exists()

    entries_path = tmp_path / "entries.json"
    entries_path.write_text(
        json.dumps(
            [
                {
                    "key": "einstein1915",
                    "title": "Field equations",
                    "authors": ["Albert Einstein"],
                    "year": 1915,
                }
            ]
        ),
        encoding="utf-8",
    )

    bib = runner.invoke(
        app,
        ["latex", "bibgen", str(entries_path), "--output", "cli-references.bib"],
    )
    assert bib.exit_code == 0
    assert (tmp_path / "cli-references.bib").exists()

    compile_cmd = runner.invoke(app, ["latex", "compile", "cli-paper.tex"])
    assert compile_cmd.exit_code == 0
    assert (tmp_path / "cli-paper.pdf").exists()

    clean_cmd = runner.invoke(app, ["latex", "clean", "cli-paper.tex"])
    assert clean_cmd.exit_code == 0
