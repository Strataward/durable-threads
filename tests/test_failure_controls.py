"""Exercise refusal and retry behavior without provider charges."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from durable_threads.config import load_roster
from durable_threads.evidence import (
    EvidenceError,
    WorkerEvidence,
    parse_worker_result,
    validate_evidence,
)
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


@pytest.mark.parametrize("limit", range(4))
def test_retry_limit_survives_reload_and_cannot_increase(tmp_path, limit):
    path = tmp_path / "ledger.json"
    args = dict(task_id="run", role="implementation", provider="codex")
    for index in range(limit + 1):
        ledger = Ledger(path)
        ledger.begin_task(**args, followup_index=index, max_followups=limit)
        ledger.record_task(task_id="run", role="implementation", status="failed")
    before = path.read_bytes()
    with pytest.raises(LedgerStateError, match="cannot change"):
        Ledger(path).begin_task(**args, followup_index=limit + 1, max_followups=limit + 1)
    assert path.read_bytes() == before


def test_legacy_task_has_no_inferred_retry_budget(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_task(task_id="old", role="implementation", status="failed")
    with pytest.raises(LedgerStateError, match="recorded retry limit"):
        ledger.begin_task(task_id="old", role="implementation", provider="codex")


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        "bad",
        {"maxFollowups": 1},
        {"maxFollowups": 1, "followups": True},
        {"maxFollowups": 1, "followups": -1},
    ],
)
def test_corrupt_task_cannot_restart(tmp_path, state):
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.save({"tasks": {"run": state}})
    before = ledger.path.read_bytes()
    with pytest.raises(LedgerStateError):
        ledger.begin_task(task_id="run", role="implementation", provider="codex")
    assert ledger.path.read_bytes() == before


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_retry_limit_rejects_nonintegers(tmp_path, value):
    with pytest.raises(LedgerStateError):
        Ledger(tmp_path / "ledger.json").begin_task(
            task_id="run",
            role="implementation",
            provider="codex",
            max_followups=value,
        )


@pytest.mark.parametrize("field", ["changedPaths", "checks", "remainingConcerns"])
@pytest.mark.parametrize("value", [None, "None", {}, [1], ["ok", False], [""]])
def test_json_result_rejects_invalid_field_types(field, value):
    payload = dict(
        status="complete",
        provider="codex",
        changedPaths=[],
        checks=["pytest: passed"],
        remainingConcerns=["None known"],
    )
    payload[field] = value
    with pytest.raises(EvidenceError):
        parse_worker_result(json.dumps(payload))


def test_explicit_empty_concerns_need_no_model_correction():
    payload = dict(
        status="complete",
        provider="codex",
        changedPaths=[],
        checks=["pytest: passed"],
        remainingConcerns=[],
    )
    evidence = validate_evidence(
        parse_worker_result(json.dumps(payload)), allowed_paths=["src"], actual_paths=[]
    )
    assert evidence.concerns == ("None known",)


@pytest.mark.parametrize("field", ["changedPaths", "checks", "remainingConcerns"])
def test_missing_json_list_is_not_an_empty_list(field):
    payload = dict(
        status="complete",
        provider="codex",
        changedPaths=[],
        checks=["pytest: passed"],
        remainingConcerns=[],
    )
    del payload[field]
    with pytest.raises(EvidenceError):
        parse_worker_result(json.dumps(payload))


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
