import { Client, Connection } from "@temporalio/client";
import type { ReviewDecision, TaskRunInput, TaskRunResult, WorkflowStatus } from "@durable-threads/contracts";
import { durableTaskWorkflow, reviewSignal, statusQuery } from "../../worker/src/workflows.js";

export class TemporalRuntime {
  constructor(
    private readonly client: Client,
    private readonly taskQueue: string,
  ) {}

  static async connect(): Promise<TemporalRuntime> {
    const address = process.env.TEMPORAL_ADDRESS ?? "localhost:7233";
    const namespace = process.env.TEMPORAL_NAMESPACE ?? "default";
    const taskQueue = process.env.DURABLE_THREADS_TASK_QUEUE ?? "durable-threads";
    const connection = await Connection.connect({ address });
    const client = new Client({ connection, namespace });
    return new TemporalRuntime(client, taskQueue);
  }

  async start(workflowId: string, input: TaskRunInput): Promise<void> {
    await this.client.workflow.start(durableTaskWorkflow, {
      args: [input],
      workflowId,
      taskQueue: this.taskQueue,
    });
  }

  async status(workflowId: string): Promise<WorkflowStatus> {
    const handle = this.client.workflow.getHandle(workflowId);
    return handle.query(statusQuery);
  }

  async review(workflowId: string, decision: ReviewDecision): Promise<void> {
    const handle = this.client.workflow.getHandle(workflowId);
    await handle.signal(reviewSignal, decision);
  }

  async result(workflowId: string): Promise<TaskRunResult> {
    const handle = this.client.workflow.getHandle(workflowId);
    return handle.result();
  }
}
