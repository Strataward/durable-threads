"""Time the deterministic policy primitives in isolation.

These are the only code paths a Rust or WebAssembly port could speed up:
risk classification, evidence parsing and validation, executor ranking, worker
routing, and the offline heuristic decision engine. No network, no Temporal,
no provider process. The output tells you how many microseconds each primitive
costs per call so you can compare it with the milliseconds Temporal adds and the
seconds a coding agent takes.

Usage:

    python scripts/bench_primitives.py --iterations 20000
    python scripts/bench_primitives.py --out docs/benchmarks/data/primitives.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
import timeit
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from durable_threads.config import load_roster
from durable_threads.decisions import HeuristicDecisionEngine
from durable_threads.evidence import parse_worker_result, validate_evidence
from durable_threads.execution import ExecutionRequirements, default_execution_registry
from durable_threads.intelligence import assess_task
from durable_threads.risk import classify_risk
from durable_threads.routing import select_workers

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "examples" / "multi-provider-roster.json"

OBJECTIVES = [
    "Fix a spelling typo in the README",
    "Add a helper that returns missing page indexes without mutating inputs",
    "Update the public API webhook payload to include a schema version",
    "Implement refresh-token rotation with replay rejection in the auth module",
    "Migrate the control plane to a multi-region architecture",
]
ALLOWED = ["src/**", "tests/**"]
ACCEPTANCE = ["Focused tests pass", "No files outside src/ change"]
WORKER_RESULT = json.dumps(
    {
        "status": "complete",
        "provider": "scripted",
        "changedPaths": ["src/page_index.py", "tests/test_page_index.py"],
        "checks": ["python -m pytest -q tests/test_page_index.py: 3 passed", "ruff check .: ok"],
        "remainingConcerns": [],
    }
)
ACTUAL_PATHS = ["src/page_index.py", "tests/test_page_index.py"]


def _bench(name: str, fn: Any, iterations: int) -> dict[str, float]:
    fn()  # warm caches, compile regexes
    total = timeit.timeit(fn, number=iterations)
    return {"name": name, "iterations": iterations, "us_per_call": total / iterations * 1e6}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--out", help="write the JSON report here")
    args = parser.parse_args(argv)
    iterations = args.iterations

    os.environ["DURABLE_THREADS_ENABLE_SCRIPTED"] = "1"
    roster = load_roster(ROSTER)
    registry = default_execution_registry()
    requirements = ExecutionRequirements(
        capabilities=frozenset({"code", "filesystem", "git"}),
        headless=True,
        structured_output=True,
        preferred_providers=("scripted",),
    )
    engine = HeuristicDecisionEngine()
    loop = asyncio.new_event_loop()

    def classify_all() -> None:
        for objective in OBJECTIVES:
            classify_risk(objective=objective, allowed_paths=ALLOWED, acceptance=ACCEPTANCE)

    def evidence() -> None:
        validate_evidence(
            parse_worker_result(WORKER_RESULT), allowed_paths=ALLOWED, actual_paths=ACTUAL_PATHS
        )

    def rank() -> None:
        registry.rank(requirements, available_only=False)

    def route() -> None:
        select_workers(
            roster, objective=OBJECTIVES[1], allowed_paths=ALLOWED, acceptance=ACCEPTANCE
        )

    def heuristic() -> None:
        loop.run_until_complete(
            assess_task(
                engine, objective=OBJECTIVES[3], allowed_paths=ALLOWED, acceptance=ACCEPTANCE
            )
        )

    results = [
        _bench(f"classify_risk x{len(OBJECTIVES)} objectives", classify_all, iterations),
        _bench("parse_worker_result + validate_evidence", evidence, iterations),
        _bench("ExecutionRegistry.rank", rank, iterations),
        _bench("select_workers (roster routing)", route, iterations),
        _bench("assess_task with HeuristicDecisionEngine", heuristic, max(1, iterations // 10)),
    ]
    loop.close()
    report = {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "results": results,
    }
    print("| Primitive | Iterations | µs / call |")
    print("| --- | ---: | ---: |")
    for row in results:
        print(f"| `{row['name']}` | {row['iterations']} | {row['us_per_call']:.1f} |")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
