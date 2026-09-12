"""Validate repository packaging and zero-config distribution files."""

from __future__ import annotations

import json
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    root = Path(__file__).parents[1]
    plugin_root = root / "plugins" / "durable-threads"
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    skill = plugin_root / "skills" / "durable-threads" / "SKILL.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))

    require(
        bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["name"])),
        "invalid plugin name",
    )
    require(manifest["name"] == "durable-threads", "unexpected plugin name")
    require(manifest["license"] == "Apache-2.0", "plugin must use Apache-2.0")
    require(manifest.get("skills") == "./skills/", "plugin must bundle the canonical skills path")
    require(
        bool(re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])),
        "plugin version must be strict semver",
    )

    entries = marketplace.get("plugins", [])
    entry = next((item for item in entries if item.get("name") == "durable-threads"), None)
    require(entry is not None, "marketplace must expose durable-threads")
    require(
        entry.get("source") == {"source": "local", "path": "./plugins/durable-threads"},
        "marketplace source must point at the canonical plugin root",
    )
    policy = entry.get("policy", {})
    require(policy.get("installation") == "AVAILABLE", "plugin must be available")
    require(policy.get("authentication") in {"ON_INSTALL", "ON_USE"}, "invalid auth policy")

    content = skill.read_text(encoding="utf-8")
    require(content.startswith("---\n"), "skill has no YAML frontmatter")
    require("name: durable-threads" in content, "skill name is missing")
    require("description:" in content, "skill description is missing")
    require("[TODO" not in content, "skill has an unfinished placeholder")

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    require(match is not None, "pyproject version is missing")
    require(match.group(1) == manifest["version"], "package and plugin versions must match")

    readme = (root / "README.md").read_text(encoding="utf-8")
    require("npx skills add" not in readme, "README contains obsolete parallel skill install")
    require("codex plugin marketplace add" in readme, "README is missing canonical install")

    for path in (root / "examples").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    for path in plugin_root.rglob("*.schema.json"):
        json.loads(path.read_text(encoding="utf-8"))

    print("repository files are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
