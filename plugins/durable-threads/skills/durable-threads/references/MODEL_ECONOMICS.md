# Model economics

Durable Threads optimizes **accepted engineering work per constrained unit of model capacity**, not raw token minimization and not first-pass benchmark prestige.

> Put scarce intelligence on consequential decisions. Put long-running execution on the cheapest model/effort combination that reliably passes acceptance.

## Economic roles

| Execution class | Purpose | Typical work |
| --- | --- | --- |
| `decision` | high-leverage choices | architecture, decomposition, ambiguity resolution, escalation |
| `workhorse` | sustained execution | implementation, debugging, tests, routine refactors |
| `review` | independent acceptance | diff review, integration review, acceptance validation |
| `specialist` | domain-specific high-risk analysis | security, privacy, destructive migrations, recovery |

A model can serve more than one class, but a roster should make the intended economics explicit.

## Default Plus profile

As of September 2026, the recommended Codex/Work profile for users optimizing included Plus allowance is:

- planner: frontier/low only when the task genuinely needs frontier planning; balanced/medium is often sufficient;
- implementation: efficient/xhigh;
- focused debugging: efficient/xhigh;
- tests: efficient/high or efficient/xhigh;
- first-line review: efficient/xhigh;
- critical review: frontier/medium;
- frontier/xhigh or frontier/max: evidence-gated exceptions.

For OpenAI's current family this often maps to Astra for frontier decisions and Luna XHigh for execution. Do not hard-code those names when a live catalog is available.

## Why efficient XHigh execution is rational

The implementation worker is not being asked to solve the entire product problem. The planner should already have frozen architecture decisions, bounded paths, acceptance checks, invariants, and non-goals. High reasoning effort on an efficient model is therefore applied to a constrained search space.

A task can afford an implementation pass, deterministic checks, a workhorse review, one focused correction, and frontier escalation only if failure evidence remains. The relevant measure is final accepted correctness after verification.

## Evidence-gated escalation

Default ladder:

```text
efficient / xhigh
      ↓ acceptance failure after a focused correction
balanced / medium
      ↓ conceptual or architectural ambiguity
frontier / low
      ↓ unresolved difficult decision
frontier / medium
```

Higher frontier effort is outside the default ladder.

Concrete escalation evidence includes repeated acceptance failure, missing architecture decisions, conflicting parallel tasks, cross-module invariant failures, plausible security findings, or inability to make a critical change reversible.

Do not escalate because a task merely looks important.

## Sleeping orchestrator

When `strategy.sleepingOrchestrator` is true, the planner must not remain in a short polling loop while workers execute. Decide, dispatch, wait through an event-driven/bounded provider mechanism, and wake on completion or material evidence.

Short no-op polling can repeatedly re-enter a large parent context. Relevant Codex reports include:

- https://github.com/openai/codex/issues/35108
- https://github.com/openai/codex/issues/41875

## Fast mode

When allowance longevity matters, keep Fast mode off by default. Fast mode is a latency optimization, not an intelligence upgrade.

## Context economics

Large context windows are capacity, not a target. Prefer retained sessions while their context is relevant, compact packets, repository state files, exact path scopes, summaries of failed approaches, and fresh bounded workers when old context becomes misleading.

## Measuring value

Record, when available: input tokens, cached input, output tokens, reasoning tokens, wall time, workers selected, follow-ups, first-pass acceptance, deterministic failures, review defects, correction count, final acceptance, model selector/effort, risk class, and task class.

Do not claim savings from packet size alone. Compare matched tasks against direct single-agent baselines.

## Current OpenAI references

- https://help.openai.com/en/articles/20001516
- https://developers.openai.com/api/docs/models/gpt-5.6-luna
- https://developers.openai.com/api/docs/models
- https://github.com/openai/codex/issues/35108
- https://github.com/openai/codex/issues/41875

Product limits and model availability change. Treat current numbers as dated inputs, never permanent constants.
