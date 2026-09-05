"""Load and validate the small JSON roster used by the skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .providers import PROVIDERS


class ConfigError(ValueError):
    """Raised when a roster is invalid or unsafe to use."""


_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


def _text(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field} must be a non-empty string")
    return value.strip()


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{field} must be an integer >= {minimum}")
    return value


def _provider(value: Any, field: str) -> str:
    provider = cast(str, _text(value, field))
    if provider.casefold() not in PROVIDERS:
        allowed = ", ".join(PROVIDERS)
        raise ConfigError(f"{field} must be one of: {allowed}")
    return provider.casefold()


@dataclass(frozen=True)
class RoleConfig:
    """Model policy for one role."""

    role: str
    provider: str
    model_selector: str
    reasoning_effort: str

    @classmethod
    def from_dict(cls, data: Any, field: str) -> RoleConfig:
        if not isinstance(data, dict):
            raise ConfigError(f"{field} must be an object")
        role = cast(str, _text(data.get("role"), f"{field}.role"))
        provider = _provider(data.get("provider", "codex"), f"{field}.provider")
        selector = cast(str, _text(data.get("modelSelector"), f"{field}.modelSelector"))
        effort = cast(str, _text(data.get("reasoningEffort"), f"{field}.reasoningEffort"))
        if effort not in _EFFORTS:
            allowed = ", ".join(sorted(_EFFORTS))
            raise ConfigError(f"{field}.reasoningEffort must be one of: {allowed}")
        return cls(
            role=role,
            provider=provider,
            model_selector=selector,
            reasoning_effort=effort,
        )


@dataclass(frozen=True)
class WorkerConfig:
    """A named worker thread definition."""

    name: str
    role: str
    provider: str
    thread_title: str
    purpose: str
    model_selector: str
    reasoning_effort: str
    thread_id: str | None
    max_followups: int
    parallel: bool

    @classmethod
    def from_dict(cls, data: Any, index: int) -> WorkerConfig:
        field = f"workers[{index}]"
        if not isinstance(data, dict):
            raise ConfigError(f"{field} must be an object")
        values = {
            "name": _text(data.get("name"), f"{field}.name"),
            "role": _text(data.get("role"), f"{field}.role"),
            "provider": _provider(data.get("provider", "codex"), f"{field}.provider"),
            "thread_title": _text(data.get("threadTitle"), f"{field}.threadTitle"),
            "purpose": _text(data.get("purpose"), f"{field}.purpose"),
            "model_selector": _text(data.get("modelSelector"), f"{field}.modelSelector"),
            "reasoning_effort": _text(
                data.get("reasoningEffort", "low"), f"{field}.reasoningEffort"
            ),
            "thread_id": _text(data.get("threadId"), f"{field}.threadId", required=False),
        }
        if values["reasoning_effort"] not in _EFFORTS:
            raise ConfigError(f"{field}.reasoningEffort is not supported")
        max_followups = _integer(data.get("maxFollowups", 1), f"{field}.maxFollowups")
        if max_followups > 3:
            raise ConfigError(f"{field}.maxFollowups must be <= 3")
        parallel = data.get("parallel", False)
        if not isinstance(parallel, bool):
            raise ConfigError(f"{field}.parallel must be a boolean")
        required_fields = (
            "name",
            "role",
            "thread_title",
            "purpose",
            "model_selector",
            "reasoning_effort",
        )
        if any(values[field_name] is None for field_name in required_fields):
            raise ConfigError(f"{field} has a missing required field")
        return cls(
            name=cast(str, values["name"]),
            role=cast(str, values["role"]),
            provider=cast(str, values["provider"]),
            thread_title=cast(str, values["thread_title"]),
            purpose=cast(str, values["purpose"]),
            model_selector=cast(str, values["model_selector"]),
            reasoning_effort=cast(str, values["reasoning_effort"]),
            thread_id=cast(str | None, values["thread_id"]),
            max_followups=max_followups,
            parallel=parallel,
        )


@dataclass(frozen=True)
class Roster:
    """Validated project routing policy."""

    schema_version: int
    project_name: str
    planner: RoleConfig
    reviewer: RoleConfig
    workers: tuple[WorkerConfig, ...]
    max_parallel_workers: int
    max_selected_workers: int
    result_max_chars: int
    allow_thread_creation: bool


def load_roster(path: str | Path) -> Roster:
    """Load a JSON roster and reject ambiguous or duplicate entries."""

    roster_path = Path(path)
    try:
        data = json.loads(roster_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"roster not found: {roster_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"roster is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("roster must be a JSON object")
    schema_version = data.get("schemaVersion", 1)
    if schema_version != 1:
        raise ConfigError("schemaVersion must be 1")
    project = data.get("project")
    if not isinstance(project, dict):
        raise ConfigError("project must be an object")
    project_name = _text(project.get("name"), "project.name")
    defaults = data.get("defaults")
    if not isinstance(defaults, dict):
        raise ConfigError("defaults must be an object")
    planner = RoleConfig.from_dict(defaults.get("planner"), "defaults.planner")
    reviewer = RoleConfig.from_dict(defaults.get("reviewer"), "defaults.reviewer")
    raw_workers = data.get("workers")
    if not isinstance(raw_workers, list) or not raw_workers:
        raise ConfigError("workers must be a non-empty array")
    workers = tuple(WorkerConfig.from_dict(item, index) for index, item in enumerate(raw_workers))
    names = [worker.name for worker in workers]
    titles = [worker.thread_title for worker in workers]
    if len(set(names)) != len(names):
        raise ConfigError("worker names must be unique")
    if len(set(titles)) != len(titles):
        raise ConfigError("worker threadTitle values must be unique")
    policy = data.get("policy", {})
    if not isinstance(policy, dict):
        raise ConfigError("policy must be an object")
    max_parallel = _integer(
        policy.get("maxParallelWorkers", 2),
        "policy.maxParallelWorkers",
        minimum=1,
    )
    max_selected = _integer(
        policy.get("maxSelectedWorkers", min(2, len(workers))),
        "policy.maxSelectedWorkers",
        minimum=1,
    )
    if max_selected > len(workers):
        raise ConfigError("policy.maxSelectedWorkers cannot exceed the worker count")
    result_max_chars = _integer(
        policy.get("resultMaxChars", 2000), "policy.resultMaxChars", minimum=200
    )
    allow_creation = policy.get("allowThreadCreation", False)
    if not isinstance(allow_creation, bool):
        raise ConfigError("policy.allowThreadCreation must be a boolean")
    return Roster(
        schema_version=schema_version,
        project_name=cast(str, project_name),
        planner=planner,
        reviewer=reviewer,
        workers=workers,
        max_parallel_workers=max_parallel,
        max_selected_workers=max_selected,
        result_max_chars=result_max_chars,
        allow_thread_creation=allow_creation,
    )
