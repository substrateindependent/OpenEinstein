"""Typed models for skill discovery and context assembly."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SkillSource(str, Enum):
    """Origin of a discovered skill, with precedence ordering."""

    bundled = "bundled"
    managed = "managed"
    workspace = "workspace"

    @property
    def precedence_rank(self) -> int:
        """Higher rank wins in precedence resolution."""
        return {"bundled": 0, "managed": 1, "workspace": 2}[self.value]


class SkillMetadata(BaseModel):
    name: str
    description: str
    path: str
    resources: list[str] = Field(default_factory=list)
    version: str | None = None
    source: SkillSource = SkillSource.bundled


class SkillInstructions(BaseModel):
    name: str
    text: str


class SkillResources(BaseModel):
    name: str
    files: list[str] = Field(default_factory=list)


class ContextReport(BaseModel):
    included_files: list[str] = Field(default_factory=list)
    omitted_files: list[str] = Field(default_factory=list)
    truncated_files: list[str] = Field(default_factory=list)
    total_chars: int = 0
    max_total_chars: int


class SkillContextBundle(BaseModel):
    content: str
    report: ContextReport


class PackManifest(BaseModel):
    """Manifest for a campaign pack."""

    name: str
    version: str
    author: str
    license: str
    sha256: str
    description: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    min_platform_version: str | None = None
    tags: list[str] = Field(default_factory=list)
