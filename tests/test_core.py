from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from codex_thread_loom.cli import main
from codex_thread_loom.config import ConfigError, load_roster
from codex_thread_loom.ledger import Ledger
from codex_thread_loom.packets import PacketError, build_packet
from codex_thread_loom.routing import ModelInfo, catalog_from_payload, resolve_model

ROOT = Path(__file__).parents[1]
ROSTER = ROOT / "examples" / "roster.json"


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


def test_roster_rejects_duplicate_worker_names(tmp_path: Path) -> None:
    data = json.loads(ROSTER.read_text(encoding="utf-8"))
    data["workers"][1]["name"] = data["workers"][0]["name"]
    path = tmp_path / "roster.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ConfigError, match="worker names must be unique"):
        load_roster(path)


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
    assert data["schema_version"] == 1
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
        thread_id="thread-1",
        result="Done. token ghp_12345678901234567890 must not persist.",
        usage={"input": 10, "output": 2},
    )

    data = ledger.read()
    assert "ghp_" not in json.dumps(data)
    assert data["tasks"]["task-1"]["status"] == "complete"
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
    assert len(payload["workers"]) == 4
