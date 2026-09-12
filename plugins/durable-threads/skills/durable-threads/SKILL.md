---
name: durable-threads
description: Coordinate coding work with frontier decisions, efficient high-reasoning execution, deterministic verification, and evidence-gated escalation. Use when a coding task benefits from delegation, context isolation, persistent workers, or risk-aware review.
---

# Durable Threads

Durable Threads should work immediately after installation. Do not require a roster, Python helper, extra provider, or project-specific configuration for the default workflow.

The operating principle is:

> Frontier decisions. Workhorse execution. Deterministic verification. Evidence-gated escalation.

Use the current task as planner and integrator. Delegate only when the handoff adds value. Prefer a capable efficient worker for sustained implementation and reserve frontier reasoning for consequential decisions or review.

## Default workflow

1. **Decide whether a handoff helps.** Keep small or already well-contextualized work in the current task. Delegate when a cheaper suitable model, narrower context, independent ownership, or durable worker context improves the task.
2. **Classify consequence.** Use R0 mechanical, R1 bounded, R2 integration, R3 critical, or R4 systemic. Difficulty alone does not raise risk.
3. **Freeze the contract.** Give the worker the objective, decisions already made, invariants, non-goals, allowed paths, acceptance checks, and constraints. Do not make a workhorse rediscover architecture unnecessarily.
4. **Execute economically.** Prefer the runtime's efficient high-reasoning option for bounded implementation/debugging. Use balanced reasoning for harder general planning. Use frontier reasoning for architecture, ambiguous failures, security-sensitive decisions, and R3/R4 review. Discover live model names; do not invent IDs.
5. **Dispatch and sleep.** Send one bounded task and avoid repeated no-op polling or transcript rereads while a healthy worker executes.
6. **Verify deterministically first.** Inspect the actual diff and prefer tests, type checks, linters, static analysis, schema checks, migration checks, and CI before asking another model for an opinion.
7. **Escalate from evidence.** A failed check, violated invariant, repeated conceptual error, or elevated risk can justify a stronger model. Do not escalate based on prestige alone.

## Default economics

When the runtime exposes equivalent tiers, a good starting policy is:

- implementation and focused debugging: `efficient` + high reasoning (`xhigh` when supported);
- difficult general planning: `balanced` + `medium`;
- consequential planning/review: `frontier` + `low` or `medium`;
- higher frontier effort only when the task or measured results justify it.

These are role policies, not hard-coded model names. Read `references/MODEL_ECONOMICS.md` when selecting or tuning models.

## Result contract

A completed worker should report changed paths, exact checks and results, and remaining concerns. When supported, use `references/RESULT.schema.json`.

```json
{
  "status": "complete",
  "provider": "codex",
  "changedPaths": [],
  "checks": ["exact command: passed"],
  "remainingConcerns": ["None known"]
}
```

A result is evidence, not acceptance. The planner still inspects the diff and reruns integration- or security-relevant checks.

## Safety and stopping

Stop on quota exhaustion, authentication failure, unknown writer state, session drift, path-scope violation, exhausted corrections, or architecture ambiguity that invalidates the packet. Do not rotate task IDs to bypass a stop.

Push, merge, deploy, publish, account creation, and production changes require explicit user authorization.

## Customize only when useful

Do not ask a new user to configure workers or JSON before starting. The defaults above are sufficient for ordinary Codex work.

Read advanced references only as needed:

- `references/WHEN_TO_USE.md` — whether delegation earns its cost;
- `references/RISK_ROUTING.md` — R0-R4 review policy;
- `references/PACKET_CONTRACT.md` — detailed implementation contracts;
- `references/MODEL_ECONOMICS.md` and `references/ASTRA.md` — model selection;
- `references/PERSISTENT_THREADS.md` — durable session lifecycle;
- `references/PROVIDERS.md` — optional Claude/Grok/Cursor adapters;
- `references/OPERATING_POLICY.md` — retry, parallelism, and approval boundaries;
- `references/BENCHMARKING.md`, `references/VALIDATION.md`, and `references/COMPARISON.md` — measurement and evaluation.

The optional Python helper and roster files are for deterministic routing, multi-provider sessions, benchmarking, or teams that want explicit policy. They are not prerequisites for using Durable Threads.
