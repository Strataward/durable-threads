# Astra-first Pro 5x: audit and optimization

Audit date: 2026-09-22. Source baseline: `3310f8ecf510c4293cb904a50b648452ce40f298`.

## Goal and boundaries

Maximize accepted engineering work using an existing ChatGPT Pro 5x allowance, with Astra explicitly preferred. This is not a claim that a subscription grants API/Jev credits, that a fixed number of tokens maps to a quota percentage, or that a particular savings multiplier has been measured.

The native plugin remains the default product. No extra orchestrator is needed to apply bounded contracts, fewer no-op calls, narrower context, explicit stop conditions and evidence-based effort selection. Installation does not change the user's config or enable experimental features.

## Findings addressed in this change

| Finding | Change |
| --- | --- |
| Native instructions encouraged efficient high/XHigh by default, even when the user wanted Astra | Preserve explicit Astra selection; separate Astra-first and optional hybrid economics |
| Parallel read-only work was encouraged freely up to runtime limits | Start with one useful helper, include startup/context/review costs, avoid speculative races |
| Large instruction sets and repeated full audits can amplify context | Shorten the entry skill and read advanced references on demand; scope each milestone and stop after acceptance |
| Model parser accepted `models` but not real App Server `data` | Parse JSON-RPC result/data, retain legacy arrays/models, use request slug, preserve advertised effort metadata |
| Partial catalogs and ambiguous aliases could lead to wrong selection | Explicit pagination and repeated-cursor bounds; reject ambiguous aliases and explicit missing models |
| Subscription usage was easy to confuse with cumulative token events | Local streaming auditor counts only per-response receipts and deduplicates response identity |
| Unknown/stale quota and plan labels invite fabricated allowances | Report unknown, inspect actual windows, do not infer 5x from `pro`, do not assume past reset means refreshed quota |
| Speculative live controls could be mistaken for working integration | Metadata-only probe always reports live control unverified; offline adviser cannot mutate execution |

## Native diagnostics

From the repository checkout:

```bash
node plugins/durable-threads/skills/durable-threads/scripts/pro5.mjs probe
node plugins/durable-threads/skills/durable-threads/scripts/pro5.mjs audit /explicit/path/to/selected-rollout.jsonl
```

`probe` launches the installed local `codex app-server` over stdio. Only `initialize`, `account/read` with `refreshToken:false`, `account/rateLimits/read`, `model/list` and `experimentalFeature/list` are requested. The client sends the `initialized` notification, pages boundedly and rejects unexpected server requests. Optional unsupported metadata methods are reported. It does not request a model turn, write config, start tools, change login or consume reset credits. Raw stderr/server errors and personal account fields are not echoed.

A model appearing in the catalog is not proof of current capacity or of experimental step-control compatibility. The probe sees one local Codex installation, not necessarily the binary bundled with Desktop. It displays available allowance buckets; select the relevant model bucket when reasoning about a model-specific restriction.

`audit` accepts explicitly selected JSONL files only. It handles the source-observed top-level `token_usage_record` / `payload.usage` shape. Response IDs are deduplicated within thread identity but not printed. Equal counts from different responses are retained. `thread_token_usage`, `turn_token_usage`, legacy cumulative `token_count`, and nested compaction copies are not added to the totals. Reasoning stays a subset of output. Missing optional metrics are marked. A final non-newline-terminated fragment is ignored and flagged because the file may have an active writer. Limits: 256 MiB total input and 4 MiB per line. Unsupported formats are explicitly incomplete, not a zero-cost session.

Do not upload original rollouts to diagnose usage; they can contain private code. The auditor's aggregate output excludes transcript content and identities. It is not a full privacy sanitizer for the original files.

## Offline adviser

The adviser runs deterministic code only. It does not invoke Jev or Astra, and it is not attached to Codex events. A caller must provide current observations, derive evidence checkpoints and deliberately apply any recommendation at a safe boundary. It must not be advertised as a hard account-level circuit breaker.

Example state fields (timestamps must be current epoch seconds):

```json
{
  "authMode": "chatgpt",
  "writerState": "known",
  "risk": "R1",
  "phase": "implement",
  "currentEffort": "medium",
  "allowEffortReduction": false,
  "supportedEfforts": ["low", "medium", "high"],
  "generations": 3,
  "noProgressGenerations": 0,
  "repeatedFailures": 0,
  "elapsedSeconds": 45,
  "stepsSinceChange": 2,
  "resolvedCheckpoints": 2,
  "observedAt": 0,
  "rateLimits": {}
}
```

Save a state file deliberately, replace the zero timestamp and empty rate-limit payload with actual observations, then run:

```bash
node plugins/durable-threads/skills/durable-threads/scripts/pro5.mjs advise /path/to/state.json
```

The example intentionally requests a quota refresh rather than pretending an account has allowance. Rate-limit input follows the documented `account/rateLimits/read` response. Never synthesize fresh observations from a stale probe. The supplied effort list must come from the selected model, not the example.

Trial limits: 60 generations, 30 minutes, four no-progress generations, two repeated failures and a 10% reserve. These are deliberately bounded DT experiment defaults in the script, not published Pro limits or an optimal universal allocation. Split genuine milestones rather than resetting identifiers to evade a stop. Required checks, scope evidence and independent review take precedence over completion claims. Human approval cannot replace a failed check. Effort reduction requires `allowEffortReduction: true`. Keep it false unless the user authorizes a trial. A two-step/two-checkpoint cooldown limits repeated changes.

## Corrections to earlier architecture claims

`turn/settings/update` is an experimental harness mechanism. An `Applied` receipt means publication for future captures, not proof that a particular next inference used it. A patch may remain effective for the rest of the active turn. A post-tool observer can lose the race to the next settings capture. A reliable controller needs an owned barrier, serialized updates, actual effective-settings receipts and compatibility tests on the installed build. The diagnostic does not implement this controller.

Model-side `configuration_update` is a different capability. Do not inject it into unsupported providers, assume cache savings from toggling a flag, or bypass documented mode restrictions. Use matched live benchmarks.

`approvalsReviewer` is tool-authorization routing, not independent code review. App Server `process/*` runs outside Codex's sandbox. Neither is a cost optimization shortcut. Temporal Activities can perform nondeterministic I/O, but heartbeats carry liveness/recovery details and may be throttled; they do not preserve every decision as an append-only audit trail.

## Remaining self-host hardening requirements

These are audit findings, not fixed or certified by the native profile:

1. `apps/api/src/local-runtime.ts` accepts `result.accepted` before combining the task's independent-review requirement. Its human-review branch can report completion on approval without requiring passing verification. The TypeScript and Python Temporal workflows now preserve task review and require verification before completion. The local API runtime still needs the same protection before production use.
2. Existing worker-reported check strings plus Git-path validation do not prove the checks ran successfully. Add trusted command receipts tied to a workspace revision and target acceptance, then invalidate them after relevant mutations.
3. Some durable routing paths collapse executor identity into provider identity, and generic effort ladders do not consult model capabilities. Wire the new catalog resolver into each runtime before claiming live provider-neutral escalation.
4. A durable wrapper around a long-running CLI does not by itself provide deduplicated side effects, safe reattachment, process-tree cancellation or workspace fencing. Test crash-after-side-effect and unknown-writer recovery explicitly.
5. Jev probabilities are not calibrated acceptance probabilities. Validate response schemas and boundary timeouts, record score provenance, and benchmark whether an external decision call actually saves total work.

For Pro 5x native usage, keep these optional runtimes out of the critical path until those tests exist. Adding a speculative nine-epic control plane would increase complexity without proving more usable allowance.

## Validation and rollout

Local validation covers the dependency-free Node diagnostic with a simulated stdio server, adversarial quota inputs, pagination, stale/unknown state, hysteresis, acceptance guards, bounded log reads, deduplication and partial-file reporting. The TypeScript catalog is compiled independently; the repository CI runs its new tests with the full existing package suite. Neither is a live Astra inference or subscription benchmark.

Begin with matched representative tasks at the same base commit: a bounded fix, an integration change and a security-sensitive change. Keep required checks identical. Compare existing settings against the new native policy, then optional permitted hybrid execution. Record final acceptance, regressions found on review, correction rounds, total elapsed time, all observed internal responses and account-window movement. Include separate child logs and compaction/warmup telemetry where available; mark anything missing.

Do not claim a quota-extension factor from one integer percentage change, mocked tasks, prompt length, or API token prices. Increase rollout only when quality holds and total accepted-work cost improves.

## Sources

- https://learn.chatgpt.com/docs/pricing
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://learn.chatgpt.com/docs/app-server
- https://developers.openai.com/api/docs/guides/latest-model
- https://github.com/openai/codex/blob/286d4ecf44b4e9daba0a9fdd229a4047b770a71a/codex-rs/protocol/src/protocol.rs
- https://github.com/openai/codex/issues/38111
- https://github.com/openai/codex/issues/42080
- https://github.com/openai/codex/issues/13733

Issue reports are design inputs, not authoritative billing facts or proof of general failure rates.
