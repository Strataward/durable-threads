"""Provider-neutral decision contracts with an optional TypeSafe Jev backend.

Durable Threads treats probabilistic judgments as evidence. Deterministic policy
retains authority over side effects, escalation, and acceptance.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .risk import RISK_LEVELS, classify_risk

JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
JSONState = str | dict[str, Any] | list[Any]


class DecisionError(RuntimeError):
    """Raised when a decision engine cannot produce a valid typed result."""


class QuestionKind(str, Enum):
    NOUL = "noul"
    CHOICE = "choice"
    SCORE = "score"


class DecisionGate(str, Enum):
    AUTO = "auto"
    VERIFY = "verify"
    REVIEW = "review"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class DecisionQuestion:
    """Provider-neutral closed-answer question."""

    kind: QuestionKind
    instructions: JSONState | None = None
    criteria: Mapping[str, JSONState | None] | tuple[JSONState, ...] | None = None

    @classmethod
    def noul(
        cls,
        instructions: JSONState,
        *,
        true: JSONState | None = None,
        false: JSONState | None = None,
    ) -> DecisionQuestion:
        criteria: dict[str, JSONState | None] | None = None
        if true is not None or false is not None:
            criteria = {"true": true, "false": false}
        return cls(QuestionKind.NOUL, instructions, criteria)

    @classmethod
    def choice(
        cls,
        instructions: JSONState,
        criteria: Mapping[str, JSONState | None],
    ) -> DecisionQuestion:
        if not criteria:
            raise ValueError("choice criteria must not be empty")
        return cls(QuestionKind.CHOICE, instructions, dict(criteria))

    @classmethod
    def score(
        cls,
        instructions: JSONState,
        criteria: tuple[JSONState, ...] | list[JSONState],
    ) -> DecisionQuestion:
        if not criteria:
            raise ValueError("score criteria must not be empty")
        return cls(QuestionKind.SCORE, instructions, tuple(criteria))


@dataclass(frozen=True)
class DecisionAnswer:
    """Canonical answer independent of the underlying decision provider.

    ``certainty`` is the highest observed probability for Noul/Choice answers or
    the provider-reported confidence for Score answers. ``provider_confidence``
    is preserved separately when the provider exposes a distinct confidence
    field. Durable Threads never treats either value as authorization by itself.
    """

    name: str
    kind: QuestionKind
    value: bool | str | float
    certainty: float
    probabilities: Mapping[str, float]
    provider_confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "value": self.value,
            "certainty": self.certainty,
            "probabilities": dict(self.probabilities),
            "providerConfidence": self.provider_confidence,
        }


@dataclass(frozen=True)
class DecisionBatch:
    """One decision-engine call over a shared state."""

    engine: str
    model: str
    state_hash: str
    answers: Mapping[str, DecisionAnswer]
    usage: Mapping[str, int] | None = None

    def answer(self, name: str) -> DecisionAnswer:
        try:
            return self.answers[name]
        except KeyError as exc:
            raise DecisionError(f"decision answer not found: {name}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "model": self.model,
            "stateHash": self.state_hash,
            "answers": {name: answer.to_dict() for name, answer in self.answers.items()},
            "usage": dict(self.usage) if self.usage is not None else None,
        }


@runtime_checkable
class DecisionEngine(Protocol):
    async def decide(
        self,
        *,
        state: JSONState,
        questions: Mapping[str, DecisionQuestion],
    ) -> DecisionBatch:
        """Evaluate typed questions against one shared state."""


def canonical_state_hash(state: JSONState) -> str:
    """Hash decision state without storing it in the canonical decision record."""

    payload = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


class JevDecisionEngine:
    """TypeSafe Jev implementation of :class:`DecisionEngine`.

    The dependency is optional. Install ``durable-threads[jev]`` and configure
    ``TYPESAFE_API_KEY`` (or pass ``api_key`` explicitly) before using it.
    """

    def __init__(
        self,
        *,
        model: str = "jev-latest",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not model.strip():
            raise ValueError("model must be a non-empty string")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    async def decide(
        self,
        *,
        state: JSONState,
        questions: Mapping[str, DecisionQuestion],
    ) -> DecisionBatch:
        if not questions:
            raise DecisionError("questions must not be empty")
        try:
            from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise DecisionError(
                "TypeSafe SDK is not installed; install durable-threads[jev]"
            ) from exc

        wire_questions: dict[str, Any] = {}
        for name, question in questions.items():
            if not name or not isinstance(name, str):
                raise DecisionError("question names must be non-empty strings")
            if question.kind is QuestionKind.NOUL:
                criteria = None
                if isinstance(question.criteria, Mapping):
                    criteria = {
                        "true": question.criteria.get("true"),
                        "false": question.criteria.get("false"),
                    }
                wire_questions[name] = Noul(
                    instructions=question.instructions,
                    criteria=criteria,
                )
            elif question.kind is QuestionKind.CHOICE:
                if not isinstance(question.criteria, Mapping) or not question.criteria:
                    raise DecisionError(f"choice question {name!r} requires mapping criteria")
                wire_questions[name] = Choice(
                    instructions=question.instructions,
                    criteria=dict(question.criteria),
                )
            elif question.kind is QuestionKind.SCORE:
                if not isinstance(question.criteria, tuple) or not question.criteria:
                    raise DecisionError(f"score question {name!r} requires ordered criteria")
                wire_questions[name] = Score(
                    instructions=question.instructions,
                    criteria=list(question.criteria),
                )
            else:  # pragma: no cover - enum prevents this in normal construction
                raise DecisionError(f"unsupported decision question kind: {question.kind}")

        async with AsyncTypeSafeClient(
            api_key=self.api_key,
            model=self.model,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            response = await client.system_one(state=state, questions=wire_questions)

        answers: dict[str, DecisionAnswer] = {}
        for name, answer in response.answers.items():
            answer_type = getattr(answer, "type", None)
            if answer_type == "noul":
                probability = float(answer.noul)
                probabilities = {"true": probability, "false": 1.0 - probability}
                answers[name] = DecisionAnswer(
                    name=name,
                    kind=QuestionKind.NOUL,
                    value=probability >= 0.5,
                    certainty=max(probabilities.values()),
                    probabilities=probabilities,
                    provider_confidence=None,
                )
            elif answer_type == "choice":
                probabilities = {
                    str(key): float(value)
                    for key, value in answer.probabilities.items()
                }
                answers[name] = DecisionAnswer(
                    name=name,
                    kind=QuestionKind.CHOICE,
                    value=str(answer.choice),
                    certainty=max(probabilities.values()) if probabilities else 0.0,
                    probabilities=probabilities,
                    provider_confidence=float(answer.confidence),
                )
            elif answer_type == "score":
                probabilities = {
                    str(key): float(value)
                    for key, value in answer.probabilities.items()
                }
                answers[name] = DecisionAnswer(
                    name=name,
                    kind=QuestionKind.SCORE,
                    value=float(answer.score),
                    certainty=float(answer.confidence),
                    probabilities=probabilities,
                    provider_confidence=float(answer.confidence),
                )
            else:
                raise DecisionError(f"unsupported Jev answer type for {name!r}: {answer_type!r}")

        usage: dict[str, int] = {}
        input_tokens = getattr(response.usage, "input_tokens", None)
        output_tokens = getattr(response.usage, "output_tokens", None)
        if isinstance(input_tokens, int):
            usage["inputTokens"] = input_tokens
        if isinstance(output_tokens, int):
            usage["outputTokens"] = output_tokens
        return DecisionBatch(
            engine="typesafe:system-one",
            model=response.model,
            state_hash=canonical_state_hash(state),
            answers=answers,
            usage=usage or None,
        )


@dataclass(frozen=True)
class HeuristicDecisionEngine:
    """Deterministic decision engine for offline execution and tests."""

    engine_name: str = "heuristic"
    model: str = "heuristic"

    async def decide(
        self,
        *,
        state: JSONState,
        questions: Mapping[str, DecisionQuestion],
    ) -> DecisionBatch:
        answers: dict[str, DecisionAnswer] = {}
        for name, question in questions.items():
            if name not in {
                "risk",
                "delegate",
                "ambiguous",
                "execution_shape",
                "independent_review",
                "semantic_complete",
                "evidence_sufficient",
                "intervention",
            }:
                raise DecisionError(f"heuristic engine does not support question: {name}")
            if not isinstance(state, dict):
                raise DecisionError("heuristic engine requires object state")
            answers[name] = self._answer(name, question, state)
        return DecisionBatch(
            engine=self.engine_name,
            model=self.model,
            state_hash=canonical_state_hash(state),
            answers=answers,
            usage=None,
        )

    @staticmethod
    def _answer(
        name: str,
        question: DecisionQuestion,
        state: Mapping[str, Any],
    ) -> DecisionAnswer:
        if name == "risk":
            risk = classify_risk(
                objective=str(state.get("objective", "")),
                allowed_paths=state.get("allowedPaths", []),
                acceptance=state.get("acceptance", []),
            ).risk_class
            probabilities = {risk_name: 0.025 for risk_name in RISK_LEVELS}
            probabilities[risk] = 0.90
            return _heuristic_answer(name, question, risk, probabilities)

        if name == "delegate":
            probability = (
                0.85
                if len(state.get("allowedPaths", [])) >= 1
                and len(state.get("acceptance", [])) >= 1
                else 0.30
            )
            return _heuristic_answer(
                name, question, probability >= 0.5, _noul_probabilities(probability)
            )

        if name == "ambiguous":
            probability = 0.20 if state.get("acceptance") else 0.70
            return _heuristic_answer(
                name, question, probability >= 0.5, _noul_probabilities(probability)
            )

        risk = str(
            classify_risk(
                objective=str(state.get("objective", "")),
                allowed_paths=state.get("allowedPaths", []),
                acceptance=state.get("acceptance", []),
            ).risk_class
        )
        high_risk = risk in {"R3", "R4"}
        if name == "execution_shape":
            value = "worker_plus_review" if high_risk else "single_worker"
            probabilities = {
                "single_worker": 0.05,
                "worker_plus_review": 0.05,
                "parallel_workers": 0.05,
            }
            probabilities[value] = 0.90
            return _heuristic_answer(name, question, value, probabilities)

        if name == "independent_review":
            probability = 0.95 if high_risk else 0.15
            return _heuristic_answer(
                name, question, probability >= 0.5, _noul_probabilities(probability)
            )

        if name == "semantic_complete":
            probability = (
                0.90
                if state.get("exitCode") == 0 and bool(state.get("evidenceComplete"))
                else 0.10
            )
            return _heuristic_answer(
                name, question, probability >= 0.5, _noul_probabilities(probability)
            )

        if name == "evidence_sufficient":
            probability = (
                0.90
                if bool(state.get("evidenceComplete")) and len(state.get("checks", [])) > 0
                else 0.10
            )
            return _heuristic_answer(
                name, question, probability >= 0.5, _noul_probabilities(probability)
            )

        exit_code = state.get("exitCode")
        if exit_code == 0 and state.get("evidenceComplete"):
            value = "accept"
            probability = 0.90
        elif exit_code == 0:
            value = "correct_same"
            probability = 0.60
        else:
            value = "switch_executor"
            probability = 0.60
        choices = ("accept", "correct_same", "switch_executor", "stronger_model", "human_review")
        remainder = (1.0 - probability) / (len(choices) - 1)
        probabilities = {choice: remainder for choice in choices}
        probabilities[value] = probability
        return _heuristic_answer(name, question, value, probabilities)


def _noul_probabilities(true_probability: float) -> dict[str, float]:
    return {"true": true_probability, "false": 1.0 - true_probability}


def _heuristic_answer(
    name: str,
    question: DecisionQuestion,
    value: bool | str,
    probabilities: Mapping[str, float],
) -> DecisionAnswer:
    expected_kind = QuestionKind.NOUL if isinstance(value, bool) else QuestionKind.CHOICE
    if question.kind is not expected_kind:
        raise DecisionError(
            f"question {name!r} has kind {question.kind.value!r}; "
            f"expected {expected_kind.value!r}"
        )
    return DecisionAnswer(
        name=name,
        kind=expected_kind,
        value=value,
        certainty=max(probabilities.values()),
        probabilities=probabilities,
        provider_confidence=None,
    )


def decision_engine_from_env(
    environ: Mapping[str, str] | None = None,
) -> DecisionEngine:
    """Build the configured decision engine without requiring network access."""

    values = os.environ if environ is None else environ
    configured = values.get("DURABLE_THREADS_DECISION_ENGINE")
    engine_name = configured or ("jev" if values.get("TYPESAFE_API_KEY") else "heuristic")
    if engine_name == "heuristic":
        return HeuristicDecisionEngine()
    if engine_name == "jev":
        return JevDecisionEngine(
            model=values.get("DURABLE_THREADS_JEV_MODEL", "jev-latest"),
            api_key=values.get("TYPESAFE_API_KEY") or None,
            base_url=values.get("TYPESAFE_BASE_URL") or None,
            timeout_seconds=float(values.get("DURABLE_THREADS_JEV_TIMEOUT_SECONDS", "30")),
        )
    raise ValueError(
        "DURABLE_THREADS_DECISION_ENGINE must be one of: jev, heuristic"
    )


@dataclass(frozen=True)
class DecisionPolicy:
    """Deterministic policy for turning uncertainty into control-flow gates."""

    escalate_below: float = 0.60
    review_below: float = 0.80
    auto_threshold_r0: float = 0.70
    auto_threshold_r1: float = 0.85
    auto_threshold_r2: float = 0.90
    auto_threshold_r3: float = 0.97
    auto_threshold_r4: float = 1.00

    def threshold_for(self, risk_class: str) -> float:
        values = {
            "R0": self.auto_threshold_r0,
            "R1": self.auto_threshold_r1,
            "R2": self.auto_threshold_r2,
            "R3": self.auto_threshold_r3,
            "R4": self.auto_threshold_r4,
        }
        try:
            return values[risk_class.upper()]
        except KeyError as exc:
            raise ValueError("risk_class must be one of R0, R1, R2, R3, R4") from exc

    def gate(self, *, certainty: float, risk_class: str) -> DecisionGate:
        if not 0 <= certainty <= 1:
            raise ValueError("certainty must be between 0 and 1")
        risk = risk_class.upper()
        threshold = self.threshold_for(risk)
        if certainty < self.escalate_below:
            return DecisionGate.ESCALATE
        if risk in {"R3", "R4"}:
            return DecisionGate.REVIEW
        if certainty < self.review_below:
            return DecisionGate.REVIEW
        if certainty < threshold:
            return DecisionGate.VERIFY
        return DecisionGate.AUTO if risk == "R0" else DecisionGate.VERIFY


@dataclass(frozen=True)
class StaticDecisionEngine:
    """Small deterministic engine useful for tests and offline policy simulation."""

    answers: Mapping[str, DecisionAnswer]
    engine_name: str = "static"
    model: str = "static"

    async def decide(
        self,
        *,
        state: JSONState,
        questions: Mapping[str, DecisionQuestion],
    ) -> DecisionBatch:
        missing = [name for name in questions if name not in self.answers]
        if missing:
            raise DecisionError(f"static engine missing answer(s): {', '.join(missing)}")
        return DecisionBatch(
            engine=self.engine_name,
            model=self.model,
            state_hash=canonical_state_hash(state),
            answers={name: self.answers[name] for name in questions},
        )


def answer_from_dict(name: str, payload: Mapping[str, Any]) -> DecisionAnswer:
    """Hydrate a canonical answer from a stored/transport representation."""

    kind = QuestionKind(str(payload["kind"]))
    value = payload["value"]
    if kind is QuestionKind.NOUL and not isinstance(value, bool):
        raise ValueError("noul answer value must be boolean")
    if kind is QuestionKind.CHOICE and not isinstance(value, str):
        raise ValueError("choice answer value must be string")
    if kind is QuestionKind.SCORE and not isinstance(value, (int, float)):
        raise ValueError("score answer value must be numeric")
    probabilities = {
        str(key): float(probability)
        for key, probability in dict(payload.get("probabilities", {})).items()
    }
    return DecisionAnswer(
        name=name,
        kind=kind,
        value=value,
        certainty=float(payload["certainty"]),
        probabilities=probabilities,
        provider_confidence=(
            None
            if payload.get("providerConfidence") is None
            else float(payload["providerConfidence"])
        ),
    )


def dataclass_to_json(value: Any) -> dict[str, Any]:
    """Return a JSON-ready dataclass payload for workflow/activity boundaries."""

    return asdict(value)
