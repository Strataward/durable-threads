---
name: durable-threads
description: Coordinate complex software work through named durable sessions across Codex, Claude, Grok, and Cursor with compact context and evidence-based review. Use when a task benefits from persistent specialist sessions. Do not use for a simple one-session request.
---

# Durable Threads

Use this skill when the user wants a planner to route work through named,
persistent worker sessions.

## Operating model

Keep the current task as the planner and integration owner. Use the current
task for architecture, scope, user decisions, and final review. Use named
worker sessions for bounded implementation, tests, research, documentation, or
security work.

Use this order:

1. Inspect the repository and the current request.
2. Inspect provider availability and current model limits.
3. Make a short plan with independent work units.
4. Resolve each worker by its exact title and provider.
5. Send one compact packet to each idle worker.
6. Wait for worker completion with one bounded wait call when the runtime supports it.
7. Read structured evidence and inspect the actual diff.
8. Ask for one focused correction only when the evidence identifies a defect.
9. Review the final result in the current task.
10. Integrate, commit, push, or deploy only when the user authorizes that action.

Read the relevant reference before the operation:

- Read `references/ASTRA.md` when selecting a frontier Codex planner or reviewer.
- Read `references/PROVIDERS.md` when a worker uses Claude, Grok, or Cursor.
- Read `references/PERSISTENT_THREADS.md` when resolving, resuming, or stopping workers.
- Read `references/OPERATING_POLICY.md` for concurrency, budget, and recovery limits.
- Read `references/RESULT_SCHEMA.md` before sending a packet or accepting a result.
- Read `references/COMPARISON.md` when comparing this approach with another orchestrator.

## Provider policy

Use the provider that matches the worker task. Keep provider session IDs in
local ignored state. Do not copy a full transcript into a new packet.

- Codex uses native Codex app actions. Use `list_threads`,
  `send_message_to_thread`, `wait_threads`, and `read_thread` when they are
  available.
- Claude uses Claude Code. Use `claude -p` for headless work and `--resume`
  for an existing session. Use `--output-format json`.
- Grok uses Grok Build. Use `grok -p` for headless work, `--resume` for an
  existing session, `--no-auto-update` in automation, and JSON output.
- Cursor uses Cursor Agent. Use `agent` when the current installation provides
  it. Use `cursor-agent` as the compatibility executable. Use `--resume` and
  JSON output.

Use `durable-threads provider-command` to inspect the exact provider command
before a new integration. Use `durable-threads dispatch` only after the user
authorizes the provider call. The helper never enables dangerous auto-approval
flags.

Treat generic model roles as policy, not as provider model IDs. Claude maps
`frontier`, `balanced`, and `efficient` to the stable aliases `opus`, `sonnet`,
and `haiku`. Grok and Cursor require `default` or a provider-visible model ID.
Do not guess a model ID for either provider.

## Model and token policy

Treat model labels as roles, not as guaranteed model IDs. Use live discovery.
Do not invent a model ID. Use the strongest available model for planning and
review when the task needs it. Use the cheapest model that can satisfy the
worker acceptance checks for routine execution.

Use Astra for difficult planning and review when the current Codex runtime
exposes it. Do not send every worker to Astra. Do not replace a missing model
silently. Report the fallback and the reason.

Use reasoning effort as a measured control. Start with `high` for a difficult
planner or reviewer. Use `medium` or `low` for bounded worker tasks. Use
`xhigh` or `max` only when a representative evaluation shows a quality gain
that justifies the extra usage.

Read `references/ASTRA.md` for the full policy.

## Context policy

Pass the smallest useful packet. Include the objective, allowed paths,
acceptance checks, constraints, provider, model selector, and result contract.
Do not paste a full conversation or an entire repository into a worker packet.

Use native notes and searchable history when the provider supports them. Keep
durable context in the provider session. Use a local roster or ledger only for
role metadata, provider session IDs, statuses, and compact evidence.

## Session policy

Use `list_threads` before creating or selecting a Codex worker. Match the exact
title and provider. Use the provider's resume flag for Claude, Grok, and
Cursor. Do not create a second session with a similar title.

Create a new worker only when the user authorizes it, no matching worker
exists, and the roster allows creation. Record the new provider session ID in
local ignored state.

Do not resume an active writer. Wait for a state change or stop the exact
stale task after reviewing its last evidence. If a provider reports a usage or
authorization limit, record the failure and stop retries until the limit resets
or a declared fallback is available.

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
