# Durable mode: Temporal + Jev

This document is the **Python** durable-mode path. Plugin users can ignore it. For the TypeScript self-host control plane, see [Self-host the TypeScript control plane](SAAS.md).

Durable Threads has two execution modes:

- **native/local mode** keeps the current zero-infrastructure Codex/plugin workflow;
- **durable mode** uses Temporal for crash-resilient orchestration and TypeSafe Jev for fast typed decisions.

The boundary is deliberate:

```text
Jev / DecisionEngine
  probabilistic judgment
          |
          v
Durable Threads policy
  deterministic authority
          |
          v
Temporal
  state, retries, timers, signals, child workflows
          |
          v
ExecutionRegistry
  provider-neutral capability routing
          |
          +--> Claude Code
          +--> Grok Build
          +--> Cursor Agent
          +--> third-party executor plugins
```

**Jev informs policy. Code authorizes side effects. Temporal remembers and coordinates. Providers execute. Deterministic checks verify.**

## Why both Temporal and Jev are deep primitives

Temporal is not just a retry wrapper. In durable mode the workflow itself is the persistent unit of work. Workflow history records task assessment, routing, child execution, evidence verification, semantic result assessment, escalation, and optional human approval.

Provider execution is intentionally configured with one Temporal Activity attempt because an automatic retry could duplicate a writer or external side effect. Recovery and escalation are explicit in the parent policy loop.

Jev is not used as a text generator. Durable Threads batches closed decisions against compact shared state:

- R0-R4 consequence class;
- whether delegation is useful;
- ambiguity;
- execution shape (`single_worker`, `worker_plus_review`, `parallel_workers`);
- independent-review need;
- semantic completeness of a worker result;
- evidence sufficiency;
- next intervention (`accept`, `correct_same`, `switch_executor`, `stronger_model`, `human_review`).

The deterministic risk classifier is a **floor**. A semantic decision may raise risk but cannot lower a deterministic R3/R4 signal. R3/R4 results are never auto-integrated solely because Jev is confident.

## Provider agnosticism

`durable_threads.execution.ExecutionRegistry` routes against capabilities rather than a closed provider enum. A task asks for capabilities such as `code`, `filesystem`, and `git`; the registry selects an available executor that satisfies them.

External runtimes can register the Python entry-point group:

```text
durable_threads.executors
```

Each entry point returns an `ExecutorPlugin` containing an `ExecutorDescriptor`, optional backend factory, and optional availability probe. Adding a provider therefore does not require editing Durable Threads routing policy.

The existing Codex/Claude/Grok/Cursor integrations remain built in. Codex is intentionally native-only in the current helper; Temporal durable mode selects headless backends unless a headless Codex/managed backend plugin is installed.

## Installation

This helper is not published to PyPI. Clone the repository and install from the checkout.

```bash
git clone https://github.com/Strataward/durable-threads.git
cd durable-threads
python3 -m pip install -e '.[dev]'
```

Jev only:

```bash
python3 -m pip install -e '.[jev]'
```

Temporal only:

```bash
python3 -m pip install -e '.[temporal]'
```

Durable mode:

```bash
python3 -m pip install -e '.[durable]'
```

Configure TypeSafe and Temporal:

```bash
export TYPESAFE_API_KEY='...'
export TEMPORAL_ADDRESS='localhost:7233'
export TEMPORAL_NAMESPACE='default'
export DURABLE_THREADS_TASK_QUEUE='durable-threads'
```

Optional Jev configuration:

```bash
export DURABLE_THREADS_JEV_MODEL='jev-latest'
export DURABLE_THREADS_JEV_TIMEOUT_SECONDS='30'
```

### Run without a TypeSafe key

Set `DURABLE_THREADS_DECISION_ENGINE=heuristic` to run without a TypeSafe key. Set it to `jev` to require Jev. The default is `jev` when `TYPESAFE_API_KEY` is set and `heuristic` otherwise.

The heuristic engine is deterministic and offline. Use it for tests and benchmarks. It does not judge evidence quality.

### Self-hosted Temporal

Use the self-hosted dev stack in [ops/temporal/docker-compose.yml](../ops/temporal/docker-compose.yml). The short setup guide is in [ops/temporal/README.md](../ops/temporal/README.md).

```bash
docker compose -f ops/temporal/docker-compose.yml up -d
```

Open the UI at <http://localhost:8233>.

## Run the worker

Start Temporal locally or point at Temporal Cloud, then:

```bash
durable-threads-temporal-worker
```

Use `--max-sync-activities` or `DURABLE_THREADS_MAX_SYNC_ACTIVITIES` to size the thread pool for routing and verification Activities. The default is 8.

The worker registers:

- `DurableTaskWorkflow` -- policy loop and human-review gate;
- `AgentExecutionWorkflow` -- one bounded executor attempt;
- Jev task/result decision Activities;
- executor routing;
- provider execution with heartbeats;
- git/evidence verification.

### Test executor

Set `DURABLE_THREADS_ENABLE_SCRIPTED=1` to enable the `scripted` provider. It replays `<cwd>/.durable-threads/scripted.json`.

```json
{
  "writes": {"relative/path": "file content"},
  "result": {
    "status": "complete",
    "changedPaths": ["relative/path"],
    "checks": ["python -m pytest -q: passed"],
    "remainingConcerns": []
  },
  "returnCode": 0,
  "delaySeconds": 0.0,
  "stderr": "",
  "extraStdout": ""
}
```

Use this executor for tests and benchmarks only. Never use it for real work.

## Start a durable task

```bash
durable-threads-temporal start \
  --objective 'Implement refresh-token rotation' \
  --allowed-path 'src/auth/**' \
  --allowed-path 'tests/auth/**' \
  --acceptance 'Refresh succeeds exactly once' \
  --acceptance 'Replay is rejected' \
  --cwd /path/to/repository \
  --wait-for-human-review \
  --detach
```

Query the workflow:

```bash
durable-threads-temporal status --workflow-id <id>
```

Approve a workflow waiting at a deterministic human gate:

```bash
durable-threads-temporal review --workflow-id <id> --approve --note 'Security review passed'
```

Or reject it:

```bash
durable-threads-temporal review --workflow-id <id> --reject --note 'Tenant-isolation concern remains'
```

## Measured overhead

Local dev-server runs measured 0.15–0.5 seconds of orchestration overhead per task and about 130 ms per Jev decision, with two decisions per attempt. A crash escalated in about 45 seconds without creating a duplicate writer. Jev held a thin-evidence task at `review_required` because `evidence_sufficient` was 0.72, below the R1 threshold of 0.85.

An R4 task parked at the human-review gate survived a worker SIGKILL. The approval signal was delivered while no worker was running, and a replacement worker resumed from history. Resume cost about 10 seconds, all of it Temporal's sticky-queue schedule-to-start timeout.

The deterministic policy layer (risk, routing, evidence, gating) costs under one millisecond per task. A Rust or WebAssembly port would not change end-to-end latency; see [ADR 0001](adr/0001-rust-wasm.md).

See the [durable-mode overhead report](benchmarks/2026-09-19-durable-mode-overhead.md) and the benchmark runners [`scripts/bench_durable.py`](../scripts/bench_durable.py) and [`scripts/bench_primitives.py`](../scripts/bench_primitives.py).

## Parallelism and speculative execution

Jev may select `parallel_workers` when uncertainty makes hedging worthwhile, and the Temporal workflow is capable of running multiple child workflows concurrently.

Durable Threads does **not** currently race multiple write-capable workers against the same checkout. The built-in coding contract requires `filesystem`/`git`, so shared-checkout mutation is serialized. This preserves the existing invariant:

> Subagents for parallel cognition. Isolated workspaces for parallel mutation.

Parallel execution is available for non-mutating/remote executor contracts. Write-capable speculation should only be enabled once an executor plugin provides real workspace isolation (for example, worktrees or remote sandboxes) and a safe integration strategy.

## Safety invariants

1. **No provider/Jev/network/filesystem calls in Workflow code.** They are Activities so Temporal replay stays deterministic.
2. **Provider mutation Activities do not blindly retry.** Duplicate writers are worse than a visible failed attempt.
3. **Risk can only move upward across deterministic + semantic classification.**
4. **R3/R4 requires independent review; R4 defaults to a human gate before execution.**
5. **Jev confidence is evidence, not authorization.** Thresholds are deterministic policy.
6. **Executor selection is capability-based.** Vendor names are preferences, not the core contract.
7. **Worker output is checked against the actual git diff.** A model claiming tests passed is not equivalent to evidence.
8. **Parallel mutation requires isolation.** Shared-checkout writers are serialized.

## Current limitations

- Built-in durable execution currently uses the headless CLI adapters. Managed OpenAI/Codex, Gemini, sandbox, or remote-runner integrations should be implemented as `ExecutorPlugin`s rather than special-cased in the workflow. No real coding-agent comparison has been benchmarked yet.
- Independent automated R3/R4 review is represented as a required gate; the first durable implementation does not run a write-capable coding CLI as a pretend read-only reviewer.
- Long histories should add a deliberate Continue-As-New boundary once workload telemetry establishes a sensible event threshold.
- Provider cost/latency learning is not yet used in ranking. Workflow records already retain decision, provider, usage, evidence, and outcome data needed for that optimizer.
