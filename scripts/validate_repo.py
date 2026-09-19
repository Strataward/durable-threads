"""Validate repository packaging and public documentation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _outside_fenced_code(text: str) -> str:
    """Return Markdown with fenced-code bodies removed but line structure preserved."""

    output: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            output.append("")
            continue
        output.append("" if in_fence else line)
    require(not in_fence, "unclosed Markdown code fence")
    return "\n".join(output)


def _validate_markdown(root: Path) -> None:
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

    for path in sorted(root.rglob("*.md")):
        if any(part in {".git", ".venv", "dist", "node_modules"} for part in path.parts):
            continue

        text = path.read_text(encoding="utf-8")
        visible = _outside_fenced_code(text)
        rel = path.relative_to(root)

        require("[TODO" not in visible, f"unfinished TODO placeholder in {rel}")
        require(
            not re.search(r"(?m)^\s*\$\$\s*$", visible),
            (
                f"unsupported block-math delimiter in {rel}; "
                "use GitHub-safe prose or a supported rendering surface"
            ),
        )

        for raw_target in link_re.findall(visible):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1].strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue

            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            if target.startswith("/"):
                destination = (root / target.lstrip("/")).resolve()
            else:
                destination = (path.parent / target).resolve()
            try:
                destination.relative_to(root.resolve())
            except ValueError as exc:
                message = f"Markdown link escapes repository in {rel}: {raw_target}"
                raise RuntimeError(message) from exc
            require(destination.exists(), f"broken local Markdown link in {rel}: {raw_target}")


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

    skill_result = plugin_root / "skills" / "durable-threads" / "references" / "RESULT.schema.json"
    contracts_result = root / "packages" / "contracts" / "schemas" / "result.schema.json"
    require(
        skill_result.read_text(encoding="utf-8") == contracts_result.read_text(encoding="utf-8"),
        "packages/contracts RESULT schema must match the skill schema",
    )
    require(
        (root / "schemas" / "roster.schema.json").read_text(encoding="utf-8")
        == (root / "packages" / "contracts" / "schemas" / "roster.schema.json").read_text(
            encoding="utf-8"
        ),
        "packages/contracts roster schema must match schemas/roster.schema.json",
    )

    _validate_markdown(root)

    print("repository files and Markdown documentation are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
