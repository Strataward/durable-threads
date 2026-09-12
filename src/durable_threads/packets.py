"""Compact, safe delegation packets."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .config import WorkerConfig
from .risk import classify_risk, validate_risk


class PacketError(ValueError):
    """Raised when a delegation packet is incomplete or unsafe."""


_SECRET_MARKERS = re.compile(
    r"(?:sk-[A-Za-z0-9]{12,}|xai-[A-Za-z0-9_\-]{12,}|gh[pousr]_[A-Za-z0-9_\-]{12,}|"
    r"github_pat_[A-Za-z0-9_\-]{12,}|"
    r"(?:OPENAI|ANTHROPIC|GITHUB|AWS|XAI|CURSOR|GROK)_[A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET)\s*[=:])",
    re.IGNORECASE,
)


def _clean_text(value: str, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > limit:
        raise PacketError(f"{field} exceeds the compact packet limit of {limit} characters")
    if _SECRET_MARKERS.search(value):
        raise PacketError(f"{field} contains a credential-like value")
    return value


def _clean_items(values: Iterable[str] | None, field: str, limit: int) -> tuple[str, ...]:
    return tuple(_clean_text(item, field, limit) for item in (values or ()))


@dataclass(frozen=True)
class DelegationPacket:
    """A bounded implementation contract that a durable worker can execute."""

    schema_version: int
    run_id: str
    task_name: str
    role: str
    provider: str
    objective: str
    risk_class: str
    execution_class: str
    decisions: tuple[str, ...]
    invariants: tuple[str, ...]
    non_goals: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    acceptance: tuple[str, ...]
    constraints: tuple[str, ...]
    result_contract: tuple[str, ...]
    model_selector: str
    reasoning_effort: str
    max_followups: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "decisions",
            "invariants",
            "non_goals",
            "allowed_paths",
            "acceptance",
            "constraints",
            "result_contract",
        ):
            data[key] = list(data[key])
        return data


def build_packet(
    worker: WorkerConfig,
    *,
    run_id: str,
    objective: str,
    allowed_paths: list[str],
    acceptance: list[str],
    constraints: list[str],
    decisions: list[str] | None = None,
    invariants: list[str] | None = None,
    non_goals: list[str] | None = None,
    risk_class: str | None = None,
) -> DelegationPacket:
    """Build one compact packet from a roster entry.

    Decisions, invariants, and non-goals make architectural intent explicit so a
    high-throughput workhorse model can execute without re-solving the plan.
    """

    if not run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", run_id):
        raise PacketError("run_id must be 3-64 characters and use safe identifier characters")
    if not allowed_paths:
        raise PacketError("allowed_paths must not be empty")
    if not acceptance:
        raise PacketError("acceptance must not be empty")
    try:
        risk = (
            validate_risk(risk_class)
            if risk_class
            else classify_risk(
                objective=objective,
                allowed_paths=allowed_paths,
                acceptance=acceptance,
            ).risk_class
        )
    except ValueError as exc:
        raise PacketError(str(exc)) from exc
    cleaned_paths = _clean_items(allowed_paths, "allowed_path", 240)
    cleaned_acceptance = _clean_items(acceptance, "acceptance", 400)
    cleaned_constraints = _clean_items(constraints, "constraint", 400)
    cleaned_decisions = _clean_items(decisions, "decision", 500)
    cleaned_invariants = _clean_items(invariants, "invariant", 500)
    cleaned_non_goals = _clean_items(non_goals, "non_goal", 500)
    result_contract = (
        "Return changed paths.",
        "Return exact checks and results.",
        "Return remaining concerns or 'None known'.",
        "Do not claim an unexecuted check passed.",
        "Do not include secrets, private data, or a full transcript.",
    )
    return DelegationPacket(
        schema_version=2,
        run_id=run_id,
        task_name=_clean_text(worker.name, "task_name", 120),
        role=_clean_text(worker.role, "role", 120),
        provider=_clean_text(worker.provider, "provider", 40),
        objective=_clean_text(f"{objective} Purpose: {worker.purpose}", "objective", 4000),
        risk_class=risk,
        execution_class=_clean_text(worker.execution_class, "execution_class", 40),
        decisions=cleaned_decisions,
        invariants=cleaned_invariants,
        non_goals=cleaned_non_goals,
        allowed_paths=cleaned_paths,
        acceptance=cleaned_acceptance,
        constraints=cleaned_constraints,
        result_contract=result_contract,
        model_selector=_clean_text(worker.model_selector, "model_selector", 120),
        reasoning_effort=_clean_text(worker.reasoning_effort, "reasoning_effort", 20),
        max_followups=worker.max_followups,
    )
