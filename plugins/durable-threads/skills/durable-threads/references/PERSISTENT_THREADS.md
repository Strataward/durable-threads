# Persistent thread lifecycle

## What durable means

Durable Threads preserves stable worker identity, provider, provider session ID, task status, compact evidence, and usage counters when available. It does not promise provider-process recovery after quota failure, crash, or unknown writer state.

## Why persistence matters

A useful persistent worker can retain provider-local context without forcing the planner to replay a large transcript. Persistence is economically useful only while retained context remains relevant.

## Resolve

1. List current provider tasks/sessions.
2. Match exact worker title and provider.
3. Confirm project directory and idle/finished state.
4. Confirm worker purpose matches the new packet.
5. Reuse the session if retained context is still useful.
6. Ask before creating a new provider task when policy requires authorization.

Never treat a similar title as the same worker.

## Send

Send one bounded packet with a new run ID for new work. Include objective, risk, frozen decisions, invariants, non-goals, allowed paths, acceptance, constraints, and result contract. Do not send the planner transcript.

## Wait

The orchestrator should sleep while the worker runs. Use event-driven completion when available. Avoid short repeated timeouts that re-enter the parent model with unchanged state. Do not repeatedly read transcripts to discover nothing changed.

## Resume

Resume for a focused correction only when provider metadata is valid, resume is supported, the failure is concrete, and the correction count remains within policy. Identify the failed check and invariant; do not resend the entire original packet unless material facts changed.

## New objective vs correction

A distinct objective can reuse an idle worker with a new task record. A retry repairs the same acceptance failure. Do not rotate IDs to bypass retry policy.

## Recovery states

| State | Action |
| --- | --- |
| idle/finished | send new bounded objective |
| active writer | wait for material state change |
| usage limit | record stop; wait for reset or declared fallback |
| missing provider metadata | do not resume blindly |
| provider failure | classify before retry |
| unknown status | inspect once, then stop writes until resolved |

## Retirement

Retire or archive a worker only when requested or when roster policy defines retirement. Preserve redacted ledger history so routing evaluations remain auditable.
