"""Load and validate the JSON roster used by Durable Threads."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .risk import validate_risk


class ConfigError(ValueError):
    """Raised when a roster is invalid or unsafe to use."""


_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
_EXECUTION_CLASSES = {"decision", "workhorse", "review", "specialist"}
_PROFILES = {"economy", "balanced", "frontier"}
_PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


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
    provider = cast(str, _text(value, field)).casefold()
    if not _PROVIDER_ID.fullmatch(provider):
        raise ConfigError(
            f"{field} must be a lowercase provider id using letters, digits, '.', '_' or '-'"
        )
    return provider


def _execution_class(value: Any, field: str, default: str) -> str:
    item = cast(str, _text(value if value is not None else default, field))
    if item not in _EXECUTION_CLASSES:
        raise ConfigError(f"{field} must be one of: {', '.join(sorted(_EXECUTION_CLASSES))}")
    return item


@dataclass(frozen=True)
class RoleConfig:
    """Model policy for a planner or reviewer role."""

    role: str
    provider: str
    model_selector: str
    reasoning_effort: str
    execution_class: str

    @classmethod
    def from_dict(cls, data: Any, field: str, *, default_execution_class: str) -> RoleConfig:
        if not isinstance(data, dict):
            raise ConfigError(f"{field} must be an object")
        role = cast(str, _text(data.get("role"), f"{field}.role"))
        provider = _provider(data.get("provider", "codex"), f"{field}.provider")
        selector = cast(str, _text(data.get("modelSelector"), f"{field}.modelSelector"))
        effort = cast(str, _text(data.get("reasoningEffort"), f"{field}.reasoningEffort"))
        if effort not in _EFFORTS:
            allowed = ", ".join(sorted(_EFFORTS))
            raise ConfigError(f"{field}.reasoningEffort must be one of: {allowed}")
        execution_class = _execution_class(
            data.get("executionClass"), f"{field}.executionClass", default_execution_class
        )
        return cls(
            role=role,
            provider=provider,
            model_selector=selector,
            reasoning_effort=effort,
            execution_class=execution_class,
        )


@dataclass(frozen=True)
class WorkerConfig:
    """A named durable worker-thread definition."""

    name: str
    role: str
    provider: str
    thread_title: str
    purpose: str
    model_selector: str
    reasoning_effort: str
    execution_class: str
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
        execution_class = _execution_class(
            data.get("executionClass"), f"{field}.executionClass", "workhorse"
        )
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
            execution_class=execution_class,
            thread_id=cast(str | None, values["thread_id"]),
            max_followups=max_followups,
            parallel=parallel,
        )


@dataclass(frozen=True)
class EscalationStep:
    """One model/effort rung in an evidence-gated escalation ladder."""

    model_selector: str
    reasoning_effort: str

    @classmethod
    def from_dict(cls, data: Any, index: int) -> EscalationStep:
        field = f"strategy.escalation[{index}]"
        if not isinstance(data, dict):
            raise ConfigError(f"{field} must be an object")
        selector = cast(str, _text(data.get("modelSelector"), f"{field}.modelSelector"))
        effort = cast(str, _text(data.get("reasoningEffort"), f"{field}.reasoningEffort"))
        if effort not in _EFFORTS:
            raise ConfigError(f"{field}.reasoningEffort is not supported")
        return cls(selector, effort)


@dataclass(frozen=True)
class StrategyConfig:
    """Economic orchestration policy independent of provider model names."""

    profile: str
    default_risk: str
    frontier_review_at: str
    sleeping_orchestrator: bool
    escalation: tuple[EscalationStep, ...]


_DEFAULT_ESCALATION = (
    EscalationStep("efficient", "xhigh"),
    EscalationStep("balanced", "medium"),
    EscalationStep("frontier", "low"),
    EscalationStep("frontier", "medium"),
)


def _strategy(data: Any) -> StrategyConfig:
    if data is None:
        return StrategyConfig("economy", "R1", "R3", True, _DEFAULT_ESCALATION)
    if not isinstance(data, dict):
        raise ConfigError("strategy must be an object")
    profile = cast(str, _text(data.get("profile", "economy"), "strategy.profile"))
    if profile not in _PROFILES:
        raise ConfigError(f"strategy.profile must be one of: {', '.join(sorted(_PROFILES))}")
    try:
        default_risk = validate_risk(str(data.get("defaultRisk", "R1")))
        frontier_review_at = validate_risk(str(data.get("frontierReviewAt", "R3")))
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    sleeping = data.get("sleepingOrchestrator", True)
    if not isinstance(sleeping, bool):
        raise ConfigError("strategy.sleepingOrchestrator must be a boolean")
    raw_escalation = data.get("escalation")
    escalation = (
        _DEFAULT_ESCALATION
        if raw_escalation is None
        else tuple(
            EscalationStep.from_dict(item, index) for index, item in enumerate(raw_escalation)
        )
    )
    if not escalation:
        raise ConfigError("strategy.escalation must not be empty")
    return StrategyConfig(profile, default_risk, frontier_review_at, sleeping, escalation)


@dataclass(frozen=True)
class Roster:
    """Validated project routing and economic policy."""

    schema_version: int
    project_name: str
    planner: RoleConfig
    reviewer: RoleConfig
    strategy: StrategyConfig
    workers: tuple[WorkerConfig, ...]
    max_parallel_workers: int
    max_selected_workers: int
    result_max_chars: int
    allow_thread_creation: bool


def load_roster(path: str | Path) -> Roster:
    """Load a JSON roster and reject ambiguous or duplicate entries.

    Schema v1 remains accepted for backwards compatibility. V2 adds strategy and
    execution-class metadata while preserving the existing worker contract.
    """

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
    if schema_version not in {1, 2}:
        raise ConfigError("schemaVersion must be 1 or 2")
    project = data.get("project")
    if not isinstance(project, dict):
        raise ConfigError("project must be an object")
    project_name = _text(project.get("name"), "project.name")
    defaults = data.get("defaults")
    if not isinstance(defaults, dict):
        raise ConfigError("defaults must be an object")
    planner = RoleConfig.from_dict(
        defaults.get("planner"), "defaults.planner", default_execution_class="decision"
    )
    reviewer = RoleConfig.from_dict(
        defaults.get("reviewer"), "defaults.reviewer", default_execution_class="review"
    )
    strategy = _strategy(data.get("strategy"))
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
        policy.get("maxParallelWorkers", 2), "policy.maxParallelWorkers", minimum=1
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
        strategy=strategy,
        workers=workers,
        max_parallel_workers=max_parallel,
        max_selected_workers=max_selected,
        result_max_chars=result_max_chars,
        allow_thread_creation=allow_creation,
    )
