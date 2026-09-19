"""Decision-intelligence layer for task routing and result acceptance."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .decisions import DecisionBatch, DecisionEngine, DecisionPolicy, DecisionQuestion
from .risk import RISK_LEVELS, classify_risk, meets_threshold, validate_risk

_RISK_RANK = {risk: index for index, risk in enumerate(RISK_LEVELS)}


def _noul_probability(batch: DecisionBatch, name: str) -> float:
    answer = batch.answer(name)
    return float(answer.probabilities.get("true", 1.0 if answer.value is True else 0.0))


def _higher_risk(left: str, right: str) -> str:
    left = validate_risk(left)
    right = validate_risk(right)
    return left if _RISK_RANK[left] >= _RISK_RANK[right] else right


@dataclass(frozen=True)
class TaskAssessment:
    """Semantic task judgment combined with deterministic safety floors."""

    heuristic_risk: str
    semantic_risk: str
    final_risk: str
    delegate_probability: float
    ambiguity_probability: float
    independent_review_probability: float
    execution_shape: str
    execution_shape_certainty: float
    review_required: bool
    human_gate_required: bool
    batch: DecisionBatch

    def to_dict(self) -> dict[str, Any]:
        return {
            "heuristicRisk": self.heuristic_risk,
            "semanticRisk": self.semantic_risk,
            "finalRisk": self.final_risk,
            "delegateProbability": self.delegate_probability,
            "ambiguityProbability": self.ambiguity_probability,
            "independentReviewProbability": self.independent_review_probability,
            "executionShape": self.execution_shape,
            "executionShapeCertainty": self.execution_shape_certainty,
            "reviewRequired": self.review_required,
            "humanGateRequired": self.human_gate_required,
            "decision": self.batch.to_dict(),
        }


@dataclass(frozen=True)
class ResultAssessment:
    """Semantic result judgment with deterministic acceptance gates."""

    semantic_complete_probability: float
    evidence_sufficient_probability: float
    intervention: str
    intervention_certainty: float
    integration_ready: bool
    accepted: bool
    review_required: bool
    batch: DecisionBatch

    def to_dict(self) -> dict[str, Any]:
        return {
            "semanticCompleteProbability": self.semantic_complete_probability,
            "evidenceSufficientProbability": self.evidence_sufficient_probability,
            "intervention": self.intervention,
            "interventionCertainty": self.intervention_certainty,
            "integrationReady": self.integration_ready,
            "accepted": self.accepted,
            "reviewRequired": self.review_required,
            "decision": self.batch.to_dict(),
        }


async def assess_task(
    engine: DecisionEngine,
    *,
    objective: str,
    allowed_paths: list[str] | tuple[str, ...],
    acceptance: list[str] | tuple[str, ...],
    context: Mapping[str, Any] | None = None,
    policy: DecisionPolicy | None = None,
    human_gate_at: str = "R4",
) -> TaskAssessment:
    """Batch the high-frequency task judgments into one decision-engine call.

    Jev may classify risk lower than the deterministic risk detector. Durable
    Threads always takes the higher class, so semantic intelligence can raise a
    safety floor but cannot silently lower it.
    """

    policy = policy or DecisionPolicy()
    human_gate_at = validate_risk(human_gate_at)
    heuristic = classify_risk(
        objective=objective,
        allowed_paths=allowed_paths,
        acceptance=acceptance,
    )
    state: dict[str, Any] = {
        "objective": objective,
        "allowedPaths": list(allowed_paths),
        "acceptance": list(acceptance),
        "runtime": dict(context or {}),
    }
    questions = {
        "risk": DecisionQuestion.choice(
            "Classify consequence risk, not implementation difficulty.",
            {
                "R0": "Mechanical or documentation-only change with negligible consequence.",
                "R1": "Bounded isolated feature or bug fix with narrow blast radius.",
                "R2": "Integration or contract change across components or external systems.",
                "R3": (
                    "Critical security, auth, privacy, payments, destructive data, "
                    "or concurrency work."
                ),
                "R4": (
                    "Systemic distributed architecture, control-plane, recovery, "
                    "or platform migration work."
                ),
            },
        ),
        "delegate": DecisionQuestion.noul(
            (
                "Would handing this bounded task to an execution worker improve "
                "throughput or isolation?"
            ),
            true="Delegation has a clear implementation/review boundary.",
            false=(
                "The current planner should keep the work local because delegation "
                "adds ambiguity or overhead."
            ),
        ),
        "ambiguous": DecisionQuestion.noul(
            (
                "Is the objective materially ambiguous such that execution risks "
                "solving the wrong problem?"
            ),
            true="Important requirements or acceptance conditions are unresolved.",
            false="The task is bounded enough to execute against the supplied contract.",
        ),
        "execution_shape": DecisionQuestion.choice(
            "Choose the smallest execution shape likely to produce reliable evidence.",
            {
                "single_worker": "One bounded executor is sufficient.",
                "worker_plus_review": "One executor followed by independent review is warranted.",
                "parallel_workers": (
                    "Two independent executors are worth the extra cost because "
                    "uncertainty is high."
                ),
            },
        ),
        "independent_review": DecisionQuestion.noul(
            "Should a successful implementation receive independent review before integration?",
            true="The consequence or ambiguity justifies a separate reviewer.",
            false="Deterministic checks are sufficient at this consequence level.",
        ),
    }
    batch = await engine.decide(state=state, questions=questions)
    semantic_risk = str(batch.answer("risk").value)
    if semantic_risk not in RISK_LEVELS:
        raise ValueError(f"decision engine returned unsupported risk class: {semantic_risk!r}")
    final_risk = _higher_risk(heuristic.risk_class, semantic_risk)
    delegate_probability = _noul_probability(batch, "delegate")
    ambiguity_probability = _noul_probability(batch, "ambiguous")
    independent_review_probability = _noul_probability(batch, "independent_review")
    shape = batch.answer("execution_shape")

    review_required = (
        meets_threshold(final_risk, "R3")
        or independent_review_probability >= policy.threshold_for(final_risk)
        or shape.value == "worker_plus_review"
    )
    execution_shape = str(shape.value)
    # Deterministic policy may strengthen, but never weaken, the semantic shape.
    if review_required and execution_shape == "single_worker":
        execution_shape = "worker_plus_review"

    return TaskAssessment(
        heuristic_risk=heuristic.risk_class,
        semantic_risk=semantic_risk,
        final_risk=final_risk,
        delegate_probability=delegate_probability,
        ambiguity_probability=ambiguity_probability,
        independent_review_probability=independent_review_probability,
        execution_shape=execution_shape,
        execution_shape_certainty=shape.certainty,
        review_required=review_required,
        human_gate_required=meets_threshold(final_risk, human_gate_at),
        batch=batch,
    )


async def assess_result(
    engine: DecisionEngine,
    *,
    objective: str,
    risk_class: str,
    provider: str,
    exit_code: int,
    evidence_complete: bool,
    worker_result: str,
    checks: list[str] | tuple[str, ...] = (),
    remaining_concerns: list[str] | tuple[str, ...] = (),
    policy: DecisionPolicy | None = None,
) -> ResultAssessment:
    """Judge semantic completeness while deterministic evidence controls acceptance."""

    policy = policy or DecisionPolicy()
    risk = validate_risk(risk_class)
    state = {
        "objective": objective,
        "riskClass": risk,
        "provider": provider,
        "exitCode": exit_code,
        "evidenceComplete": evidence_complete,
        "checks": list(checks),
        "remainingConcerns": list(remaining_concerns),
        "workerResult": worker_result[:6000],
    }
    questions = {
        "semantic_complete": DecisionQuestion.noul(
            (
                "Does the reported result satisfy the user's objective rather than "
                "merely completing some work?"
            ),
            true="The result substantively satisfies the objective and stated acceptance intent.",
            false="Important requested behavior is missing, contradicted, or unresolved.",
        ),
        "evidence_sufficient": DecisionQuestion.noul(
            "Is the supplied evidence sufficient to justify the claimed result?",
            true="The checks and reported evidence are proportionate to the claim.",
            false="The claim is under-evidenced, vague, or depends on unverified assumptions.",
        ),
        "intervention": DecisionQuestion.choice(
            "Choose the next intervention if this result cannot be integrated as-is.",
            {
                "accept": "The result is complete enough to pass semantic review.",
                "correct_same": "A focused correction by the same executor is likely sufficient.",
                "switch_executor": "The failure suggests a capability or execution mismatch.",
                "stronger_model": (
                    "The work needs materially stronger reasoning, not just another attempt."
                ),
                "human_review": "The remaining ambiguity or consequence requires a person.",
            },
        ),
    }
    batch = await engine.decide(state=state, questions=questions)
    semantic_probability = _noul_probability(batch, "semantic_complete")
    evidence_probability = _noul_probability(batch, "evidence_sufficient")
    intervention = batch.answer("intervention")
    threshold = policy.threshold_for(risk)

    deterministic_pass = exit_code == 0 and evidence_complete
    review_required = meets_threshold(risk, "R3") or intervention.value == "human_review"
    integration_ready = (
        deterministic_pass
        and semantic_probability >= threshold
        and evidence_probability >= threshold
        and intervention.value == "accept"
    )
    accepted = integration_ready and not review_required
    return ResultAssessment(
        semantic_complete_probability=semantic_probability,
        evidence_sufficient_probability=evidence_probability,
        intervention=str(intervention.value),
        intervention_certainty=intervention.certainty,
        integration_ready=integration_ready,
        accepted=accepted,
        review_required=review_required,
        batch=batch,
    )
