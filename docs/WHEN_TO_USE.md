# When to Use Durable Threads

Durable Threads adds value when you need **risk-aware decision making, deterministic verification, and economical model usage** without building orchestration yourself. Use it when delegation adds genuine benefit — keep self-contained, well-contextualized work in-task when possible.

## Reach for Durable Threads when:

### 1. You need risk-aware risk classification (R0–R4)
- **R0 (mechanical)**: docs, formatting, typos, narrow renames — use native Codex checks instead
- **R1 (bounded)**: isolated feature or bug fix — Durable Threads provides deterministic checks (tests, typecheck, linter) rather than expensive review
- **R2 (integration)**: API contracts, queues, webhooks, caches — add integration review when contracts, external boundaries, or schemas change
- **R3 (critical)**: auth, payments, privacy, destructive migration, concurrency — Durable Threads requires independent specialist/frontier review by default
- **R4 (systemic)**: distributed architecture, control plane, recovery design — frontier/specialist review mandatory

### 2. You want economical model selection
- **Bounded implementation/debugging**: efficient model + high/XHigh reasoning
- **Read-heavy exploration**: efficient or balanced at low/medium effort unless the question is unusually hard
- **Difficult general planning**: balanced model + medium reasoning
- **Consequential planning/review**: frontier model + low or medium reasoning
- **Higher frontier effort**: only when the task or measured results justify it

### 3. You need deterministic verification before human review
- Inspect the actual diff and prefer tests, type checks, linters, static analysis, schema checks, migration checks, and CI before asking another model for an opinion
- A child result is evidence, not acceptance. The planner still inspects the diff and reruns integration- or security-relevant checks

### 4. You want safe parallelism without building orchestration
- **Parallel explorers/reviewers**: safe when independent and read-only — free within the runtime's configured concurrency limit
- **One bounded writer**: shared checkout is fine
- **Multiple independent writers**: prefer isolated worktrees when the runtime supports them — give each worker explicit file/module ownership and integrate centrally after verification
- **Overlapping writers**: serialize. Worktrees prevent filesystem collisions but do not make semantically overlapping changes safe

**Core invariant**: Subagents for parallel cognition. Worktrees for parallel mutation.

### 5. You want evidence-gated escalation
- **Failed check, violated invariant, repeated conceptual error, unresolved ambiguity, or elevated risk** can justify a stronger model
- **Do not escalate based on prestige alone** — escalation must be supported by evidence

### 6. You want to avoid premature configuration
- **Do not ask a new user to configure workers or JSON before starting**. Native Codex roles plus the defaults above are sufficient for ordinary work
- Read advanced references only as needed

## When NOT to reach for Durable Threads

| Situation | Better alternative |
| --- | --- |
| trivial docs/formatting/typo | Native Codex `--check-spelling` or similar |
| isolated feature with clear boundaries | Direct Codex task with no delegation needed |
| work that fits in a single Codex session | Keep it in-task; no delegation needed |
| you just need model-IDs pinned | Use the runtime's live model discovery instead |
| you want a hosted sign-up product | None exists in this repository |

## Quick decision framework

```text
Is the work?
  ✓ self-contained, well-contextualized → keep in task
  ✓ needs narrower context or parallel reads → consider delegation
  ✓ R3/R4 risk → plan for specialist review
  ✓ needs economical model usage → use efficient models + high reasoning
  ✓ needs deterministic verification → run tests/linters/CI first
  ✓ needs evidence-gated escalation → plan for escalation from evidence
```

Start at Level 0 (plugin + native roles). Add policy only when it solves a real problem you encounter.