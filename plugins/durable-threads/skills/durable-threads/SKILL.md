---
name: durable-threads
description: Coordinate coding work with native Codex subagents, frontier decisions, efficient high-reasoning execution, deterministic verification, safe parallelism, and evidence-gated escalation. Use when a coding task benefits from delegation, context isolation, persistent workers, or risk-aware review.
---

# Durable Threads

Durable Threads should work immediately after installation. Do not require a roster, Python helper, extra provider, or project-specific configuration for the default workflow.

The operating principle is:

> Frontier decisions. Workhorse execution. Native agents. Deterministic verification.

Use the current task as planner and integrator. Delegate only when the handoff adds value. On current Codex, prefer the runtime's **native subagent system** rather than launching another Codex process or emulating orchestration yourself.

## Native-runtime rule

When native Codex subagents are available:

- use `explorer` for specific, read-heavy codebase questions;
- use `worker` for bounded implementation, debugging, tests, and production work;
- use a project-defined read-only reviewer/specialist role when one is available and justified;
- otherwise use the default agent for independent review;
- use the runtime's native wait/resume lifecycle instead of repeatedly resampling the parent just to check status.

If native subagents are unavailable, fall back to the existing provider/session mechanisms. Do not require external providers merely because they exist.

## Default workflow

1. **Decide whether a handoff helps.** Keep small, dependent, or already well-contextualized work in the current task. Delegate when narrower context, independent ownership, lower-cost execution, or parallel read-heavy work improves the task.
2. **Classify consequence.** Use R0 mechanical, R1 bounded, R2 integration, R3 critical, or R4 systemic. Difficulty alone does not raise risk.
3. **Freeze the contract.** Give the child the objective, decisions already made, invariants, non-goals, allowed paths, acceptance checks, and constraints. Do not make a workhorse rediscover architecture unnecessarily.
4. **Choose the native role.** Prefer `explorer` for codebase discovery and `worker` for execution. Use custom reviewer/security roles only when they materially improve independence or risk coverage.
5. **Choose the model/effort economically.** Prefer the runtime's efficient high-reasoning option for bounded implementation/debugging. Use balanced reasoning for harder general planning. Use frontier reasoning for architecture, ambiguous failures, security-sensitive decisions, and R3/R4 review. Discover live model names; do not invent IDs.
6. **Choose isolation before fan-out.** Read-only agents can usually share a checkout. One writer can use the shared checkout. Multiple independent writers should use isolated worktrees when supported. Overlapping writers should be serialized.
7. **Dispatch and sleep.** Send bounded work and avoid repeated no-op polling or transcript rereads while a healthy child executes. Wake the planner on completion, failure, user steering, or material new evidence.
8. **Verify deterministically first.** Inspect the actual diff and prefer tests, type checks, linters, static analysis, schema checks, migration checks, and CI before asking another model for an opinion.
9. **Escalate from evidence.** A failed check, violated invariant, repeated conceptual error, unresolved ambiguity, or elevated risk can justify a stronger model. Do not escalate based on prestige alone.

## Safe parallelism

Use this invariant:

> **Subagents for parallel cognition. Worktrees for parallel mutation.**

Parallelize independent explorers, reviewers, and other read-heavy work freely within the runtime's configured concurrency limit. For writers, assign explicit ownership. Do not run overlapping writers in parallel. When several independent writers are useful and worktree isolation exists, prefer one checkout per writer.

Do not treat a worktree as proof that two changes are semantically independent; integration still belongs to the planner.

## Default economics

When the runtime exposes equivalent tiers, a good starting policy is:

- implementation and focused debugging: `efficient` + high reasoning (`xhigh` when supported);
- read-heavy exploration: `efficient` or `balanced` at low/medium effort unless the question is unusually hard;
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

A child result is evidence, not acceptance. The planner still inspects the diff and reruns integration- or security-relevant checks.

## Review gate

- R0/R1: deterministic checks are normally enough unless the result is suspicious.
- R2: add integration review when contracts, queues, schemas, or external boundaries changed.
- R3/R4: require independent specialist/frontier review by default.

A reviewer should preferably be read-only and should receive the contract plus the actual diff/evidence, not the implementation worker's self-assessment as a substitute for inspection.

## Safety and stopping

Stop on quota exhaustion, authentication failure, unknown writer state, session drift, path-scope violation, exhausted corrections, or architecture ambiguity that invalidates the packet. Do not rotate task IDs or agent identities to bypass a stop.

Push, merge, deploy, publish, account creation, and production changes require explicit user authorization.

## Customize only when useful

Do not ask a new user to configure workers or JSON before starting. Native Codex roles plus the defaults above are sufficient for ordinary work.

Read advanced references only as needed:

- `references/ARCHITECTURE.md` — policy/runtime/verification architecture;
- `references/WHEN_TO_USE.md` — whether delegation earns its cost;
- `references/RISK_ROUTING.md` — R0-R4 review policy;
- `references/PACKET_CONTRACT.md` — detailed implementation contracts;
- `references/MODEL_ECONOMICS.md` and `references/ASTRA.md` — model selection;
- `references/PERSISTENT_THREADS.md` — durable session lifecycle;
- `references/PROVIDERS.md` — native Codex vs optional Claude/Grok/Cursor adapters;
- `references/OPERATING_POLICY.md` — retry, parallelism, isolation, and approval boundaries;
- `references/BENCHMARKING.md`, `references/VALIDATION.md`, and `references/COMPARISON.md` — measurement and evaluation.

The optional Python helper and roster files are for deterministic routing, provider-neutral experiments, benchmarking, or teams that want explicit policy. They are not prerequisites for using Durable Threads.
