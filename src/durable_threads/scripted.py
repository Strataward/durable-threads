"""Deterministic scripted executor for offline durable-mode runs."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from .execution import (
    ExecutionError,
    ExecutionOutcome,
    ExecutionRequest,
    ExecutorDescriptor,
    ExecutorPlugin,
)


class ScriptedExecutionBackend:
    """Execute a checked-in scenario from the task working directory."""

    async def execute(self, request: ExecutionRequest) -> ExecutionOutcome:
        if request.provider != "scripted":
            raise ExecutionError(
                f"backend 'scripted' cannot execute provider {request.provider!r}"
            )
        cwd = Path(request.cwd).expanduser()
        if not cwd.is_dir():
            raise ExecutionError(f"provider working directory not found: {cwd}")
        scenario_path = cwd / ".durable-threads" / "scripted.json"
        if not scenario_path.is_file():
            raise ExecutionError(f"scripted scenario not found: {scenario_path}")
        scenario = _load_scenario(scenario_path)
        delay_seconds = scenario["delaySeconds"]
        await asyncio.sleep(delay_seconds)

        for raw_path, content in scenario["writes"].items():
            path = _safe_write_path(cwd, raw_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        result = {"provider": request.provider, **scenario["result"]}
        stdout = f'{scenario["extraStdout"]}\n{json.dumps(result)}'
        return ExecutionOutcome(
            provider=request.provider,
            return_code=scenario["returnCode"],
            stdout=stdout,
            stderr=scenario["stderr"],
            session_id=f"scripted-{request.session_name}",
            usage={"inputTokens": 0, "outputTokens": 0},
        )


def _load_scenario(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"could not load scripted scenario {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ExecutionError("scripted scenario must be a JSON object")

    writes = payload.get("writes", {})
    if not isinstance(writes, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in writes.items()
    ):
        raise ExecutionError(
            "scripted scenario writes must be an object of string paths to strings"
        )
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ExecutionError("scripted scenario result must be an object")
    return_code = payload.get("returnCode", 0)
    if type(return_code) is not int:
        raise ExecutionError("scripted scenario returnCode must be an integer")
    delay_seconds = payload.get("delaySeconds", 0.0)
    if (
        isinstance(delay_seconds, bool)
        or not isinstance(delay_seconds, (int, float))
        or delay_seconds < 0
    ):
        raise ExecutionError("scripted scenario delaySeconds must be a non-negative number")
    stderr = payload.get("stderr", "")
    if not isinstance(stderr, str):
        raise ExecutionError("scripted scenario stderr must be a string")
    extra_stdout = payload.get("extraStdout", "")
    if not isinstance(extra_stdout, str):
        raise ExecutionError("scripted scenario extraStdout must be a string")
    return {
        "writes": writes,
        "result": result,
        "returnCode": return_code,
        "delaySeconds": float(delay_seconds),
        "stderr": stderr,
        "extraStdout": extra_stdout,
    }


def _safe_write_path(cwd: Path, raw_path: str) -> Path:
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ExecutionError(f"scripted write path escapes cwd: {raw_path!r}")
    path = (cwd / relative).resolve()
    try:
        path.relative_to(cwd.resolve())
    except ValueError as exc:
        raise ExecutionError(f"scripted write path escapes cwd: {raw_path!r}") from exc
    return path


def scripted_executor_plugin() -> ExecutorPlugin:
    return ExecutorPlugin(
        descriptor=ExecutorDescriptor(
            executor_id="scripted",
            provider="scripted",
            runtime="Scripted test executor",
            capabilities=frozenset(
                {"code", "filesystem", "git", "shell", "structured-output"}
            ),
            headless=True,
            structured_output=True,
            persistent_sessions=False,
            supports_effort=True,
            metadata={"protocol": "scripted"},
        ),
        backend_factory=ScriptedExecutionBackend,
        availability_probe=lambda: os.environ.get("DURABLE_THREADS_ENABLE_SCRIPTED") == "1",
    )
