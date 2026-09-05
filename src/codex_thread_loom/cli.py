"""Command line helpers for packet planning and local evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from .config import ConfigError, load_roster
from .ledger import Ledger
from .packets import build_packet
from .routing import catalog_from_payload, resolve_model


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _plan(args: argparse.Namespace) -> int:
    roster = load_roster(args.roster)
    run_id = args.run_id or f"loom-{uuid.uuid4().hex[:12]}"
    packets = []
    for worker in roster.workers:
        packet = build_packet(
            worker,
            run_id=run_id,
            objective=args.objective,
            allowed_paths=args.allowed_path,
            acceptance=args.acceptance,
            constraints=args.constraint,
        )
        packets.append(
            {
                "worker": {
                    "name": worker.name,
                    "threadTitle": worker.thread_title,
                    "threadId": worker.thread_id,
                    "parallel": worker.parallel,
                },
                "packet": packet.to_dict(),
            }
        )
    _dump(
        {
            "schemaVersion": 1,
            "runId": run_id,
            "project": roster.project_name,
            "planner": {
                "role": roster.planner.role,
                "modelSelector": roster.planner.model_selector,
                "reasoningEffort": roster.planner.reasoning_effort,
            },
            "reviewer": {
                "role": roster.reviewer.role,
                "modelSelector": roster.reviewer.model_selector,
                "reasoningEffort": roster.reviewer.reasoning_effort,
            },
            "policy": {
                "maxParallelWorkers": roster.max_parallel_workers,
                "resultMaxChars": roster.result_max_chars,
                "allowThreadCreation": roster.allow_thread_creation,
            },
            "workers": packets,
        }
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    roster = load_roster(args.roster)
    _dump(
        {
            "valid": True,
            "project": roster.project_name,
            "workers": [worker.name for worker in roster.workers],
            "threadTitles": [worker.thread_title for worker in roster.workers],
        }
    )
    return 0


def _resolve(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    resolution = resolve_model(catalog_from_payload(payload), args.selector)
    _dump(
        {
            "matched": resolution.matched,
            "reason": resolution.reason,
            "model": None
            if resolution.model is None
            else {
                "id": resolution.model.model_id,
                "displayName": resolution.model.display_name,
                "tier": resolution.model.tier,
            },
        }
    )
    return 0 if resolution.model is not None else 2


def _doctor(_: argparse.Namespace) -> int:
    codex_path = shutil.which("codex")
    result: dict[str, Any] = {"codex": {"available": codex_path is not None}}
    if codex_path is not None:
        try:
            completed = subprocess.run(
                [codex_path, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            result["codex"]["path"] = codex_path
            result["codex"]["version"] = (completed.stdout or completed.stderr).strip()
            result["codex"]["exitCode"] = completed.returncode
        except (OSError, subprocess.SubprocessError) as exc:
            result["codex"]["error"] = str(exc)
    result["note"] = "This helper does not start threads or call provider APIs."
    _dump(result)
    return 0 if result["codex"]["available"] else 1


def _record(args: argparse.Namespace) -> int:
    task = Ledger(args.ledger).record_task(
        task_id=args.task_id,
        role=args.role,
        status=args.status,
        thread_id=args.thread_id,
        result=args.result,
        usage=json.loads(args.usage) if args.usage else None,
    )
    _dump({"recorded": task})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-thread-loom")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-roster", help="validate a JSON roster")
    validate.add_argument("roster", type=Path)
    validate.set_defaults(handler=_validate)

    plan = subparsers.add_parser("plan", help="create compact worker packets")
    plan.add_argument("--roster", type=Path, required=True)
    plan.add_argument("--objective", required=True)
    plan.add_argument("--allowed-path", action="append", required=True)
    plan.add_argument("--acceptance", action="append", required=True)
    plan.add_argument("--constraint", action="append", default=[])
    plan.add_argument("--run-id")
    plan.set_defaults(handler=_plan)

    resolve = subparsers.add_parser("resolve-model", help="resolve a role against a model catalog")
    resolve.add_argument("--catalog", type=Path, required=True)
    resolve.add_argument("--selector", required=True)
    resolve.set_defaults(handler=_resolve)

    doctor = subparsers.add_parser("doctor", help="check the local Codex executable")
    doctor.set_defaults(handler=_doctor)

    record = subparsers.add_parser("record", help="write one redacted task record")
    record.add_argument("--ledger", type=Path, required=True)
    record.add_argument("--task-id", required=True)
    record.add_argument("--role", required=True)
    record.add_argument("--status", required=True)
    record.add_argument("--thread-id")
    record.add_argument("--result")
    record.add_argument("--usage", help="JSON object with provider usage counters")
    record.set_defaults(handler=_record)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
