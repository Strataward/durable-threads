from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("temporalio")

from durable_threads import temporal_worker


def test_build_parser_sync_activity_default_and_environment(monkeypatch) -> None:
    assert temporal_worker.build_parser().parse_args([]).max_sync_activities == 8

    monkeypatch.setenv("DURABLE_THREADS_MAX_SYNC_ACTIVITIES", "3")

    assert temporal_worker.build_parser().parse_args([]).max_sync_activities == 3


def test_run_worker_passes_sync_activity_executor(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def connect(address: str, *, namespace: str):
        return object()

    class FakeWorker:
        def __init__(self, client, **kwargs) -> None:
            captured.update(kwargs)

        async def run(self) -> None:
            return None

    monkeypatch.setattr(temporal_worker.Client, "connect", connect)
    monkeypatch.setattr(temporal_worker, "Worker", FakeWorker)

    asyncio.run(
        temporal_worker.run_worker(
            address="localhost:7233",
            namespace="default",
            task_queue="test",
            max_sync_activities=3,
        )
    )

    executor = captured["activity_executor"]
    assert isinstance(executor, ThreadPoolExecutor)
    assert executor._max_workers == 3
