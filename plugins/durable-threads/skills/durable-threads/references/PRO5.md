# Astra-first Pro 5x profile

Audited 2026-09-22. These are Durable Threads experiment defaults, not OpenAI rate limits or a promise of additional hours. Keep an existing successful baseline until matched tasks show an improvement.

## Start with less overhead, not less acceptance

Use ChatGPT sign-in and standard speed. Keep the explicitly selected Astra model in one relevant thread. Do not require another provider, paid API key, Temporal, or Jev for ordinary native work. Use one active writer. Add one bounded helper only when independence, context reduction, or critical review justifies the total handoff cost.

Start normal work at the current proven effort, often medium. Trial low for mechanical or well-bounded work once key decisions are resolved. Use medium for ambiguity or integration reasoning; high for a demonstrated conceptual failure or unresolved critical issue. XHigh/max stays an explicit experiment. Do not change settings before an exact next inference unless the runtime actually provides and verifies that boundary.

Standard speed is the default recommendation because OpenAI documents faster included-allowance consumption for Fast mode. Pro has 5x and 20x variants. Message ranges are estimates, not fixed quotas. Local/cloud and related agentic products can share allowance. Check all relevant windows through `/status` or the usage dashboard; API token prices are not an entitlement calculator.

Sources: https://learn.chatgpt.com/docs/pricing and https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan

## Practical work unit

Give one objective, current decisions, bounded paths, non-goals and named acceptance checks. Read focused file ranges. Batch independent discovery/checks, cap output, and preserve exact error details. Keep the full logs outside the prompt. Avoid broad repository rereads after every correction.

Complete one coherent acceptance milestone, run the required checks, then stop. Do not demand ten speculative improvements or repeated full audits in the same task. For a genuinely unrelated milestone, hand off a compact context capsule rather than growing an indefinitely stale transcript. Do not compact on every turn; compare a checkpoint/new-thread cost with the next useful work.

If a build is merely running, use the existing native wait/event mechanism. Another model inference is not a process scheduler. Never hide a failed check, skip required review, or approve unsafe tools to save quota.

## Local diagnostics bundled with this skill

Requires Node 20+ for diagnostics only. The skill itself requires no Node installation. In this skill's directory:

```bash
node scripts/pro5.mjs probe
node scripts/pro5.mjs audit /explicit/path/to/selected-rollout.jsonl
```

The probe starts a local Codex App Server subprocess and requests metadata only: initialization, account, rate limits, models and experimental feature flags. It does not request a thread, model turn, tool execution, config write or quota reset. It does not print email, credentials, raw config or transcripts. It cannot prove a 5x multiplier from `planType: pro`, or prove live step control from a feature flag. Inspect the billing UI to confirm the plan variant.

The audit streams only the files explicitly named. It counts top-level completed-response usage records, deduplicates by response identity, and ignores cumulative totals and nested compaction mirrors. Reasoning is a subset of output, not an additional charge. Missing, invalid, conflicting, oversized and partial data are reported. Warmups, compactions, children, other sessions and other products may be absent: the result is not the bill or remaining allowance.

The optional `advise <state.json>` command is an offline recommendation, not an attached controller. Its trial caps are 60 observed generations, 30 minutes, four no-progress generations, two repeated failures, and a 10% quota reserve. Two resolved checkpoints and two steps at the current setting are needed before an ordinary downshift. These thresholds are adjustable design assumptions, not measured optimal settings. See the repository's `docs/PRO5_OPTIMIZATION.md` for the explicit state contract.

Do not install a second copy of this skill. Do not enable broad hooks that rerun the probe or reread all logs on every tool call.

## Experimental features are not the default optimization

Codex active-turn settings and model-side reasoning configuration updates are distinct. Publishing a patch does not prove the next inference used it. Updates may persist across the remainder of a turn, and already captured steps are unchanged. Do not claim a one-step override or exact timing without an owned pause boundary and effective-settings receipt.

Keep approval/reviewer authority separate from effort. `approvalsReviewer` routes tool authorization; it is not an independent code-review result. Never auto-relax it for economics. Likewise, do not use App Server `process/*` as a sandbox replacement: its processes are outside the Codex sandbox.

Sources: https://learn.chatgpt.com/docs/app-server and https://developers.openai.com/api/docs/guides/latest-model

## Measure before promising savings

Compare the same tasks, base revisions and acceptance checks under existing settings versus Astra-first bounded work. Capture total corrections, independent review, internal responses, elapsed time, uncached/cached input, output/reasoning and actual account-window changes. Separate warmup/compaction overhead when observable. Reject a policy that saves apparent tokens by failing more tasks.

Primary objective: more accepted work per measured allowance. Do not extrapolate a token percentage into "2x longer", and do not equate a feature flag, synthetic test, or import smoke test with a live account benchmark.
