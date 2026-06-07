import os
from pathlib import Path
from typing import Optional


SKILL_FILENAMES = ("SKILL.md", "skill.md", "skills.md")


class SkillManager:
    def __init__(self, search_paths: Optional[list[Path]] = None):
        self._search_paths = search_paths or self._default_paths()

    def _default_paths(self) -> list[Path]:
        paths: list[Path] = []
        cwd = Path.cwd()
        paths.append(cwd)
        paths.append(cwd / "nokton")
        paths.append(cwd / ".nokton")
        home = Path.home()
        paths.append(home / ".nokton")
        paths.append(home / ".nokton" / "skills")
        env_path = os.environ.get("NOKTON_SKILLS_DIR")
        if env_path:
            paths.append(Path(env_path))
        seen = set()
        unique = []
        for p in paths:
            try:
                rp = p.resolve()
            except Exception:
                rp = p
            if rp not in seen:
                seen.add(rp)
                unique.append(p)
        return unique

    def discover(self) -> list[Path]:
        found = []
        for base in self._search_paths:
            try:
                if not base.exists() or not base.is_dir():
                    continue
            except Exception:
                continue
            for name in SKILL_FILENAMES:
                candidate = base / name
                try:
                    if candidate.is_file():
                        found.append(candidate)
                except Exception:
                    continue
        return found

    def load_all(self) -> str:
        parts: list[str] = []
        for path in self.discover():
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if not content.strip():
                continue
            header = f"## {path.parent.name}/{path.name}"
            parts.append(f"{header}\n{content.strip()}")
        return "\n\n".join(parts)

    def add_search_path(self, path: Path) -> None:
        if path not in self._search_paths:
            self._search_paths.append(path)
