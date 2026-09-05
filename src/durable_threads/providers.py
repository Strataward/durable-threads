"""Provider-specific session and command contracts.

The provider adapters build argument arrays. They never build shell strings.
This keeps prompts, model names, and session IDs separate from shell parsing.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROVIDERS = ("codex", "claude", "grok", "cursor")
_ROLE_SELECTORS = {"frontier", "balanced", "efficient"}
_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
_SAFE_MODEL = re.compile(r"^[A-Za-z0-9._:/=@+?\-]+$")
_SESSION_KEY_NAMES = {
    "session_id",
    "sessionId",
    "chat_id",
    "chatId",
    "agent_id",
    "agentId",
}


class ProviderError(ValueError):
    """Raised when a provider request cannot be represented safely."""


@dataclass(frozen=True)
class ProviderCapability:
    """Stable capability facts for one provider integration."""

    provider: str
    display_name: str
    executable_candidates: tuple[str, ...]
    persistent_sessions: bool
    headless: bool
    structured_output: bool
    supports_effort: bool
    protocol: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "displayName": self.display_name,
            "executableCandidates": list(self.executable_candidates),
            "persistentSessions": self.persistent_sessions,
            "headless": self.headless,
            "structuredOutput": self.structured_output,
            "supportsEffort": self.supports_effort,
            "protocol": self.protocol,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ProviderInvocation:
    """An executable provider call or a native Codex action description."""

    provider: str
    executable: str | None
    argv: tuple[str, ...]
    model: str | None
    reasoning_effort: str
    session_id: str | None
    execution_mode: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "executable": self.executable,
            "argv": list(self.argv),
            "model": self.model,
            "reasoningEffort": self.reasoning_effort,
            "sessionId": self.session_id,
            "executionMode": self.execution_mode,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class DispatchResult:
    """Bounded output from one provider process."""

    provider: str
    return_code: int
    stdout: str
    stderr: str
    session_id: str | None
    usage: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "returnCode": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "sessionId": self.session_id,
            "usage": self.usage,
        }


class _Adapter:
    capability: ProviderCapability

    def resolve_model(self, selector: str) -> str | None:
        value = _selector_value(self.capability.provider, selector)
        if value.casefold() == "default":
            return None
        if not _SAFE_MODEL.fullmatch(value):
            raise ProviderError(
                f"{self.capability.provider} model selector must not contain whitespace "
                "or control characters"
            )
        return value

    def effort(self, value: str) -> str | None:
        if value not in _EFFORTS:
            allowed = ", ".join(sorted(_EFFORTS))
            raise ProviderError(f"reasoning effort must be one of: {allowed}")
        if value in {"none", "minimal"}:
            return None
        if not self.capability.supports_effort:
            return None
        return value

    def executable(self, override: str | None) -> str:
        if override:
            return override
        for candidate in self.capability.executable_candidates:
            resolved = _resolve_executable(candidate)
            if resolved:
                return resolved
        return self.capability.executable_candidates[0]

    def build(
        self,
        *,
        prompt: str,
        model_selector: str,
        reasoning_effort: str,
        session_id: str | None,
        session_name: str | None,
        executable: str | None,
    ) -> ProviderInvocation:
        raise NotImplementedError


class _CodexAdapter(_Adapter):
    capability = ProviderCapability(
        provider="codex",
        display_name="OpenAI Codex",
        executable_candidates=("codex",),
        persistent_sessions=True,
        headless=False,
        structured_output=False,
        supports_effort=True,
        protocol="native-app",
        notes=(
            "Use native Codex task actions for list, send, wait, and read operations.",
            "The Python helper does not replace Codex app actions.",
        ),
    )

    def build(self, **_: Any) -> ProviderInvocation:
        return ProviderInvocation(
            provider="codex",
            executable=None,
            argv=(),
            model=None,
            reasoning_effort="native",
            session_id=None,
            execution_mode="native-app",
            notes=self.capability.notes,
        )


class _ClaudeAdapter(_Adapter):
    capability = ProviderCapability(
        provider="claude",
        display_name="Anthropic Claude Code",
        executable_candidates=("claude",),
        persistent_sessions=True,
        headless=True,
        structured_output=True,
        supports_effort=True,
        protocol="cli",
        notes=(
            "Use Claude Code --resume with the provider session ID.",
            "Use model aliases such as opus, sonnet, or haiku to avoid retired IDs.",
        ),
    )

    def resolve_model(self, selector: str) -> str | None:
        value = _selector_value(self.capability.provider, selector)
        aliases = {"frontier": "opus", "balanced": "sonnet", "efficient": "haiku"}
        value = aliases.get(value.casefold(), value)
        if value.casefold() == "default":
            return None
        if not _SAFE_MODEL.fullmatch(value):
            raise ProviderError("Claude model selector contains unsafe characters")
        return value

    def build(
        self,
        *,
        prompt: str,
        model_selector: str,
        reasoning_effort: str,
        session_id: str | None,
        session_name: str | None,
        executable: str | None,
    ) -> ProviderInvocation:
        model = self.resolve_model(model_selector)
        effort = self.effort(reasoning_effort)
        argv = [self.executable(executable), "-p", prompt, "--output-format", "json"]
        if model:
            argv.extend(("--model", model))
        if effort:
            argv.extend(("--effort", effort))
        if session_id:
            argv.extend(("--resume", session_id))
        elif session_name:
            argv.extend(("--name", session_name))
        return ProviderInvocation(
            provider="claude",
            executable=argv[0],
            argv=tuple(argv),
            model=model,
            reasoning_effort=reasoning_effort,
            session_id=session_id,
            execution_mode="cli",
            notes=self.capability.notes,
        )


class _GrokAdapter(_Adapter):
    capability = ProviderCapability(
        provider="grok",
        display_name="xAI Grok Build",
        executable_candidates=("grok",),
        persistent_sessions=True,
        headless=True,
        structured_output=True,
        supports_effort=True,
        protocol="cli",
        notes=(
            "Use Grok Build --resume or --session-id for durable headless sessions.",
            "Use a model name from the local Grok catalog or use default.",
            "Disable automatic CLI updates in automation with --no-auto-update.",
        ),
    )

    def resolve_model(self, selector: str) -> str | None:
        value = _selector_value(self.capability.provider, selector)
        if value.casefold() in _ROLE_SELECTORS:
            raise ProviderError(
                "Grok does not map generic role selectors safely; use grok:default or a model "
                "name from `grok inspect`"
            )
        return super().resolve_model(value)

    def build(
        self,
        *,
        prompt: str,
        model_selector: str,
        reasoning_effort: str,
        session_id: str | None,
        session_name: str | None,
        executable: str | None,
    ) -> ProviderInvocation:
        del session_name
        model = self.resolve_model(model_selector)
        effort = self.effort(reasoning_effort)
        argv = [
            self.executable(executable),
            "--no-auto-update",
            "-p",
            prompt,
            "--output-format",
            "json",
        ]
        if model:
            argv.extend(("-m", model))
        if effort:
            argv.extend(("--effort", effort))
        if session_id:
            argv.extend(("--resume", session_id))
        return ProviderInvocation(
            provider="grok",
            executable=argv[0],
            argv=tuple(argv),
            model=model,
            reasoning_effort=reasoning_effort,
            session_id=session_id,
            execution_mode="cli",
            notes=self.capability.notes,
        )


class _CursorAdapter(_Adapter):
    capability = ProviderCapability(
        provider="cursor",
        display_name="Cursor Agent",
        executable_candidates=("agent", "cursor-agent"),
        persistent_sessions=True,
        headless=True,
        structured_output=True,
        supports_effort=False,
        protocol="cli",
        notes=(
            "Use --resume with the Cursor chat ID.",
            "Use an account-visible model ID from the Cursor model catalog.",
            "Cursor model parameters are account-specific and are not guessed by this adapter.",
        ),
    )

    def resolve_model(self, selector: str) -> str | None:
        value = _selector_value(self.capability.provider, selector)
        if value.casefold() in _ROLE_SELECTORS:
            raise ProviderError(
                "Cursor does not map generic role selectors safely; use cursor:default or an "
                "account-visible model ID"
            )
        return super().resolve_model(value)

    def build(
        self,
        *,
        prompt: str,
        model_selector: str,
        reasoning_effort: str,
        session_id: str | None,
        session_name: str | None,
        executable: str | None,
    ) -> ProviderInvocation:
        del session_name
        model = self.resolve_model(model_selector)
        self.effort(reasoning_effort)
        argv = [self.executable(executable), "-p", prompt, "--output-format", "json"]
        if model:
            argv.extend(("--model", model))
        if session_id:
            argv.extend(("--resume", session_id))
        return ProviderInvocation(
            provider="cursor",
            executable=argv[0],
            argv=tuple(argv),
            model=model,
            reasoning_effort=reasoning_effort,
            session_id=session_id,
            execution_mode="cli",
            notes=self.capability.notes,
        )


_ADAPTERS: dict[str, _Adapter] = {
    "codex": _CodexAdapter(),
    "claude": _ClaudeAdapter(),
    "grok": _GrokAdapter(),
    "cursor": _CursorAdapter(),
}


def _selector_value(provider: str, selector: str) -> str:
    if not isinstance(selector, str) or not selector.strip():
        raise ProviderError(f"{provider} model selector must be a non-empty string")
    value = selector.strip()
    prefix, separator, remainder = value.partition(":")
    if separator and prefix.casefold() in PROVIDERS:
        if prefix.casefold() != provider:
            raise ProviderError(f"model selector {selector!r} belongs to provider {prefix!r}")
        value = remainder
    if not value or "\x00" in value or any(char in value for char in "\r\n"):
        raise ProviderError(f"{provider} model selector is invalid")
    return value


def get_adapter(provider: str) -> _Adapter:
    normalized = provider.strip().casefold()
    try:
        return _ADAPTERS[normalized]
    except KeyError as exc:
        allowed = ", ".join(PROVIDERS)
        raise ProviderError(f"provider must be one of: {allowed}") from exc


def get_capabilities(provider: str | None = None) -> tuple[ProviderCapability, ...]:
    if provider is None:
        return tuple(adapter.capability for adapter in _ADAPTERS.values())
    return (get_adapter(provider).capability,)


def build_invocation(
    *,
    provider: str,
    prompt: str,
    model_selector: str,
    reasoning_effort: str,
    session_id: str | None = None,
    session_name: str | None = None,
    executable: str | None = None,
) -> ProviderInvocation:
    """Build a provider-specific argv array without starting a provider."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ProviderError("prompt must be a non-empty string")
    if "\x00" in prompt:
        raise ProviderError("prompt must not contain a null character")
    if session_id is not None and (not session_id.strip() or "\x00" in session_id):
        raise ProviderError("session_id must be empty or a non-empty safe string")
    if session_name is not None and (not session_name.strip() or "\x00" in session_name):
        raise ProviderError("session_name must be empty or a non-empty safe string")
    adapter = get_adapter(provider)
    return adapter.build(
        prompt=prompt,
        model_selector=model_selector,
        reasoning_effort=reasoning_effort,
        session_id=session_id,
        session_name=session_name,
        executable=executable,
    )


def _resolve_executable(candidate: str) -> str | None:
    path = Path(candidate).expanduser()
    if path.parent != Path(".") and path.is_file() and path.stat().st_mode & 0o111:
        return str(path)
    return shutil.which(candidate)


def provider_status(provider: str | None = None) -> tuple[dict[str, Any], ...]:
    """Report local executable availability without checking credentials."""

    statuses = []
    for capability in get_capabilities(provider):
        candidates = [
            {"name": candidate, "path": _resolve_executable(candidate)}
            for candidate in capability.executable_candidates
        ]
        selected = next((item["path"] for item in candidates if item["path"]), None)
        statuses.append(
            {
                **capability.to_dict(),
                "available": selected is not None or capability.provider == "codex",
                "selectedExecutable": selected,
                "candidates": candidates,
                "authentication": "not checked; use the provider's own login or environment",
            }
        )
    return tuple(statuses)


def _bounded(value: str, limit: int = 20_000) -> str:
    if len(value) <= limit:
        return value
    marker = "\n[output truncated]\n"
    if limit <= len(marker) + 2:
        return value[:limit]
    head = (limit - len(marker)) // 2
    tail = limit - len(marker) - head
    return value[:head] + marker + value[-tail:]


def _find_session_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SESSION_KEY_NAMES and isinstance(item, str) and item.strip():
                return item.strip()
        for item in value.values():
            session_id = _find_session_id(item)
            if session_id:
                return session_id
    elif isinstance(value, list):
        for item in value:
            session_id = _find_session_id(item)
            if session_id:
                return session_id
    return None


def extract_session_id(output: str) -> str | None:
    """Extract a session ID from JSON or newline-delimited JSON output."""

    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = _find_session_id(value)
        if session_id:
            return session_id
    try:
        return _find_session_id(json.loads(output))
    except json.JSONDecodeError:
        return None


_USAGE_KEYS = {
    "input_tokens": "inputTokens",
    "inputTokens": "inputTokens",
    "prompt_tokens": "inputTokens",
    "promptTokens": "inputTokens",
    "output_tokens": "outputTokens",
    "outputTokens": "outputTokens",
    "completion_tokens": "outputTokens",
    "completionTokens": "outputTokens",
    "total_tokens": "totalTokens",
    "totalTokens": "totalTokens",
}


def _find_usage(value: Any) -> dict[str, int] | None:
    if isinstance(value, dict):
        found: dict[str, int] = {}
        for key, item in value.items():
            target = _USAGE_KEYS.get(key)
            if target and isinstance(item, int) and not isinstance(item, bool) and item >= 0:
                found[target] = item
        if found:
            return found
        for key, item in value.items():
            if key.casefold() in {"usage", "usage_metadata", "token_usage", "tokenusage"}:
                nested = _find_usage(item)
                if nested:
                    return nested
        for item in value.values():
            nested = _find_usage(item)
            if nested:
                return nested
    elif isinstance(value, list):
        for item in value:
            nested = _find_usage(item)
            if nested:
                return nested
    return None


def extract_usage(output: str) -> dict[str, int] | None:
    """Extract common provider token counters without storing the response."""

    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = _find_usage(value)
        if usage:
            return usage
    try:
        return _find_usage(json.loads(output))
    except json.JSONDecodeError:
        return None


def run_invocation(
    invocation: ProviderInvocation,
    *,
    cwd: str | Path,
    timeout_seconds: int = 3600,
    max_output_chars: int = 20_000,
) -> DispatchResult:
    """Run one non-Codex provider call with no shell interpolation."""

    if invocation.execution_mode != "cli" or not invocation.argv:
        raise ProviderError("Codex uses native app actions and cannot run through this CLI")
    if isinstance(timeout_seconds, bool) or timeout_seconds < 1:
        raise ProviderError("timeout_seconds must be an integer >= 1")
    if isinstance(max_output_chars, bool) or max_output_chars < 200:
        raise ProviderError("max_output_chars must be an integer >= 200")
    working_directory = Path(cwd).expanduser()
    if not working_directory.is_dir():
        raise ProviderError(f"provider working directory not found: {working_directory}")
    try:
        completed = subprocess.run(
            list(invocation.argv),
            cwd=working_directory,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        raise ProviderError(
            f"{invocation.provider} exceeded the {timeout_seconds}s timeout; "
            f"partial output was not persisted"
        ) from exc
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return DispatchResult(
        provider=invocation.provider,
        return_code=completed.returncode,
        stdout=_bounded(stdout, max_output_chars),
        stderr=_bounded(stderr, max_output_chars),
        session_id=extract_session_id(stdout),
        usage=extract_usage(stdout),
    )
