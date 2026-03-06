"""Skill registry exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openeinstein.skills.models import (
    ContextReport,
    PackManifest,
    SkillContextBundle,
    SkillInstructions,
    SkillMetadata,
    SkillResources,
    SkillSource,
)
from openeinstein.skills.registry import SkillRegistry
from openeinstein.skills.versioning import (
    is_compatible,
    parse_version,
    version_satisfies_constraint,
)

if TYPE_CHECKING:
    from openeinstein.skills.installer import PackInstaller

__all__ = [
    "ContextReport",
    "PackInstaller",
    "PackManifest",
    "SkillContextBundle",
    "SkillInstructions",
    "SkillMetadata",
    "SkillRegistry",
    "SkillResources",
    "SkillSource",
    "is_compatible",
    "parse_version",
    "version_satisfies_constraint",
]


def __getattr__(name: str) -> object:
    if name == "PackInstaller":
        from openeinstein.skills.installer import PackInstaller

        return PackInstaller
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
