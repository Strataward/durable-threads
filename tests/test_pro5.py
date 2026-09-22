from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from durable_threads.intelligence import completion_gate

SCRIPT = (
    Path(__file__).parents[1]
    / "plugins/durable-threads/skills/durable-threads/scripts/pro5.py"
)
spec = importlib.util.spec_from_file_location("dt_pro5", SCRIPT)
assert spec is not None and spec.loader is not None
pro5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pro5)


def test_config_audit_is_redacted_and_does_not_mutate() -> None:
    config = {
        "model": "gpt-6-astra",
        "model_reasoning_effort": "max",
        "service_tier": "fast",
        "model_context_window": 400000,
        "mcp_servers": {"private-name": {"env": {"TOKEN": "super-secret"}}},
        "agents": {"max_concurrent_threads_per_session": 8},
    }
    before = json.dumps(config)
    result = pro5.audit_config(config)
    assert json.dumps(config) == before
    assert {x["code"] for x in result["findings"]} >= {
        "EXPENSIVE_BASELINE", "FAST_TIER", "MANUAL_CONTEXT", "FANOUT", "MCP_CONTEXT"
    }
    assert "super-secret" not in json.dumps(result)
    assert "private-name" not in json.dumps(result)
    assert result["writesPerformed"] is False
    assert result["subscriptionMultiplierVerified"] is False


def test_profile_overrides_only_selected_file_layer(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(pro5.PROFILE)
    parsed = pro5.read_toml(path)
    result = pro5.audit_config(parsed, "dt-pro5")
    assert result["model"] == "gpt-6-astra"
    assert result["effort"] == "medium"
    assert result["serviceTier"] == "default"
    assert result["scope"] == "one-config-file-not-effective-runtime"
    example = Path(__file__).parents[1] / "examples/codex-pro5.toml"
    assert example.read_text() == pro5.PROFILE


@pytest.mark.parametrize("config", [[], {"profile": []}, {"agents": []},
                                     {"profile": "a", "profiles": []}])
def test_bad_config_shape_fails(config) -> None:
    with pytest.raises(ValueError):
        pro5.audit_config(config)


def test_invalid_setting_does_not_disclose_nested_values() -> None:
    result = pro5.audit_config({"model_reasoning_effort": ["sensitive"],
                               "service_tier": {"sensitive": "value"}})
    assert "sensitive" not in json.dumps(result)


def quota(used=50, reset=2000):
    return {"rateLimits": {"limitId": "codex", "primary": {
        "usedPercent": used, "resetsAt": reset, "windowDurationMins": 300,
    }}}


def test_quota_checks_both_windows_and_bucket_scope() -> None:
    payload = quota(used=1)
    payload["rateLimits"]["secondary"] = {
        "usedPercent": 90, "resetsAt": 5000, "windowDurationMins": 10080,
    }
    result = pro5.quota_summary(payload, now=1000)
    assert result["status"] == "pause"
    assert result["remainingPercent"] == 10
    assert pro5.quota_summary(quota(reset=1000), now=1000)["status"] == "refresh_required"
    payload["rateLimits"]["limitId"] = "unrelated"
    assert pro5.quota_summary(payload, now=1000)["status"] == "unknown"


@pytest.mark.parametrize("value", [True, -1, 101, float("nan"), float("inf"), "100"])
def test_invalid_quota_is_never_treated_as_available(value) -> None:
    result = pro5.quota_summary(quota(used=value), now=1000)
    assert result["status"] in {"unknown", "refresh_required"}


def test_bounded_mock_app_server_probe_never_starts_generation(tmp_path) -> None:
    # An actual subprocess wire test, with fake metadata instead of paid model calls.
    mock = tmp_path / "fake_codex.py"
    mock.write_text('''import json, sys, time
allowed = {"initialize", "initialized", "account/read", "model/list", "account/rateLimits/read"}
for line in sys.stdin:
    item = json.loads(line)
    method = item.get("method")
    if method not in allowed:
        raise SystemExit("forbidden operation")
    if "id" not in item:
        continue
    if method == "initialize":
        assert item["params"]["capabilities"]["experimentalApi"] is False
        result = {}
    elif method == "account/read":
        assert item["params"]["refreshToken"] is False
        result = {"account": {"type": "chatgpt", "email": "private@example.com", "id": "secret"}}
    elif method == "model/list":
        result = {"data": [{"model": "gpt-6-astra", "supportedReasoningEfforts": [
            {"reasoningEffort": "medium"}, {"reasoningEffort": "high"}]}], "nextCursor": None}
    else:
        result = {"rateLimits": {"limitId": "codex", "primary": {
            "usedPercent": 20, "resetsAt": time.time()+3600, "windowDurationMins": 300}}}
    print(json.dumps({"id": item["id"], "result": result}), flush=True)
''')
    result = asyncio.run(pro5.probe_metadata([sys.executable, str(mock)]))
    assert result["modelGenerationsRequested"] == 0
    assert result["stepSwitchingVerified"] is False
    assert result["chatgptSignIn"] is True
    assert "private@example.com" not in json.dumps(result)
    assert "secret" not in json.dumps(result)
    assert set(result["requestedMethods"]) == {
        "initialize", "account/read", "model/list", "account/rateLimits/read"
    }


def test_probe_times_out_without_retry(tmp_path) -> None:
    mock = tmp_path / "stalled_codex.py"
    mock.write_text("import time\ntime.sleep(30)\n")
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(pro5.probe_metadata([sys.executable, str(mock)], timeout=0.05))


@pytest.mark.parametrize("approved", [False, True])
def test_human_approval_cannot_invent_evidence(approved: bool) -> None:
    assert completion_gate(integration_ready=False, task_review_required=True,
                           result_review_required=True, review_approved=approved) == "unverified"


def test_explicit_task_review_cannot_be_dropped() -> None:
    assert completion_gate(integration_ready=True, task_review_required=True,
                           result_review_required=False) == "review_required"
    assert completion_gate(integration_ready=True, task_review_required=True,
                           result_review_required=False, review_approved=True) == "complete"
