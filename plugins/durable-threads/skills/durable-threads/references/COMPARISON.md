# Approach comparison record

## Scope

This record compares the upstream `backnotprop/orchestrator` trial with the
skill-first design in this repository. It is a practical decision record. It
is not a benchmark or a claim about every project.

## Trial result

The upstream tool completed one bounded StoriBuk task in a persistent Codex
session. The worker changed only the two allowed files. The focused tests,
typecheck, lint, and diff checks passed.

The follow-up turn then hit the account usage limit. A later resume attempt saw
an active provider writer. The local task record did not recover the provider
state automatically.

## Decision

The final same-model trial kept context in both arms. Direct continuation
passed the same checks with fewer input tokens and no corrections. It is the
default for related work when the current model and context are suitable.
See the repository report at `docs/benchmarks/2026-09-05-retained-baseline.md`.

Use direct execution for small tasks. Keep the skill as an experimental option
for related work that can reuse context. Leave task creation, sending, waiting,
and recovery in the native Codex app actions where available. A CLI-session
comparison does not validate those app actions or the upstream runtime.

Keep the helper library deterministic. It validates rosters, builds compact
packets, resolves role selectors against a live catalog, and writes redacted
evidence. It does not execute model output.

Add a richer runtime adapter only after a second live comparison proves that it
reduces total rework and handles usage-limit recovery correctly.

The public claim is intentionally narrow. This repository is a packet and
evidence control layer. It is not a workflow engine. It does not own automatic
provider restart or provider-side writer recovery.

## Remaining evidence gap

The comparison below remains untested. It is not scheduled work. The final
local decision does not require another run.

Use the same small, reversible repository task for two runs:

1. Native skill-first routing with existing named threads.
2. A runtime adapter that starts and resumes persistent app-server sessions.

Hold the objective, allowed paths, acceptance checks, and reviewer policy
constant. Measure correctness, test evidence, follow-up reliability, observed
usage, number of workers, and recovery after quota or writer failure.

Record these values for each run:

- input and output tokens from every provider that reports them;
- number of selected workers and provider calls;
- follow-up count and correction count;
- changed paths outside the allow-list;
- failed checks and final correctness;
- time to recover from quota and active-writer states.

The result is not a benchmark until both runs use the same task, baseline
commit, acceptance checks, and reviewer standard. A lower token count without
equal correctness is not a win.
