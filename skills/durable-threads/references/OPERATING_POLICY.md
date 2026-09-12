# Operating policy

## Default limits

- At most two selected workers and two parallel workers unless a roster raises the limits.
- At most one focused correction per worker by default.
- Result summaries below 2,000 characters unless more evidence is required.
- No hard goal token budget unless the user asks for one.
- Keep provider/session identity with every worker record.
- Keep Fast mode off when allowance longevity is the goal.
- Prefer `economy` strategy for constrained subscription usage.

## Sleeping orchestrator rule

When `strategy.sleepingOrchestrator` is enabled, the planner must not poll unchanged worker state in short loops. Dispatch and wake the planner on completion or material change. Repeated no-op wait timeouts are a routing failure because they spend control-plane capacity without producing evidence.

## Decision/execution separation

The planner owns architecture, risk, scope, and integration. A workhorse owns bounded implementation. Resolve architecture ambiguity before dispatch; conversely, do not keep a frontier planner in the execution loop merely because it authored the plan.

## Fan-out

Fan out only independent work. Verify no overlapping writes, shared migration state, hidden generated-file conflicts, or acceptance dependencies. If uncertain, serialize.

## Risk gate

Classify R0–R4. Default economy policy recommends frontier review at R3+. Lowering an automatically high risk should include a reason.

## Acceptance rule

Every worker needs checks another agent can run. Prefer compiler/type checker, focused tests, integration tests, schema/migration validation, lint/static analysis, and CI before model review.

## Correction rule

Send a correction only for a concrete defect. Include failed check/finding, expected result, allowed paths, relevant invariant, and unchanged decisions. Do not resend the full transcript.

## Escalation rule

Default ladder: efficient/xhigh → balanced/medium → frontier/low → frontier/medium. Higher frontier effort requires explicit justification or benchmark evidence.

## External actions

The skill never infers permission to push, merge, deploy, publish, create accounts, modify production, or change external systems. User authorization must be clear at the action boundary.

## Privacy

Do not place credentials, raw private data, environment values, or full sensitive logs into packets, ledgers, prompts, issues, commits, or benchmark fixtures.

## Recovery

Stop on quota exhaustion, authentication errors, unknown writer state, session drift, unsafe path changes, or ambiguous evidence. Do not create a new task ID solely to bypass a stopped retry counter.

## Measurement

Record provider usage where available. Compare total work, corrections, defects, wall time, and final correctness against matched baselines before changing economic defaults.
