from __future__ import annotations

from pathlib import Path

from durable_threads.config import load_roster
from durable_threads.packets import build_packet
from durable_threads.risk import classify_risk, meets_threshold
from durable_threads.routing import select_workers

ROOT = Path(__file__).parents[1]
ROSTER = ROOT / "examples" / "roster.json"


def test_economy_roster_uses_workhorse_execution_defaults() -> None:
    roster = load_roster(ROSTER)

    assert roster.schema_version == 2
    assert roster.strategy.profile == "economy"
    assert roster.strategy.sleeping_orchestrator
    assert roster.planner.reasoning_effort == "low"
    assert roster.reviewer.model_selector == "efficient"
    assert roster.reviewer.reasoning_effort == "xhigh"
    assert roster.workers[0].execution_class == "workhorse"
    assert roster.workers[0].reasoning_effort == "xhigh"


def test_risk_classifier_separates_mechanical_and_critical_work() -> None:
    docs = classify_risk(
        objective="Correct a typo in the README.",
        allowed_paths=["README.md"],
    )
    auth = classify_risk(
        objective="Fix authorization and refresh-token replay handling.",
        allowed_paths=["src/auth/session.py"],
    )

    assert docs.risk_class == "R0"
    assert auth.risk_class == "R3"
    assert meets_threshold(auth.risk_class, "R3")
    assert not meets_threshold(docs.risk_class, "R3")


def test_high_risk_route_recommends_frontier_review() -> None:
    roster = load_roster(ROSTER)

    decision = select_workers(
        roster,
        objective="Fix an authorization vulnerability in the session boundary.",
        allowed_paths=["src/auth/session.py"],
        acceptance=["Unauthorized replay is rejected."],
    )

    assert decision.risk.risk_class == "R3"
    assert decision.frontier_review_recommended
    assert [worker.name for worker in decision.selected] == [
        "implementation",
        "security-review",
    ]


def test_packet_carries_frozen_decisions_invariants_and_non_goals() -> None:
    worker = load_roster(ROSTER).workers[0]

    packet = build_packet(
        worker,
        run_id="economic-routing",
        objective="Implement refresh-token rotation.",
        allowed_paths=["src/auth/**", "tests/auth/**"],
        acceptance=["Replay invalidates descendants."],
        constraints=["Do not read environment files."],
        decisions=["Redis remains the refresh-token state store."],
        invariants=["Existing access-token behavior remains unchanged."],
        non_goals=["Do not redesign the JWT abstraction."],
        risk_class="R3",
    )

    data = packet.to_dict()
    assert data["risk_class"] == "R3"
    assert data["execution_class"] == "workhorse"
    assert data["decisions"] == ["Redis remains the refresh-token state store."]
    assert data["invariants"] == ["Existing access-token behavior remains unchanged."]
    assert data["non_goals"] == ["Do not redesign the JWT abstraction."]
