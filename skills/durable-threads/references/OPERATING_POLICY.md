# Operating policy

## Default limits

- Use at most two parallel workers.
- Select at most two workers for one plan unless the roster raises the limit.
- Use at most one follow-up per worker.
- Keep one planner and one reviewer in the current task.
- Keep result summaries below 2,000 characters unless the user needs more.
- Use one bounded wait for up to eight workers.
- Do not set a hard goal token budget by default.
- Keep the provider and provider session ID with every worker record.

The plan command enforces the selected-worker limit and the parallel-worker
limit. The dispatch command enforces the output limit, follow-up limit, and
local ledger writer guard when the caller supplies a roster and ledger.

The helper does not claim automatic recovery for provider quota errors, private
active-writer state, or provider process failure. It records the stop state and
requires a new authorized action.

Set limits before a task starts. The ledger stores `maxFollowups` on the first
call. Later calls must use that same limit. Old records without a limit stop
for inspection. Do not clear a record or choose a new task ID to bypass a stop.
An authorized policy change applies to new work, not retries of the same task.

## Fan-out rule

Fan out only independent work. Keep dependent work in sequence. A worker must
not modify files outside its packet. The current task owns integration.

Automatic routing uses conservative signals. It selects implementation for a
bounded code change. It adds test, research, or security work only when the
objective or path names show a matching need. Use an explicit worker selection
when the planner has better information.

## Acceptance rule

Every worker needs an acceptance check that another agent can run. A result
without exact checks is incomplete. The planner must inspect the actual diff and
run the checks again when the change affects integration or security.

The result verifier rejects a complete result without a provider, checks, or
remaining concerns. It rejects a changed path outside the allow-list. It can
reject a result when its changed-path list does not match a clean git diff.

## Correction rule

Send a correction only when the failure is concrete. Name the failed check, the
expected result, and the allowed paths. Stop when the same failure repeats or
when the provider reports a quota or authorization limit.

The local ledger marks a task as running before dispatch. A second local writer
for the same task stops. A follow-up must use the recorded provider and session
ID. The provider can still have an active writer that the local ledger cannot
see. Treat that provider report as a hard stop.

## External actions

The skill does not infer permission to push, merge, deploy, publish, create
accounts, change production settings, or start a provider session that can
modify files. Ask for a clear user instruction at the boundary. Prepare a
reviewable result first.

## Privacy

Do not put secrets, environment values, raw logs, child or family data, or
private customer data in packets, ledgers, model prompts, issues, or commits.
Use file names and redacted summaries when evidence is enough.

Do not claim token savings from packet size alone. Record provider usage when it
is available. Compare total input tokens, output tokens, follow-ups, rework, and
correctness against a single-agent baseline before changing the defaults.
