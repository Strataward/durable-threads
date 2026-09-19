"""Temporal Workflows for crash-resilient Durable Threads execution.

Workflow code is deterministic. Jev calls, provider execution, availability
probes, filesystem reads, and git inspection are delegated to Activities.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .temporal_activities import (
        assess_result_activity,
        assess_task_activity,
        route_executors_activity,
        run_execution_activity,
        verify_execution_activity,
    )
    from .temporal_contracts import (
        AttemptResult,
        ExecutionAttemptInput,
        ResultDecisionInput,
        ReviewDecision,
        RouteExecutorsInput,
        TaskRunInput,
        TaskRunResult,
        VerificationInput,
    )

_DECISION_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)
_READ_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=5),
    maximum_attempts=2,
)
# Provider execution can mutate a checkout or a remote system. Blind Activity
# retries may duplicate side effects, so recovery/escalation is explicit.
_EXECUTION_RETRY = RetryPolicy(maximum_attempts=1)


def _failed_attempt(provider: str, error: BaseException) -> AttemptResult:
    return AttemptResult(
        provider=provider,
        return_code=1,
        stdout="",
        stderr=f"child workflow failed: {type(error).__name__}: {error}",
        session_id=None,
        usage=None,
        verification={
            "complete": False,
            "status": "child_failure",
            "changedPaths": [],
            "checks": [],
            "remainingConcerns": ["Execution failed before verified completion."],
            "actualPaths": [],
            "error": type(error).__name__,
        },
        result_assessment={
            "integrationReady": False,
            "accepted": False,
            "reviewRequired": True,
            "intervention": "human_review",
            "interventionCertainty": 1.0,
            "semanticCompleteProbability": 0.0,
            "evidenceSufficientProbability": 0.0,
        },
        accepted=False,
        review_required=True,
    )


def _attempt_rank(attempt: AttemptResult) -> tuple[int, int, float, float]:
    semantic = attempt.result_assessment
    return (
        1 if attempt.accepted else 0,
        1 if semantic.get("integrationReady") else 0,
        float(semantic.get("semanticCompleteProbability") or 0.0),
        float(semantic.get("evidenceSufficientProbability") or 0.0),
    )


def _stronger_effort(current: str) -> str:
    ladder = ["none", "minimal", "low", "medium", "high", "xhigh", "max"]
    try:
        index = ladder.index(current)
    except ValueError:
        return "high"
    return ladder[min(index + 1, len(ladder) - 1)]


@workflow.defn
class AgentExecutionWorkflow:
    """One bounded executor attempt plus deterministic and semantic verification."""

    @workflow.run
    async def run(self, request: ExecutionAttemptInput) -> AttemptResult:
        outcome = await workflow.execute_activity(
            run_execution_activity,
            request,
            start_to_close_timeout=timedelta(
                seconds=request.task.provider_timeout_seconds + 60
            ),
            heartbeat_timeout=timedelta(seconds=45),
            retry_policy=_EXECUTION_RETRY,
        )
        verification = await workflow.execute_activity(
            verify_execution_activity,
            VerificationInput(
                cwd=request.task.cwd,
                base_ref=request.task.base_ref,
                allowed_paths=request.task.allowed_paths,
                stdout=str(outcome.get("stdout") or ""),
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_READ_RETRY,
        )
        assessment = await workflow.execute_activity(
            assess_result_activity,
            ResultDecisionInput(
                task=request.task,
                provider=request.provider,
                risk_class=request.risk_class,
                return_code=int(outcome.get("returnCode") or 0),
                stdout=str(outcome.get("stdout") or ""),
                verification=verification,
            ),
            start_to_close_timeout=timedelta(seconds=45),
            retry_policy=_DECISION_RETRY,
        )
        usage = outcome.get("usage")
        return AttemptResult(
            provider=request.provider,
            return_code=int(outcome.get("returnCode") or 0),
            stdout=str(outcome.get("stdout") or ""),
            stderr=str(outcome.get("stderr") or ""),
            session_id=(
                None if outcome.get("sessionId") is None else str(outcome["sessionId"])
            ),
            usage=(
                None
                if usage is None
                else {str(key): int(value) for key, value in dict(usage).items()}
            ),
            verification=verification,
            result_assessment=assessment,
            accepted=bool(assessment.get("accepted")),
            review_required=bool(assessment.get("reviewRequired")),
        )


@workflow.defn
class DurableTaskWorkflow:
    """Decide -> route -> execute -> verify -> escalate as a durable policy loop."""

    def __init__(self) -> None:
        self._phase = "created"
        self._risk: str | None = None
        self._round = 0
        self._active_providers: list[str] = []
        self._review_decision: ReviewDecision | None = None

    @workflow.query
    def status(self) -> dict[str, Any]:
        return {
            "phase": self._phase,
            "risk": self._risk,
            "round": self._round,
            "activeProviders": list(self._active_providers),
            "reviewPending": self._phase == "waiting_for_human_review",
        }

    @workflow.signal
    def review(self, decision: ReviewDecision) -> None:
        self._review_decision = decision

    async def _wait_for_review(self) -> ReviewDecision:
        self._phase = "waiting_for_human_review"
        self._review_decision = None
        await workflow.wait_condition(lambda: self._review_decision is not None)
        assert self._review_decision is not None
        decision = self._review_decision
        self._review_decision = None
        return decision

    async def _run_children(
        self,
        task: TaskRunInput,
        *,
        risk: str,
        execution_shape: str,
        providers: list[str],
    ) -> list[AttemptResult]:
        self._active_providers = providers
        parent_id = workflow.info().workflow_id

        async def run_one(index: int, provider: str) -> AttemptResult:
            try:
                return await workflow.execute_child_workflow(
                    AgentExecutionWorkflow.run,
                    ExecutionAttemptInput(
                        task=task,
                        provider=provider,
                        risk_class=risk,
                        attempt=self._round,
                        execution_shape=execution_shape,
                    ),
                    id=f"{parent_id}:exec:{self._round}:{index}:{provider}",
                )
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                return _failed_attempt(provider, exc)

        children = [
            asyncio.create_task(run_one(index, provider))
            for index, provider in enumerate(providers)
        ]
        results = await asyncio.gather(*children)
        self._active_providers = []
        return list(results)

    def _result(
        self,
        *,
        status: str,
        risk: str,
        assessment: dict[str, Any],
        attempts: list[AttemptResult],
        provider: str | None,
        review_note: str | None = None,
    ) -> TaskRunResult:
        self._phase = status
        return TaskRunResult(
            status=status,
            final_risk=risk,
            selected_provider=provider,
            task_assessment=assessment,
            attempts=attempts,
            review_note=review_note,
        )

    @workflow.run
    async def run(self, task: TaskRunInput) -> TaskRunResult:
        self._phase = "assessing"
        task_assessment = await workflow.execute_activity(
            assess_task_activity,
            task,
            start_to_close_timeout=timedelta(seconds=45),
            retry_policy=_DECISION_RETRY,
        )
        risk = str(task_assessment["finalRisk"])
        self._risk = risk

        # Consequence policy remains authoritative: a high-risk gate pauses
        # durably even if the probabilistic decision engine is highly confident.
        if bool(task_assessment.get("humanGateRequired")):
            decision = await self._wait_for_review()
            if not decision.approved:
                return self._result(
                    status="rejected",
                    risk=risk,
                    assessment=task_assessment,
                    attempts=[],
                    provider=None,
                    review_note=decision.note,
                )

        attempts: list[AttemptResult] = []
        excluded: list[str] = []
        preferred = list(task.preferred_providers)
        execution_shape = str(task_assessment["executionShape"])

        for round_index in range(1, task.max_attempts + 1):
            self._round = round_index
            self._phase = "routing"
            routes = await workflow.execute_activity(
                route_executors_activity,
                RouteExecutorsInput(
                    task=task,
                    assessment=task_assessment,
                    excluded_providers=excluded,
                    preferred_providers=preferred,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_READ_RETRY,
            )
            providers: list[str] = []
            for route in routes:
                provider = str(route["executor"]["provider"])
                if provider not in providers:
                    providers.append(provider)
            if not providers:
                break

            self._phase = "executing"
            current = await self._run_children(
                task,
                risk=risk,
                execution_shape=execution_shape,
                providers=providers,
            )
            attempts.extend(current)
            best = max(current, key=_attempt_rank)
            semantic = best.result_assessment

            if best.accepted:
                return self._result(
                    status="complete",
                    risk=risk,
                    assessment=task_assessment,
                    attempts=attempts,
                    provider=best.provider,
                )

            integration_ready = bool(semantic.get("integrationReady"))
            review_required = (
                bool(task_assessment.get("reviewRequired"))
                or best.review_required
            )
            if integration_ready and review_required:
                if task.wait_for_human_review:
                    decision = await self._wait_for_review()
                    if decision.approved:
                        return self._result(
                            status="complete",
                            risk=risk,
                            assessment=task_assessment,
                            attempts=attempts,
                            provider=best.provider,
                            review_note=decision.note,
                        )
                    return self._result(
                        status="rejected",
                        risk=risk,
                        assessment=task_assessment,
                        attempts=attempts,
                        provider=best.provider,
                        review_note=decision.note,
                    )
                return self._result(
                    status="review_required",
                    risk=risk,
                    assessment=task_assessment,
                    attempts=attempts,
                    provider=best.provider,
                )

            intervention = str(semantic.get("intervention") or "human_review")
            if intervention == "human_review":
                if task.wait_for_human_review:
                    decision = await self._wait_for_review()
                    if decision.approved:
                        return self._result(
                            status="complete",
                            risk=risk,
                            assessment=task_assessment,
                            attempts=attempts,
                            provider=best.provider,
                            review_note=decision.note,
                        )
                    return self._result(
                        status="rejected",
                        risk=risk,
                        assessment=task_assessment,
                        attempts=attempts,
                        provider=best.provider,
                        review_note=decision.note,
                    )
                return self._result(
                    status="review_required",
                    risk=risk,
                    assessment=task_assessment,
                    attempts=attempts,
                    provider=best.provider,
                )

            if intervention == "switch_executor":
                if best.provider not in excluded:
                    excluded.append(best.provider)
                preferred = []
            elif intervention == "correct_same":
                preferred = [best.provider]
            elif intervention == "stronger_model":
                task.reasoning_effort = _stronger_effort(task.reasoning_effort)
                preferred = [best.provider]
            else:
                return self._result(
                    status="review_required",
                    risk=risk,
                    assessment=task_assessment,
                    attempts=attempts,
                    provider=best.provider,
                )

        selected = max(attempts, key=_attempt_rank).provider if attempts else None
        return self._result(
            status="failed",
            risk=risk,
            assessment=task_assessment,
            attempts=attempts,
            provider=selected,
        )
