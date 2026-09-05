---
name: durable-threads
description: Coordinate bounded work across separate provider sessions when model specialization or independent ownership requires a handoff. Do not use merely to continue related edits in a suitable current task.
---

# Durable Threads

Keep simple work in the current task. Continue related edits there when its
model and context are suitable. When a handoff is useful, prefer one existing
worker. Add a second worker only for independent work. Do not delegate merely
because this skill is loaded.

If the current task already has the right context and model, continue there.
Use a worker for a cheaper suitable model, narrower context, or independent
ownership. Session reuse alone does not require this skill.
Read `references/WHEN_TO_USE.md` when the choice is unclear.

The planner owns scope, model selection, review, and integration. Workers need
the task packet, not this skill or the planner's conversation. Read only the
reference needed for the current operation.

## Send work

1. Define the task, allowed paths, exact acceptance checks, and constraints.
2. Resolve the idle worker by its recorded provider and session ID.
3. Send the packet with the JSON result shape below.
4. Wait for completion without repeated transcript reads.
5. Inspect the diff and run the acceptance checks before integration.

Use the least expensive available model that passes the task checks. Reserve
frontier reasoning for difficult planning or review. Verify model availability;
do not guess IDs or change providers without disclosure. Read
`references/ASTRA.md` only when selecting a frontier Codex model.

For native Codex tasks, read `references/PERSISTENT_THREADS.md`. Use the app's
list, send, wait, and read actions. Create a new task only with explicit user
authorization. For Claude, Grok, or Cursor, read `references/PROVIDERS.md`.
The CLI helper does not dispatch Codex. State when an evaluation uses Codex CLI
sessions instead of native app tasks.

## Keep limits

Default to at most two workers and one correction for a demonstrated defect.
Read `references/OPERATING_POLICY.md` before dispatch or recovery. Keep the
original retry limit for the task. Stop on quota, authentication failure,
uncertain writer state, or exhausted retries. Do not retry until the cause is
resolved. An existing session ID does not prove safe execution recovery.

Keep session IDs and compact evidence in ignored local state. Do not send
secrets, private data, or transcripts. A packet's allowed paths do not prevent
writes. Use isolation and inspect all changed paths. Commit, push, merge, and
deploy only with user authorization.

## Worker result

Include this shape in the packet. The provider identifies the worker itself.
Use empty arrays for no changed paths. Record exact checks and their results.
An explicit empty concerns array means no concerns. Missing fields still fail.
When supported, use `references/RESULT.schema.json` as the output schema.

```json
{
  "status": "complete",
  "provider": "codex",
  "changedPaths": [],
  "checks": ["exact command: passed"],
  "remainingConcerns": ["None known"]
}
```

Use `blocked` or `failed` when work cannot complete. Do not report unexecuted
checks as passed. Read `references/RESULT_SCHEMA.md` for verification details.
`verify-result` checks claims against the diff; it does not run tests.

For comparisons, read `references/VALIDATION.md` and `references/COMPARISON.md`.
Count planning, worker calls, review, and corrections. Keep missing usage and
subscription cost unknown. Do not claim savings from raw token counts alone.
