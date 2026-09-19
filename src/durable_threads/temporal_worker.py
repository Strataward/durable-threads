"""Worker entry point for Durable Threads durable mode."""

from __future__ import annotations

import argparse
import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .temporal_activities import (
    assess_result_activity,
    assess_task_activity,
    route_executors_activity,
    run_execution_activity,
    verify_execution_activity,
)
from .temporal_workflows import AgentExecutionWorkflow, DurableTaskWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="durable-threads-temporal-worker")
    parser.add_argument(
        "--address",
        default=os.getenv("TEMPORAL_ADDRESS", "localhost:7233"),
        help="Temporal frontend address",
    )
    parser.add_argument(
        "--namespace",
        default=os.getenv("TEMPORAL_NAMESPACE", "default"),
    )
    parser.add_argument(
        "--task-queue",
        default=os.getenv("DURABLE_THREADS_TASK_QUEUE", "durable-threads"),
    )
    return parser


async def run_worker(*, address: str, namespace: str, task_queue: str) -> None:
    client = await Client.connect(address, namespace=namespace)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[DurableTaskWorkflow, AgentExecutionWorkflow],
        activities=[
            assess_task_activity,
            route_executors_activity,
            run_execution_activity,
            verify_execution_activity,
            assess_result_activity,
        ],
    )
    await worker.run()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(arg)
    asyncio.run(
        run_worker(
            address=args.address,
            namespace=args.namespace,
            task_queue=args.task_queue,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
