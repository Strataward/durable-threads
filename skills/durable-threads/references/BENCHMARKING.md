# Benchmarking and telemetry

Durable Threads should change defaults only when matched evaluations show a better outcome.

## Primary question

For a given task class and risk class, which model/effort topology maximizes accepted correct work under the user's constraints?

## Minimum benchmark record

```json
{
  "taskClass": "implementation",
  "riskClass": "R2",
  "modelSelector": "efficient",
  "reasoningEffort": "xhigh",
  "inputTokens": 0,
  "cachedInputTokens": 0,
  "outputTokens": 0,
  "reasoningTokens": 0,
  "wallTimeSeconds": 0,
  "followups": 0,
  "firstPassAcceptance": false,
  "deterministicFailures": 0,
  "reviewDefects": 0,
  "finalAcceptance": false
}
```

Unknown provider usage stays unknown. Do not replace missing telemetry with estimates in measured results.

## Matched comparison

Compare direct retained-session baseline, fresh single-agent baseline when testing context reuse, Durable Threads economy route, and frontier-heavy route when testing whether frontier review materially improves correctness. Use the same repository state, objective, acceptance checks, and paths.

## Metrics

Correctness: first-pass acceptance, final acceptance, independent review defects, post-integration regressions, severity-weighted defects.

Economic cost: provider counters, subscription allowance movement when observable, model turns, parent turns, no-op polling turns, repeated context volume.

Operational cost: wall time, human interventions, follow-ups, corrections, merge conflicts, blocked/unknown provider states.

## Avoid misleading claims

Do not claim that fewer packet characters equal token savings, persistence always saves context, parallelism always increases throughput, a lower-cost model remains cheaper after unmeasured rework, or a single community telemetry run establishes provider-wide quota semantics.

## Empirical routing roadmap

A future router can learn from task class, risk class, language/framework, model selector, effort, acceptance outcome, corrections, and review defects. Any learned route should remain explainable and preserve explicit planner override.
