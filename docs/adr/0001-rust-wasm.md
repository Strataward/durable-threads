# ADR 0001: Should Durable Threads move to Rust or WebAssembly?

Date: 2026-09-19
Status: Accepted
Evidence: [Durable mode overhead benchmark](../benchmarks/2026-09-19-durable-mode-overhead.md)

## Context

Durable Threads is a Python package. The question was whether a
higher-performance language (Rust) or a portable sandbox (WebAssembly) would
make it a faster or better harness.

A harness run has four cost layers. The benchmark measured each one in
isolation with the deterministic `scripted` executor so nothing is guessed.

| Layer | Where the time goes | Measured cost per task |
|---|---|---|
| Deterministic policy (Python) | risk classification, routing, evidence validation, gating | < 1 ms total (each primitive 7-90 µs) |
| Jev decisions (network) | two closed-answer calls per attempt | ~130 ms per decision |
| Temporal orchestration (network + dispatch) | parent + child workflow, 26 history events | 0.15-0.5 s |
| Provider execution (subprocess) | Codex, Claude Code, Cursor, Grok | seconds to minutes |

Rust or WASM can only shrink the first row. The other three are I/O waits on
services and processes that a different language does not change.

## Decision

Stay on Python for the harness, the Temporal workflows, and the Jev client.

Do not start a Rust or WebAssembly port now. Re-open this decision only when
one of the triggers below is measured, not assumed.

## Reasons

1. **The Python hot path is already below the noise floor.** The complete
   deterministic policy layer costs under one millisecond. Temporal dispatch is
   about three orders of magnitude larger; a real coding-agent run is about six.
   A perfect Rust port that made the policy layer free would change end-to-end
   latency by less than 0.2 %.
2. **Temporal workflows must stay in one SDK.** Workflow code and activities
   share dataclass contracts, replay semantics, and the worker process. Splitting
   the workflow into Rust would need a second SDK, a second worker, and a
   cross-language contract boundary that Temporal replays deterministically.
   That adds risk in the one place the project exists to reduce risk.
3. **Jev's SDK is Python-first.** `typesafe-sdk` is the supported client. A Rust
   client would be an unsupported reimplementation of an evolving API.
4. **Provider adapters are subprocess drivers.** They spawn `codex`, `claude`,
   `cursor-agent`, and `grok` CLIs and parse their output. Process spawn and
   agent runtime dominate; the parsing is microseconds.
5. **The extension surface is Python entry points.** Third-party executors and
   decision engines plug in through `durable_threads.executors` entry points.
   Moving the core would break every plugin for no measured gain.

## What would change the decision

Re-run `scripts/bench_primitives.py` and `scripts/bench_durable.py` first. Then
consider a targeted change if any of these hold:

- **Rust for a hot primitive.** A deterministic primitive exceeds ~10 ms per
  call at production task shapes (for example evidence validation over tens of
  thousands of changed paths, or risk classification over very large
  objectives). Port only that primitive as a PyO3 module behind the same Python
  function signature. Keep workflows, activities, and adapters in Python.
- **WebAssembly for sandboxed third-party plugins.** A requirement appears to
  run untrusted executor or decision plugins with no filesystem or network
  access. WASM (for example via `wasmtime`) is the right tool for that
  isolation. It is a security feature, not a performance one.
- **WebAssembly for portability.** A requirement appears to run the policy
  layer inside a browser, an edge runtime, or a non-Python host. Port the
  deterministic layer only; it has no I/O and is small.
- **Temporal cost becomes the bottleneck.** If the 0.15-0.5 s per task matters,
  the fixes are Temporal-side, not language-side: fewer history events, a
  co-located worker, a lower `sticky_queue_schedule_to_start_timeout`, or
  batching decisions. None of these require leaving Python.

## Consequences

- No rewrite work is scheduled. Effort goes to richer evidence, provider
  adapters, and Temporal operations instead.
- The two benchmark scripts are the regression guard for this decision. Run
  them when the policy layer changes shape.
- This ADR must be revisited if a trigger above is hit, with the new numbers
  attached.
