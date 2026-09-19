import { Hono } from "hono";
import { cors } from "hono/cors";
import { randomUUID } from "node:crypto";
import type { CreateTaskRequest, ReviewDecision, TaskRunInput } from "@durable-threads/contracts";
import { applyResult, MemoryTaskStore, newTask, type TaskStore } from "./store.js";
import { PostgresTaskStore } from "./postgres.js";
import { initWorkspace, runLocalTask } from "./local-runtime.js";
import { TemporalRuntime } from "./temporal-runtime.js";

export interface AppOptions {
  store?: TaskStore;
  temporal?: TemporalRuntime | null;
  useTemporal?: boolean;
}

interface ReviewWaiter {
  resolve: (decision: ReviewDecision) => void;
}

export async function createStore(): Promise<TaskStore> {
  if (process.env.DATABASE_URL) {
    return PostgresTaskStore.connect(process.env.DATABASE_URL);
  }
  return new MemoryTaskStore();
}

export function createApp(options: AppOptions = {}): Hono {
  const store = options.store ?? new MemoryTaskStore();
  const waiters = new Map<string, ReviewWaiter>();
  const useTemporal = options.useTemporal ?? Boolean(process.env.TEMPORAL_ADDRESS);
  const app = new Hono();
  app.use("/*", cors());

  app.onError((error, context) => {
    return context.json({ error: error.message }, 500);
  });

  app.use("/*", async (context, next) => {
    const required = process.env.DURABLE_THREADS_API_KEY;
    if (!required || context.req.path === "/health") {
      await next();
      return;
    }
    if (context.req.header("x-api-key") !== required) {
      return context.json({ error: "unauthorized" }, 401);
    }
    await next();
  });

  app.get("/health", (context) =>
    context.json({ ok: true, mode: useTemporal ? "temporal" : "local", store: process.env.DATABASE_URL ? "postgres" : "memory" }),
  );

  app.get("/v1/tasks", async (context) => {
    return context.json({ tasks: await store.list() });
  });

  app.get("/v1/tasks/:id", async (context) => {
    const task = await store.get(context.req.param("id"));
    if (!task) {
      return context.json({ error: "task not found" }, 404);
    }
    return context.json(task);
  });

  app.post("/v1/tasks", async (context) => {
    const body = (await context.req.json()) as CreateTaskRequest;
    if (!body.objective?.trim() || !body.allowedPaths?.length || !body.acceptance?.length) {
      return context.json({ error: "objective, allowedPaths, and acceptance are required" }, 400);
    }
    const id = randomUUID();
    const workflowId = `dt-${id.slice(0, 8)}`;
    const cwd = body.cwd?.trim() || initWorkspace();
    const record = newTask({ id, workflowId, objective: body.objective.trim() });
    await store.create(record);
    const input: TaskRunInput = {
      objective: body.objective.trim(),
      allowedPaths: body.allowedPaths,
      acceptance: body.acceptance,
      cwd,
      constraints: body.constraints ?? [],
      preferredProviders: body.preferredProviders ?? [],
      modelSelector: body.modelSelector,
      reasoningEffort: body.reasoningEffort,
      maxAttempts: body.maxAttempts,
      humanGateAt: body.humanGateAt,
      waitForHumanReview: body.waitForHumanReview ?? true,
    };

    void (async () => {
      try {
        if (useTemporal && options.temporal) {
          await options.temporal.start(workflowId, input);
          const result = await options.temporal.result(workflowId);
          await store.update(id, applyResult(result));
          return;
        }
        const result = await runLocalTask(input, {
          onStatus: async (status) => {
            await store.update(id, {
              phase: status.phase,
              risk: status.risk,
              reviewPending: status.reviewPending,
              status: status.reviewPending ? "waiting_for_human_review" : "executing",
            });
          },
          waitForReview: () =>
            new Promise<ReviewDecision>((resolve) => {
              waiters.set(id, { resolve });
            }),
        });
        await store.update(id, applyResult(result));
      } catch (error) {
        await store.update(id, {
          status: "failed",
          phase: "failed",
          result: {
            status: "failed",
            finalRisk: "R1",
            selectedProvider: null,
            taskAssessment: { error: error instanceof Error ? error.message : String(error) },
            attempts: [],
            reviewNote: null,
          },
        });
      }
    })();

    return context.json({ id, workflowId }, 202);
  });

  app.post("/v1/tasks/:id/review", async (context) => {
    const id = context.req.param("id");
    const task = await store.get(id);
    if (!task) {
      return context.json({ error: "task not found" }, 404);
    }
    const body = (await context.req.json()) as ReviewDecision;
    const decision = { approved: Boolean(body.approved), note: body.note ?? "" };
    if (useTemporal && options.temporal) {
      await options.temporal.review(task.workflowId, decision);
      return context.json({ ok: true });
    }
    const waiter = waiters.get(id);
    if (!waiter) {
      return context.json({ error: "no review is waiting" }, 409);
    }
    waiters.delete(id);
    waiter.resolve(decision);
    return context.json({ ok: true });
  });

  app.get("/v1/tasks/:id/stream", async (context) => {
    const id = context.req.param("id");
    return new Response(
      new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          for (let attempt = 0; attempt < 120; attempt += 1) {
            const task = await store.get(id);
            if (!task) {
              controller.close();
              return;
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(task)}\n\n`));
            if (["complete", "failed", "rejected", "review_required"].includes(task.status)) {
              controller.close();
              return;
            }
            await new Promise((resolve) => setTimeout(resolve, 500));
          }
          controller.close();
        },
      }),
      { headers: { "content-type": "text/event-stream", "cache-control": "no-cache" } },
    );
  });

  return app;
}
