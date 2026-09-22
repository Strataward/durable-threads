# OpenAI compatibility and documentation audit

Last audited: **2026-09-22**. Native Pro 5x optimization scope; prior 2026-09-19 install/runtime research is retained in linked references. This document distinguishes official interfaces, source-observed experiments and Durable Threads policy.

## Plugin and native runtime

Durable Threads has one canonical skill under `plugins/durable-threads/skills/durable-threads/`. The plugin distributes that workflow and its optional resources/scripts. Do not add a separate skill install surface. The existing marketplace install remains:

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Update the Git marketplace snapshot before reinstalling an existing plugin:

```bash
codex plugin marketplace upgrade strataward && codex plugin add durable-threads@strataward
```

Native explorer/worker roles, configured custom reviewers and native wait/resume remain the preferred runtime. Model/effort and concurrency controls depend on the installed build and effective managed configuration. Worktree support is not evidence of semantic independence. The plugin cannot enforce the host sandbox by itself.

Sources:

- https://learn.chatgpt.com/docs/build-plugins
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs
- https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs
- https://github.com/openai/codex/blob/main/codex-rs/core/src/agent/role.rs

## Account and model metadata

The read-only native probe uses documented `account/read`, `account/rateLimits/read`, `model/list` and `experimentalFeature/list` methods after initialization. Catalogs are paginated. The real `model/list` response uses `result.data`; its `model` field is the request slug. Effort options are advertised per model. Unsupported or incomplete metadata must remain unknown rather than becoming an invented capability.

A `pro` label alone does not establish the 5x/20x multiplier. Current account-window signals are separate from cumulative model token totals and separately billed API usage. The diagnostic never changes account settings or consumes reset credits.

Source: https://learn.chatgpt.com/docs/app-server

## Experimental live control

Active-turn settings publication is distinct from future thread defaults and from model-side reasoning configuration updates. A feature flag or published update is not proof that a specific next generation captured it. Changes do not retroactively alter already captured steps. Exact boundary control needs runtime testing and receipts; it is not implemented by the native Pro5 diagnostic.

Approval reviewer selection is authorization routing, not a completed independent code review. `process/*` runs outside the Codex sandbox and must not be substituted for sandboxed execution to reduce overhead. Temporal heartbeats are not a per-step audit ledger.

Sources:

- https://learn.chatgpt.com/docs/app-server
- https://developers.openai.com/api/docs/guides/latest-model
- https://github.com/openai/codex/blob/main/codex-rs/core/src/session/step_activation.rs

## Durable Threads policy, not an OpenAI guarantee

The Astra-first profile, one-helper starting limit, phase-based effort experiments, risk classes, correction budget, reserve percentage and stopping thresholds are project choices. They require matched quality/cost evaluation. They do not establish a fixed subscription lifetime, a quota multiplier or an optimal reasoning level.

Keep a proven reasoning baseline; test low effort on bounded work rather than downgrading everything. Preserve explicit model selection and required acceptance/review gates. Do not enable Fast mode, extra providers or experimental controls without the user's intent.

Sources:

- https://learn.chatgpt.com/docs/pricing
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://developers.openai.com/api/docs/guides/latest-model

## Optional control planes

The TypeScript self-host plane and Python Temporal helper are not required by the plugin. Managed APIs and Jev have separate authentication/billing and must not be presented as included Pro resources. Read [the optimization audit](PRO5_OPTIMIZATION.md) for known self-host acceptance, provenance and recovery hardening needs before production deployment.

## Integration check on 2026-09-22

The installed Codex CLI exposes `plugin add` and `plugin marketplace`. The official plugin guide still supports bundled skills. The pricing page confirms the listed Standard rates. Credit estimates do not measure subscription allowance.

## Validation boundary

Run native offline tests, repository tests, TypeScript typecheck, Python lint/compile and packaging validation before merging. Verify the installed binary separately: mock protocol tests and source inspection cannot certify live Astra behavior or account savings. No public hosted deployment, public directory listing, global config modification or automatic feature enablement is claimed.
