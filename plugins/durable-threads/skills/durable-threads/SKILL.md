---
name: durable-threads
description: Risk-aware, economical coding with native agents, bounded contracts, and evidence-based completion. Use for delegation, durable work, or Pro usage optimization.
---

# Durable Threads

Use the host's native runtime. Own policy, not a second agent scheduler. Preserve the user's chosen model and workflow unless a change is authorized. Do not require rosters, Python, Temporal, or Jev for ordinary use.

## First decision

Keep small, dependent, or already-contextualized work in the current thread. Delegate only when a bounded worker, independent reviewer, or parallel reader earns its context and coordination cost. Do not spawn a swarm or monitoring agent by default.

For ChatGPT Pro 5x, Astra efficiency, or quota optimization, read `references/PRO5_POLICY.md`. Otherwise use the policy below. Load only references needed for the present decision.

## Execute a bounded task

1. Inspect the actual repository and requested target. Classify consequence: R0 mechanical; R1 bounded; R2 integration; R3 authentication, payments, privacy, destructive data or concurrency; R4 systemic architecture or recovery.
2. Freeze the objective, important decisions, invariants, non-goals, allowed paths, and observable acceptance criteria. Do not send a whole transcript to a worker. Keep architecture and security decisions with the planner.
3. Select the smallest sufficient execution shape. Prefer native `explorer` for read-heavy discovery and `worker` for implementation. Resolve model and supported effort from the live runtime, not guessed IDs. For bounded delegated work, start with an efficient model and supported high effort; use frontier reasoning for consequential decisions and independent review.
4. Use one writer per shared checkout. Independent readers may run concurrently. Multiple writers require isolated worktrees or sandboxes and non-overlapping ownership; serialize dependent or overlapping changes. Worktrees are not a security sandbox.
5. Run focused checks and inspect the diff. Batch independent reads/checks when safe; stop on a failed prerequisite. Keep full logs out of model context and return bounded failure excerpts. Never report a check as passed unless it actually ran.
6. Accept only what evidence supports. A worker's completion statement is not acceptance. The planner reruns integration/security-relevant checks and obtains required independent review.

## Efficient continuation

Reuse a healthy, relevant session for bounded corrections. Do not respawn a worker to reread the same files. Start a fresh scoped context when history is predominantly irrelevant, not after every tool call. Retain the objective, decisions, file references, unresolved risks and next check; exclude secrets and unneeded transcripts.

Use event-driven or blocking tool waits. Do not call a model repeatedly to ask whether a build finished. When a runtime cannot notify, report the waiting state rather than inventing wake support. Automatic retries need a classified transient failure; repeated identical failure or no acceptance progress requires diagnosis, not another blind attempt.

## Evidence and review

Return changed paths, exact commands/results, remaining concerns, and what was not tested. Use `references/RESULT.schema.json` when structured output is available.

R0/R1 normally need deterministic checks. R2 needs boundary/integration checks. R3/R4 requires independent specialist/frontier review. A reviewer receives the contract and actual diff/evidence in a separate, preferably read-only context. Preserve an explicit review requirement even when the implementation worker reports success. Human approval never substitutes for missing verification.

## Boundaries

Stop or checkpoint on exhausted quota/budget, authentication failure, unknown writer state, session drift, path-scope violation, exhausted corrections, or invalidated architecture assumptions. Do not rotate identities, create accounts, silently use paid API fallback, or weaken approval/sandbox/review policy to keep running.

Push, merge, deploy, publish and production changes require explicit authorization. Do not write project memory into a repository or publish transcripts without permission.

## References on demand

Read `references/PACKET_CONTRACT.md` for task contracts, `references/RISK_ROUTING.md` for consequence gates, `references/MODEL_ECONOMICS.md` for model tradeoffs, `references/PERSISTENT_THREADS.md` for session lifecycle, `references/OPERATING_POLICY.md` for recovery/isolation, and `references/PROVIDERS.md` for optional adapters. Use `references/BENCHMARKING.md` for measured comparisons. None is an instruction to load every file.
