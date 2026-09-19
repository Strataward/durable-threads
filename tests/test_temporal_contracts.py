from __future__ import annotations

import pytest

from durable_threads.temporal_contracts import TaskRunInput


def test_durable_task_contract_bounds_parallelism() -> None:
    with pytest.raises(ValueError, match="speculative_parallelism"):
        TaskRunInput(
            objective="Implement a bounded change",
            allowed_paths=["src/**"],
            acceptance=["tests pass"],
            cwd="repo",
            speculative_parallelism=5,
        )


def test_durable_task_contract_defaults_to_provider_neutral_capabilities() -> None:
    task = TaskRunInput(
        objective="Implement a bounded change",
        allowed_paths=["src/**"],
        acceptance=["tests pass"],
        cwd="repo",
    )
    assert task.required_capabilities == ["code", "filesystem", "git"]
    assert task.preferred_providers == []
