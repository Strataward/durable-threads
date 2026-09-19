# Self-host the TypeScript control plane

Plugin users can ignore this file. This is optional localhost self-host only. This repository has no public deployment.

The Codex plugin and skill stay markdown-first. The in-repo TypeScript tree is the self-host control plane.

See [ADR 0002](adr/0002-typescript-saas.md).

## Layout

- `packages/contracts` — shared task, packet, and result types from the skill and roster schemas
- `packages/policy` — risk, routing, packets, evidence, heuristic/Jev decisions
- `packages/executors` — hosted registry: sandbox, headless HTTP, optional scripted. No local CLI adapters
- `apps/worker` — Temporal TypeScript workflows
- `apps/api` — task submit, status, human-gate signals, Postgres or memory store
- `apps/web` — React control plane

## Run locally

```bash
npm install
npm test
DURABLE_THREADS_DECISION_ENGINE=heuristic npm run dev:api
npm run dev:web
```

Open http://127.0.0.1:5173. The API defaults to the in-process local runtime and an in-memory store. The default hosted executor is `sandbox`. It copies the workspace, writes only inside allowed paths, and emits a RESULT JSON object.

## Temporal

Start Temporal from `ops/temporal`, then set:

```bash
export TEMPORAL_ADDRESS=localhost:7233
export TEMPORAL_NAMESPACE=default
export DURABLE_THREADS_TASK_QUEUE=durable-threads
npm run dev:worker
DURABLE_THREADS_DECISION_ENGINE=heuristic npm run dev:api
```

The API starts `durableTaskWorkflow` and signals `review` for human gates. The browser reads live status from `/v1/tasks/:id/stream`. It does not query Temporal.

## Postgres

Set `DATABASE_URL`. The API creates a `tasks` table on startup.

```bash
docker compose -f ops/temporal/docker-compose.yml up -d postgres
export DATABASE_URL=postgres://durable:durable@127.0.0.1:5432/durable_threads
```

## Hosted execution

The hosted registry does not spawn `codex`, `claude`, `grok`, or `cursor`.

| Executor | Enable with |
|---|---|
| `sandbox` | Default. Isolated allowed-path writer for the hosted path |
| `headless-http` | `DURABLE_THREADS_HEADLESS_URL` pointing at a headless agent API |
| `scripted` | `DURABLE_THREADS_ENABLE_SCRIPTED=1` for tests that ship a scenario file |

Set `DURABLE_THREADS_SANDBOX=0` only when a test must write the original checkout. Writer activities still use `maximumAttempts: 1`.

## Auth

If `DURABLE_THREADS_API_KEY` is set, every route except `/health` requires header `X-Api-Key`.
