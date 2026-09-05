# Context reuse trial — 2026-09-05

This historical trial used fresh sessions as its baseline. The later
[retained-session trial](2026-09-05-retained-baseline.md) is the stronger
comparison for ordinary sequential work. It favored direct continuation.
The parser later changed to accept explicit empty concerns arrays.

## Decision

Keep Durable Threads as an optional protocol for related work. Use direct
execution for small tasks. Pause provider expansion and new orchestration
features. This trial supports further use of one persistent worker, but it
does not establish subscription savings.

## Method

Two detached StoriBuk worktrees started from the same commit. The active
project remained unchanged. Each approach completed three related changes:

1. Reject invalid chapter counts in the page-index helper.
2. Add a helper that returns missing page indexes.
3. Bound page-index allocation at 10,000 chapters.

These are benchmark changes, not approved product requirements. They remain
in the benchmark worktrees.

Both approaches used Codex CLI 0.153.4, gpt-5.6-luna, low reasoning, the same
task packets, and the same independent Node assertions. Workers could change
only the source module and its test file. The direct approach started a fresh
session for each change. The persistent approach resumed one session.
The order was direct/persistent, persistent/direct, direct/persistent.

Workers received the JSON result contract. They did not load the planner
skill. This measures a session-reuse mechanism, not the whole skill, native
Codex app actions, or backnotprop/orchestrator.

## Observed worker usage

All eight calls are included. Failed calls and corrections are not removed.

| Counter | Direct, fresh per change | Persistent |
| --- | ---: | ---: |
| Provider calls | 4 | 4 |
| Input tokens | 454,221 | 446,544 |
| Cached input tokens | 382,208 | 411,904 |
| Input minus cached input | 72,013 | 34,640 |
| Output tokens | 4,766 | 3,587 |
| Reported reasoning output tokens | 750 | 456 |
| Test corrections | 1 | 0 |
| Runner repairs with a repeated call | 0 | 1 |
| Observed out-of-scope changes | 0 | 0 |

Input minus cached input was 51.9% lower with persistence. Total input was
1.7% lower. Output was 24.7% lower. Reasoning tokens are shown separately;
they are not added to output tokens.

Parent planning, implementation, and review usage is unknown. Subscription
allowance cost is unknown. Do not translate these figures into subscription
savings. Complete elapsed time is unavailable because the direct correction
did not record duration.

## Failures and acceptance

The first persistent resume used the CLI's default read-only mode. It could
not add the requested helper. The worker reported blocked status. The runner
stopped. The planner set workspace-write on the parent exec command and
repeated that step once. The same provider session ID resumed successfully.
This was a runner defect, not evidence of automatic skill recovery.

The direct approach wrote one incorrect test expectation. Independent Vitest
execution found it. One correction fixed the test. Final independent checks
passed for both approaches:

- the common behavior assertions;
- the focused Vitest file: direct 9 tests, persistent 7 tests;
- shared-package type checking;
- lint for both changed files;
- whitespace checks and allowed-path inspection.

Different test counts do not establish better coverage. The common assertions
provide the matched behavior check. The full application suite was not run.

The direct phase-two result claimed complete status while listing an
unexecuted check. Its final correction returned an empty concerns array.
The strict verifier rejected both records. No second format correction ran.
The planner accepted the code from independent checks, not those result
claims. Persistent results passed the format checks, including the blocked
record. Passing format checks does not mean a blocked task completed.

## Limits

This is one small sequence, not a repeated or randomized study. Cache state
was not controlled. The global skill catalog was not isolated. The installed
skill changed during the first run. Worker requests excluded skill loading,
but discovery context could differ.

Dependencies were linked only for final independent review. Earlier workers
could not run Vitest. The final direct correction used those dependencies.
The independent check script was visible to workers. There was no hidden
test set.

The source changes, runner repair, and result-format failures make this a
practical trial, not a causal estimate of efficiency. No live quota or
active-writer recovery test ran. Local refusal tests do not prove recovery
of provider execution.

## Changes to Durable Threads

The helper now preserves the original retry limit. It rejects changed
limits, malformed task records, and legacy records without a limit. JSON
list fields reject invalid types. The local suite has 71 passing tests.

The planner skill decreased from 961 to 450 words. The skill-creator guidance
kept routing with the planner and removed repeated instructions from worker
context. The installed skill matches the updated repository files.

Do not rotate task IDs to bypass an exhausted retry limit. New, distinct
work can reuse an idle session with a separate task record. This boundary
prevents the term “follow-up” from conflating new work with corrections.
