# Operating policy

## Default limits

- Use at most two parallel workers.
- Use at most one follow-up per worker.
- Keep one planner and one reviewer in the current task.
- Keep result summaries below 2,000 characters unless the user needs more.
- Use one bounded wait for up to eight workers.
- Do not set a hard goal token budget by default.

Change a limit only when the user requests it or when a measured evaluation
supports the change.

## Fan-out rule

Fan out only independent work. Keep dependent work in sequence. A worker must
not modify files outside its packet. The current task owns integration.

## Acceptance rule

Every worker needs an acceptance check that another agent can run. A result
without exact checks is incomplete. The planner must inspect the actual diff and
run the checks again when the change affects integration or security.

## Correction rule

Send a correction only when the failure is concrete. Name the failed check, the
expected result, and the allowed paths. Stop when the same failure repeats or
when the provider reports a quota or authorization limit.

## External actions

The skill does not infer permission to push, merge, deploy, publish, create
accounts, or change production settings. Ask for a clear user instruction at
the boundary. Prepare a reviewable result first.

## Privacy

Do not put secrets, environment values, raw logs, child or family data, or
private customer data in packets, ledgers, model prompts, issues, or commits.
Use file names and redacted summaries when evidence is enough.
