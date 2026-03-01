"""Unit tests for LaTeX toolchain helpers."""

from __future__ import annotations

from pathlib import Path

from openeinstein.tools import BibEntry, LatexToolchain


def test_generate_bibtex_and_skeleton_files(tmp_path: Path) -> None:
    toolchain = LatexToolchain()

    bib_path = toolchain.generate_bibtex(
        [
            BibEntry(
                key="einstein1915",
                title="Die Feldgleichungen der Gravitation",
                authors=["Albert Einstein"],
                year=1915,
                doi="10.1002/andp.19163540702",
            )
        ],
        output_file=tmp_path / "references.bib",
    )
    assert bib_path.exists()
    text = bib_path.read_text(encoding="utf-8")
    assert "@article{einstein1915" in text
    assert "Albert Einstein" in text

    tex_path = toolchain.generate_skeleton(
        title="Sample",
        author="OpenEinstein",
        abstract="Testing skeleton generation.",
        output_file=tmp_path / "paper.tex",
    )
    assert tex_path.exists()
    tex = tex_path.read_text(encoding="utf-8")
    assert "\\section{Introduction}" in tex
