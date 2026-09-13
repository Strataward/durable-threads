# Operating policy

## Default limits

- At most two selected workers and two parallel workers unless a roster or explicit native-runtime policy raises the limits.
- At most one focused correction per worker by default.
- Result summaries below 2,000 characters unless more evidence is required.
- No hard goal token budget unless the user asks for one.
- Keep provider/session identity with every worker record when an external provider is used.
- Keep Fast mode off when allowance longevity is the goal.
- Prefer `economy` strategy for constrained subscription usage.

## Native-runtime preference

When current Codex provides native subagents, use those capabilities before inventing a second Codex scheduler. Durable Threads should decide delegation, role, model/effort policy, ownership, review, and escalation; Codex should handle native child lifecycle, waiting, and resume behavior.

Use built-in `explorer` for specific read-heavy codebase questions and `worker` for execution/production work. Use project-defined reviewer/security roles only when they add value.

## Sleeping orchestrator rule

The planner must not poll unchanged child state in short loops. Dispatch and wake the planner on completion, failure, user steering, or material new evidence. Repeated no-op waits that resample the parent are a routing failure because they spend control-plane capacity without producing evidence.

## Decision/execution separation

The planner owns architecture, risk, scope, ownership, isolation, and integration. A workhorse owns bounded implementation. Resolve architecture ambiguity before dispatch; conversely, do not keep a frontier planner in the execution loop merely because it authored the plan.

## Fan-out and isolation

Fan out only independent work.

Use the default matrix:

| Work shape | Default workspace policy |
| --- | --- |
| independent explorers/reviewers | shared checkout, read-only intent |
| one bounded writer | shared checkout |
| multiple independent writers | isolated worktrees when supported |
| overlapping writers | serialize |

The short rule is:

> **Subagents for parallel cognition. Worktrees for parallel mutation.**

Before parallel writers start, verify disjoint ownership, no shared migration state, no hidden generated-file conflicts, and no acceptance dependency. A worktree prevents filesystem collisions but does not make semantically overlapping changes safe.

## Risk gate

Classify R0-R4. Default economy policy recommends independent frontier/specialist review at R3+. Lowering an automatically high risk should include a reason.

## Acceptance rule

Every worker needs checks another agent can run. Prefer compiler/type checker, focused tests, integration tests, schema/migration validation, lint/static analysis, and CI before model review.

## Correction rule

Send a correction only for a concrete defect. Include failed check/finding, expected result, allowed paths, relevant invariant, and unchanged decisions. Do not resend the full transcript.

## Escalation rule

Default ladder: efficient/xhigh -> balanced/medium -> frontier/low -> frontier/medium. Higher frontier effort requires explicit justification or benchmark evidence.

## External actions

The skill never infers permission for consequential external actions. User authorization must be clear at the action boundary.

## Privacy

Do not place credentials, raw private data, environment values, or full sensitive logs into packets, ledgers, prompts, issues, commits, or benchmark fixtures.

## Recovery

Stop on quota exhaustion, authentication errors, unknown writer state, session drift, unsafe path changes, or ambiguous evidence. Do not create a new task ID or child merely to bypass a stopped retry counter.

## Measurement

Compare total work, corrections, defects, wall time, and final correctness against matched baselines before changing economic defaults. For v0.5, benchmark at least these three shapes: single Codex, native Codex multi-agent, and native Codex multi-agent with Durable Threads policy.
