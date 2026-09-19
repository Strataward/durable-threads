"""Measure durable-mode orchestration overhead against a running Temporal server.

The benchmark runs the real ``DurableTaskWorkflow`` with the deterministic
``scripted`` executor so provider variance is removed. What remains is the cost
Durable Threads adds around execution: Temporal scheduling, Activity round
trips, child workflow start/complete, decision-engine latency (heuristic or
Jev), and evidence verification against the git diff.

Scenarios:

- ``happy``: worker completes, evidence matches the diff, task accepted.
- ``mismatch``: worker claims a path it did not change; policy must not accept.
- ``crash``: the worker process is SIGKILLed mid-execution; a replacement
  worker must drive the workflow to a deterministic escalation without
  re-running the writer.

Usage:

    python scripts/bench_durable.py --runs 10 --engine heuristic --out out.json
    python scripts/bench_durable.py --scenario crash --runs 2 --engine heuristic

Requires ``durable-threads[durable]`` and a Temporal frontend (default
``localhost:7233``). Jev runs additionally require ``TYPESAFE_API_KEY``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from temporalio.api.enums.v1 import EventType
from temporalio.client import Client, WorkflowHandle

from durable_threads.decisions import decision_engine_from_env
from durable_threads.evidence import git_changed_paths, parse_worker_result, validate_evidence
from durable_threads.execution import ExecutionRequest
from durable_threads.intelligence import assess_result, assess_task
from durable_threads.scripted import ScriptedExecutionBackend
from durable_threads.temporal_contracts import TaskRunInput
from durable_threads.temporal_workflows import DurableTaskWorkflow

OBJECTIVE = "Add a helper that returns missing page indexes in the shared page-index module"
ALLOWED = ["src/**"]
ACCEPTANCE = ["Focused tests pass", "No files outside src/ change"]
WRITE_PATH = "src/page_index.py"
WRITE_BODY = (
    "def missing_page_indexes(present, total):\n"
    "    return [i for i in range(total) if i not in set(present)]\n"
)


def _git(path: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=bench",
            "-c",
            "user.email=bench@example.com",
            *args,
        ],
        check=True,
        capture_output=True,
    )


def make_repo(root: Path, scenario: str, *, delay_seconds: float) -> Path:
    repo = root / f"repo-{uuid.uuid4().hex[:8]}"
    repo.mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo / ".gitignore").write_text(".durable-threads/\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    claimed = [WRITE_PATH] if scenario != "mismatch" else ["src/other.py"]
    payload = {
        "writes": {WRITE_PATH: WRITE_BODY},
        "result": {
            "status": "complete",
            "changedPaths": claimed,
            "checks": ["python -m pytest -q tests/test_page_index.py: 3 passed"],
            "remainingConcerns": [],
        },
        "returnCode": 0,
        "delaySeconds": delay_seconds,
        "stderr": "",
        "extraStdout": "",
    }
    (repo / ".durable-threads").mkdir()
    (repo / ".durable-threads" / "scripted.json").write_text(json.dumps(payload), encoding="utf-8")
    return repo


def task_input(repo: Path) -> TaskRunInput:
    return TaskRunInput(
        objective=OBJECTIVE,
        allowed_paths=ALLOWED,
        acceptance=ACCEPTANCE,
        cwd=str(repo),
        preferred_providers=["scripted"],
        required_capabilities=["code", "filesystem", "git"],
        max_attempts=2,
        provider_timeout_seconds=120,
    )


class WorkerProcess:
    """The real CLI worker in a child process so a crash is a real crash."""

    def __init__(self, *, address: str, namespace: str, task_queue: str, env: dict[str, str]):
        self.args = [
            sys.executable,
            "-m",
            "durable_threads.temporal_worker",
            "--address",
            address,
            "--namespace",
            namespace,
            "--task-queue",
            task_queue,
        ]
        self.env = env
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self.process = subprocess.Popen(self.args, env=self.env)
        time.sleep(1.5)

    def kill(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGKILL)
            self.process.wait()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def _ts(event: Any) -> datetime:
    return event.event_time.ToDatetime()


async def phase_durations(handle: WorkflowHandle) -> dict[str, Any]:
    """Derive per-phase durations from workflow history event timestamps."""

    history = await handle.fetch_history()
    events = list(history.events)
    by_id = {event.event_id: event for event in events}
    phases: dict[str, float] = {}
    children: list[str] = []
    started = completed = None
    for event in events:
        kind = event.event_type
        if kind == EventType.EVENT_TYPE_WORKFLOW_EXECUTION_STARTED:
            started = _ts(event)
        elif kind in (
            EventType.EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED,
            EventType.EVENT_TYPE_WORKFLOW_EXECUTION_FAILED,
        ):
            completed = _ts(event)
        elif kind == EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED:
            attrs = event.activity_task_completed_event_attributes
            scheduled = by_id[attrs.scheduled_event_id]
            name = scheduled.activity_task_scheduled_event_attributes.activity_type.name
            delta = (_ts(event) - _ts(scheduled)).total_seconds()
            phases[name] = phases.get(name, 0.0) + delta
        elif kind == EventType.EVENT_TYPE_ACTIVITY_TASK_FAILED:
            attrs = event.activity_task_failed_event_attributes
            scheduled = by_id[attrs.scheduled_event_id]
            name = scheduled.activity_task_scheduled_event_attributes.activity_type.name
            phases[f"{name}:failed"] = (_ts(event) - _ts(scheduled)).total_seconds()
        elif kind == EventType.EVENT_TYPE_ACTIVITY_TASK_TIMED_OUT:
            attrs = event.activity_task_timed_out_event_attributes
            scheduled = by_id[attrs.scheduled_event_id]
            name = scheduled.activity_task_scheduled_event_attributes.activity_type.name
            phases[f"{name}:timed_out"] = (_ts(event) - _ts(scheduled)).total_seconds()
        elif kind == EventType.EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_STARTED:
            attrs = event.child_workflow_execution_started_event_attributes
            children.append(attrs.workflow_execution.workflow_id)
        elif kind in (
            EventType.EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_COMPLETED,
            EventType.EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_FAILED,
        ):
            attrs = (
                event.child_workflow_execution_completed_event_attributes
                if kind == EventType.EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_COMPLETED
                else event.child_workflow_execution_failed_event_attributes
            )
            initiated = by_id[attrs.initiated_event_id]
            delta = (_ts(event) - _ts(initiated)).total_seconds()
            phases["child_workflow"] = phases.get("child_workflow", 0.0) + delta
    total = (completed - started).total_seconds() if started and completed else None
    return {"total": total, "phases": phases, "events": len(events), "children": children}


async def run_direct(repo: Path) -> dict[str, Any]:
    """Same policy loop without Temporal: the no-orchestrator baseline."""

    engine = decision_engine_from_env()
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    assessment = await assess_task(
        engine, objective=OBJECTIVE, allowed_paths=ALLOWED, acceptance=ACCEPTANCE
    )
    timings["assess_task"] = time.perf_counter() - t0

    t1 = time.perf_counter()
    outcome = await ScriptedExecutionBackend().execute(
        ExecutionRequest(provider="scripted", prompt="bench", cwd=str(repo), timeout_seconds=120)
    )
    timings["execute"] = time.perf_counter() - t1

    t2 = time.perf_counter()
    evidence = parse_worker_result(outcome.stdout)
    actual = git_changed_paths(str(repo), None)
    try:
        verified = validate_evidence(evidence, allowed_paths=ALLOWED, actual_paths=actual)
        complete = verified.status == "complete"
        checks = list(verified.checks)
    except ValueError:
        complete = False
        checks = []
    timings["verify"] = time.perf_counter() - t2

    t3 = time.perf_counter()
    result = await assess_result(
        engine,
        objective=OBJECTIVE,
        risk_class=assessment.final_risk,
        provider="scripted",
        exit_code=outcome.return_code,
        evidence_complete=complete,
        worker_result=outcome.stdout,
        checks=checks,
    )
    timings["assess_result"] = time.perf_counter() - t3
    return {
        "total": time.perf_counter() - t0,
        "phases": timings,
        "accepted": result.accepted,
        "risk": assessment.final_risk,
    }


async def run_temporal(
    client: Client, *, task_queue: str, repo: Path
) -> tuple[dict[str, Any], WorkflowHandle]:
    workflow_id = f"dt-bench-{uuid.uuid4().hex[:12]}"
    t0 = time.perf_counter()
    handle = await client.start_workflow(
        DurableTaskWorkflow.run, task_input(repo), id=workflow_id, task_queue=task_queue
    )
    result = await handle.result()
    wall = time.perf_counter() - t0
    history = await phase_durations(handle)
    child_phases: dict[str, float] = {}
    for child_id in history["children"]:
        child = await phase_durations(client.get_workflow_handle(child_id))
        for name, value in child["phases"].items():
            child_phases[name] = child_phases.get(name, 0.0) + value
    return (
        {
            "workflowId": workflow_id,
            "status": result.status,
            "risk": result.final_risk,
            "attempts": len(result.attempts),
            "clientWall": wall,
            "historyTotal": history["total"],
            "parentPhases": history["phases"],
            "childPhases": child_phases,
            "historyEvents": history["events"],
            "decisionEngine": (
                result.task_assessment.get("decision", {}).get("engine")
                if isinstance(result.task_assessment, dict)
                else None
            ),
        },
        handle,
    )


async def run_crash(
    client: Client,
    *,
    task_queue: str,
    repo: Path,
    worker_env: dict[str, str],
    address: str,
    namespace: str,
) -> dict[str, Any]:
    worker = WorkerProcess(
        address=address, namespace=namespace, task_queue=task_queue, env=worker_env
    )
    worker.start()
    workflow_id = f"dt-crash-{uuid.uuid4().hex[:12]}"
    t0 = time.perf_counter()
    handle = await client.start_workflow(
        DurableTaskWorkflow.run, task_input(repo), id=workflow_id, task_queue=task_queue
    )
    # Wait until the parent reports the executing phase, then kill the worker mid-write.
    while True:
        status = await handle.query(DurableTaskWorkflow.status)
        if status["phase"] == "executing":
            break
        await asyncio.sleep(0.2)
    await asyncio.sleep(2.0)
    kill_at = time.perf_counter() - t0
    worker.kill()
    replacement = WorkerProcess(
        address=address, namespace=namespace, task_queue=task_queue, env=worker_env
    )
    replacement.start()
    try:
        result = await handle.result()
    finally:
        replacement.stop()
    wall = time.perf_counter() - t0
    history = await phase_durations(handle)
    child_phases: dict[str, float] = {}
    for child_id in history["children"]:
        child = await phase_durations(client.get_workflow_handle(child_id))
        child_phases.update(child["phases"])
    written = (repo / WRITE_PATH).exists()
    return {
        "workflowId": workflow_id,
        "status": result.status,
        "attempts": len(result.attempts),
        "killedAfter": kill_at,
        "clientWall": wall,
        "historyTotal": history["total"],
        "childPhases": child_phases,
        "writerReExecuted": False if not written else None,
        "intervention": (
            result.attempts[-1].result_assessment.get("intervention") if result.attempts else None
        ),
        "verificationStatus": (
            result.attempts[-1].verification.get("status") if result.attempts else None
        ),
    }


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return {
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p95": ordered[p95_index],
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
    }


async def main_async(args: argparse.Namespace) -> int:
    env = dict(os.environ)
    env["DURABLE_THREADS_DECISION_ENGINE"] = args.engine
    env["DURABLE_THREADS_ENABLE_SCRIPTED"] = "1"
    os.environ.update(
        {
            "DURABLE_THREADS_DECISION_ENGINE": args.engine,
            "DURABLE_THREADS_ENABLE_SCRIPTED": "1",
        }
    )
    if args.engine == "jev" and not os.environ.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY is required for --engine jev", file=sys.stderr)
        return 2

    task_queue = args.task_queue or f"dt-bench-{uuid.uuid4().hex[:8]}"
    root = Path(tempfile.mkdtemp(prefix="dt-bench-"))
    client = await Client.connect(args.address, namespace=args.namespace)
    report: dict[str, Any] = {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "scenario": args.scenario,
        "engine": args.engine,
        "runs": args.runs,
        "temporal": {"address": args.address, "namespace": args.namespace, "taskQueue": task_queue},
        "delaySeconds": args.delay,
        "results": [],
    }
    try:
        if args.scenario == "crash":
            for _ in range(args.runs):
                repo = make_repo(root, "happy", delay_seconds=max(args.delay, 15.0))
                report["results"].append(
                    await run_crash(
                        client,
                        task_queue=task_queue,
                        repo=repo,
                        worker_env=env,
                        address=args.address,
                        namespace=args.namespace,
                    )
                )
        else:
            worker = WorkerProcess(
                address=args.address, namespace=args.namespace, task_queue=task_queue, env=env
            )
            worker.start()
            try:
                # Warm-up run absorbs worker/registry cold start; it is reported separately.
                warm_repo = make_repo(root, args.scenario, delay_seconds=args.delay)
                warm, _ = await run_temporal(client, task_queue=task_queue, repo=warm_repo)
                report["warmup"] = warm
                for _ in range(args.runs):
                    repo = make_repo(root, args.scenario, delay_seconds=args.delay)
                    temporal_result, _ = await run_temporal(
                        client, task_queue=task_queue, repo=repo
                    )
                    direct_repo = make_repo(root, args.scenario, delay_seconds=args.delay)
                    direct = await run_direct(direct_repo)
                    report["results"].append({"temporal": temporal_result, "direct": direct})
            finally:
                worker.stop()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if args.scenario != "crash":
        walls = [r["temporal"]["clientWall"] for r in report["results"]]
        hist = [r["temporal"]["historyTotal"] for r in report["results"]]
        direct = [r["direct"]["total"] for r in report["results"]]
        overhead = [w - d for w, d in zip(walls, direct, strict=True)]
        phase_names = sorted(
            {
                name
                for r in report["results"]
                for name in {**r["temporal"]["parentPhases"], **r["temporal"]["childPhases"]}
            }
        )
        phases = {
            name: summarize(
                [
                    {**r["temporal"]["parentPhases"], **r["temporal"]["childPhases"]}.get(name, 0.0)
                    for r in report["results"]
                ]
            )
            for name in phase_names
        }
        direct_phases = {
            name: summarize([r["direct"]["phases"][name] for r in report["results"]])
            for name in report["results"][0]["direct"]["phases"]
        }
        report["summary"] = {
            "statuses": sorted({r["temporal"]["status"] for r in report["results"]}),
            "temporalClientWall": summarize(walls),
            "temporalHistoryTotal": summarize(hist),
            "directTotal": summarize(direct),
            "orchestrationOverhead": summarize(overhead),
            "temporalPhases": phases,
            "directPhases": direct_phases,
            "historyEvents": summarize([r["temporal"]["historyEvents"] for r in report["results"]]),
        }
    else:
        report["summary"] = {
            "statuses": sorted({r["status"] for r in report["results"]}),
            "timeToEscalation": summarize([r["clientWall"] for r in report["results"]]),
            "writerReExecuted": any(r["writerReExecuted"] for r in report["results"]),
        }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--address", default=os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    parser.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))
    parser.add_argument("--task-queue")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--engine", choices=["heuristic", "jev"], default="heuristic")
    parser.add_argument("--scenario", choices=["happy", "mismatch", "crash"], default="happy")
    parser.add_argument(
        "--delay", type=float, default=0.0, help="simulated provider execution seconds"
    )
    parser.add_argument("--out", help="write the full JSON report here")
    args = parser.parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
