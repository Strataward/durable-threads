from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from durable_threads.cli import main
from durable_threads.config import ConfigError, load_roster
from durable_threads.evidence import EvidenceError, parse_worker_result, validate_evidence
from durable_threads.ledger import Ledger, LedgerBusyError, LedgerStateError
from durable_threads.packets import PacketError, build_packet
from durable_threads.providers import (
    ProviderError,
    build_invocation,
    extract_session_id,
    extract_usage,
    run_invocation,
)
from durable_threads.routing import (
    ModelInfo,
    catalog_from_payload,
    resolve_model,
    select_workers,
)

ROOT = Path(__file__).parents[1]
ROSTER = ROOT / "examples" / "roster.json"
MULTI_ROSTER = ROOT / "examples" / "multi-provider-roster.json"


def test_example_roster_loads_with_unique_workers() -> None:
    roster = load_roster(ROSTER)

    assert roster.project_name == "example-project"
    assert [worker.name for worker in roster.workers] == [
        "implementation",
        "test-debug",
        "research-docs",
        "security-review",
    ]
    assert len({worker.thread_title for worker in roster.workers}) == 4


def test_multi_provider_roster_loads_with_provider_sessions() -> None:
    roster = load_roster(MULTI_ROSTER)

    assert roster.planner.provider == "codex"
    assert [worker.provider for worker in roster.workers] == [
        "claude",
        "grok",
        "cursor",
        "codex",
    ]


def test_roster_rejects_duplicate_worker_names(tmp_path: Path) -> None:
    data = json.loads(ROSTER.read_text(encoding="utf-8"))
    data["workers"][1]["name"] = data["workers"][0]["name"]
    path = tmp_path / "roster.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ConfigError, match="worker names must be unique"):
        load_roster(path)


def test_roster_rejects_selected_worker_limit_above_worker_count(tmp_path: Path) -> None:
    data = json.loads(ROSTER.read_text(encoding="utf-8"))
    data["policy"]["maxSelectedWorkers"] = 99
    path = tmp_path / "roster.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ConfigError, match="cannot exceed the worker count"):
        load_roster(path)


def test_auto_routing_selects_one_worker_for_a_bounded_change() -> None:
    roster = load_roster(ROSTER)

    decision = select_workers(
        roster,
        objective="Fix one bounded behaviour.",
        allowed_paths=["src/example.py"],
        acceptance=["The focused test passes."],
    )

    assert [worker.name for worker in decision.selected] == ["implementation"]
    assert not decision.explicit
    assert "test-debug" in [worker.name for worker in decision.skipped]


def test_auto_routing_caps_independent_specialists() -> None:
    roster = load_roster(ROSTER)

    decision = select_workers(
        roster,
        objective="Fix a security regression and add regression tests.",
        allowed_paths=["src/example.py"],
        acceptance=["The security review and tests pass."],
    )

    assert [worker.name for worker in decision.selected] == ["implementation", "security-review"]
    assert any("maxSelectedWorkers" in reason for reason in decision.reasons)


def test_explicit_routing_rejects_more_workers_than_policy() -> None:
    roster = load_roster(ROSTER)

    with pytest.raises(ValueError, match="maxSelectedWorkers"):
        select_workers(
            roster,
            objective="Review the repository.",
            requested_workers=["implementation", "test-debug", "research-docs"],
        )


def test_role_resolution_uses_live_metadata_without_guessing() -> None:
    catalog = catalog_from_payload(
        {
            "models": [
                {"id": "astra-live", "displayName": "GPT-6 Astra", "tier": "frontier"},
                {"id": "terra-live", "displayName": "Balanced", "tier": "balanced"},
                {"id": "luna-live", "displayName": "Efficient", "tier": "efficient"},
            ]
        }
    )

    frontier = resolve_model(catalog, "frontier")
    named = resolve_model(catalog, "Astra")
    exact = resolve_model(catalog, "astra-live")
    missing = resolve_model(catalog, "a-model-that-is-not-in-the-catalog")

    assert frontier.model is not None and frontier.model.model_id == "astra-live"
    assert named.model is not None and named.model.model_id == "astra-live"
    assert exact.model is not None and exact.model.display_name == "GPT-6 Astra"
    assert missing.model is None
    assert not missing.matched


def test_role_resolution_falls_back_to_default_when_tier_is_missing() -> None:
    catalog = (ModelInfo("default-live", "Runtime default", "unknown", is_default=True),)

    resolution = resolve_model(catalog, "frontier")

    assert resolution.model is not None
    assert resolution.model.model_id == "default-live"
    assert not resolution.matched


def test_packet_is_compact_and_contains_result_contract() -> None:
    worker = load_roster(ROSTER).workers[0]

    packet = build_packet(
        worker,
        run_id="demo-run",
        objective="Fix one bounded behaviour.",
        allowed_paths=["src/example.py"],
        acceptance=["The focused test passes."],
        constraints=["Do not read environment files."],
    )

    data = packet.to_dict()
    assert data["schema_version"] == 2
    assert data["provider"] == "codex"
    assert data["allowed_paths"] == ["src/example.py"]
    assert "Return exact checks and results." in data["result_contract"]


def test_packet_rejects_credential_like_text() -> None:
    worker = load_roster(ROSTER).workers[0]

    with pytest.raises(PacketError, match="credential-like"):
        build_packet(
            worker,
            run_id="demo-run",
            objective="Inspect sk-12345678901234567890",
            allowed_paths=["src/example.py"],
            acceptance=["The focused test passes."],
            constraints=[],
        )


def test_ledger_redacts_and_writes_private_file(tmp_path: Path) -> None:
    path = tmp_path / ".loom" / "ledger.json"
    ledger = Ledger(path)

    ledger.record_task(
        task_id="task-1",
        role="implementation",
        status="complete",
        provider="claude",
        thread_id="thread-1",
        result="Done. token ghp_12345678901234567890 must not persist.",
        usage={"input": 10, "output": 2},
    )

    data = ledger.read()
    assert "ghp_" not in json.dumps(data)
    assert data["tasks"]["task-1"]["status"] == "complete"
    assert data["tasks"]["task-1"]["provider"] == "claude"
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_cli_plan_writes_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "plan",
            "--roster",
            str(ROSTER),
            "--objective",
            "Fix one bounded behaviour.",
            "--allowed-path",
            "src/example.py",
            "--acceptance",
            "The focused test passes.",
            "--run-id",
            "demo-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["runId"] == "demo-run"
    assert len(payload["workers"]) == 1
    assert payload["route"]["selectedWorkers"] == ["implementation"]


def test_claude_invocation_maps_roles_and_resumes() -> None:
    invocation = build_invocation(
        provider="claude",
        prompt="Do the bounded work.",
        model_selector="frontier",
        reasoning_effort="high",
        session_id="claude-session",
    )

    assert Path(invocation.argv[0]).name == "claude"
    assert "--model" in invocation.argv and "opus" in invocation.argv
    assert "--effort" in invocation.argv and "high" in invocation.argv
    assert "--resume" in invocation.argv and "claude-session" in invocation.argv


def test_grok_invocation_uses_default_without_guessing_a_model() -> None:
    invocation = build_invocation(
        provider="grok",
        prompt="Research the bounded question.",
        model_selector="default",
        reasoning_effort="medium",
        session_id="grok-session",
    )

    assert Path(invocation.argv[0]).name == "grok"
    assert "--no-auto-update" in invocation.argv
    assert "--output-format" in invocation.argv and "json" in invocation.argv
    assert "-m" not in invocation.argv
    assert "--effort" in invocation.argv and "medium" in invocation.argv
    assert "--resume" in invocation.argv and "grok-session" in invocation.argv


def test_cursor_invocation_accepts_compatibility_binary() -> None:
    invocation = build_invocation(
        provider="cursor",
        prompt="Review the bounded diff.",
        model_selector="composer-2.5",
        reasoning_effort="low",
        executable="cursor-agent",
    )

    assert invocation.argv[0] == "cursor-agent"
    assert "--model" in invocation.argv and "composer-2.5" in invocation.argv
    assert "--resume" not in invocation.argv
    assert invocation.execution_mode == "cli"


def test_provider_rejects_unsafe_generic_model_guesses() -> None:
    with pytest.raises(ProviderError, match="does not map generic role selectors"):
        build_invocation(
            provider="grok",
            prompt="Research.",
            model_selector="frontier",
            reasoning_effort="low",
        )

    with pytest.raises(ProviderError, match="does not map generic role selectors"):
        build_invocation(
            provider="cursor",
            prompt="Review.",
            model_selector="balanced",
            reasoning_effort="low",
        )


def test_session_id_extraction_handles_json_and_streaming_json() -> None:
    assert extract_session_id('{"session_id":"claude-123"}') == "claude-123"
    assert extract_session_id('{"type":"event"}\n{"sessionId":"grok-456"}') == "grok-456"
    assert extract_session_id("plain output") is None


def test_usage_extraction_handles_provider_metadata() -> None:
    output = '{"usage":{"input_tokens":12,"output_tokens":7,"total_tokens":19}}'

    assert extract_usage(output) == {
        "inputTokens": 12,
        "outputTokens": 7,
        "totalTokens": 19,
    }


def test_worker_evidence_requires_checks_and_matches_the_diff() -> None:
    result = parse_worker_result(
        "Status: complete\n"
        "Provider: claude\n"
        "Changed paths:\n"
        "- src/example.py\n"
        "Checks:\n"
        "- `pytest tests/test_core.py`: passed\n"
        "Remaining concerns:\n"
        "- None known\n"
    )

    verified = validate_evidence(
        result,
        allowed_paths=["src/**"],
        actual_paths=["src/example.py"],
    )

    assert verified.changed_paths == ("src/example.py",)


@pytest.mark.parametrize(
    "path",
    ["../secret.txt", str(Path.cwd() / "secret.txt"), "docs/../secret.txt"],
)
def test_worker_evidence_rejects_unsafe_paths(path: str) -> None:
    result = parse_worker_result(
        json.dumps(
            {
                "status": "complete",
                "provider": "claude",
                "changedPaths": [path],
                "checks": ["focused check passed"],
                "remainingConcerns": ["None known"],
            }
        )
    )

    with pytest.raises(EvidenceError, match="unsafe|outside"):
        validate_evidence(result, allowed_paths=["src/**"], actual_paths=[path])


def test_worker_evidence_rejects_unreported_diff() -> None:
    result = parse_worker_result(
        json.dumps(
            {
                "status": "complete",
                "provider": "claude",
                "changedPaths": ["src/example.py"],
                "checks": ["focused check passed"],
                "remainingConcerns": ["None known"],
            }
        )
    )

    with pytest.raises(EvidenceError, match="do not match"):
        validate_evidence(
            result,
            allowed_paths=["src/**"],
            actual_paths=["src/example.py", "src/other.py"],
        )


def test_ledger_blocks_duplicate_local_writers(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.begin_task(task_id="task-1", role="implementation", provider="claude")

    with pytest.raises(LedgerBusyError, match="active writer"):
        ledger.begin_task(task_id="task-1", role="implementation", provider="claude")


def test_ledger_enforces_followup_order(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_task(task_id="task-1", role="implementation", status="complete")

    with pytest.raises(LedgerStateError, match="expects follow-up index 0"):
        ledger.begin_task(
            task_id="task-1",
            role="implementation",
            provider="claude",
            followup_index=1,
            max_followups=1,
        )


def test_dispatch_uses_an_argument_array_and_returns_session_id(tmp_path: Path) -> None:
    executable = tmp_path / "fake-grok"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'session_id': 'fake-session', 'status': 'complete'}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    invocation = build_invocation(
        provider="grok",
        prompt="Do not use a shell.",
        model_selector="default",
        reasoning_effort="low",
        executable=str(executable),
    )
    result = run_invocation(invocation, cwd=tmp_path)

    assert result.return_code == 0
    assert result.session_id == "fake-session"
    assert "complete" in result.stdout


def test_cli_dispatch_records_bounded_usage_and_session_state(tmp_path: Path, capsys) -> None:
    executable = tmp_path / "fake-grok"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'session_id': 'fake-session', 'status': 'complete', "
        "'usage': {'input_tokens': 11, 'output_tokens': 5}}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    ledger_path = tmp_path / "ledger.json"

    exit_code = main(
        [
            "dispatch",
            "--provider",
            "grok",
            "--prompt",
            "Run the bounded task.",
            "--model",
            "default",
            "--binary",
            str(executable),
            "--cwd",
            str(tmp_path),
            "--ledger",
            str(ledger_path),
            "--task-id",
            "task-1",
            "--role",
            "implementation",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["sessionId"] == "fake-session"
    assert payload["usage"] == {"inputTokens": 11, "outputTokens": 5}
    task = Ledger(ledger_path).read()["tasks"]["task-1"]
    assert task["status"] == "unverified"
    assert task["threadId"] == "fake-session"
    assert task["usage"] == {"inputTokens": 11, "outputTokens": 5}
