"""Validate the repository files that do not need third-party tooling."""

from __future__ import annotations

import json
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    root = Path(__file__).parents[1]
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    require(
        bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["name"])), "invalid plugin name"
    )
    require(manifest["license"] == "Apache-2.0", "plugin must use Apache-2.0")
    skill = root / "skills" / "codex-thread-loom" / "SKILL.md"
    content = skill.read_text(encoding="utf-8")
    require(content.startswith("---\n"), "skill has no YAML frontmatter")
    require("name: codex-thread-loom" in content, "skill name is missing")
    require("description:" in content, "skill description is missing")
    require("[TODO" not in content, "skill has an unfinished placeholder")
    for path in (root / "examples").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    print("repository files are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
