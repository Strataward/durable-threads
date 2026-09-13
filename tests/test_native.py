from __future__ import annotations

from pathlib import Path

import pytest

from durable_threads.config import load_roster
from durable_threads.native import codex_agent_role, recommend_native_execution

ROOT = Path(__file__).parents[1]
ROSTER = ROOT / "examples" / "roster.json"


def _worker(name: str):
    roster = load_roster(ROSTER)
    return next(worker for worker in roster.workers if worker.name == name)


def test_native_role_mapping_uses_codex_built_ins() -> None:
    assert codex_agent_role(_worker("implementation")) == "worker"
    assert codex_agent_role(_worker("test-debug")) == "worker"
    assert codex_agent_role(_worker("research-docs")) == "explorer"
    assert codex_agent_role(_worker("security-review")) == "default"


def test_read_only_review_can_share_checkout() -> None:
    hint = recommend_native_execution(_worker("security-review"), risk_class="R3")

    assert hint.workspace_mode == "shared-readonly"
    assert hint.parallel_safe
    assert hint.frontier_review_recommended


def test_parallel_writers_prefer_isolated_worktrees() -> None:
    hint = recommend_native_execution(
        _worker("implementation"),
        risk_class="R2",
        concurrent_writers=2,
    )

    assert hint.workspace_mode == "isolated-worktree"
    assert hint.parallel_safe
    assert not hint.frontier_review_recommended


def test_overlapping_writers_are_serialized() -> None:
    hint = recommend_native_execution(
        _worker("implementation"),
        risk_class="R2",
        concurrent_writers=2,
        overlapping_writes=True,
    )

    assert hint.workspace_mode == "serial"
    assert not hint.parallel_safe


def test_native_hint_rejects_invalid_writer_count() -> None:
    with pytest.raises(ValueError, match="concurrent_writers"):
        recommend_native_execution(
            _worker("implementation"),
            risk_class="R1",
            concurrent_writers=-1,
        )
