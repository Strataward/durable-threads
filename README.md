# Durable Threads

[![CI](https://github.com/Strataward/durable-threads/actions/workflows/ci.yml/badge.svg)](https://github.com/Strataward/durable-threads/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache-2.0-blue.svg)](LICENSE)

**Useful frontier work. Bounded execution. Evidence before acceptance.**

Durable Threads is a risk- and allowance-aware policy layer for coding-agent runtimes. The Codex plugin is the product; the TypeScript self-host plane and Python helper are optional. The native skill guides behavior. It does not replace Codex's sandbox, enforce account quotas, or provide a hosted service.

## Install and work

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Start a new session and ask for bounded work:

```text
Use Durable Threads. Fix refresh-token rotation in src/auth and tests/auth.
Preserve the existing public API. Run focused tests and typecheck.
Require independent security review before acceptance.
```

No roster, extra model provider, Node installation, Jev key or Temporal server is required for this workflow.

## Astra-first value on Pro 5x

Ask:

```text
Use Durable Threads' Astra-first Pro 5x profile. Keep Astra and standard speed.
Preserve my working reasoning setting; trial lower effort only on bounded work.
Use one active writer and at most one justified helper. Batch independent reads,
keep logs bounded, run required checks once per relevant code state, and stop
when acceptance passes. Do not silently switch models, billing, or approvals.
```

The profile prioritizes fewer unnecessary model responses and less irrelevant context, rather than indiscriminately reducing reasoning. High effort can be economical when it avoids repeated mistakes. Required checks and independent R3/R4 review remain mandatory.

See [the Pro 5x profile](plugins/durable-threads/skills/durable-threads/references/PRO5.md) and [the dated audit and validation plan](docs/PRO5_OPTIMIZATION.md).

Optional local diagnostics require Node 20+. From this checkout:

```bash
node plugins/durable-threads/skills/durable-threads/scripts/pro5.mjs probe
node plugins/durable-threads/skills/durable-threads/scripts/pro5.mjs audit /explicit/path/to/rollout.jsonl
```

The probe reads Codex account/model/feature metadata without requesting a model turn or changing config. The audit reads only selected files and avoids double-counting cumulative usage. Neither establishes the user's plan multiplier, proves exact billing, or provides live per-step control. No measured subscription-extension multiplier is claimed.

## Operating policy

Keep the current task as planner and integrator. Delegate only when startup, context, correction and review costs are justified. Prefer native `explorer` for focused reading, `worker` for bounded implementation, and read-only independent reviewers when needed.

Freeze the objective, decisions, invariants, non-goals, allowed paths and acceptance checks before delegation. A worker should not rediscover the architecture or receive an entire transcript for a narrow question.

Use native wait/resume rather than repeated model polling. Batch independent reads and checks; do not batch dependent mutations. Inspect the actual diff and run required tests once per relevant code state. A reported test result is a claim until tied to execution evidence. Stop after target acceptance rather than launching speculative improvement loops.

| Risk | Consequence | Acceptance policy |
| --- | --- | --- |
| R0 | Mechanical changes | Focused deterministic checks |
| R1 | Bounded feature/bug | Scoped checks and diff inspection |
| R2 | Cross-component contracts | Integration/contract coverage |
| R3 | Auth, privacy, payments, destructive data, concurrency | Independent specialist/frontier review |
| R4 | Systemic architecture or recovery | Explicit approval and independent review |

**Subagents for parallel cognition. Worktrees for parallel mutation.** Multiple writers need disjoint ownership and actual isolation; overlapping changes must be serialized. A worktree alone does not make changes semantically independent.

Preserve an explicitly chosen model. Use live catalog slugs and advertised reasoning levels. The optional hybrid economy strategy is an alternative, not a silent downgrade from Astra. Quota pressure should pause or narrow work, not remove safety gates.

## Optional control plane and Python helper

[Self-host the TypeScript control plane](docs/SAAS.md) for localhost Temporal, human gates and a UI. There is no public sign-up deployment. Python remains an optional helper and CLI durable-mode path until TypeScript parity; it is not on PyPI:

```bash
python3 -m pip install -e '.[dev]'
# Optional Jev and Temporal dependencies:
python3 -m pip install -e '.[durable]'
```

[Temporal + Jev](docs/TEMPORAL_JEV.md) provide optional orchestration and typed decisions. They are not required to extend useful native Astra work. Jev is separately billed/configured. Temporal cannot stop a nested agent's internal polling without a runtime integration, and heartbeats are not a complete decision ledger.

The hosted/self-host experimental runtime and native policy are distinct. Read [the audit's remaining hardening requirements](docs/PRO5_OPTIMIZATION.md) before treating either as production enforcement.

## Documentation

- [Installation and updates](docs/INSTALLATION.md)
- [Native multi-agent integration](docs/NATIVE_MULTI_AGENT.md)
- [Customization](docs/CUSTOMIZATION.md)
- [OpenAI compatibility](docs/OPENAI_COMPATIBILITY.md)
- [Architecture](plugins/durable-threads/skills/durable-threads/references/ARCHITECTURE.md)
- [Model economics](plugins/durable-threads/skills/durable-threads/references/MODEL_ECONOMICS.md)
- [Astra guide](plugins/durable-threads/skills/durable-threads/references/ASTRA.md)
- [Packet contract](plugins/durable-threads/skills/durable-threads/references/PACKET_CONTRACT.md)
- [Provider adapters](plugins/durable-threads/skills/durable-threads/references/PROVIDERS.md)
- [Benchmarking](plugins/durable-threads/skills/durable-threads/references/BENCHMARKING.md)
- [Durable overhead benchmark](docs/benchmarks/2026-09-19-durable-mode-overhead.md)
- [ADR: TypeScript control plane](docs/adr/0002-typescript-saas.md)

## Development

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
ruff check .
python3 -m compileall -q src scripts
python3 scripts/validate_repo.py
npm install
npm test
npm run typecheck
node --test tests/pro5_checks.mjs
```

Durable Threads is alpha software. Product capabilities and limits change; use dated official documentation and runtime probes, not stale model assumptions. This is an optimization policy and diagnostic toolset, not a rate-limit bypass or a guarantee of more hours.

## License

Apache-2.0.
