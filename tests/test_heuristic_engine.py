from __future__ import annotations

import asyncio

import pytest

from durable_threads.decisions import (
    HeuristicDecisionEngine,
    JevDecisionEngine,
    decision_engine_from_env,
)
from durable_threads.intelligence import assess_result, assess_task


def _task_assessment(objective: str, *, human_gate_at: str = "R4"):
    return asyncio.run(
        assess_task(
            HeuristicDecisionEngine(),
            objective=objective,
            allowed_paths=["docs/README.md"],
            acceptance=["the documentation is accurate"],
            human_gate_at=human_gate_at,
        )
    )


def test_docs_objective_uses_low_risk_single_worker() -> None:
    assessment = _task_assessment("Update the docs README")

    assert assessment.final_risk == "R0"
    assert assessment.execution_shape == "single_worker"
    assert not assessment.review_required


def test_auth_token_rotation_requires_review_without_default_human_gate() -> None:
    assessment = _task_assessment("Implement auth token rotation")
    gated = _task_assessment("Implement auth token rotation", human_gate_at="R3")

    assert assessment.final_risk == "R3"
    assert assessment.execution_shape == "worker_plus_review"
    assert assessment.review_required
    assert not assessment.human_gate_required
    assert gated.human_gate_required


def test_result_assessment_accepts_verified_success_and_switches_on_failure() -> None:
    accepted = asyncio.run(
        assess_result(
            HeuristicDecisionEngine(),
            objective="Update the docs README",
            risk_class="R1",
            provider="scripted",
            exit_code=0,
            evidence_complete=True,
            worker_result="complete",
            checks=["pytest -q: passed"],
        )
    )
    failed = asyncio.run(
        assess_result(
            HeuristicDecisionEngine(),
            objective="Update the docs README",
            risk_class="R1",
            provider="scripted",
            exit_code=1,
            evidence_complete=False,
            worker_result="failed",
        )
    )

    assert accepted.accepted
    assert failed.intervention == "switch_executor"
    assert not failed.accepted


def test_decision_engine_factory_defaults_and_validates() -> None:
    assert isinstance(decision_engine_from_env({}), HeuristicDecisionEngine)
    assert isinstance(
        decision_engine_from_env({"TYPESAFE_API_KEY": "x"}),
        JevDecisionEngine,
    )
    with pytest.raises(ValueError, match="jev, heuristic"):
        decision_engine_from_env({"DURABLE_THREADS_DECISION_ENGINE": "bogus"})
