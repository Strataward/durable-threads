# Persistent thread lifecycle

## Roster fields

Each worker entry should have:

- a unique `name`;
- an exact `threadTitle`;
- a purpose;
- a role selector;
- a reasoning effort;
- an optional local `threadId`;
- a maximum follow-up count.

Never commit real thread IDs. A thread ID can expose project history or local
account state.

## Resolve

1. List current tasks.
2. Find the exact title.
3. Check the task status and project directory.
4. Confirm that the worker purpose matches the packet.
5. Reuse an idle matching task.
6. Ask before creating a new task when no match exists.

Similar titles are not a match. A stale or unrelated task can carry the wrong
context.

## Send and wait

Send one packet per worker. Include the run ID so results can be matched.
Wait for up to eight workers in one bounded call. Do not poll unchanged state.
Read only the completed turn and the evidence needed for integration.

Keep parallel work independent. Do not start a dependent worker until its
input is available.

## Resume

Resume a finished worker only when its provider metadata is valid and its
runtime supports resume. Use a focused follow-up that names the failed check.
Do not resend the full original packet.

Use at most one normal correction by default. Use a second correction only if
the new evidence is concrete and the user has not asked for a strict limit.

## Recovery states

| State | Action |
| --- | --- |
| idle or finished | Send a new bounded turn. |
| active writer | Wait for a state change. Stop the exact stale task only after review. |
| usage limit | Record the limit. Wait for reset or use a declared fallback. |
| missing provider metadata | Do not resume. Start a new authorized task if needed. |
| provider failure | Preserve evidence. Classify the failure before retry. |
| unknown status | Inspect once. Do not issue repeated writes. |

The active-writer rule matters because a failed follow-up can leave provider
state alive even when the local task record looks stale.

## Retire

Archive a worker only when the user asks or when the roster explicitly defines
retirement. Keep the ledger entry so the decision remains auditable.
