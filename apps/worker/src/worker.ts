import { NativeConnection, Worker } from "@temporalio/worker";
import { fileURLToPath } from "node:url";
import * as activities from "./activities.js";

async function main(): Promise<void> {
  const address = process.env.TEMPORAL_ADDRESS ?? "localhost:7233";
  const namespace = process.env.TEMPORAL_NAMESPACE ?? "default";
  const taskQueue = process.env.DURABLE_THREADS_TASK_QUEUE ?? "durable-threads";
  const connection = await NativeConnection.connect({ address });
  const worker = await Worker.create({
    connection,
    namespace,
    taskQueue,
    workflowsPath: fileURLToPath(new URL("./workflows.ts", import.meta.url)),
    activities,
  });
  await worker.run();
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
