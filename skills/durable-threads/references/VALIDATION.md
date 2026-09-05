# Validation and limits

The automated suite uses fake providers. It checks routing limits, result
contracts, path claims, ledger locks, retry indices, and session identity drift.
It does not consume a subscription allowance.

## Enforcement boundaries

- `plan --local` selects no workers. Automatic routing selects up to the roster
  limit. Keyword routing needs planner review.
- The parallel limit checks the proposed selection. It is not a scheduler or
  a global limit across separate processes.
- Ledger transactions use an exclusive lock file. A stale lock requires manual
  inspection. The local running state does not prove provider state.
- Dispatch without a ledger has no persisted retry guard. Supply a roster,
  worker name, ledger, and task ID for the recorded workflow.
- Output limits truncate returned text after process completion. They do not
  cap provider tokens or process memory. Truncated evidence can fail parsing.
- Evidence verification compares path claims. It does not execute checks or
  prevent out-of-scope writes. Use a clean isolated checkout and inspect the diff.
- Usage extraction reads common counters. Missing usage is unknown. Counters
  do not establish subscription cost or include every resumed context cost.
- Session compaction and provider recovery remain manual.

## Live comparison gate

Use matched tasks from the same baseline in separate worktrees. Compare one
direct agent, native persistent workers, and the upstream orchestrator. Keep
models, task scope, tests, and review criteria fixed where each tool permits it.
Record any differences. Alternate run order across several tasks.

Record allowed-path violations, independently run checks, provider calls,
follow-ups, rework, elapsed time, and all reported token counters. Include planner
and reviewer usage. Mark missing counters as unknown. Report each provider's
allowance separately.

Inject quota and writer errors with fake providers first. In a live run, verify
that the system stops and preserves evidence. Resume only after the real state
changes. Do not consume an account allowance merely to trigger a quota error.

No controlled live comparison has established a token-saving percentage for
this version. The earlier StoriBuk task remains smoke-test evidence only.
