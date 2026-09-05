"""Command line helpers for packet planning and local evidence."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from .config import ConfigError, load_roster
from .evidence import EvidenceError, git_changed_paths, parse_worker_result, validate_evidence
from .ledger import Ledger, LedgerBusyError, LedgerStateError
from .packets import build_packet
from .providers import (
    PROVIDERS,
    ProviderError,
    build_invocation,
    provider_status,
    run_invocation,
)
from .routing import catalog_from_payload, resolve_model, select_workers

_EFFORT_CHOICES = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _plan(args: argparse.Namespace) -> int:
    roster = load_roster(args.roster)
    run_id = args.run_id or f"loom-{uuid.uuid4().hex[:12]}"
    decision = select_workers(
        roster,
        objective=args.objective,
        allowed_paths=args.allowed_path,
        acceptance=args.acceptance,
        requested_workers=args.worker,
        local_only=args.local,
    )
    packets = []
    for worker in decision.selected:
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
                    "provider": worker.provider,
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
                "provider": roster.planner.provider,
                "modelSelector": roster.planner.model_selector,
                "reasoningEffort": roster.planner.reasoning_effort,
            },
            "reviewer": {
                "role": roster.reviewer.role,
                "provider": roster.reviewer.provider,
                "modelSelector": roster.reviewer.model_selector,
                "reasoningEffort": roster.reviewer.reasoning_effort,
            },
            "policy": {
                "maxParallelWorkers": roster.max_parallel_workers,
                "maxSelectedWorkers": roster.max_selected_workers,
                "resultMaxChars": roster.result_max_chars,
                "allowThreadCreation": roster.allow_thread_creation,
            },
            "route": {
                "mode": "explicit" if decision.explicit else "automatic",
                "selectedWorkers": [worker.name for worker in decision.selected],
                "skippedWorkers": [worker.name for worker in decision.skipped],
                "reasons": list(decision.reasons),
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
    statuses = provider_status()
    _dump(
        {
            "providers": list(statuses),
            "note": "Authentication is not checked. The helper does not start provider sessions.",
        }
    )
    codex = next(item for item in statuses if item["provider"] == "codex")
    return 0 if codex["available"] else 1


def _provider_doctor(args: argparse.Namespace) -> int:
    statuses = provider_status(args.provider)
    _dump({"providers": list(statuses)})
    return 0 if all(item["available"] for item in statuses) else 1


def _provider_command(args: argparse.Namespace) -> int:
    invocation = build_invocation(
        provider=args.provider,
        prompt=args.prompt,
        model_selector=args.model,
        reasoning_effort=args.effort,
        session_id=args.session_id,
        session_name=args.session_name,
        executable=args.binary,
    )
    _dump(invocation.to_dict())
    return 0


def _dispatch(args: argparse.Namespace) -> int:
    if bool(args.ledger) != bool(args.task_id):
        raise ProviderError("--ledger and --task-id must be used together")
    if args.verify_evidence and not args.allowed_path:
        raise EvidenceError("--verify-evidence requires at least one --allowed-path")
    provider = args.provider
    session_id = args.session_id
    role = args.role
    max_followups = args.max_followups if args.max_followups is not None else 1
    max_output_chars = args.max_output_chars if args.max_output_chars is not None else 2000
    if args.roster or args.worker_name:
        if not args.roster or not args.worker_name:
            raise ProviderError("--roster and --worker-name must be used together")
        roster = load_roster(args.roster)
        worker = next(
            (item for item in roster.workers if item.name == args.worker_name),
            None,
        )
        if worker is None:
            raise ProviderError(f"worker not found in roster: {args.worker_name}")
        if worker.provider != provider:
            raise ProviderError(
                f"worker {worker.name!r} belongs to provider {worker.provider!r}, not {provider!r}"
            )
        role = worker.role
        session_id = session_id or worker.thread_id
        max_followups = (
            worker.max_followups
            if args.max_followups is None
            else min(args.max_followups, worker.max_followups)
        )
        max_output_chars = min(max_output_chars, roster.result_max_chars)
    invocation = build_invocation(
        provider=provider,
        prompt=args.prompt,
        model_selector=args.model,
        reasoning_effort=args.effort,
        session_id=session_id,
        session_name=args.session_name,
        executable=args.binary,
    )
    ledger = Ledger(args.ledger) if args.ledger else None
    claimed = False
    try:
        if ledger:
            ledger.begin_task(
                task_id=args.task_id,
                role=role,
                provider=provider,
                thread_id=session_id,
                followup_index=args.followup_index,
                max_followups=max_followups,
            )
            claimed = True
        result = run_invocation(
            invocation,
            cwd=args.cwd,
            timeout_seconds=args.timeout,
            max_output_chars=max_output_chars,
        )
        if session_id and result.session_id and session_id != result.session_id:
            raise ProviderError("provider returned a different session ID; inspect before retry")
        verified = None
        if args.verify_evidence:
            if not args.allowed_path:
                raise EvidenceError("--verify-evidence requires at least one --allowed-path")
            evidence = parse_worker_result(result.stdout)
            actual_paths = git_changed_paths(args.cwd, args.base_ref)
            verified = validate_evidence(
                evidence,
                allowed_paths=args.allowed_path,
                actual_paths=actual_paths,
            )
        accepted = result.return_code == 0 and (verified is None or verified.status == "complete")
        if ledger:
            ledger.record_task(
                task_id=args.task_id,
                role=role,
                status=(
                    "complete" if accepted and verified else "unverified" if accepted else "blocked"
                ),
                provider=provider,
                thread_id=result.session_id or session_id,
                result=(
                    "Provider completed. Evidence was verified."
                    if verified is not None and accepted
                    else "Provider completed. Evidence was not verified."
                    if result.return_code == 0
                    else f"Provider returned exit code {result.return_code}."
                ),
                usage=result.usage,
            )
        payload = result.to_dict()
        if verified is not None:
            payload["evidence"] = verified.to_dict()
        _dump(payload)
        return result.return_code if result.return_code != 0 else (0 if accepted else 2)
    except (EvidenceError, LedgerBusyError, LedgerStateError, OSError, ProviderError) as exc:
        if ledger and claimed:
            ledger.record_task(
                task_id=args.task_id,
                role=role,
                status="unknown",
                provider=provider,
                thread_id=session_id,
                result=f"Dispatch stopped: {type(exc).__name__}.",
            )
        raise


def _verify_result(args: argparse.Namespace) -> int:
    text = sys.stdin.read() if str(args.result) == "-" else args.result.read_text(encoding="utf-8")
    evidence = parse_worker_result(text)
    actual_paths = git_changed_paths(args.repo, args.base_ref)
    verified = validate_evidence(
        evidence,
        allowed_paths=args.allowed_path,
        actual_paths=actual_paths,
    )
    _dump(
        {
            "valid": True,
            "evidence": verified.to_dict(),
            "actualPaths": list(actual_paths),
        }
    )
    return 0 if verified.status == "complete" else 2


def _record(args: argparse.Namespace) -> int:
    task = Ledger(args.ledger).record_task(
        task_id=args.task_id,
        role=args.role,
        status=args.status,
        provider=args.provider,
        thread_id=args.thread_id,
        result=args.result,
        usage=json.loads(args.usage) if args.usage else None,
    )
    _dump({"recorded": task})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="durable-threads")
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
    plan.add_argument(
        "--worker",
        action="append",
        default=[],
        help="select a named worker explicitly; repeat up to maxSelectedWorkers",
    )
    plan.add_argument("--run-id")
    plan.add_argument("--local", action="store_true", help="keep work in the current task")
    plan.set_defaults(handler=_plan)

    resolve = subparsers.add_parser("resolve-model", help="resolve a role against a model catalog")
    resolve.add_argument("--catalog", type=Path, required=True)
    resolve.add_argument("--selector", required=True)
    resolve.set_defaults(handler=_resolve)

    doctor = subparsers.add_parser("doctor", help="report all provider integrations")
    doctor.set_defaults(handler=_doctor)

    provider_doctor = subparsers.add_parser(
        "provider-doctor", help="check one provider executable without checking credentials"
    )
    provider_doctor.add_argument("--provider", choices=PROVIDERS, required=True)
    provider_doctor.set_defaults(handler=_provider_doctor)

    provider_command = subparsers.add_parser(
        "provider-command", help="render one provider-specific command without running it"
    )
    provider_command.add_argument("--provider", choices=PROVIDERS, required=True)
    provider_command.add_argument("--prompt", required=True)
    provider_command.add_argument("--model", default="default")
    provider_command.add_argument("--effort", default="low", choices=sorted(_EFFORT_CHOICES))
    provider_command.add_argument("--session-id")
    provider_command.add_argument("--session-name")
    provider_command.add_argument("--binary")
    provider_command.set_defaults(handler=_provider_command)

    dispatch = subparsers.add_parser(
        "dispatch", help="run one provider CLI session with an explicit prompt"
    )
    dispatch.add_argument("--provider", choices=("claude", "grok", "cursor"), required=True)
    dispatch.add_argument("--prompt", required=True)
    dispatch.add_argument("--model", default="default")
    dispatch.add_argument("--effort", default="low", choices=sorted(_EFFORT_CHOICES))
    dispatch.add_argument("--session-id")
    dispatch.add_argument("--session-name")
    dispatch.add_argument("--binary")
    dispatch.add_argument("--cwd", type=Path, default=Path.cwd())
    dispatch.add_argument("--timeout", type=int, default=3600)
    dispatch.add_argument("--max-output-chars", type=int)
    dispatch.add_argument("--ledger", type=Path)
    dispatch.add_argument("--task-id")
    dispatch.add_argument("--role", default="worker")
    dispatch.add_argument("--followup-index", type=int, default=0)
    dispatch.add_argument("--max-followups", type=int)
    dispatch.add_argument("--roster", type=Path)
    dispatch.add_argument("--worker-name")
    dispatch.add_argument("--verify-evidence", action="store_true")
    dispatch.add_argument("--allowed-path", action="append", default=[])
    dispatch.add_argument("--base-ref")
    dispatch.set_defaults(handler=_dispatch)

    verify = subparsers.add_parser(
        "verify-result", help="verify worker evidence against the allowed paths and git diff"
    )
    verify.add_argument("--result", type=Path, required=True, help="result file, or - for stdin")
    verify.add_argument("--repo", type=Path, default=Path.cwd())
    verify.add_argument("--base-ref")
    verify.add_argument("--allowed-path", action="append", required=True)
    verify.set_defaults(handler=_verify_result)

    record = subparsers.add_parser("record", help="write one redacted task record")
    record.add_argument("--ledger", type=Path, required=True)
    record.add_argument("--task-id", required=True)
    record.add_argument("--role", required=True)
    record.add_argument("--status", required=True)
    record.add_argument("--provider", choices=PROVIDERS)
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
    except (
        ConfigError,
        EvidenceError,
        LedgerBusyError,
        LedgerStateError,
        ProviderError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
