"""Skill discovery and progressive context loading."""

from __future__ import annotations

from pathlib import Path

from openeinstein.skills.models import (
    ContextReport,
    SkillContextBundle,
    SkillInstructions,
    SkillMetadata,
)


class SkillRegistry:
    """Discovers skills and builds bounded context bundles."""

    def __init__(
        self,
        roots: list[str | Path],
        *,
        max_chars_per_file: int = 4000,
        max_total_chars: int = 12000,
    ) -> None:
        self._roots = [Path(root) for root in roots]
        self._max_chars_per_file = max_chars_per_file
        self._max_total_chars = max_total_chars

    def discover_skills(self) -> dict[str, SkillMetadata]:
        discovered: dict[str, SkillMetadata] = {}
        for root in self._roots:
            if not root.exists():
                continue
            for skill_file in root.rglob("SKILL.md"):
                name = skill_file.parent.name
                text = skill_file.read_text(encoding="utf-8")
                description = self._extract_description(text)
                discovered[name] = SkillMetadata(
                    name=name,
                    description=description,
                    path=str(skill_file),
                    resources=[],
                )
        return dict(sorted(discovered.items()))

    def load_instructions(self, skill_name: str) -> SkillInstructions:
        discovered = self.discover_skills()
        if skill_name not in discovered:
            raise KeyError(f"Unknown skill: {skill_name}")
        path = Path(discovered[skill_name].path)
        text = path.read_text(encoding="utf-8")
        return SkillInstructions(name=skill_name, text=text)

    def build_context(self, skill_names: list[str]) -> SkillContextBundle:
        discovered = self.discover_skills()
        sections: list[str] = []
        included_files: list[str] = []
        omitted_files: list[str] = []
        truncated_files: list[str] = []
        used_chars = 0

        for skill_name in skill_names:
            if skill_name not in discovered:
                omitted_files.append(skill_name)
                continue
            metadata = discovered[skill_name]
            path = Path(metadata.path)
            text = path.read_text(encoding="utf-8")

            if len(text) > self._max_chars_per_file:
                text = text[: self._max_chars_per_file]
                truncated_files.append(str(path))

            section = f"## Skill: {skill_name}\n{text}\n"
            if used_chars + len(section) > self._max_total_chars:
                omitted_files.append(str(path))
                continue

            sections.append(section)
            included_files.append(str(path))
            used_chars += len(section)

        content = "\n".join(sections)
        report = ContextReport(
            included_files=included_files,
            omitted_files=omitted_files,
            truncated_files=truncated_files,
            total_chars=len(content),
            max_total_chars=self._max_total_chars,
        )
        return SkillContextBundle(content=content, report=report)

    @staticmethod
    def _extract_description(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            return stripped[:120]
        return "No description provided"
