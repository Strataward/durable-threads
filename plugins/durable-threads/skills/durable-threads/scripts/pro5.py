#!/usr/bin/env python3
"""Local config audit and no-generation Codex metadata probe. Never writes user config."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

RATE_DATE = "2026-09-22"
PROFILE = '''# Merge these named profiles into config.toml; do not replace existing configuration.
# Verify model availability in your own Codex session before use.
[profiles.dt-pro5]
model = "gpt-6-astra"
model_reasoning_effort = "medium"
service_tier = "default"

[profiles.dt-pro5-deep]
model = "gpt-6-astra"
model_reasoning_effort = "high"
service_tier = "default"

[profiles.dt-pro5-routine]
model = "gpt-5.6-luna"
model_reasoning_effort = "xhigh"
service_tier = "default"
'''


def safe_identifier(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,96}", value):
        return value
    return None


def audit_config(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    """Inspect one config file only, not the resolved managed/project/CLI configuration."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a table")
    selected = profile or config.get("profile")
    if selected is not None and not isinstance(selected, str):
        raise ValueError("profile must be a string")
    effective = dict(config)
    if selected:
        profiles = config.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ValueError("profiles must be a table")
        layer = profiles.get(selected)
        if not isinstance(layer, dict):
            raise ValueError("selected profile is absent from this configuration")
        for key, value in layer.items():
            if isinstance(value, dict) and isinstance(effective.get(key), dict):
                effective[key] = {**effective[key], **value}
            else:
                effective[key] = value
    findings: list[dict[str, str]] = []

    def flag(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    effort = effective.get("model_reasoning_effort")
    if isinstance(effort, str) and effort in {"high", "xhigh", "max", "ultra"}:
        flag(
            "EXPENSIVE_BASELINE",
            "Benchmark Astra medium for routine work; reserve higher effort for hard "
            "decisions. Keep quality checks.",
        )
    tier = effective.get("service_tier")
    if isinstance(tier, str) and tier in {"fast", "priority"}:
        flag(
            "FAST_TIER",
            "Prefer standard speed for allowance efficiency. Published Astra Fast "
            "credit consumption is 2.5x standard.",
        )
    if any(key in effective for key in ("model_context_window", "model_auto_compact_token_limit")):
        flag(
            "MANUAL_CONTEXT",
            "Manual context/compaction overrides need workload evidence. A larger "
            "window is capacity, not free context.",
        )
    agents = effective.get("agents", {})
    if not isinstance(agents, dict):
        raise ValueError("agents must be a table")
    if agents.get("enabled", True) and not agents.get("default_subagent_model"):
        flag(
            "CHILD_INHERITANCE",
            "Unspecified child models may inherit the parent. Select an economical "
            "worker explicitly when delegation is justified.",
        )
    concurrency = agents.get("max_concurrent_threads_per_session", agents.get("max_threads"))
    if isinstance(concurrency, (int, float)) and concurrency > 2:
        flag(
            "FANOUT",
            "A high per-session child limit can amplify spend. Prefer one writer and "
            "an on-demand independent reviewer.",
        )
    servers = effective.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcp_servers must be a table")
    count = sum(
        isinstance(item, dict) and item.get("enabled", True) is not False
        for item in servers.values()
    )
    if count:
        flag(
            "MCP_CONTEXT",
            "Enable only tools relevant to the task. Audit schemas and outputs; do "
            "not disable required safety tooling.",
        )
    features = effective.get("features", {})
    experimental = ("reasoning_effort_override", "step_model_switching")
    if isinstance(features, dict) and any(features.get(key) for key in experimental):
        flag(
            "EXPERIMENTAL",
            "Verify the installed server, enabled flags, model support, and "
            "compaction compatibility before live step changes.",
        )
    return {
        "scope": "one-config-file-not-effective-runtime", "profile": safe_identifier(selected),
        "model": safe_identifier(effective.get("model")), "effort": safe_identifier(effort),
        "serviceTier": safe_identifier(effective.get("service_tier")), "enabledMcpServers": count,
        "findings": findings, "writesPerformed": False, "subscriptionMultiplierVerified": False,
    }


def quota_summary(payload: dict[str, Any], *, now: float) -> dict[str, Any]:
    """Expose only the relevant bucket, not emails, account IDs or raw account data."""
    if not isinstance(payload, dict) or not math.isfinite(now) or now < 0:
        raise ValueError("invalid quota observation")
    buckets = payload.get("rateLimitsByLimitId")
    bucket = buckets.get("codex") if isinstance(buckets, dict) else None
    if bucket is None:
        bucket = payload.get("rateLimits")
    if not isinstance(bucket, dict) or bucket.get("limitId") not in (None, "codex"):
        return {"status": "unknown", "windows": []}
    windows = []
    for key in ("primary", "secondary"):
        item = bucket.get(key)
        if item is None:
            continue
        if not isinstance(item, dict):
            return {"status": "unknown", "windows": []}
        used, reset, duration = (
            item.get(name) for name in ("usedPercent", "resetsAt", "windowDurationMins")
        )
        values = (used, reset, duration)
        if any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in values
        ):
            return {"status": "unknown", "windows": []}
        if not 0 <= used <= 100 or reset <= now or duration <= 0:
            return {"status": "refresh_required", "windows": []}
        windows.append({"window": key, "usedPercent": used, "remainingPercent": 100 - used,
                        "resetsAt": reset, "windowDurationMins": duration})
    remaining = min((item["remainingPercent"] for item in windows), default=None)
    reached = bucket.get("rateLimitReachedType") is not None
    status = "observed" if windows else "unknown"
    if reached or (remaining is not None and remaining <= 15):
        status = "pause"
    return {"status": status,
            "windows": windows, "remainingPercent": remaining, "observedAt": now,
            "reservePercent": 15, "reserveIsLocalPolicy": True}


async def probe_metadata(command: list[str], timeout: float = 20) -> dict[str, Any]:
    """Uses only initialize/account-read/model-list/rate-limit-read; never starts a turn."""
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, limit=1_048_576,
    )
    next_id = 0
    methods: list[str] = []

    async def send(message: dict[str, Any]) -> None:
        if process.stdin is None:
            raise RuntimeError("Codex input unavailable")
        process.stdin.write((json.dumps(message) + "\n").encode())
        await process.stdin.drain()

    async def rpc(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal next_id
        next_id += 1
        identifier = next_id
        methods.append(method)
        message: dict[str, Any] = {"id": identifier, "method": method}
        if params is not None:
            message["params"] = params
        await send(message)
        for _ in range(1000):
            if process.stdout is None:
                raise RuntimeError("Codex output unavailable")
            raw = await process.stdout.readline()
            if not raw:
                raise RuntimeError("Codex exited before answering metadata request")
            response = json.loads(raw)
            if not isinstance(response, dict):
                raise ValueError("invalid Codex metadata response")
            if "method" in response and "id" in response:
                # Deny every server-initiated action. The probe is never an approver.
                await send({
                    "id": response["id"],
                    "error": {"code": -32601, "message": "Read-only probe"},
                })
            if response.get("id") == identifier and "method" not in response:
                if "error" in response:
                    raise RuntimeError(f"Codex rejected {method}")
                result = response.get("result")
                if not isinstance(result, dict):
                    raise ValueError("invalid Codex result")
                return result
        raise RuntimeError("Codex metadata notification limit exceeded")

    async def run() -> dict[str, Any]:
        await rpc("initialize", {
            "clientInfo": {"name": "durable_threads_probe", "version": "0.6.0"},
            "capabilities": {"experimentalApi": False},
        })
        await send({"method": "initialized"})
        account_payload = await rpc("account/read", {"refreshToken": False})
        account = account_payload.get("account")
        account_type = safe_identifier(account.get("type")) if isinstance(account, dict) else None
        # Do not output the raw account object: it can include email and account identifiers.
        result: dict[str, Any] = {
            "authType": account_type, "chatgptSignIn": account_type == "chatgpt",
            "subscriptionMultiplierVerified": False, "models": [], "warnings": [],
        }
        cursor = None
        for page in range(8):
            params: dict[str, Any] = {"limit": 100}
            if cursor:
                params["cursor"] = cursor
            model_page = await rpc("model/list", params)
            for model in model_page.get("data", []):
                if not isinstance(model, dict):
                    continue
                identifier = safe_identifier(model.get("model") or model.get("id"))
                if identifier not in {"gpt-6-astra", "gpt-5.6-luna", "gpt-5.6-terra"}:
                    continue
                efforts = model.get("supportedReasoningEfforts", [])
                result["models"].append({"model": identifier, "supportedEfforts": [
                    safe_identifier(item.get("reasoningEffort") or item.get("effort"))
                    for item in efforts if isinstance(item, dict)
                ]})
            cursor = model_page.get("nextCursor")
            if not cursor:
                break
            if page == 7:
                result["warnings"].append("Model listing truncated after eight pages")
        if account_type == "chatgpt":
            try:
                limits = await rpc("account/rateLimits/read")
                result["quota"] = quota_summary(limits, now=time.time())
            except RuntimeError:
                result["quota"] = {"status": "unknown", "windows": []}
                result["warnings"].append("Rate-limit read unavailable; check /status")
        else:
            result["warnings"].append(
                "ChatGPT-managed sign-in not verified; do not assume subscription billing"
            )
        result.update({"requestedMethods": methods, "modelGenerationsRequested": 0,
                       "stepSwitchingVerified": False, "writesToUserConfig": False})
        return result

    try:
        return await asyncio.wait_for(run(), timeout)
    finally:
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), 3)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()


def schema_probe(codex: str) -> dict[str, Any]:
    """Schema presence is not proof that a live turn or model accepts an update."""
    with tempfile.TemporaryDirectory(prefix="dt-schema-") as directory:
        completed = subprocess.run(
            [codex, "app-server", "generate-json-schema", "--experimental", "--out", directory],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False,
        )
        if completed.returncode != 0:
            return {"status": "unavailable", "liveSwitchingVerified": False}
        found = any('turn/settings/update' in path.read_text(encoding="utf-8")
                    for path in Path(directory).rglob("*.json") if path.stat().st_size < 20_000_000)
        return {"status": "schema_only", "turnSettingsUpdateAdvertised": found,
                "liveSwitchingVerified": False}


def read_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError as exc:
            raise RuntimeError("Use Python 3.11+ or install tomli for the TOML audit") from exc
    if path.stat().st_size > 2_000_000:
        raise ValueError("configuration is too large")
    with path.open("rb") as stream:
        return tomllib.load(stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="read one config file without displaying secrets")
    audit.add_argument("--config", type=Path, default=Path.home() / ".codex" / "config.toml")
    audit.add_argument("--profile")
    probe = commands.add_parser(
        "probe", help="inspect existing Codex sign-in, models and quota; no turns"
    )
    probe.add_argument("--codex", default="codex")
    probe.add_argument("--timeout", type=float, default=20)
    probe.add_argument(
        "--schema", action="store_true", help="also generate experimental schema temporarily"
    )
    schema = commands.add_parser("schema", help="inspect schema without starting a model turn")
    schema.add_argument("--codex", default="codex")
    commands.add_parser("profile", help="print named TOML profiles without installing them")
    args = parser.parse_args(argv)
    try:
        if args.command == "profile":
            print(PROFILE, end="")
            return 0
        if args.command == "schema":
            result = schema_probe(args.codex)
        elif args.command == "audit":
            result = audit_config(read_toml(args.config.expanduser()), args.profile)
        else:
            if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 120:
                raise ValueError("timeout must be between 1 and 120 seconds")
            result = asyncio.run(probe_metadata([args.codex, "app-server"], args.timeout))
            if args.schema:
                result["experimentalSchema"] = schema_probe(args.codex)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (
        OSError, RuntimeError, ValueError, asyncio.TimeoutError, subprocess.TimeoutExpired
    ) as exc:
        # TOML error text and filesystem exceptions can contain private values/paths.
        failure = {
            "error": type(exc).__name__,
            "message": (
                "Audit/probe failed; check file syntax, selected profile, executable, "
                "and timeout locally."
            ),
        }
        print(json.dumps(failure), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
