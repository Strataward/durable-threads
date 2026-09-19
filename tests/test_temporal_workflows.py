from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("temporalio")

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from durable_threads.temporal_activities import (
    assess_result_activity,
    assess_task_activity,
    route_executors_activity,
    run_execution_activity,
    verify_execution_activity,
)
from durable_threads.temporal_contracts import ReviewDecision, TaskRunInput
from durable_threads.temporal_workflows import AgentExecutionWorkflow, DurableTaskWorkflow


def _git_repo(path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    (path / ".gitignore").write_text(".durable-threads/\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "README.md", ".gitignore"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "initial",
        ],
        check=True,
        capture_output=True,
    )


def _scenario(path, *, writes, changed_paths, return_code=0, status="complete") -> None:
    scenario_dir = path / ".durable-threads"
    scenario_dir.mkdir()
    payload = {
        "writes": writes,
        "result": {
            "status": status,
            "changedPaths": changed_paths,
            "checks": ["python -m pytest -q: passed"],
            "remainingConcerns": [],
        },
        "returnCode": return_code,
        "delaySeconds": 0.0,
        "stderr": "",
        "extraStdout": "",
    }
    (scenario_dir / "scripted.json").write_text(json.dumps(payload), encoding="utf-8")


def _task(path, *, objective="Update a bounded file", max_attempts=2, **kwargs):
    return TaskRunInput(
        objective=objective,
        allowed_paths=["src/**"],
        acceptance=["the file is updated"],
        cwd=str(path),
        preferred_providers=["scripted"],
        required_capabilities=["code", "filesystem", "git"],
        max_attempts=max_attempts,
        provider_timeout_seconds=60,
        **kwargs,
    )


async def _execute(task: TaskRunInput):
    queue = f"durable-test-{uuid.uuid4().hex}"
    async with await WorkflowEnvironment.start_time_skipping() as env:
        with ThreadPoolExecutor(max_workers=5) as activity_executor:
            async with Worker(
                env.client,
                task_queue=queue,
                workflows=[DurableTaskWorkflow, AgentExecutionWorkflow],
                activities=[
                    assess_task_activity,
                    route_executors_activity,
                    run_execution_activity,
                    verify_execution_activity,
                    assess_result_activity,
                ],
                activity_executor=activity_executor,
            ):
                return await env.client.execute_workflow(
                    DurableTaskWorkflow.run,
                    task,
                    id=f"workflow-{uuid.uuid4().hex}",
                    task_queue=queue,
                )


def test_happy_path(tmp_path, monkeypatch) -> None:
    _git_repo(tmp_path)
    _scenario(
        tmp_path,
        writes={"src/result.py": "result = True\n"},
        changed_paths=["src/result.py"],
    )
    monkeypatch.setenv("DURABLE_THREADS_DECISION_ENGINE", "heuristic")
    monkeypatch.setenv("DURABLE_THREADS_ENABLE_SCRIPTED", "1")

    result = asyncio.run(_execute(_task(tmp_path)))

    assert result.status == "complete"
    assert result.selected_provider == "scripted"
    assert len(result.attempts) == 1
    assert result.attempts[0].verification["complete"] is True


def test_evidence_mismatch_is_bounded_and_not_complete(tmp_path, monkeypatch) -> None:
    _git_repo(tmp_path)
    _scenario(
        tmp_path,
        writes={"src/a.py": "value = 1\n"},
        changed_paths=["src/b.py"],
    )
    monkeypatch.setenv("DURABLE_THREADS_DECISION_ENGINE", "heuristic")
    monkeypatch.setenv("DURABLE_THREADS_ENABLE_SCRIPTED", "1")

    result = asyncio.run(_execute(_task(tmp_path)))

    assert result.status != "complete"
    assert result.status in {"review_required", "failed"}
    assert len(result.attempts) <= 2


def test_nonzero_return_code_fails_after_available_provider_is_excluded(
    tmp_path, monkeypatch
) -> None:
    _git_repo(tmp_path)
    _scenario(
        tmp_path,
        writes={"src/failure.py": "value = False\n"},
        changed_paths=["src/failure.py"],
        return_code=1,
        status="failed",
    )
    monkeypatch.setenv("DURABLE_THREADS_DECISION_ENGINE", "heuristic")
    monkeypatch.setenv("DURABLE_THREADS_ENABLE_SCRIPTED", "1")

    result = asyncio.run(_execute(_task(tmp_path, max_attempts=2)))

    assert result.status == "failed"
    assert len(result.attempts) == 1
    assert result.selected_provider == "scripted"


def test_human_gate_rejects_with_review_note(tmp_path, monkeypatch) -> None:
    _git_repo(tmp_path)
    monkeypatch.setenv("DURABLE_THREADS_DECISION_ENGINE", "heuristic")
    monkeypatch.setenv("DURABLE_THREADS_ENABLE_SCRIPTED", "1")

    async def run() -> object:
        queue = f"durable-test-{uuid.uuid4().hex}"
        async with await WorkflowEnvironment.start_time_skipping() as env:
            with ThreadPoolExecutor(max_workers=5) as activity_executor:
                async with Worker(
                    env.client,
                    task_queue=queue,
                    workflows=[DurableTaskWorkflow, AgentExecutionWorkflow],
                    activities=[
                        assess_task_activity,
                        route_executors_activity,
                        run_execution_activity,
                        verify_execution_activity,
                        assess_result_activity,
                    ],
                    activity_executor=activity_executor,
                ):
                    handle = await env.client.start_workflow(
                        DurableTaskWorkflow.run,
                        _task(
                            tmp_path,
                            objective="Design a distributed architecture control plane",
                        ),
                        id=f"workflow-{uuid.uuid4().hex}",
                        task_queue=queue,
                    )
                    status = None
                    for _ in range(100):
                        status = await handle.query(DurableTaskWorkflow.status)
                        if status["phase"] == "waiting_for_human_review":
                            break
                        await asyncio.sleep(0.01)
                    assert status is not None
                    assert status["phase"] == "waiting_for_human_review"
                    await handle.signal(
                        DurableTaskWorkflow.review,
                        ReviewDecision(approved=False, note="Not approved offline."),
                    )
                    return await handle.result()

    result = asyncio.run(run())

    assert result.status == "rejected"
    assert result.review_note == "Not approved offline."
