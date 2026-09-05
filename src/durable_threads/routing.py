"""Resolve role selectors against a live model catalog."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .config import Roster, WorkerConfig


@dataclass(frozen=True)
class ModelInfo:
    """The small model subset needed by the router."""

    model_id: str
    display_name: str
    tier: str
    is_default: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelInfo:
        model_id = data.get("id", data.get("model"))
        display_name = data.get("displayName", data.get("display_name", model_id))
        tier = data.get("tier", data.get("costTier", "unknown"))
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model catalog entries need an id")
        return cls(
            model_id=model_id.strip(),
            display_name=str(display_name).strip(),
            tier=str(tier).strip().lower(),
            is_default=bool(data.get("isDefault", data.get("default", False))),
        )


@dataclass(frozen=True)
class Resolution:
    """A model choice with a reason that can be shown to the user."""

    model: ModelInfo | None
    reason: str
    matched: bool


@dataclass(frozen=True)
class RouteDecision:
    """The small set of workers selected for one bounded task."""

    selected: tuple[WorkerConfig, ...]
    skipped: tuple[WorkerConfig, ...]
    reasons: tuple[str, ...]
    explicit: bool


_CHANGE_SIGNAL = re.compile(
    r"\b(add|build|change|create|debug|fix|implement|migrate|modify|refactor|remove|repair|update)\b",
    re.IGNORECASE,
)
_ROLE_SIGNALS = {
    "test-debug": re.compile(
        r"\b(coverage|debug|failure|failing|flaky|lint|regression|test|tests|testing|typecheck)\b",
        re.IGNORECASE,
    ),
    "research-docs": re.compile(
        r"\b(analy[sz]e|audit|compare|document|documentation|docs|investigate|research|readme)\b",
        re.IGNORECASE,
    ),
    "security-review": re.compile(
        r"\b(auth|authorization|hardening|permission|privacy|secret|security|threat|vulnerab)\w*\b",
        re.IGNORECASE,
    ),
}


def select_workers(
    roster: Roster,
    *,
    objective: str,
    allowed_paths: Iterable[str] = (),
    acceptance: Iterable[str] = (),
    requested_workers: Iterable[str] = (),
    local_only: bool = False,
) -> RouteDecision:
    """Select only the workers that a bounded task needs.

    Explicit worker names take priority. Automatic routing uses conservative
    keyword signals. It never creates a worker and never selects more than the
    roster policy allows.
    """

    worker_names = {worker.name: worker for worker in roster.workers}
    requested = tuple(name.strip() for name in requested_workers if name.strip())
    if local_only:
        if requested:
            raise ValueError("local work cannot select workers")
        return RouteDecision((), roster.workers, ("keep work in the current task",), True)
    if len(set(requested)) != len(requested):
        raise ValueError("requested worker names must be unique")
    unknown = [name for name in requested if name not in worker_names]
    if unknown:
        raise ValueError(f"unknown worker name(s): {', '.join(unknown)}")
    if len(requested) > roster.max_selected_workers:
        raise ValueError(
            "explicit worker selection exceeds policy.maxSelectedWorkers "
            f"({roster.max_selected_workers})"
        )

    if requested:
        selected = tuple(worker_names[name] for name in requested)
        parallel_count = sum(worker.parallel for worker in selected)
        if parallel_count > roster.max_parallel_workers:
            raise ValueError(
                f"route selects {parallel_count} parallel workers, but policy.maxParallelWorkers "
                f"is {roster.max_parallel_workers}"
            )
        skipped = tuple(worker for worker in roster.workers if worker.name not in requested)
        return RouteDecision(
            selected=selected,
            skipped=skipped,
            reasons=("explicit worker selection was requested",),
            explicit=True,
        )

    context = " ".join(
        item.strip()
        for item in (objective, *allowed_paths)
        if isinstance(item, str) and item.strip()
    )
    change_requested = bool(_CHANGE_SIGNAL.search(context))
    signals = {role: bool(pattern.search(context)) for role, pattern in _ROLE_SIGNALS.items()}
    specialized = any(signals.values())

    desired_roles: list[tuple[str, str]] = []
    implementation_worker = next(
        (worker for worker in roster.workers if worker.role == "implementation"), None
    )
    if implementation_worker and (change_requested or not specialized):
        desired_roles.append(("implementation", "a code-change signal or no specialist signal"))
    for role in ("security-review", "test-debug", "research-docs"):
        worker = next((item for item in roster.workers if item.role == role), None)
        if worker and _ROLE_SIGNALS[role].search(context):
            desired_roles.append((role, f"the {role} signal was detected"))

    selected: list[WorkerConfig] = []
    reasons: list[str] = []
    for role, reason in desired_roles:
        worker = next(item for item in roster.workers if item.role == role)
        if worker in selected:
            continue
        if len(selected) >= roster.max_selected_workers:
            reasons.append(
                f"skipped {worker.name}: policy.maxSelectedWorkers is {roster.max_selected_workers}"
            )
            continue
        selected.append(worker)
        reasons.append(f"selected {worker.name}: {reason}")

    if not selected:
        selected.append(roster.workers[0])
        reasons.append(f"selected {roster.workers[0].name}: safe roster fallback")

    parallel_count = sum(worker.parallel for worker in selected)
    if parallel_count > roster.max_parallel_workers:
        raise ValueError(
            f"route selects {parallel_count} parallel workers, but policy.maxParallelWorkers "
            f"is {roster.max_parallel_workers}"
        )

    selected_names = {worker.name for worker in selected}
    skipped = tuple(worker for worker in roster.workers if worker.name not in selected_names)
    return RouteDecision(
        selected=tuple(selected),
        skipped=skipped,
        reasons=tuple(reasons),
        explicit=False,
    )


def catalog_from_payload(payload: Any) -> tuple[ModelInfo, ...]:
    """Read common Codex model-list shapes without assuming model names."""

    if isinstance(payload, dict):
        raw_models = payload.get("models", [])
    else:
        raw_models = payload
    if not isinstance(raw_models, list):
        raise ValueError("model catalog must contain a models array")
    return tuple(ModelInfo.from_dict(item) for item in raw_models if isinstance(item, dict))


def _normal(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").replace("-", " ").split())


def resolve_model(catalog: Iterable[ModelInfo], selector: str) -> Resolution:
    """Resolve an exact id or a stable role selector.

    Role selectors use catalog metadata first. The fallback keeps the runtime's
    default model instead of guessing a stale provider-specific slug.
    """

    models = tuple(catalog)
    wanted = _normal(selector)
    for model in models:
        names = {
            _normal(model.model_id),
            _normal(model.display_name),
            *_normal(model.model_id).split(),
            *_normal(model.display_name).split(),
        }
        if wanted in names:
            return Resolution(model, f"exact catalog match for {selector!r}", True)

    tier_groups = {
        "frontier": {"frontier", "flagship", "high"},
        "balanced": {"balanced", "standard", "medium"},
        "efficient": {"efficient", "low", "mini"},
    }
    if wanted in tier_groups:
        candidates = [model for model in models if model.tier in tier_groups[wanted]]
        if candidates:
            default = next((model for model in candidates if model.is_default), candidates[0])
            return Resolution(default, f"{wanted} role matched live catalog metadata", True)
        default = next((model for model in models if model.is_default), None)
        if default:
            return Resolution(
                default,
                f"{wanted} role was unavailable; using the runtime default without guessing",
                False,
            )
    return Resolution(None, f"no live model matched selector {selector!r}", False)
