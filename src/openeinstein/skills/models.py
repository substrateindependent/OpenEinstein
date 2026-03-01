"""Typed models for skill discovery and context assembly."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    name: str
    description: str
    path: str
    resources: list[str] = Field(default_factory=list)


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
