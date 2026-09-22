# Model economics

Optimize accepted engineering work per measured allowance, including planning, startup, context, corrections, tools and review. Do not optimize token count at the expense of correctness.

## Select an explicit profile

**Astra-first / Pro 5x:** retain Astra when requested, including bounded implementation in a relevant existing thread. Reduce unnecessary inference, context, fan-out and repeated verification before switching models. See `PRO5.md`.

**Hybrid economy:** use an explicitly permitted efficient provider/model for a bounded contract when the expected saved execution cost exceeds startup, handoff, correction and review costs. A cheap worker is not automatically cheaper overall. Paid API or Jev usage is a separate budget and must be disclosed.

Neither profile assumes a fixed exchange rate between tokens and included subscription allowance. Live catalogs supply model names and effort support. Account observations supply usage; a generic `pro` label does not prove 5x or 20x.

## Reasoning allocation

Retain a working baseline when adopting the skill. Trial low effort for narrow, resolved work; medium for integration and ambiguity; high for evidence of a conceptual difficulty or critical unresolved finding. Higher effort may be the economical choice when it prevents repeated failed attempts. Do not make efficient high/XHigh, or frontier low, universal rules.

Downshift only after the hard question is resolved and multiple checkpoints support it. Keep a cooldown to avoid oscillation. Do not reduce required R3/R4 review when allowance is scarce. Pause, defer or narrow instead. Automatic model changes must not override an explicit user model preference.

## Eliminate avoidable work

Prefer one retained, relevant worker over repeated startups. Add a helper for a specific independent question, not a generic second opinion. Reuse a bounded contract rather than a full transcript. Parallel writers require actual isolation and disjoint ownership; parallel models are not a quota discount.

Wait through native lifecycle/events instead of repeatedly asking a model for status. Batch independent reads/checks, not dependent mutations. Limit logs in the prompt. Run each acceptance check once per relevant code state; repeat only after changes or new evidence. Stop after target acceptance rather than generating a new quality loop.

Keep Fast mode off when longevity matters. Large context is capacity, not a target. Retain useful context; checkpoint and start a fresh bounded task when old context is mostly irrelevant. Do not force compaction repeatedly without evidence that it helps.

## Separate layers and budgets

Native mode has no mandatory Jev or Temporal round-trips. Jev may help with ambiguous control decisions, but its scores need calibration against outcomes and it is not included in ChatGPT Pro. Deterministic counters and acceptance gates should not require another model.

Temporal can coordinate long-lived external work; it cannot prevent a nested Codex agent from polling internally without an actual runtime integration. Heartbeats are liveness/recovery checkpoints, not an append-only decision ledger. Durable decision receipts need dedicated persistence and idempotency.

## Measurement

Compare fixed settings, bounded Astra-first settings and permitted hybrid settings on matched task revisions with identical acceptance gates. Include correction/review costs. Record completed model responses rather than treating user-visible turns as generations. Keep cached input separate and do not double-count reasoning within output or cumulative usage mirrors.

Report coverage: unseen warmups, compactions, child sessions and unrelated account activity prevent exact attribution. Do not present simulated savings as measured quota extension. A successful mock protocol test verifies our client logic, not the user's installation or billing.

Audited 2026-09-22. Current sources:

- https://learn.chatgpt.com/docs/pricing
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://developers.openai.com/api/docs/guides/latest-model
- https://learn.chatgpt.com/docs/app-server

Product facts can change. The profile and governor thresholds are Durable Threads policy, not OpenAI guarantees.
