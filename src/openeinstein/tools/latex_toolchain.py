"""LaTeX toolchain helpers for compile, clean, and bibliography generation."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BibEntry(BaseModel):
    key: str = Field(min_length=1)
    title: str
    authors: list[str] = Field(default_factory=list)
    year: str | int | None = None
    doi: str | None = None
    url: str | None = None
    entry_type: str = "article"


class CompileResult(BaseModel):
    success: bool
    pdf_path: str | None = None
    stdout: str = ""
    stderr: str = ""


class LatexToolchain:
    """Wrapper around `latexmk` plus deterministic skeleton/bib generation."""

    def compile(self, tex_file: str | Path, timeout_seconds: float = 120.0) -> CompileResult:
        path = Path(tex_file).resolve()
        completed = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                path.name,
            ],
            cwd=path.parent,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        pdf_path = path.with_suffix(".pdf")
        return CompileResult(
            success=completed.returncode == 0 and pdf_path.exists(),
            pdf_path=str(pdf_path) if pdf_path.exists() else None,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def clean(self, tex_file: str | Path, timeout_seconds: float = 60.0) -> bool:
        path = Path(tex_file).resolve()
        completed = subprocess.run(
            ["latexmk", "-c", path.name],
            cwd=path.parent,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return completed.returncode == 0

    def generate_bibtex(self, entries: list[BibEntry], output_file: str | Path) -> Path:
        output = Path(output_file).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        blocks: list[str] = []
        for entry in entries:
            authors = " and ".join(entry.authors) if entry.authors else "Unknown"
            year = str(entry.year) if entry.year is not None else ""
            doi = entry.doi or ""
            url = entry.url or ""
            block = "\n".join(
                [
                    f"@{entry.entry_type}{{{entry.key},",
                    f"  title = {{{entry.title}}},",
                    f"  author = {{{authors}}},",
                    f"  year = {{{year}}},",
                    f"  doi = {{{doi}}},",
                    f"  url = {{{url}}},",
                    "}",
                ]
            )
            blocks.append(block)

        output.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
        return output

    def generate_skeleton(
        self,
        *,
        title: str,
        author: str,
        abstract: str,
        output_file: str | Path,
    ) -> Path:
        output = Path(output_file).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(
            [
                r"\documentclass[11pt]{article}",
                r"\usepackage[T1]{fontenc}",
                r"\usepackage{lmodern}",
                r"\usepackage{geometry}",
                r"\geometry{margin=1in}",
                r"\usepackage{hyperref}",
                "",
                rf"\title{{{title}}}",
                rf"\author{{{author}}}",
                r"\date{\today}",
                "",
                r"\begin{document}",
                r"\maketitle",
                r"\begin{abstract}",
                abstract,
                r"\end{abstract}",
                "",
                r"\section{Introduction}",
                "TODO: Introduce the research question and motivation.",
                "",
                r"\section{Methods}",
                "TODO: Describe methods and assumptions.",
                "",
                r"\section{Results}",
                "TODO: Present key findings and tables/figures.",
                "",
                r"\section{Discussion}",
                "TODO: Discuss implications, limitations, and next steps.",
                "",
                r"\end{document}",
                "",
            ]
        )
        output.write_text(content, encoding="utf-8")
        return output

    @staticmethod
    def entries_from_payload(payload: list[dict[str, Any]]) -> list[BibEntry]:
        return [BibEntry.model_validate(item) for item in payload]
