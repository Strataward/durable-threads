# Persistent thread lifecycle

## What durable means

Durable Threads preserves the worker title, provider, provider session ID, task
status, and compact evidence. It does not own the provider's private runtime.
It does not restart a provider after a quota error. It does not clear an active
writer that the provider reports.

## Roster fields

Each worker entry should have:

- a unique `name`;
- a provider such as `codex`, `claude`, `grok`, or `cursor`;
- an exact `threadTitle`;
- a purpose;
- a role selector;
- a reasoning effort;
- an optional local provider `threadId`;
- a maximum follow-up count.

Never commit real thread or provider session IDs. An ID can expose project
history or local account state.

## Resolve

1. List current tasks.
2. Find the exact title and provider.
3. Check the task status and project directory.
4. Confirm that the worker purpose matches the packet.
5. Reuse an idle matching task or provider session.
6. Ask before creating a new task when no match exists.

Similar titles are not a match. A stale or unrelated task can carry the wrong
context.

## Send and wait

Send one packet per worker. Include the run ID so results can be matched.
Use the provider adapter for Claude, Grok, and Cursor. Use native Codex app
actions for Codex.
Wait for up to eight workers in one bounded call. Do not poll unchanged state.
Read only the completed turn and the evidence needed for integration.

Keep parallel work independent. Do not start a dependent worker until its
input is available.

## Resume

Resume a finished worker only when its provider metadata is valid and its
runtime supports resume. Claude, Grok, and Cursor use their provider session
resume controls. Codex uses the native task action. Use a focused follow-up
that names the failed check.
Do not resend the full original packet.

Use at most one correction by default. Set the limit before the task starts.

The local ledger enforces the follow-up index. It rejects a provider change or
session ID change during a follow-up. It also rejects a changed retry limit.
Stop when the limit is reached. Do not rotate IDs to retry the same failed work.
A new, distinct objective can reuse an idle session with a new task record.
This is new work, not a correction. Keep both records for review.

## Recovery states

| State | Action |
| --- | --- |
| idle or finished | Send a new bounded turn. |
| active writer | Wait for a state change. Stop the exact stale task only after review. |
| usage limit | Record the limit. Wait for reset or use a declared fallback. |
| missing provider metadata | Do not resume. Start a new authorized task if needed. |
| provider failure | Preserve evidence. Classify the failure before retry. |
| unknown status | Inspect once. Do not issue repeated writes. |

The local writer guard covers tasks that use the same ledger. It is not a
provider status API. Treat a provider-side active-writer response as unknown
state and stop.

The active-writer rule matters because a failed follow-up can leave provider
state alive even when the local task record looks stale.

## Retire

Archive a worker only when the user asks or when the roster explicitly defines
retirement. Keep the ledger entry so the decision remains auditable.
