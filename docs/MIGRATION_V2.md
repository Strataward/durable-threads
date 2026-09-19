# Migrating to the model-economic v2 strategy

Version 0.3 introduces a model-economic operating strategy while preserving schema-v1 roster loading.

The pre-v2 repository state is preserved on the GitHub branch [archive/pre-model-economics-2026-09-12](https://github.com/Strataward/durable-threads/tree/archive/pre-model-economics-2026-09-12).

## What changed

V2 adds execution classes (`decision`, `workhorse`, `review`, `specialist`), an economic strategy block, R0–R4 risk-aware review, and richer implementation contracts containing frozen decisions, invariants, and non-goals.

The recommended economy profile changes the OpenAI-oriented default from frontier-heavy execution to efficient/high-reasoning implementation with frontier escalation.

## V1 compatibility

Existing schema-v1 rosters continue to load. Missing v2 fields receive safe defaults: economy profile, default risk R1, frontier review at R3, sleeping orchestrator true, escalation efficient/xhigh → balanced/medium → frontier/low → frontier/medium, planner class decision, reviewer class review, and worker class workhorse.

No provider session ID format changes.

## Recommended roster change

Move planner frontier effort from `high` to `low`, first-line reviewer from frontier/medium to efficient/xhigh, and implementation from efficient/low to efficient/xhigh. Add the strategy block from `examples/roster.json`.

For implementation, prefer `efficient/xhigh` unless matched benchmarks for your workload show another setting is better.

## Planner behavior change

The biggest behavioral change is not a JSON field: the planner should sleep during healthy worker execution. Do not keep an expensive parent in short `wait_agent` polling loops. Wake it only when completion or material evidence requires another decision.

## Review behavior change

V1 used a frontier reviewer more broadly. V2 defaults first-line review to efficient/xhigh and invokes frontier review at the configured risk threshold or when failure evidence requires it. R3/R4 still call for frontier/specialist review.

## Packet migration

Add `DECISIONS ALREADY MADE`, `INVARIANTS`, `NON-GOALS`, and `RISK CLASS` where possible. The Python packet builder accepts these fields programmatically while retaining existing callers.

## Validation

```bash
python3 -m pip install -e '.[dev]'
durable-threads validate-roster examples/roster.json
pytest
ruff check .
```

Run a matched benchmark before claiming the new strategy saves allowance for your workload.