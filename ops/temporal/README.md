# Local Temporal and Postgres

Start the self-hosted Temporal server and the hosted-task Postgres database:

```sh
docker compose -f ops/temporal/docker-compose.yml up -d
```

Open the Temporal UI at <http://localhost:8233>.

Set these variables for Durable Threads:

```sh
export TEMPORAL_ADDRESS=localhost:7233
export TEMPORAL_NAMESPACE=default
export DURABLE_THREADS_TASK_QUEUE=durable-threads
export DATABASE_URL=postgres://durable:durable@127.0.0.1:5432/durable_threads
```

Python worker (legacy helper):

```sh
source .venv/bin/activate
durable-threads-temporal-worker
```

TypeScript worker and API:

```sh
npm run dev:worker
DURABLE_THREADS_DECISION_ENGINE=heuristic npm run dev:api
```

See [Self-host the TypeScript control plane](../../docs/SAAS.md).
