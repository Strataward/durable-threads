# Durable mode overhead: self-hosted Temporal + Jev

Date: 2026-09-19
Script: `scripts/bench_durable.py`
Raw data: `docs/benchmarks/data/2026-09-19-*.json`

## Question

Does routing a task through Temporal + Jev make Durable Threads faster?

Short answer: no, and it is not supposed to. Durable mode adds a small, bounded
orchestration cost per task and buys crash recovery, exactly-one writer, and a
deterministic escalation path. This report measures that cost so the trade is
explicit instead of assumed.

## What was measured

The benchmark runs the real `DurableTaskWorkflow` and `AgentExecutionWorkflow`
against a self-hosted Temporal dev server (`temporalio/temporal:latest`,
SQLite, one worker process). The provider is the deterministic `scripted`
executor, so provider variance is zero and every millisecond left is Durable
Threads plus Temporal.

Each Temporal run is paired with a **direct** run of the same policy loop
(`assess_task` -> execute -> verify -> `assess_result`) in-process with no
orchestrator. The difference is the orchestration overhead.

Per-phase timings come from workflow history event timestamps
(`ActivityTaskScheduled` -> `ActivityTaskCompleted`, child workflow
initiated -> completed), so they include Temporal task dispatch and worker
polling, not just Python time.

Hardware: one Linux VM, Python 3.12, `temporalio` 1.x, Temporal and worker on
the same host. Warm-up run excluded.

## Results

### Happy path (worker completes, evidence matches diff)

| Engine | Runs | Status | Temporal wall (median / p95) | Direct (median) | Orchestration overhead (median / p95) |
|---|---|---|---|---|---|
| heuristic | 20 | `complete` | 0.479 s / 0.482 s | 0.004 s | 0.474 s / 0.477 s |
| Jev (`jev-1.13.0`) | 10 | `review_required` | 0.433 s / 0.482 s | 0.264 s | 0.175 s / 0.255 s |

Per-phase (Temporal, history-derived, median):

| Phase | heuristic | Jev |
|---|---|---|
| `assess_task_activity` | 5 ms | 147 ms |
| `route_executors_activity` | 6 ms | 7 ms |
| child `run_execution_activity` | 7 ms | 7 ms |
| child `verify_execution_activity` | 8 ms | 8 ms |
| `assess_result_activity` | 5 ms | 115 ms |
| whole child workflow | 293 ms | 204 ms |
| history events per task | 26 | 26 |

Direct Jev calls: `assess_task` 137 ms median (p95 232 ms), `assess_result`
124 ms median (p95 248 ms), 745 + 677 input tokens, 153 + 98 output tokens per
task.

### Evidence mismatch (worker claims a path it did not change)

| Engine | Runs | Status | Attempts | Temporal wall (median) | Overhead (median) |
|---|---|---|---|---|---|
| heuristic | 10 | `failed` | 2 | 0.877 s | 0.872 s |
| Jev | 5 | `review_required` | 1 | 0.445 s | 0.146 s |

No mismatch run was accepted. The deterministic verifier rejected the claim
before any semantic judgment could accept it.

### Worker crash (SIGKILL mid-execution, replacement worker starts)

| Runs | Killed after | Time to escalation | Final status | Writer re-executed |
|---|---|---|---|---|
| 2 | 2.3 s | 45.2 s / 45.3 s | `review_required` (intervention `human_review`, verification `child_failure`) | no |

The execution Activity has a 45 s heartbeat timeout and `maximum_attempts=1`.
The replacement worker observed `ActivityTaskTimedOut`, the child workflow
failed, and the parent escalated to a human without starting a second writer.
No duplicate file write happened.

## Reading the numbers

1. **Orchestration overhead is 0.15-0.5 s per task**, dominated by Temporal
   task dispatch for one parent workflow plus one child workflow (26 history
   events). Python-side Activity work is under 10 ms per phase. Against a
   coding-agent run that takes minutes, this is noise.
2. **Jev costs about 130 ms per decision** and two decisions per attempt.
   Both calls sit inside Activities, so a Jev outage or slow response is
   retried and recorded by Temporal rather than crashing the planner.
3. **Jev did not auto-accept the trivial happy-path task.** Jev answered
   `intervention=accept` (0.73) and `semantic_complete` (0.83), but
   `evidence_sufficient` was 0.72, below the R1 auto threshold (0.85). The
   deterministic gate therefore returned `review_required`. This is the
   documented invariant working: confidence is evidence, not authorization.
   The scripted evidence (one check line, no test output) is thin, and Jev
   said so. Real runs with richer `checks` evidence should clear the gate;
   that has not been measured yet.
4. **The heuristic engine is the offline control**, not a recommendation. It
   is deterministic and free, which is what a benchmark baseline needs. It
   over-accepts compared with Jev because it cannot judge evidence quality.
5. **Crash recovery is bounded by the heartbeat timeout**, not by human
   attention. 45 s is the current constant in `temporal_workflows.py`; lower
   it if provider heartbeats are frequent.

## What this does not show

- No comparison against a real coding agent (Codex, Claude Code, Cursor, Grok).
  None was installed in the benchmark environment. Provider execution time
  will dominate everything above by two to three orders of magnitude.
- No cost or quality delta versus native mode. The 2026-09-05 reports remain
  the only task-quality observations, and they are not controlled.
- Temporal dev server with SQLite on one host. Temporal Cloud or a
  Postgres-backed cluster will add network latency per event.
- Sample sizes are small (5-20 runs). p95 values are indicative, not
  statistically tight.

## Reproduce

```bash
docker compose -f ops/temporal/docker-compose.yml up -d
python3 -m pip install -e '.[durable,dev]'

python3 scripts/bench_durable.py --runs 20 --engine heuristic --scenario happy \
  --out docs/benchmarks/data/heuristic-happy.json
python3 scripts/bench_durable.py --runs 10 --engine heuristic --scenario mismatch
python3 scripts/bench_durable.py --runs 2  --engine heuristic --scenario crash

export TYPESAFE_API_KEY='...'
python3 scripts/bench_durable.py --runs 10 --engine jev --scenario happy
```

The script sets `DURABLE_THREADS_ENABLE_SCRIPTED=1` and
`DURABLE_THREADS_DECISION_ENGINE` for the worker it spawns. It creates one
throwaway git repository per run and deletes them afterwards.
