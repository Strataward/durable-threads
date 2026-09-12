---
name: durable-threads
description: Coordinate bounded engineering work across durable provider sessions with risk-aware, model-economic routing. Use frontier reasoning for consequential decisions and efficient high-reasoning workers for sustained execution.
---

# Durable Threads

Use Durable Threads when a handoff improves model fit, context isolation, independent ownership, or economic efficiency. Keep simple work in the current task.

The operating principle is:

> Frontier decisions. Workhorse execution. Deterministic verification. Evidence-gated escalation.

The planner owns architecture, scope, risk, acceptance, escalation, review policy, and integration. Workers receive a bounded implementation contract, not the planner's transcript.

## 1. Decide whether to hand off

Continue locally when the current task has the right model, context, and ownership. Use a durable worker when a cheaper suitable model can perform sustained execution, context should be isolated, independent work can run safely in parallel, a specialist review needs independence, or a persistent provider session already contains useful context.

Read `references/WHEN_TO_USE.md` when unclear.

## 2. Classify risk

Classify the objective R0–R4 before deciding review depth: R0 mechanical, R1 bounded, R2 integration, R3 critical, R4 systemic.

Read `references/RISK_ROUTING.md`. The deterministic helper is advisory; explicitly override when repository facts justify it.

## 3. Freeze the implementation contract

Before dispatch, define objective, decisions already made, invariants, non-goals, allowed paths, exact acceptance checks, constraints, and risk class.

Read `references/PACKET_CONTRACT.md`. Do not make a workhorse rediscover architecture that the planner can decide once.

## 4. Select economically

Use the least expensive model/effort combination that can reliably satisfy acceptance.

For constrained Codex/Work usage, prefer:

- implementation/debugging: `efficient` + `xhigh`;
- difficult general planning: `balanced` + `medium`;
- consequential architecture/review: `frontier` + `low` or `medium`;
- higher frontier effort only after evidence shows it is needed.

Do not hard-code provider model names when a live catalog is available. Read `references/MODEL_ECONOMICS.md` and `references/ASTRA.md`.

## 5. Dispatch and sleep

Resolve the idle worker by provider and exact session identity. Send one packet. Then let the orchestrator sleep.

Do not repeatedly poll unchanged worker state or reread transcripts while execution is healthy. Wake the planner for completion, material evidence, provider failure, user steering, or a consequential decision.

Read `references/PERSISTENT_THREADS.md`.

## 6. Verify deterministically first

Prefer compiler, tests, type checking, static analysis, schema checks, migration checks, and CI before another model review. Inspect the actual diff; an allowed-path instruction is not a sandbox.

A worker result must include:

```json
{
  "status": "complete",
  "provider": "codex",
  "changedPaths": [],
  "checks": ["exact command: passed"],
  "remainingConcerns": ["None known"]
}
```

Missing evidence is incomplete. Do not report an unexecuted check as passed.

## 7. Apply the risk gate

Default economy policy recommends frontier review at R3 and above. R0/R1 normally use deterministic checks and efficient review only when useful. R2 gets integration review. R3/R4 get independent specialist/frontier review.

Do not use Astra to review every small edit.

## 8. Correct or escalate from evidence

Default correction limit is one focused retry. Name the failed check and violated invariant.

If the same conceptual failure repeats, escalate:

`efficient/xhigh -> balanced/medium -> frontier/low -> frontier/medium`

Do not escalate based on prestige. Do not rotate task IDs to bypass retry limits.

## 9. Keep hard stops

Stop on quota exhaustion, authentication failure, unknown writer state, session drift, path-scope violation, exhausted corrections, or architecture ambiguity that invalidates the packet.

Push, merge, deploy, publish, account creation, and production changes require explicit user authorization.

## 10. Measure

When comparing strategies, record model usage when available, parent turns, follow-ups, wall time, first-pass acceptance, review defects, corrections, and final correctness. Do not claim savings from token counts alone.

Read `references/BENCHMARKING.md`, `references/VALIDATION.md`, and `references/COMPARISON.md`.
