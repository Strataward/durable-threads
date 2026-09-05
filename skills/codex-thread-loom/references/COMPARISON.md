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

Use the skill-first control plane as the default. It keeps the durable-thread
benefit but leaves thread creation, sending, waiting, and recovery in the
native Codex app actions. It avoids a second daemon and avoids a mandatory
provider-specific CLI.

Keep the helper library deterministic. It validates rosters, builds compact
packets, resolves role selectors against a live catalog, and writes redacted
evidence. It does not execute model output.

Add a richer runtime adapter only after a second live comparison proves that it
reduces total rework and handles usage-limit recovery correctly.

## Re-test plan

Use the same small, reversible repository task for two runs:

1. Native skill-first routing with existing named threads.
2. A runtime adapter that starts and resumes persistent app-server sessions.

Hold the objective, allowed paths, acceptance checks, and reviewer policy
constant. Measure correctness, test evidence, follow-up reliability, observed
usage, number of workers, and recovery after quota or writer failure.
