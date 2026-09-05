# Final retained-session comparison

Date: 2026-09-05.

## Decision

Keep the skill installed for bounded handoffs. Do not use it merely to continue
related work. A direct task can retain context without the skill.

The skill is stronger as a scope and evidence protocol. This final trial does
not support it as a general token-saving layer. Pause feature expansion.
Use it when a cheaper suitable model, narrower context, or independent owner
justifies a handoff. Those benefits were not measured in this same-model trial.

## Method

Two new detached StoriBuk worktrees started from commit
435f90eaf0724b27b70495b70b2b814fed2a768d. Neither contained the earlier trial
patches. The active StoriBuk checkout remained unchanged.

Both arms used Codex CLI 0.153.4 with gpt-5.6-luna and low reasoning. Each
retained one provider session through three related changes:

1. Reject invalid chapter counts.
2. Return the missing page indexes without mutating inputs.
3. Bound page-index allocation at 10,000 chapters.

These changes are benchmark fixtures, not approved product requirements.

Both arms had dependencies available before execution. Both used the same
workspace-write setting on new and resumed calls. The skill installation,
output schema, and checker code remained fixed during all six calls.
Order alternated: protocol/direct, direct/protocol, protocol/direct.

The direct arm returned concise prose. The protocol arm used the supplied
JSON schema, the production ledger, and the production evidence verifier.
Both received the same task requirements, allowed paths, and test commands.
Neither worker loaded the planner skill or the full conversation. The current
task used the skill as the planner. This is a CLI protocol test, not a test of
native app task routing or the upstream orchestrator.

## Results

| Measure | Direct retained session | Protocol retained session |
| --- | ---: | ---: |
| Provider calls | 3 | 3 |
| Accepted steps | 3/3 | 3/3 |
| Corrections | 0 | 0 |
| Observed out-of-scope changes | 0 | 0 |
| Input tokens | 261,668 | 414,299 |
| Cached input tokens | 238,848 | 359,424 |
| Input minus cached input | 22,820 | 54,875 |
| Output tokens | 3,123 | 3,489 |
| Reported reasoning output tokens | 211 | 337 |
| Sum of provider call durations | 86.75 seconds | 102.29 seconds |

The protocol used 58.3% more total input tokens and 11.7% more output tokens.
Its summed provider time was 17.9% higher. These are observations from one
sequence, not general estimates. Reasoning tokens are not added to output.

Each step passed independent Node behavior assertions, focused Vitest tests,
shared-package type checking, lint for both changed files, and whitespace
checks. Both final focused test files passed seven tests. All protocol results
passed the format and changed-path checks. Session IDs stayed stable in both
arms. The full application suite did not run.

The parent reviewed both final diffs. Both implementations met the bounded
requirements. No benchmark change entered StoriBuk dev or main.

## Why this changes the interpretation

The previous trial compared a fresh session for every change against one
retained session. That test suggested a benefit from context reuse. It did not
isolate the benefit of this skill.

This trial retained context in both arms. The extra protocol did not improve
correctness or reduce corrections on these tasks. Its higher measured usage
makes direct continuation the better starting choice for this workload.

The extra usage cannot be attributed to the schema alone. Model choices
within a turn, tool use, caching, and structured output can all affect it.
Do not remove evidence controls from necessary handoffs based on this result.

## Improvements validated

- Explicit empty JSON concerns arrays now normalize to no concerns.
- Missing or invalid list fields still fail.
- The optional output schema produced valid results in all three protocol steps.
- The original retry limit remains fixed.
- The local helper suite passes 75 tests.
- Skill discovery and the default prompt now allow direct continuation instead
  of implying that every invocation must create a handoff.

The skill-creator guidance kept worker packets separate from planner
instructions. The usage guide states when a separate worker is justified.

A separate Grok review attempt failed before starting a provider session
because its read-only sandbox could not be applied. The parent completed the
review. No Grok result is counted as independent acceptance.

## Limits

This is one small, non-randomized sequence using an already studied module.
The same model performed both arms. No cross-model or multi-provider saving
was tested. Cache state was not controlled. The independent assertions were
visible to workers. The global skill catalog was not isolated.

Parent planning and review tokens are unavailable. The reported time excludes
parent work and independent check duration. Subscription allowance cost is
unknown. The protocol cannot claim an end-to-end saving from these counters.

No live quota or active-writer recovery test ran. Local refusal tests do not
prove provider-side recovery. The worktrees and local result records remain
available for inspection. No further model runs are needed for this decision.
