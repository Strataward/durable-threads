"""Build a source archive without including local state."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist"}


def build(root: Path, output: Path) -> Path:
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    name = manifest["name"]
    version = manifest["version"]
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            if path == archive:
                continue
            handle.write(path, Path(name) / path.relative_to(root))
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    archive = build(Path(__file__).parents[1], args.output)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
