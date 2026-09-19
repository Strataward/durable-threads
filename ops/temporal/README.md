# Local Temporal

Start the self-hosted dev server:

```sh
docker compose -f ops/temporal/docker-compose.yml up -d
```

Open the UI at <http://localhost:8233>.

Set these variables for Durable Threads:

```sh
export TEMPORAL_ADDRESS=localhost:7233
export TEMPORAL_NAMESPACE=default
export DURABLE_THREADS_TASK_QUEUE=durable-threads
```

Start the worker from the repository root:

```sh
source .venv/bin/activate
durable-threads-temporal-worker
```
