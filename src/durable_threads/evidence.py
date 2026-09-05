"""Parse and verify compact worker evidence before integration."""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EvidenceError(ValueError):
    """Raised when worker evidence cannot support integration."""


@dataclass(frozen=True)
class WorkerEvidence:
    """The small result contract that the planner can inspect."""

    status: str
    provider: str | None
    changed_paths: tuple[str, ...]
    checks: tuple[str, ...]
    concerns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "changedPaths": list(self.changed_paths),
            "checks": list(self.checks),
            "remainingConcerns": list(self.concerns),
        }


_STATUS = {"complete", "blocked", "failed"}
_HEADINGS = re.compile(
    r"^(Status|Provider|Changed paths|Checks|Remaining concerns):\s*(.*)$",
    re.IGNORECASE,
)
_JSON_KEYS = {
    "status",
    "provider",
    "changedPaths",
    "changed_paths",
    "checks",
    "remainingConcerns",
    "remaining_concerns",
    "concerns",
}


def _values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list | tuple):
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return ()


def _json_payload(text: str) -> dict[str, Any] | None:
    candidates: list[Any] = []
    for line in reversed(text.splitlines()):
        try:
            candidates.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    try:
        candidates.append(json.loads(text))
    except json.JSONDecodeError:
        pass
    for candidate in candidates:
        if isinstance(candidate, dict) and _JSON_KEYS.intersection(candidate):
            return candidate
    return None


def _section_values(text: str, heading: str) -> tuple[str, ...]:
    lines = text.splitlines()
    values: list[str] = []
    active = False
    for line in lines:
        match = _HEADINGS.match(line.strip())
        if match:
            active = match.group(1).casefold() == heading.casefold()
            if active and match.group(2).strip():
                values.append(match.group(2).strip().lstrip("- "))
            continue
        if active and line.strip():
            values.append(line.strip().lstrip("- ").strip())
    return tuple(value for value in values if value)


def parse_worker_result(text: str) -> WorkerEvidence:
    """Parse JSON or the documented plain-text evidence contract."""

    if not isinstance(text, str) or not text.strip():
        raise EvidenceError("worker result is empty")
    payload = _json_payload(text)
    if payload:
        status = str(payload.get("status", "")).strip().casefold()
        provider_value = payload.get("provider")
        provider = provider_value.strip() if isinstance(provider_value, str) else None
        changed = _values(payload.get("changedPaths", payload.get("changed_paths")))
        checks = _values(payload.get("checks"))
        concerns = _values(
            payload.get(
                "remainingConcerns",
                payload.get("remaining_concerns", payload.get("concerns")),
            )
        )
    else:
        status_match = re.search(r"^Status:\s*(\S+)", text, re.IGNORECASE | re.MULTILINE)
        provider_match = re.search(r"^Provider:\s*(\S+)", text, re.IGNORECASE | re.MULTILINE)
        status = status_match.group(1).strip().casefold() if status_match else ""
        provider = provider_match.group(1).strip() if provider_match else None
        changed = _section_values(text, "Changed paths")
        checks = _section_values(text, "Checks")
        concerns = _section_values(text, "Remaining concerns")
    if status not in _STATUS:
        raise EvidenceError("worker result must declare status: complete, blocked, or failed")
    return WorkerEvidence(
        status=status,
        provider=provider,
        changed_paths=changed,
        checks=checks,
        concerns=concerns,
    )


def _path_matches(path: str, allowed: str) -> bool:
    path = path.replace("\\", "/")
    allowed = allowed.replace("\\", "/").rstrip("/")
    return path == allowed or path.startswith(f"{allowed}/") or fnmatch.fnmatchcase(path, allowed)


def _validate_paths(paths: Iterable[str], allowed_paths: Iterable[str]) -> tuple[str, ...]:
    allowed = tuple(item.strip() for item in allowed_paths if item.strip())
    if not allowed:
        raise EvidenceError("at least one allowed path is required")
    clean: list[str] = []
    for raw_path in paths:
        path = raw_path.replace("\\", "/").strip()
        if not path or path.startswith("/") or path == "." or ".." in path.split("/"):
            raise EvidenceError(f"changed path is unsafe: {raw_path!r}")
        if not any(_path_matches(path, item) for item in allowed):
            raise EvidenceError(f"changed path is outside the allowed paths: {path}")
        if path not in clean:
            clean.append(path)
    return tuple(clean)


def validate_evidence(
    evidence: WorkerEvidence,
    *,
    allowed_paths: Iterable[str],
    actual_paths: Iterable[str] | None = None,
) -> WorkerEvidence:
    """Validate status, paths, checks, and optionally the exact working-tree diff."""

    if evidence.provider not in {"codex", "claude", "grok", "cursor"}:
        raise EvidenceError("worker result must declare a provider")
    changed = _validate_paths(evidence.changed_paths, allowed_paths)
    if evidence.status == "complete" and not evidence.checks:
        raise EvidenceError("complete worker result must include exact checks")
    if evidence.status == "complete" and not evidence.concerns:
        raise EvidenceError("complete worker result must declare remaining concerns")
    if evidence.status == "complete" and any(
        re.search(r"\b(failed|skipped|not run)\b", check, re.IGNORECASE)
        for check in evidence.checks
    ):
        raise EvidenceError("complete result contains an unsuccessful check")
    if actual_paths is not None:
        actual = tuple(
            dict.fromkeys(path.replace("\\", "/").strip() for path in actual_paths if path)
        )
        _validate_paths(actual, allowed_paths)
        if set(changed) != set(actual):
            missing = sorted(set(actual) - set(changed))
            extra = sorted(set(changed) - set(actual))
            details = []
            if missing:
                details.append(f"missing claims: {', '.join(missing)}")
            if extra:
                details.append(f"claims without diff: {', '.join(extra)}")
            raise EvidenceError(
                "worker paths do not match the actual diff (" + "; ".join(details) + ")"
            )
    return WorkerEvidence(
        status=evidence.status,
        provider=evidence.provider,
        changed_paths=changed,
        checks=evidence.checks,
        concerns=evidence.concerns,
    )


def git_changed_paths(repository: str | Path, base_ref: str | None = None) -> tuple[str, ...]:
    """Return tracked and untracked paths changed from a clean baseline."""

    root = Path(repository).expanduser()
    if not root.is_dir():
        raise EvidenceError(f"repository not found: {root}")
    diff_args = ["git", "diff", "--name-only", "--no-renames"]
    if base_ref:
        diff_args.append(base_ref)
    else:
        diff_args.extend(["HEAD", "--"])
    if base_ref:
        if base_ref.startswith("-"):
            raise EvidenceError("base ref must not be an option")
        diff_args.append("--")
    diff = subprocess.run(diff_args, cwd=root, check=False, capture_output=True, text=True)
    if diff.returncode != 0:
        raise EvidenceError(diff.stderr.strip() or "could not inspect the git diff")
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--no-renames"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if staged.returncode != 0:
        raise EvidenceError(staged.stderr.strip() or "could not inspect the staged diff")
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        raise EvidenceError(untracked.stderr.strip() or "could not inspect untracked files")
    paths = {
        line.strip().replace("\\", "/")
        for output in (diff.stdout, staged.stdout, untracked.stdout)
        for line in output.splitlines()
        if line.strip()
    }
    return tuple(sorted(paths))
