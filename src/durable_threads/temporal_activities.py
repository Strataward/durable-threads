"""Temporal Activities for decision intelligence, routing, execution, and verification.

All nondeterministic operations live here: Jev API calls, provider process
execution, filesystem/git inspection, and provider availability probes.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from temporalio import activity

from .decisions import JevDecisionEngine
from .evidence import EvidenceError, git_changed_paths, parse_worker_result, validate_evidence
from .execution import (
    ExecutionRequest,
    ExecutionRequirements,
    default_execution_registry,
)
from .intelligence import assess_result, assess_task
from .temporal_contracts import (
    ExecutionAttemptInput,
    ResultDecisionInput,
    RouteExecutorsInput,
    TaskRunInput,
    VerificationInput,
)


def _jev_engine() -> JevDecisionEngine:
    return JevDecisionEngine(
        model=os.getenv("DURABLE_THREADS_JEV_MODEL", "jev-latest"),
        api_key=os.getenv("TYPESAFE_API_KEY") or None,
        base_url=os.getenv("TYPESAFE_BASE_URL") or None,
        timeout_seconds=float(os.getenv("DURABLE_THREADS_JEV_TIMEOUT_SECONDS", "30")),
    )


@activity.defn
async def assess_task_activity(task: TaskRunInput) -> dict[str, Any]:
    engine = _jev_engine()
    assessment = await assess_task(
        engine,
        objective=task.objective,
        allowed_paths=task.allowed_paths,
        acceptance=task.acceptance,
        context={
            "constraints": task.constraints,
            "preferredProviders": task.preferred_providers,
            "requiredCapabilities": task.required_capabilities,
            "maxAttempts": task.max_attempts,
            "speculativeParallelism": task.speculative_parallelism,
        },
        human_gate_at=task.human_gate_at,
    )
    return assessment.to_dict()


@activity.defn
def route_executors_activity(request: RouteExecutorsInput) -> list[dict[str, Any]]:
    registry = default_execution_registry(load_entry_points=True)
    task = request.task
    preferred = tuple(request.preferred_providers or task.preferred_providers)
    requirements = ExecutionRequirements(
        capabilities=frozenset(task.required_capabilities),
        headless=True,
        persistent_session=False,
        structured_output=True,
        effort_control=False,
        preferred_providers=preferred,
        excluded_providers=tuple(request.excluded_providers),
    )
    count = 1
    # Parallel readers/remote workers are safe; parallel writers sharing one checkout are not.
    # Until a runtime advertises isolated workspaces/worktrees, serialize mutating coding work.
    mutating_checkout = bool({"filesystem", "git"} & set(task.required_capabilities))
    if request.assessment.get("executionShape") == "parallel_workers" and not mutating_checkout:
        count = task.speculative_parallelism
    selections = registry.select(requirements, count=count, available_only=True)
    return [selection.to_dict() for selection in selections]


def _runtime_prompt(request: ExecutionAttemptInput) -> str:
    task = request.task
    constraints = "\n".join(f"- {item}" for item in task.constraints) or "- None supplied"
    allowed = "\n".join(f"- {item}" for item in task.allowed_paths)
    acceptance = "\n".join(f"- {item}" for item in task.acceptance)
    return f"""OBJECTIVE
{task.objective}

RISK
{request.risk_class}

ALLOWED PATHS
{allowed}

ACCEPTANCE
{acceptance}

CONSTRAINTS
{constraints}

EXECUTION RULES
- Work only inside the allowed paths unless a generated lockfile or required metadata
  change is unavoidable; report any such exception.
- Do not expose credentials, environment secrets, or private data.
- Run focused deterministic checks before claiming completion.
- Do not claim a check passed unless you executed it.

RESULT CONTRACT
Return a JSON object with exactly these semantic fields (additional diagnostic fields are allowed):
{{
  "status": "complete|blocked|failed",
  "provider": "{request.provider}",
  "changedPaths": ["path"],
  "checks": ["exact command/check and result"],
  "remainingConcerns": ["concern or None known"]
}}
"""


@activity.defn
async def run_execution_activity(request: ExecutionAttemptInput) -> dict[str, Any]:
    registry = default_execution_registry(load_entry_points=True)
    backend = registry.backend(request.provider)
    execution = ExecutionRequest(
        provider=request.provider,
        prompt=_runtime_prompt(request),
        cwd=request.task.cwd,
        model_selector=request.task.model_selector,
        reasoning_effort=request.task.reasoning_effort,
        session_name=f"dt-{request.attempt}-{request.provider}",
        timeout_seconds=request.task.provider_timeout_seconds,
        max_output_chars=request.task.max_output_chars,
    )
    task = asyncio.create_task(backend.execute(execution))
    heartbeat_seconds = 30.0
    while True:
        try:
            outcome = await asyncio.wait_for(asyncio.shield(task), timeout=heartbeat_seconds)
            return outcome.to_dict()
        except asyncio.TimeoutError:
            activity.heartbeat(
                {
                    "provider": request.provider,
                    "attempt": request.attempt,
                    "status": "running",
                }
            )
        except asyncio.CancelledError:
            task.cancel()
            raise


@activity.defn
def verify_execution_activity(request: VerificationInput) -> dict[str, Any]:
    """Verify structured worker evidence against the actual git diff.

    Evidence problems are returned as data instead of retryable Activity errors;
    they are semantic execution outcomes, not infrastructure failures.
    """

    try:
        evidence = parse_worker_result(request.stdout)
        actual_paths = git_changed_paths(request.cwd, request.base_ref)
        verified = validate_evidence(
            evidence,
            allowed_paths=request.allowed_paths,
            actual_paths=actual_paths,
        )
        return {
            "complete": verified.status == "complete",
            "status": verified.status,
            "changedPaths": list(verified.changed_paths),
            "checks": list(verified.checks),
            "remainingConcerns": list(verified.remaining_concerns),
            "actualPaths": list(actual_paths),
            "error": None,
        }
    except (EvidenceError, OSError, ValueError) as exc:
        return {
            "complete": False,
            "status": "invalid_evidence",
            "changedPaths": [],
            "checks": [],
            "remainingConcerns": ["Evidence verification failed."],
            "actualPaths": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


@activity.defn
async def assess_result_activity(request: ResultDecisionInput) -> dict[str, Any]:
    engine = _jev_engine()
    verification = request.verification
    assessment = await assess_result(
        engine,
        objective=request.task.objective,
        risk_class=request.risk_class,
        provider=request.provider,
        exit_code=request.return_code,
        evidence_complete=bool(verification.get("complete")),
        worker_result=request.stdout,
        checks=list(verification.get("checks") or []),
        remaining_concerns=list(verification.get("remainingConcerns") or []),
    )
    return assessment.to_dict()
