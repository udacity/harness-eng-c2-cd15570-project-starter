"""Progressive-disclosure skill catalog."""

from __future__ import annotations

from pathlib import Path


class SkillCatalog:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir

    def discover(self) -> dict[str, str]:
        skills: dict[str, str] = {}
        if not self.skills_dir.exists():
            return skills

        for skill_dir in sorted(self.skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.exists():
                continue

            name = skill_dir.name
            description = "No description."
            in_frontmatter = False
            for line in skill_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped == "---":
                    in_frontmatter = not in_frontmatter
                elif in_frontmatter and stripped.startswith("name:"):
                    name = stripped.split(":", 1)[1].strip()
                elif in_frontmatter and stripped.startswith("description:"):
                    description = stripped.split(":", 1)[1].strip()
            skills[name] = description
        return skills

    def load(self, name: str) -> tuple[str, str] | None:
        registry = self.discover()
        if name not in registry:
            return None
        content = (self.skills_dir / name / "SKILL.md").read_text(encoding="utf-8")
        return registry[name], content
