from __future__ import annotations

import asyncio
import json
import subprocess

import pytest

from durable_threads.evidence import parse_worker_result
from durable_threads.execution import (
    ExecutionError,
    ExecutionRequest,
    default_execution_registry,
)
from durable_threads.scripted import ScriptedExecutionBackend


def _git_repo(path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
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


def _request(path) -> ExecutionRequest:
    return ExecutionRequest(
        provider="scripted",
        prompt="test",
        cwd=str(path),
        session_name="test-session",
    )


def _write_scenario(path, **overrides) -> None:
    scenario = {
        "writes": {"src/result.txt": "generated\n"},
        "result": {
            "status": "complete",
            "changedPaths": ["src/result.txt"],
            "checks": ["python -m pytest -q: passed"],
            "remainingConcerns": [],
        },
        "returnCode": 0,
        "delaySeconds": 0.0,
        "stderr": "",
        "extraStdout": "",
    }
    scenario.update(overrides)
    scenario_dir = path / ".durable-threads"
    scenario_dir.mkdir()
    (scenario_dir / "scripted.json").write_text(json.dumps(scenario), encoding="utf-8")


def test_scripted_backend_writes_and_reports_result(tmp_path) -> None:
    _git_repo(tmp_path)
    _write_scenario(tmp_path)

    outcome = asyncio.run(ScriptedExecutionBackend().execute(_request(tmp_path)))

    assert outcome.return_code == 0
    assert (tmp_path / "src/result.txt").read_text(encoding="utf-8") == "generated\n"
    assert parse_worker_result(outcome.stdout).status == "complete"


def test_scripted_backend_rejects_path_escape(tmp_path) -> None:
    _git_repo(tmp_path)
    _write_scenario(tmp_path, writes={"../escape.txt": "unsafe"})

    with pytest.raises(ExecutionError, match="escapes cwd"):
        asyncio.run(ScriptedExecutionBackend().execute(_request(tmp_path)))


def test_scripted_backend_requires_scenario(tmp_path) -> None:
    _git_repo(tmp_path)

    with pytest.raises(ExecutionError, match="scenario not found"):
        asyncio.run(ScriptedExecutionBackend().execute(_request(tmp_path)))


def test_scripted_registry_availability(monkeypatch) -> None:
    monkeypatch.setenv("DURABLE_THREADS_ENABLE_SCRIPTED", "1")
    enabled = default_execution_registry(load_entry_points=False)
    assert enabled.available("scripted")

    monkeypatch.delenv("DURABLE_THREADS_ENABLE_SCRIPTED")
    disabled = default_execution_registry(load_entry_points=False)
    assert not disabled.available("scripted")
