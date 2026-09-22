# Durable Threads

[![CI](https://github.com/Strataward/durable-threads/actions/workflows/ci.yml/badge.svg)](https://github.com/Strataward/durable-threads/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache-2.0-blue.svg)](LICENSE)

**Useful frontier work. Bounded execution. Evidence before acceptance.**

Durable Threads is a Codex plugin that helps coding agents keep work in scope, choose useful handoffs, and check results. Install the plugin to use the core workflow. The Python helper and self-hosted TypeScript runtime are optional.

## Install and work

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Start a new session and ask for bounded work:

```text
Use Durable Threads to fix the failing test.
Keep the change small. Run the relevant checks.
Report the changed files and any remaining concerns.
```

No roster, extra model provider, Node installation, Jev key or Temporal server is required for this workflow.

## When this helps

Use Durable Threads when a change needs clear scope, a useful handoff, or independent review. It gives each worker a small contract. It asks the planner to inspect the diff and verify the result before acceptance.

For a small edit, keep the work in the current task. You do not need to create an agent team.

A result should tell you:

- Which files changed.
- Which checks ran and what they found.
- Which requirements remain unverified.

## Optional allowance tools

You can use the plugin with your current model and settings. No Pro 5x profile is required.

For Astra-specific settings and local diagnostics, see [the optional allowance guide](docs/PRO5_OPTIMIZATION.md). These tools do not prove subscription savings.

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
