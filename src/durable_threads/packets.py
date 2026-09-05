"""Compact, safe delegation packets."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .config import WorkerConfig


class PacketError(ValueError):
    """Raised when a delegation packet is incomplete or unsafe."""


_SECRET_MARKERS = re.compile(
    r"(?:sk-[A-Za-z0-9]{12,}|xai-[A-Za-z0-9_\-]{12,}|gh[pousr]_[A-Za-z0-9_\-]{12,}|github_pat_[A-Za-z0-9_\-]{12,}|"
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


@dataclass(frozen=True)
class DelegationPacket:
    """A bounded instruction that a durable worker can execute."""

    schema_version: int
    run_id: str
    task_name: str
    role: str
    provider: str
    objective: str
    allowed_paths: tuple[str, ...]
    acceptance: tuple[str, ...]
    constraints: tuple[str, ...]
    result_contract: tuple[str, ...]
    model_selector: str
    reasoning_effort: str
    max_followups: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("allowed_paths", "acceptance", "constraints", "result_contract"):
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
) -> DelegationPacket:
    """Build one compact packet from a roster entry."""

    if not run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", run_id):
        raise PacketError("run_id must be 3-64 characters and use safe identifier characters")
    if not allowed_paths:
        raise PacketError("allowed_paths must not be empty")
    if not acceptance:
        raise PacketError("acceptance must not be empty")
    cleaned_paths = tuple(_clean_text(item, "allowed_path", 240) for item in allowed_paths)
    cleaned_acceptance = tuple(_clean_text(item, "acceptance", 400) for item in acceptance)
    cleaned_constraints = tuple(_clean_text(item, "constraint", 400) for item in constraints)
    result_contract = (
        "Return changed paths.",
        "Return exact checks and results.",
        "Return remaining concerns or 'None known'.",
        "Do not include secrets, private data, or a full transcript.",
    )
    return DelegationPacket(
        schema_version=2,
        run_id=run_id,
        task_name=_clean_text(worker.name, "task_name", 120),
        role=_clean_text(worker.role, "role", 120),
        provider=_clean_text(worker.provider, "provider", 40),
        objective=_clean_text(f"{objective} Purpose: {worker.purpose}", "objective", 4000),
        allowed_paths=cleaned_paths,
        acceptance=cleaned_acceptance,
        constraints=cleaned_constraints,
        result_contract=result_contract,
        model_selector=_clean_text(worker.model_selector, "model_selector", 120),
        reasoning_effort=_clean_text(worker.reasoning_effort, "reasoning_effort", 20),
        max_followups=worker.max_followups,
    )
