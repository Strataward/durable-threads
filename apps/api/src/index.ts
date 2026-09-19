import { serve } from "@hono/node-server";
import { createApp, createStore } from "./app.js";
import { TemporalRuntime } from "./temporal-runtime.js";

const port = Number(process.env.PORT ?? "8787");

async function main(): Promise<void> {
  const store = await createStore();
  let temporal: TemporalRuntime | null = null;
  if (process.env.TEMPORAL_ADDRESS) {
    temporal = await TemporalRuntime.connect();
  }
  const app = createApp({ store, temporal, useTemporal: Boolean(temporal) });
  serve({ fetch: app.fetch, port });
  console.log(`Durable Threads API on http://127.0.0.1:${port}`);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
