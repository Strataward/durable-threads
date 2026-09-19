"""Serializable contracts shared by Durable Threads Temporal workflows and activities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskRunInput:
    objective: str
    allowed_paths: list[str]
    acceptance: list[str]
    cwd: str
    constraints: list[str] = field(default_factory=list)
    preferred_providers: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(
        default_factory=lambda: ["code", "filesystem", "git"]
    )
    model_selector: str = "default"
    reasoning_effort: str = "medium"
    base_ref: str | None = None
    max_attempts: int = 2
    speculative_parallelism: int = 2
    human_gate_at: str = "R4"
    wait_for_human_review: bool = False
    provider_timeout_seconds: int = 3600
    max_output_chars: int = 8000

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("objective must not be empty")
        if not self.allowed_paths:
            raise ValueError("allowed_paths must not be empty")
        if not self.acceptance:
            raise ValueError("acceptance must not be empty")
        if not self.cwd.strip():
            raise ValueError("cwd must not be empty")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if not 1 <= self.speculative_parallelism <= 4:
            raise ValueError("speculative_parallelism must be between 1 and 4")
        if self.provider_timeout_seconds < 1:
            raise ValueError("provider_timeout_seconds must be >= 1")
        if self.max_output_chars < 200:
            raise ValueError("max_output_chars must be >= 200")


@dataclass
class RouteExecutorsInput:
    task: TaskRunInput
    assessment: dict[str, Any]
    excluded_providers: list[str] = field(default_factory=list)
    preferred_providers: list[str] = field(default_factory=list)


@dataclass
class ExecutionAttemptInput:
    task: TaskRunInput
    provider: str
    risk_class: str
    attempt: int
    execution_shape: str


@dataclass
class VerificationInput:
    cwd: str
    base_ref: str | None
    allowed_paths: list[str]
    stdout: str


@dataclass
class ResultDecisionInput:
    task: TaskRunInput
    provider: str
    risk_class: str
    return_code: int
    stdout: str
    verification: dict[str, Any]


@dataclass
class AttemptResult:
    provider: str
    return_code: int
    stdout: str
    stderr: str
    session_id: str | None
    usage: dict[str, int] | None
    verification: dict[str, Any]
    result_assessment: dict[str, Any]
    accepted: bool
    review_required: bool


@dataclass
class ReviewDecision:
    approved: bool
    note: str = ""


@dataclass
class TaskRunResult:
    status: str
    final_risk: str
    selected_provider: str | None
    task_assessment: dict[str, Any]
    attempts: list[AttemptResult]
    review_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "finalRisk": self.final_risk,
            "selectedProvider": self.selected_provider,
            "taskAssessment": self.task_assessment,
            "attempts": [
                {
                    "provider": attempt.provider,
                    "returnCode": attempt.return_code,
                    "stdout": attempt.stdout,
                    "stderr": attempt.stderr,
                    "sessionId": attempt.session_id,
                    "usage": attempt.usage,
                    "verification": attempt.verification,
                    "resultAssessment": attempt.result_assessment,
                    "accepted": attempt.accepted,
                    "reviewRequired": attempt.review_required,
                }
                for attempt in self.attempts
            ],
            "reviewNote": self.review_note,
        }
