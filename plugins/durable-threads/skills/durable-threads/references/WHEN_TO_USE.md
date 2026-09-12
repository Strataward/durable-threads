# When to use Durable Threads

Use Durable Threads when a handoff buys something concrete: **a cheaper suitable executor, narrower context, independent ownership, durable specialist context, or stronger review boundaries**.

If none of those benefits applies, keep the work in the current task. Orchestration is overhead, and the skill should earn that overhead rather than create ceremony.

| Situation | Starting mode | Why |
| --- | --- | --- |
| Small fix, question, or one-file review | Current task | A handoff adds more coordination than value. |
| Related edits where the current task has the right model and context | Continue the current task | Retain useful context without adding another owner. |
| Bounded implementation a cheaper model can reliably execute | One worker | Separate high-leverage decisions from sustained execution. |
| Specialist work that benefits from narrow context | One worker | Isolate the relevant evidence and avoid unrelated history. |
| Independent changes with disjoint write scopes | At most two workers | Parallelism is useful only when writers do not conflict. |
| Quota, authentication failure, or uncertain writer state | Stop | A fresh task ID is not a recovery mechanism. |

## Before delegating

State the reason for the handoff in one sentence. Good reasons include “Luna XHigh can execute this frozen design,” “the security reviewer should not inherit the implementation transcript,” or “these two tasks have disjoint paths and can proceed independently.”

If the reason is only “multi-agent sounds better,” do not delegate.

Give the worker a bounded implementation contract: objective, decisions already made, invariants, non-goals, allowed paths, acceptance commands, constraints, and result shape. Do not send the entire planner conversation by default.

Before dispatch, confirm the provider/model, working directory, available permissions, session identity when resuming, and that acceptance commands are runnable. For write tasks, use a clean or otherwise inspectable checkout.

## Accept work on evidence

A correctly shaped result is not proof that the code is correct. Inspect changed paths and independently run the checks that matter.

Use at most one focused correction by default. A correction should name a concrete failed check or review finding, preserve decisions that have not changed, and keep the original scope unless new evidence invalidates it.

If the correction fails for the same conceptual reason, stop or escalate according to policy. Do not rotate task IDs to manufacture more retries.

## What our local trials actually showed

Durable Threads does not assume that orchestration always saves tokens. The repo's retained-session trial is a useful counterexample: both arms preserved context, both completed the three related changes, and direct continuation used fewer input tokens. For that workload, staying in the current task was better.

See `docs/benchmarks/2026-09-05-retained-baseline.md`.

An earlier context-reuse trial showed lower uncached input with session reuse but also included a runner permission repair and a direct test correction, so it is not strong evidence for subscription savings. See `docs/benchmarks/2026-09-05-context-reuse.md`.

These results are why the current policy starts with **“does a handoff help?”** rather than automatically spawning workers.

## How to judge value

Compare against a direct session that also retains context. A fresh session for every edit is a different baseline and can exaggerate the benefit of persistence.

Keep correctness and allowed paths as gates. Then compare provider calls, parent turns, corrections, elapsed time, reported usage counters, review defects, and final acceptance. Keep cached input separate and mark missing usage or subscription cost as unknown.

Do not translate a raw token percentage directly into a subscription-savings percentage unless the provider exposes evidence that supports that conclusion.
