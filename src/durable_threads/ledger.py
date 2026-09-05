"""A redacted, atomic local ledger for durable task metadata."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

_SECRET = re.compile(
    r"(?:sk-[A-Za-z0-9]{12,}|xai-[A-Za-z0-9_\-]{12,}|gh[pousr]_[A-Za-z0-9_\-]{12,}|"
    r"github_pat_[A-Za-z0-9_\-]{12,}|(?:OPENAI|ANTHROPIC|XAI|CURSOR|GROK)_"
    r"[A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET)\s*[=:]\s*[^\s,;]+)",
    re.IGNORECASE,
)


class LedgerBusyError(RuntimeError):
    """Raised when a local task already has an active writer."""


class LedgerStateError(ValueError):
    """Raised when a follow-up does not match the recorded task state."""


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LedgerBusyError("ledger is locked; inspect the writer before recovery") from exc
        try:
            return method(self, *args, **kwargs)
        finally:
            os.close(descriptor)
            lock.unlink()

    return call


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

    @_locked
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
        return _redact(task)

    @_locked
    def begin_task(
        self,
        *,
        task_id: str,
        role: str,
        provider: str,
        thread_id: str | None = None,
        followup_index: int = 0,
        max_followups: int = 1,
    ) -> dict[str, Any]:
        """Claim a task locally before a provider process starts.

        This protects against duplicate local writers. It does not prove that
        a provider has no external writer. Provider status remains a hard stop.
        """

        if followup_index < 0 or max_followups < 0 or followup_index > max_followups:
            raise LedgerStateError(f"followup index must be between 0 and {max_followups}")
        data = self.read()
        tasks = data.setdefault("tasks", {})
        existing = tasks.get(task_id, {})
        if not isinstance(existing, dict):
            existing = {}
        if existing.get("status") == "running":
            raise LedgerBusyError(f"task {task_id!r} already has a local active writer")
        existing_provider = existing.get("provider")
        if existing_provider and existing_provider != provider:
            raise LedgerStateError(
                f"task {task_id!r} belongs to provider {existing_provider!r}, not {provider!r}"
            )
        existing_thread = existing.get("threadId")
        if existing_thread and existing_thread != thread_id:
            raise LedgerStateError(f"task {task_id!r} requires its recorded provider session ID")
        if existing_thread and not thread_id:
            raise LedgerStateError(f"task {task_id!r} cannot resume without its session ID")
        recorded_followups = existing.get("followups", -1) + 1
        if not isinstance(recorded_followups, int) or recorded_followups < 0:
            raise LedgerStateError(f"task {task_id!r} has invalid follow-up state")
        if followup_index != recorded_followups:
            raise LedgerStateError(
                f"task {task_id!r} expects follow-up index {recorded_followups}, "
                f"not {followup_index}"
            )
        if existing.get("status") in {"blocked", "unknown", "complete", "unverified"}:
            raise LedgerStateError("task cannot retry in its current state; inspect it first")
        task = {
            **existing,
            "taskId": task_id,
            "role": role,
            "provider": provider,
            "status": "running",
            "followups": followup_index,
            "updatedAt": _now(),
        }
        if thread_id:
            task["threadId"] = thread_id
        tasks[task_id] = task
        self.save(data)
        return task
