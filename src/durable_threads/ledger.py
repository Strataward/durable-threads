"""A redacted, atomic local ledger for durable task metadata."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SECRET = re.compile(
    r"(?:sk-[A-Za-z0-9]{12,}|xai-[A-Za-z0-9_\-]{12,}|gh[pousr]_[A-Za-z0-9_\-]{12,}|"
    r"github_pat_[A-Za-z0-9_\-]{12,}|(?:OPENAI|ANTHROPIC|XAI|CURSOR|GROK)_"
    r"[A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET)\s*[=:]\s*[^\s,;]+)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _redact(value: Any, limit: int = 2000) -> Any:
    if isinstance(value, str):
        return _SECRET.sub("[REDACTED]", value)[:limit]
    if isinstance(value, list):
        return [_redact(item, limit) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact(item, limit) for key, item in value.items()}
    return value


class Ledger:
    """Persist task ids, provider thread ids, status, and compact evidence."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schemaVersion": 1, "updatedAt": _now(), "tasks": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schemaVersion") != 1:
            raise ValueError("ledger must use schemaVersion 1")
        tasks = data.get("tasks")
        if not isinstance(tasks, dict):
            raise ValueError("ledger tasks must be an object")
        return data

    def save(self, data: dict[str, Any]) -> None:
        clean = _redact(data)
        clean["schemaVersion"] = 1
        clean["updatedAt"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=".ledger-",
            suffix=".json",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(clean, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def record_task(
        self,
        *,
        task_id: str,
        role: str,
        status: str,
        provider: str | None = None,
        thread_id: str | None = None,
        result: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upsert one task without persisting its full conversation."""

        data = self.read()
        tasks = data.setdefault("tasks", {})
        existing = tasks.get(task_id, {})
        if not isinstance(existing, dict):
            existing = {}
        task = {
            **existing,
            "taskId": task_id,
            "role": role,
            "status": status,
            "updatedAt": _now(),
        }
        if provider:
            task["provider"] = provider
        if thread_id:
            task["threadId"] = thread_id
        if result is not None:
            task["result"] = result
        if usage is not None:
            task["usage"] = usage
        tasks[task_id] = task
        self.save(data)
        return task
