from __future__ import annotations

import asyncio

from durable_threads.decisions import (
    DecisionAnswer,
    DecisionPolicy,
    QuestionKind,
    StaticDecisionEngine,
)
from durable_threads.intelligence import assess_result, assess_task


def _answer(name: str, kind: QuestionKind, value, certainty: float, probabilities):
    return DecisionAnswer(
        name=name,
        kind=kind,
        value=value,
        certainty=certainty,
        probabilities=probabilities,
    )


def test_semantic_risk_cannot_lower_deterministic_floor() -> None:
    engine = StaticDecisionEngine(
        {
            "risk": _answer("risk", QuestionKind.CHOICE, "R1", 0.9, {"R1": 0.9}),
            "delegate": _answer("delegate", QuestionKind.NOUL, True, 0.9, {"true": 0.9, "false": 0.1}),
            "ambiguous": _answer("ambiguous", QuestionKind.NOUL, False, 0.9, {"true": 0.1, "false": 0.9}),
            "execution_shape": _answer(
                "execution_shape", QuestionKind.CHOICE, "single_worker", 0.9, {"single_worker": 0.9}
            ),
            "independent_review": _answer(
                "independent_review", QuestionKind.NOUL, False, 0.9, {"true": 0.1, "false": 0.9}
            ),
        }
    )
    result = asyncio.run(
        assess_task(
            engine,
            objective="Fix authorization and refresh-token replay handling.",
            allowed_paths=["src/auth/session.py"],
            acceptance=["Unauthorized replay is rejected."],
        )
    )
    assert result.heuristic_risk == "R3"
    assert result.semantic_risk == "R1"
    assert result.final_risk == "R3"
    assert result.review_required
    assert result.execution_shape == "worker_plus_review"


def test_low_risk_result_can_pass_only_with_verified_evidence() -> None:
    engine = StaticDecisionEngine(
        {
            "semantic_complete": _answer(
                "semantic_complete", QuestionKind.NOUL, True, 0.96, {"true": 0.96, "false": 0.04}
            ),
            "evidence_sufficient": _answer(
                "evidence_sufficient", QuestionKind.NOUL, True, 0.96, {"true": 0.96, "false": 0.04}
            ),
            "intervention": _answer(
                "intervention", QuestionKind.CHOICE, "accept", 0.95, {"accept": 0.95}
            ),
        }
    )
    accepted = asyncio.run(
        assess_result(
            engine,
            objective="Fix one bounded UI bug.",
            risk_class="R1",
            provider="custom",
            exit_code=0,
            evidence_complete=True,
            worker_result="complete",
            checks=["pytest: passed"],
        )
    )
    missing_evidence = asyncio.run(
        assess_result(
            engine,
            objective="Fix one bounded UI bug.",
            risk_class="R1",
            provider="custom",
            exit_code=0,
            evidence_complete=False,
            worker_result="complete",
        )
    )
    assert accepted.integration_ready
    assert accepted.accepted
    assert not missing_evidence.integration_ready
    assert not missing_evidence.accepted


def test_critical_result_is_ready_for_review_not_auto_accepted() -> None:
    engine = StaticDecisionEngine(
        {
            "semantic_complete": _answer(
                "semantic_complete", QuestionKind.NOUL, True, 0.99, {"true": 0.99, "false": 0.01}
            ),
            "evidence_sufficient": _answer(
                "evidence_sufficient", QuestionKind.NOUL, True, 0.99, {"true": 0.99, "false": 0.01}
            ),
            "intervention": _answer(
                "intervention", QuestionKind.CHOICE, "accept", 0.99, {"accept": 0.99}
            ),
        }
    )
    result = asyncio.run(
        assess_result(
            engine,
            objective="Fix authorization replay handling.",
            risk_class="R3",
            provider="custom",
            exit_code=0,
            evidence_complete=True,
            worker_result="complete",
        )
    )
    assert result.integration_ready
    assert result.review_required
    assert not result.accepted


def test_policy_escalates_low_certainty() -> None:
    policy = DecisionPolicy()
    assert policy.gate(certainty=0.55, risk_class="R1").value == "escalate"
