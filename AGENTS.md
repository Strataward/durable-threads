# Repository instructions

## Scope

Durable Threads is the public Codex plugin. The bundled `durable-threads` skill is the canonical workflow.

Canonical source: `plugins/durable-threads/skills/durable-threads/`. Do not add a second skill install surface.

The Python helper and provider adapters are optional. The TypeScript tree (`apps/*`, `packages/*`) is the public self-host control plane.

Hosted and customer-deploy work does not belong in this repository. Do not copy private deploy or customer secrets into this repository.

## Key paths

| Path | Role |
|---|---|
| `plugins/durable-threads/` | Installable Codex plugin |
| `plugins/durable-threads/skills/durable-threads/` | Canonical skill and references |
| `.agents/plugins/marketplace.json` | Marketplace entry for this plugin |
| `src/` | Optional Python helper |
| `docs/` | Install, native agents, Temporal, self-host, compatibility |
| `apps/api`, `apps/worker`, `apps/web` | Public self-host TypeScript plane |
| `packages/contracts`, `packages/policy`, `packages/executors` | Shared TypeScript policy |

## Required checks

Run these checks before a pull request:

```text
python3 -m pytest
ruff check .
python3 -m compileall -q src scripts
python3 scripts/validate_repo.py
npm test
```

When installation or packaging changes, verify current OpenAI plugin/skill documentation and update `docs/OPENAI_COMPATIBILITY.md` with the audit date.

## Codegraph

This repository has `.codegraph/`. Pass `projectPath` as this folder. Do not init Codegraph in `../` or in `PROJECTS/`.

## Safety rules

- Keep architecture and security decisions in the parent/planner role.
- Use live model discovery. Do not invent a model identifier.
- Keep provider-specific session controls in the provider adapter.
- Do not add real thread IDs to examples or committed files.
- Do not log secrets or copy full conversation transcripts into task packets.
- Do not merge, push, deploy, or create provider sessions without explicit user intent.
- Preserve unrelated work in a target repository.

## Documentation style

Lead with the zero-config path. Put optional rosters, provider adapters, and benchmarking after the basic workflow. Clearly separate OpenAI product facts from Durable Threads policy.

Use short sentences. Use active voice. Use one term for one meaning. Keep examples complete and runnable.
