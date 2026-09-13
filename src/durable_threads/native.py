"""Provider-neutral hints for native Codex multi-agent execution.

The helpers in this module do not spawn agents. They translate Durable Threads
roles and risk into inspectable execution hints that a native Codex runtime can
apply using its own subagent, sandbox, wait, and worktree primitives.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import WorkerConfig
from .risk import meets_threshold, validate_risk

_NATIVE_AGENT_ROLES = {"default", "explorer", "worker"}
_WORKSPACE_MODES = {"shared-readonly", "shared-write", "isolated-worktree", "serial"}
_READ_ONLY_ROLES = {"research-docs", "security-review"}


@dataclass(frozen=True)
class NativeExecutionHint:
    """Recommended native-runtime shape for one Durable Threads worker."""

    agent_role: str
    workspace_mode: str
    parallel_safe: bool
    frontier_review_recommended: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "agentRole": self.agent_role,
            "workspaceMode": self.workspace_mode,
            "parallelSafe": self.parallel_safe,
            "frontierReviewRecommended": self.frontier_review_recommended,
            "reason": self.reason,
        }


def codex_agent_role(worker: WorkerConfig) -> str:
    """Map a Durable Threads worker to a built-in Codex agent role.

    The mapping intentionally uses only roles Codex ships by default. Teams may
    substitute a project-defined reviewer or specialist role when one exists.
    """

    if worker.role == "research-docs":
        return "explorer"
    if worker.execution_class == "workhorse" or worker.role in {"implementation", "test-debug"}:
        return "worker"
    return "default"


def recommend_native_execution(
    worker: WorkerConfig,
    *,
    risk_class: str,
    concurrent_writers: int = 1,
    overlapping_writes: bool = False,
) -> NativeExecutionHint:
    """Recommend a native Codex role and workspace-isolation strategy.

    Read-only exploration/review can safely share a checkout. A single writer can
    use the shared checkout. Multiple independent writers should use isolated
    worktrees when available. Overlapping writers should be serialized instead of
    relying on worktrees to resolve semantic conflicts.
    """

    risk = validate_risk(risk_class)
    if concurrent_writers < 0:
        raise ValueError("concurrent_writers must be >= 0")

    agent_role = codex_agent_role(worker)
    if agent_role not in _NATIVE_AGENT_ROLES:
        raise ValueError(f"unsupported native agent role: {agent_role}")

    read_only = worker.role in _READ_ONLY_ROLES or worker.execution_class in {
        "review",
        "specialist",
    }
    if read_only:
        workspace_mode = "shared-readonly"
        parallel_safe = True
        reason = "read-only exploration/review can share the parent checkout"
    elif overlapping_writes:
        workspace_mode = "serial"
        parallel_safe = False
        reason = "overlapping write ownership must be serialized"
    elif concurrent_writers > 1:
        workspace_mode = "isolated-worktree"
        parallel_safe = True
        reason = "independent parallel writers should use isolated worktrees"
    else:
        workspace_mode = "shared-write"
        parallel_safe = True
        reason = "one bounded writer can use the shared checkout"

    if workspace_mode not in _WORKSPACE_MODES:
        raise ValueError(f"unsupported workspace mode: {workspace_mode}")

    return NativeExecutionHint(
        agent_role=agent_role,
        workspace_mode=workspace_mode,
        parallel_safe=parallel_safe,
        frontier_review_recommended=meets_threshold(risk, "R3"),
        reason=reason,
    )
