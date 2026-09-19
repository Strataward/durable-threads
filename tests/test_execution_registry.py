from __future__ import annotations

from durable_threads.execution import (
    ExecutionRegistry,
    ExecutionRequirements,
    ExecutorDescriptor,
    ExecutorPlugin,
)


def test_registry_accepts_provider_plugins_without_core_provider_enum() -> None:
    registry = ExecutionRegistry()
    registry.register(
        ExecutorPlugin(
            descriptor=ExecutorDescriptor(
                executor_id="future-agent",
                provider="future-ai",
                runtime="Future Agent",
                capabilities=frozenset({"code", "filesystem", "git", "structured-output"}),
                persistent_sessions=True,
                headless=True,
                structured_output=True,
                supports_effort=True,
            ),
            availability_probe=lambda: True,
        )
    )
    selected = registry.select(
        ExecutionRequirements(
            capabilities=frozenset({"code", "filesystem", "git"}),
            headless=True,
            preferred_providers=("future-ai",),
        )
    )
    assert selected[0].descriptor.provider == "future-ai"
    assert selected[0].descriptor.executor_id == "future-agent"
