# Astra operating guide

Astra is a scarce frontier resource in the Durable Threads economy profile. Use it where additional reasoning changes an important decision, not as the default long-running executor.

This guide describes role policy. It does not promise that any account or runtime has Astra.

## Availability

Check the live Codex catalog and current account allowance before selection. Use the exact model ID returned by the runtime. If Astra is absent, report that fact and use the declared fallback. Never guess a versioned slug.

## Preferred Astra roles

Use Astra for complex architecture planning, decomposition where incorrect parallelism would cause rework, resolving contradictory requirements, reviewing R3/R4 security/privacy/migration/production changes, deciding whether repeated worker failure means the implementation or plan is wrong, and final integration review when blast radius is broad.

Do not use Astra merely to wait for workers, poll status, apply routine code changes, rerun known checks, format code, or review every small edit.

## Reasoning effort

Economy profile:

- `low`: default frontier planner or narrow frontier review;
- `medium`: difficult architecture or R3/R4 review;
- `high`: exceptional tasks with demonstrated value;
- `xhigh`/`max`: benchmarked or pathological cases only.

Higher effort is not automatically better. It can increase latency, exploration, and allowance consumption.

## Astra + workhorse pattern

```text
Astra Low/Medium
  architecture + acceptance
        ↓
freeze decisions
        ↓
efficient XHigh workhorse
  implementation + local checks
        ↓
deterministic verification
        ↓
risk gate
        ↓
Astra only when review threshold is met
```

## Sleeping orchestrator

An Astra parent must not burn turns monitoring workers. Dispatch, then use event-driven/bounded waiting without repeated parent resampling. Wake Astra only when material evidence requires a decision.

Related Codex reports:

- https://github.com/openai/codex/issues/35108
- https://github.com/openai/codex/issues/41875

## Context

Do not transfer full old transcripts into a new Astra call. Provide the current objective, frozen decisions, invariants, relevant paths, acceptance evidence, and the one unresolved decision Astra must make.

## Current OpenAI references

- https://help.openai.com/en/articles/20001516
- https://developers.openai.com/api/docs/models
- https://developers.openai.com/api/docs/guides/latest-model

See `MODEL_ECONOMICS.md` for the broader provider-neutral policy.
