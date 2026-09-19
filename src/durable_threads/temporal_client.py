"""CLI client for starting, querying, and reviewing Durable Threads workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path

from temporalio.client import Client

from .temporal_contracts import ReviewDecision, TaskRunInput
from .temporal_workflows import DurableTaskWorkflow


def _connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--address", default=os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    parser.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="durable-threads-temporal")
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="start a durable engineering task")
    _connection_args(start)
    start.add_argument(
        "--task-queue",
        default=os.getenv("DURABLE_THREADS_TASK_QUEUE", "durable-threads"),
    )
    start.add_argument("--workflow-id")
    start.add_argument("--objective", required=True)
    start.add_argument("--allowed-path", action="append", required=True)
    start.add_argument("--acceptance", action="append", required=True)
    start.add_argument("--constraint", action="append", default=[])
    start.add_argument("--cwd", type=Path, default=Path.cwd())
    start.add_argument("--preferred-provider", action="append", default=[])
    start.add_argument("--model", default="default")
    start.add_argument("--effort", default="medium")
    start.add_argument("--max-attempts", type=int, default=2)
    start.add_argument("--speculative-parallelism", type=int, default=2)
    start.add_argument("--human-gate-at", default="R4")
    start.add_argument("--wait-for-human-review", action="store_true")
    start.add_argument("--base-ref")
    start.add_argument("--detach", action="store_true")

    review = commands.add_parser("review", help="approve or reject a waiting workflow")
    _connection_args(review)
    review.add_argument("--workflow-id", required=True)
    choice = review.add_mutually_exclusive_group(required=True)
    choice.add_argument("--approve", action="store_true")
    choice.add_argument("--reject", action="store_true")
    review.add_argument("--note", default="")

    status = commands.add_parser("status", help="query workflow policy state")
    _connection_args(status)
    status.add_argument("--workflow-id", required=True)
    return parser


async def _connect(args: argparse.Namespace) -> Client:
    return await Client.connect(args.address, namespace=args.namespace)


async def _start(args: argparse.Namespace) -> int:
    client = await _connect(args)
    workflow_id = args.workflow_id or f"dt-{uuid.uuid4().hex[:16]}"
    task = TaskRunInput(
        objective=args.objective,
        allowed_paths=args.allowed_path,
        acceptance=args.acceptance,
        cwd=str(args.cwd.resolve()),
        constraints=args.constraint,
        preferred_providers=args.preferred_provider,
        model_selector=args.model,
        reasoning_effort=args.effort,
        base_ref=args.base_ref,
        max_attempts=args.max_attempts,
        speculative_parallelism=args.speculative_parallelism,
        human_gate_at=args.human_gate_at,
        wait_for_human_review=args.wait_for_human_review,
    )
    handle = await client.start_workflow(
        DurableTaskWorkflow.run,
        task,
        id=workflow_id,
        task_queue=args.task_queue,
    )
    if args.detach:
        print(json.dumps({"workflowId": workflow_id, "started": True}, indent=2))
        return 0
    result = await handle.result()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.status == "complete" else 2


async def _review(args: argparse.Namespace) -> int:
    client = await _connect(args)
    handle = client.get_workflow_handle(args.workflow_id)
    await handle.signal(
        DurableTaskWorkflow.review,
        ReviewDecision(approved=bool(args.approve), note=args.note),
    )
    print(json.dumps({"workflowId": args.workflow_id, "reviewSent": True}, indent=2))
    return 0


async def _status(args: argparse.Namespace) -> int:
    client = await _connect(args)
    handle = client.get_workflow_handle(args.workflow_id)
    payload = await handle.query(DurableTaskWorkflow.status)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "start":
        return asyncio.run(_start(args))
    if args.command == "review":
        return asyncio.run(_review(args))
    if args.command == "status":
        return asyncio.run(_status(args))
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
