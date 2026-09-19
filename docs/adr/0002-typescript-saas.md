# ADR 0002: TypeScript for the hosted SaaS control plane

Date: 2026-09-19
Status: Accepted
Supersedes: [ADR 0001](0001-rust-wasm.md)
Evidence: [Durable mode overhead benchmark](../benchmarks/2026-09-19-durable-mode-overhead.md)

## Context

ADR 0001 asked whether Rust or WebAssembly would make the Python harness
faster. The 2026-09-19 benchmark still answers that question: no.

| Layer | Where the time goes | Measured cost per task |
|---|---|---|
| Deterministic policy | risk classification, routing, evidence validation, gating | < 1 ms total (each primitive 7-90 µs) |
| Jev decisions | two closed-answer calls per attempt | ~130 ms per decision |
| Temporal orchestration | parent + child workflow, 26 history events | 0.15-0.5 s |
| Provider execution | coding-agent run | seconds to minutes |

A language change cannot shrink the last three rows. A perfect Rust port of
the policy layer would change end-to-end latency by less than 0.2 %.

The product shape changed. Durable Threads is adding a hosted SaaS control
plane: users sign in, submit work, watch agents, and approve human gates. The
UI is React. That is a portability and product-boundary trigger, not a CPU
trigger.

## Decision

Build the hosted control plane in TypeScript:

- `packages/policy` owns deterministic risk, routing, packets, evidence, and
  heuristic decisions.
- `packages/contracts` owns shared JSON types generated from the existing
  schemas.
- `apps/worker` owns Temporal workflows and activities.
- `apps/api` owns task submit, status, and human-gate signals.
- `apps/web` is the React UI.

Keep the Codex plugin and skill as markdown under
`plugins/durable-threads/skills/durable-threads/`. Do not add a second skill
install surface.

Deprecate the Python helper after the TypeScript surface reaches parity. Do
not rewrite Python because it is slow. It is not.

Do not use Rust as the application language. Revisit Rust only for a measured
hot primitive (greater than ~10 ms) or for a WASM sandbox for untrusted
plugins.

Do not use Go as the first hosted language. Use it later only if a dedicated
execution cluster measures Node worker cost as the bottleneck.

## Reasons

1. **React needs the same contracts as the worker.** Packet, risk, evidence,
   and gate state are the product. One TypeScript module avoids a parallel
   Python model on the UI.
2. **TypeSafe publishes a first-party JavaScript SDK.** Hosted Jev calls use
   `@typesafe-ai/sdk` or the same System One HTTP API. Rust would reimplement
   an evolving API.
3. **The Temporal TypeScript SDK is production-ready.** Workflows run in a V8
   isolate. Workflow definitions stay in one SDK. Mixed-language workflow
   types for the same task are out of scope.
4. **Hosted execution is I/O.** The load is in-flight agent jobs, Jev HTTP,
   and Temporal history, not CPU-bound classification.
5. **Local CLI adapters are not a multi-tenant runtime.** The hosted path
   uses headless HTTP executors and isolated sandboxes. It does not spawn
   `codex`, `claude`, `grok`, or `cursor` on the control-plane host.

## Consequences

- Native Codex plugin use stays zero-config and markdown-first.
- Durable mode on the hosted path is TypeScript + Temporal + Jev.
- The Python package remains for the existing CLI until parity, then it is
  deprecated.
- Postgres replaces the local JSON ledger on the hosted path.
- Primitive and durable-mode benches remain the performance regression
  guard. Language choice is not the first knob when latency rises.

## What would change this decision

- A deterministic primitive exceeds ~10 ms on production task shapes. Port
  only that function to Rust behind the same TypeScript signature.
- A measured Node worker-cost bottleneck at production concurrency. Split a
  Go execution cluster and keep React + policy types in TypeScript.
- A requirement to run untrusted third-party plugins with no filesystem or
  network. Use WASM isolation. That is a security feature, not a speed
  feature.
