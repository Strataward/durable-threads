"""Deterministic task-risk classification for economic model routing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

RISK_LEVELS = ("R0", "R1", "R2", "R3", "R4")
_RISK_RANK = {risk: index for index, risk in enumerate(RISK_LEVELS)}

_R4 = re.compile(
    r"\b(architecture|architectural|distributed|multi[- ]region|consensus|disaster recovery|"
    r"cross[- ]service|systemic|platform migration|control plane|data plane)\b",
    re.IGNORECASE,
)
_R3 = re.compile(
    r"\b(auth|authentication|authorization|permission|payment|billing|crypto|cryptograph|"
    r"secret|credential|privacy|pii|production|database migration|schema migration|delete data|"
    r"destructive|concurren|race condition|locking|idempotency|security|vulnerab)\w*\b",
    re.IGNORECASE,
)
_R2 = re.compile(
    r"\b(api|integration|webhook|queue|cache|database|schema|migration|cross[- ]module|"
    r"multiple modules|public contract|backward compat|dependency upgrade|release)\w*\b",
    re.IGNORECASE,
)
_R0 = re.compile(
    r"\b(typo|spelling|formatting|comment|comments|readme|documentation|docs only|rename only)\b",
    re.IGNORECASE,
)
_CHANGE = re.compile(
    r"\b(add|build|change|create|debug|fix|implement|migrate|modify|refactor|remove|repair|"
    r"update)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RiskAssessment:
    risk_class: str
    reasons: tuple[str, ...]
    explicit: bool = False


def validate_risk(value: str) -> str:
    risk = value.upper().strip()
    if risk not in _RISK_RANK:
        raise ValueError(f"risk must be one of: {', '.join(RISK_LEVELS)}")
    return risk


def meets_threshold(risk: str, threshold: str) -> bool:
    return _RISK_RANK[validate_risk(risk)] >= _RISK_RANK[validate_risk(threshold)]


def classify_risk(
    *,
    objective: str,
    allowed_paths: Iterable[str] = (),
    acceptance: Iterable[str] = (),
    explicit: str | None = None,
    default: str = "R1",
) -> RiskAssessment:
    """Classify risk conservatively from bounded task text.

    The classifier is intentionally deterministic and inspectable. It is a routing
    hint, not a security boundary. Callers can always provide an explicit risk.
    """

    if explicit:
        risk = validate_risk(explicit)
        return RiskAssessment(risk, ("risk explicitly supplied by the planner",), True)

    default = validate_risk(default)
    items = [objective, *allowed_paths, *acceptance]
    context = " ".join(item.strip() for item in items if isinstance(item, str) and item.strip())

    if _R4.search(context):
        return RiskAssessment("R4", ("systemic or architecture-level signal detected",))
    if _R3.search(context):
        return RiskAssessment(
            "R3", ("critical security, data, production, or concurrency signal detected",)
        )
    if _R2.search(context):
        return RiskAssessment("R2", ("integration or public-contract signal detected",))
    if _R0.search(context) and not _CHANGE.search(context):
        return RiskAssessment("R0", ("mechanical or documentation-only signal detected",))
    code_paths = any(
        path.startswith(("src/", "app/", "packages/")) for path in allowed_paths
    )
    if _R0.search(context) and not code_paths:
        return RiskAssessment("R0", ("mechanical or documentation-only signal detected",))
    return RiskAssessment(default, (f"no higher-risk signal detected; using default {default}",))
