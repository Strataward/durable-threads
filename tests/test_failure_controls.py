"""Exercise refusal and retry behavior without provider charges."""

from dataclasses import replace
from pathlib import Path

import pytest

from durable_threads.config import load_roster
from durable_threads.evidence import EvidenceError, WorkerEvidence, validate_evidence
from durable_threads.ledger import Ledger, LedgerBusyError, LedgerStateError
from durable_threads.routing import select_workers


def test_followup_cannot_repeat_or_exceed_limit(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    args = dict(task_id="run", role="implementation", provider="claude", thread_id="session")
    ledger.begin_task(**args)
    ledger.record_task(task_id="run", role="implementation", status="failed")
    with pytest.raises(LedgerStateError):
        ledger.begin_task(**args)
    ledger.begin_task(**args, followup_index=1)
    ledger.record_task(task_id="run", role="implementation", status="failed")
    with pytest.raises(LedgerStateError):
        ledger.begin_task(**args, followup_index=2)


@pytest.mark.parametrize("status", ["blocked", "unknown", "unverified", "complete"])
def test_stopped_task_cannot_retry(tmp_path, status):
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.begin_task(task_id="run", role="implementation", provider="claude")
    ledger.record_task(task_id="run", role="implementation", status=status)
    with pytest.raises(LedgerStateError):
        ledger.begin_task(task_id="run", role="implementation", provider="claude", followup_index=1)


@pytest.mark.parametrize("provider,session", [("grok", "one"), ("claude", "two")])
def test_identity_drift_stops_resume(tmp_path, provider, session):
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.begin_task(task_id="run", role="implementation", provider="claude", thread_id="one")
    ledger.record_task(task_id="run", role="implementation", status="failed")
    with pytest.raises(LedgerStateError):
        ledger.begin_task(
            task_id="run",
            role="implementation",
            provider=provider,
            thread_id=session,
            followup_index=1,
        )


def test_existing_transaction_lock_stops_writer(tmp_path):
    path = tmp_path / "ledger.json"
    path.with_suffix(".json.lock").touch()
    with pytest.raises(LedgerBusyError):
        Ledger(path).begin_task(task_id="run", role="implementation", provider="claude")


def test_failed_check_cannot_support_complete():
    evidence = WorkerEvidence("complete", "claude", (), ("pytest: failed",), ("None known",))
    with pytest.raises(EvidenceError):
        validate_evidence(evidence, allowed_paths=["src"], actual_paths=[])


def test_local_route_and_explicit_parallel_cap():
    roster = load_roster(Path(__file__).parents[1] / "examples/roster.json")
    assert not select_workers(roster, objective="Fix typo", local_only=True).selected
    with pytest.raises(ValueError):
        select_workers(
            replace(roster, max_parallel_workers=1),
            objective="Review",
            requested_workers=["test-debug", "research-docs"],
        )
