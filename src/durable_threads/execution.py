"""Provider-agnostic executor registry, routing, and backend contracts."""

from __future__ import annotations

import asyncio
import importlib.metadata
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .providers import (
    ProviderError,
    build_invocation,
    extract_session_id,
    extract_usage,
    get_capabilities,
    provider_status,
)

_EXECUTOR_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_PLUGIN_GROUP = "durable_threads.executors"


class ExecutionError(RuntimeError):
    """Raised when no safe executor can satisfy a request."""


@dataclass(frozen=True)
class ExecutorDescriptor:
    """Stable capabilities used by routing, independent of model/provider names."""

    executor_id: str
    provider: str
    runtime: str
    capabilities: frozenset[str]
    persistent_sessions: bool
    headless: bool
    structured_output: bool
    supports_effort: bool
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _EXECUTOR_ID.fullmatch(self.executor_id):
            raise ValueError(f"invalid executor_id: {self.executor_id!r}")
        if not _EXECUTOR_ID.fullmatch(self.provider):
            raise ValueError(f"invalid provider id: {self.provider!r}")
        if not self.runtime.strip():
            raise ValueError("runtime must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "executorId": self.executor_id,
            "provider": self.provider,
            "runtime": self.runtime,
            "capabilities": sorted(self.capabilities),
            "persistentSessions": self.persistent_sessions,
            "headless": self.headless,
            "structuredOutput": self.structured_output,
            "supportsEffort": self.supports_effort,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ExecutionRequirements:
    """What execution needs, without naming a vendor or model."""

    capabilities: frozenset[str] = frozenset({"code", "filesystem", "git"})
    headless: bool = False
    persistent_session: bool = False
    structured_output: bool = False
    effort_control: bool = False
    preferred_providers: tuple[str, ...] = ()
    excluded_providers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionSelection:
    descriptor: ExecutorDescriptor
    score: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "executor": self.descriptor.to_dict(),
            "score": self.score,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class ExecutionRequest:
    provider: str
    prompt: str
    cwd: str
    model_selector: str = "default"
    reasoning_effort: str = "medium"
    session_id: str | None = None
    session_name: str | None = None
    executable: str | None = None
    timeout_seconds: int = 3600
    max_output_chars: int = 20_000


@dataclass(frozen=True)
class ExecutionOutcome:
    provider: str
    return_code: int
    stdout: str
    stderr: str
    session_id: str | None
    usage: Mapping[str, int] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "returnCode": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "sessionId": self.session_id,
            "usage": dict(self.usage) if self.usage is not None else None,
        }


class ExecutionBackend(Protocol):
    async def execute(self, request: ExecutionRequest) -> ExecutionOutcome:
        """Execute exactly one provider/runtime request."""


class CliExecutionBackend:
    """Async backend for the existing CLI adapters.

    Subprocesses are launched without a shell. Cancellation terminates the child
    process so Temporal activity cancellation does not leave an intentional
    orphaned writer behind.
    """

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def execute(self, request: ExecutionRequest) -> ExecutionOutcome:
        if request.provider != self.provider:
            raise ExecutionError(
                f"backend {self.provider!r} cannot execute provider {request.provider!r}"
            )
        invocation = build_invocation(
            provider=request.provider,
            prompt=request.prompt,
            model_selector=request.model_selector,
            reasoning_effort=request.reasoning_effort,
            session_id=request.session_id,
            session_name=request.session_name,
            executable=request.executable,
        )
        if invocation.execution_mode != "cli" or not invocation.argv:
            raise ExecutionError(
                f"provider {request.provider!r} requires a native runtime and is not headless"
            )
        cwd = Path(request.cwd).expanduser()
        if not cwd.is_dir():
            raise ExecutionError(f"provider working directory not found: {cwd}")
        if request.timeout_seconds < 1:
            raise ExecutionError("timeout_seconds must be >= 1")
        if request.max_output_chars < 200:
            raise ExecutionError("max_output_chars must be >= 200")

        process = await asyncio.create_subprocess_exec(
            *invocation.argv,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_raw, stderr_raw = await asyncio.wait_for(
                process.communicate(), timeout=request.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            raise ExecutionError(
                f"{request.provider} exceeded the {request.timeout_seconds}s timeout"
            ) from exc
        except asyncio.CancelledError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            raise

        stdout = stdout_raw.decode(errors="replace") if stdout_raw else ""
        stderr = stderr_raw.decode(errors="replace") if stderr_raw else ""
        stdout = _bounded(stdout, request.max_output_chars)
        stderr = _bounded(stderr, request.max_output_chars)
        return ExecutionOutcome(
            provider=request.provider,
            return_code=int(process.returncode or 0),
            stdout=stdout,
            stderr=stderr,
            session_id=extract_session_id(stdout) or request.session_id,
            usage=extract_usage(stdout),
        )


def _bounded(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    marker = "\n[output truncated]\n"
    head = max(1, (limit - len(marker)) // 2)
    tail = max(1, limit - len(marker) - head)
    return value[:head] + marker + value[-tail:]


@dataclass(frozen=True)
class ExecutorPlugin:
    descriptor: ExecutorDescriptor
    backend_factory: Callable[[], ExecutionBackend] | None = None
    availability_probe: Callable[[], bool] | None = None


class ExecutionRegistry:
    """Runtime-extensible executor registry.

    Third parties can register ``durable_threads.executors`` entry points that
    return :class:`ExecutorPlugin`. Core routing therefore does not need a new
    release every time a provider/runtime is added.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, ExecutorPlugin] = {}

    def register(self, plugin: ExecutorPlugin, *, replace: bool = False) -> None:
        executor_id = plugin.descriptor.executor_id
        if executor_id in self._plugins and not replace:
            raise ValueError(f"executor already registered: {executor_id}")
        self._plugins[executor_id] = plugin

    def get(self, executor_id: str) -> ExecutorPlugin:
        try:
            return self._plugins[executor_id]
        except KeyError as exc:
            raise ExecutionError(f"executor not registered: {executor_id}") from exc

    def descriptors(self) -> tuple[ExecutorDescriptor, ...]:
        return tuple(plugin.descriptor for plugin in self._plugins.values())

    def available(self, executor_id: str) -> bool:
        plugin = self.get(executor_id)
        return True if plugin.availability_probe is None else bool(plugin.availability_probe())

    def backend(self, executor_id: str) -> ExecutionBackend:
        plugin = self.get(executor_id)
        if plugin.backend_factory is None:
            raise ExecutionError(
                f"executor {executor_id!r} is native-only and has no headless backend"
            )
        return plugin.backend_factory()

    def rank(
        self,
        requirements: ExecutionRequirements,
        *,
        available_only: bool = True,
    ) -> tuple[ExecutionSelection, ...]:
        preferred = {
            provider: len(requirements.preferred_providers) - index
            for index, provider in enumerate(requirements.preferred_providers)
        }
        excluded = set(requirements.excluded_providers)
        selections: list[ExecutionSelection] = []
        for plugin in self._plugins.values():
            descriptor = plugin.descriptor
            if descriptor.provider in excluded:
                continue
            if not requirements.capabilities.issubset(descriptor.capabilities):
                continue
            if requirements.headless and not descriptor.headless:
                continue
            if requirements.persistent_session and not descriptor.persistent_sessions:
                continue
            if requirements.structured_output and not descriptor.structured_output:
                continue
            if requirements.effort_control and not descriptor.supports_effort:
                continue
            if available_only and not self.available(descriptor.executor_id):
                continue

            score = preferred.get(descriptor.provider, 0) * 100
            reasons: list[str] = ["required capabilities satisfied"]
            if descriptor.provider in preferred:
                reasons.append("preferred provider")
            if descriptor.structured_output:
                score += 5
                reasons.append("structured output")
            if descriptor.persistent_sessions:
                score += 3
                reasons.append("persistent sessions")
            if descriptor.supports_effort:
                score += 1
                reasons.append("reasoning effort control")
            selections.append(ExecutionSelection(descriptor, score, tuple(reasons)))
        return tuple(
            sorted(
                selections,
                key=lambda selection: (-selection.score, selection.descriptor.executor_id),
            )
        )

    def select(
        self,
        requirements: ExecutionRequirements,
        *,
        count: int = 1,
        available_only: bool = True,
    ) -> tuple[ExecutionSelection, ...]:
        if count < 1:
            raise ValueError("count must be >= 1")
        ranked = self.rank(requirements, available_only=available_only)
        if not ranked:
            raise ExecutionError("no registered executor satisfies the execution requirements")
        return ranked[:count]

    def load_entry_points(self) -> tuple[str, ...]:
        loaded: list[str] = []
        entries = importlib.metadata.entry_points()
        selected = entries.select(group=_PLUGIN_GROUP)
        for entry in selected:
            value = entry.load()
            plugin = value() if callable(value) and not isinstance(value, ExecutorPlugin) else value
            if not isinstance(plugin, ExecutorPlugin):
                raise TypeError(
                    f"entry point {entry.name!r} must return "
                    "durable_threads.execution.ExecutorPlugin"
                )
            self.register(plugin)
            loaded.append(plugin.descriptor.executor_id)
        return tuple(loaded)


def _builtin_availability(provider: str) -> Callable[[], bool]:
    def probe() -> bool:
        try:
            status = provider_status(provider)[0]
        except (ProviderError, OSError, IndexError):
            return False
        return bool(status["available"])

    return probe


def _builtin_backend_factory(provider: str) -> Callable[[], ExecutionBackend]:
    def factory() -> ExecutionBackend:
        return CliExecutionBackend(provider)

    return factory


def default_execution_registry(*, load_entry_points: bool = True) -> ExecutionRegistry:
    """Build the default registry around current built-in coding-agent adapters."""

    registry = ExecutionRegistry()
    from .scripted import scripted_executor_plugin

    registry.register(scripted_executor_plugin())
    for capability in get_capabilities():
        provider = capability.provider
        capabilities = {"code", "filesystem", "git"}
        if capability.headless:
            capabilities.add("shell")
        if capability.structured_output:
            capabilities.add("structured-output")
        descriptor = ExecutorDescriptor(
            executor_id=provider,
            provider=provider,
            runtime=capability.display_name,
            capabilities=frozenset(capabilities),
            persistent_sessions=capability.persistent_sessions,
            headless=capability.headless,
            structured_output=capability.structured_output,
            supports_effort=capability.supports_effort,
            metadata={"protocol": capability.protocol},
        )
        backend_factory = (
            _builtin_backend_factory(provider) if capability.headless else None
        )
        registry.register(
            ExecutorPlugin(
                descriptor=descriptor,
                backend_factory=backend_factory,
                availability_probe=_builtin_availability(provider),
            )
        )
    if load_entry_points:
        registry.load_entry_points()
    return registry


def providers_for(selections: Iterable[ExecutionSelection]) -> tuple[str, ...]:
    return tuple(selection.descriptor.provider for selection in selections)
