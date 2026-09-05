---
name: codex-thread-loom
description: Coordinate complex software work through named durable Codex threads with frontier planning, efficient execution, compact context, and evidence-based review. Use when a task benefits from persistent specialist threads. Do not use for a simple one-thread request.
---

# Codex Thread Loom

Use this skill when the user wants a planner to route work through named,
persistent Codex worker threads.

## Operating model

Keep the current task as the planner and integration owner. Use the current
task for architecture, scope, user decisions, and final review. Use named worker
threads for bounded implementation, tests, research, documentation, or security
work.

Use this order:

1. Inspect the repository and the current request.
2. Inspect the current runtime catalog and provider limits.
3. Make a short plan with independent work units.
4. Resolve each worker by its exact existing thread title.
5. Send one compact packet to each idle worker.
6. Wait for worker completion with one bounded wait call.
7. Read structured evidence and inspect the actual diff.
8. Ask a worker for one focused correction only when the evidence identifies a defect.
9. Review the final result in the current task.
10. Integrate, commit, push, or deploy only when the user authorizes that action.

Read the relevant reference before the operation:

- Read `references/ASTRA.md` when selecting a frontier planner or reviewer.
- Read `references/PERSISTENT_THREADS.md` when resolving, resuming, or stopping workers.
- Read `references/OPERATING_POLICY.md` for concurrency, budget, and recovery limits.
- Read `references/RESULT_SCHEMA.md` before sending a packet or accepting a result.
- Read `references/COMPARISON.md` when comparing this approach with another orchestrator.

## Model policy

Treat model labels as roles, not as guaranteed model IDs. Use live discovery.
Do not invent a model ID. Use the strongest available model for planning and
review when the task needs it. Use the cheapest model that can satisfy the
worker acceptance checks for routine execution.

Use Astra for difficult planning and review when the current runtime exposes
it. Do not send every worker to Astra. Do not replace a missing model silently.
Report the fallback and the reason.

Use reasoning effort as a measured control. Start with `high` for a difficult
planner or reviewer. Use `medium` or `low` for bounded worker tasks. Use
`xhigh` or `max` only when a representative evaluation shows a quality gain
that justifies the extra usage.

## Context policy

Pass the smallest useful packet. Include the objective, allowed paths,
acceptance checks, constraints, and result contract. Do not paste a full
conversation or an entire repository into a worker packet.

Use native notes and searchable history when the current Codex runtime provides
them. Keep durable context in the worker thread. Use a local roster or ledger
only for role metadata, IDs, statuses, and compact evidence.

## Thread policy

Use `list_threads` before creating or selecting a worker. Match the exact title
and inspect its status. Reuse the matching idle thread. Do not create a second
thread with a similar title.

Use `send_message_to_thread` for a new turn in an existing worker. Use
`wait_threads` for bounded waiting. Use `read_thread` to collect evidence.
Use `set_thread_archived` only when the user asks to retire a thread.

Create a new worker only when the user authorizes it, no matching worker exists,
and the roster allows creation. Record the new ID in local ignored state.

If a thread has an active writer, wait for a state change or stop the exact
stale task after reviewing its last evidence. Do not resume blindly. If a
provider returns a usage limit, record the limit and stop retries until the
limit resets or a declared fallback is available.

## Result policy

Accept a worker result only when it includes:

- changed paths;
- exact checks and results;
- remaining concerns;
- no secrets, private data, or full transcript.

The worker's claim is not proof. Inspect the diff and run the required checks
in the current task before integration.

## Safety boundary

Do not place credentials, environment values, private child or family data, or
raw provider transcripts in packets, ledgers, issues, or commits. Keep paths
and scope narrow. Stop before destructive, external, or production actions
unless the user authorized them.
