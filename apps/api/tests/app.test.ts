import { describe, expect, it } from "vitest";
import { createApp } from "../src/app.js";
import { MemoryTaskStore } from "../src/store.js";

describe("SaaS API", () => {
  it("rejects an incomplete task", async () => {
    const app = createApp({ store: new MemoryTaskStore() });
    const response = await app.request("/v1/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ objective: "x" }),
    });
    expect(response.status).toBe(400);
  });

  it("creates a task and waits at an R4 human gate", async () => {
    process.env.DURABLE_THREADS_DECISION_ENGINE = "heuristic";
    const app = createApp({ store: new MemoryTaskStore(), useTemporal: false });
    const created = await app.request("/v1/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        objective: "Design a distributed architecture control plane",
        allowedPaths: ["src/**"],
        acceptance: ["the design is recorded"],
        waitForHumanReview: true,
      }),
    });
    expect(created.status).toBe(202);
    const { id } = (await created.json()) as { id: string };
    let task = (await (await app.request(`/v1/tasks/${id}`)).json()) as {
      reviewPending: boolean;
      status: string;
      result: { reviewNote: string } | null;
    };
    for (let attempt = 0; attempt < 40 && !task.reviewPending; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      task = (await (await app.request(`/v1/tasks/${id}`)).json()) as typeof task;
    }
    expect(task.reviewPending).toBe(true);
    const reviewed = await app.request(`/v1/tasks/${id}/review`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ approved: false, note: "Not now." }),
    });
    expect(reviewed.status).toBe(200);
    for (let attempt = 0; attempt < 40 && task.status === "waiting_for_human_review"; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      task = (await (await app.request(`/v1/tasks/${id}`)).json()) as typeof task;
    }
    expect(task.status).toBe("rejected");
    expect(task.result?.reviewNote).toBe("Not now.");
  });

  it("completes a bounded docs task with the sandbox executor", async () => {
    process.env.DURABLE_THREADS_DECISION_ENGINE = "heuristic";
    const app = createApp({ store: new MemoryTaskStore(), useTemporal: false });
    const created = await app.request("/v1/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        objective: "Fix a spelling typo in the README",
        allowedPaths: ["README.md"],
        acceptance: ["The README is accurate."],
        waitForHumanReview: true,
      }),
    });
    expect(created.status).toBe(202);
    const { id } = (await created.json()) as { id: string };
    let task = (await (await app.request(`/v1/tasks/${id}`)).json()) as {
      status: string;
      result: { selectedProvider: string | null } | null;
    };
    for (let attempt = 0; attempt < 80 && !["complete", "failed", "rejected"].includes(task.status); attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      task = (await (await app.request(`/v1/tasks/${id}`)).json()) as typeof task;
    }
    expect(task.status).toBe("complete");
    expect(task.result?.selectedProvider).toBe("sandbox");
  });

  it("approves an R4 gate and completes in the sandbox", async () => {
    process.env.DURABLE_THREADS_DECISION_ENGINE = "heuristic";
    const app = createApp({ store: new MemoryTaskStore(), useTemporal: false });
    const created = await app.request("/v1/tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        objective: "Design a distributed architecture control plane",
        allowedPaths: ["src/**"],
        acceptance: ["the design is recorded"],
        waitForHumanReview: true,
      }),
    });
    expect(created.status).toBe(202);
    const { id } = (await created.json()) as { id: string };

    const load = async () =>
      (await (await app.request(`/v1/tasks/${id}`)).json()) as {
        reviewPending: boolean;
        status: string;
        result: { selectedProvider: string | null } | null;
      };
    const approve = async (note: string) =>
      app.request(`/v1/tasks/${id}/review`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ approved: true, note }),
      });

    let task = await load();
    for (let attempt = 0; attempt < 40 && !task.reviewPending; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      task = await load();
    }
    expect(task.reviewPending).toBe(true);
    expect((await approve("Proceed.")).status).toBe(200);

    for (let attempt = 0; attempt < 40 && task.reviewPending; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      task = await load();
    }

    for (let attempt = 0; attempt < 80 && !["complete", "failed", "rejected"].includes(task.status); attempt += 1) {
      if (task.reviewPending) {
        expect((await approve("Integrate.")).status).toBe(200);
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
      task = await load();
    }
    expect(task.status).toBe("complete");
    expect(task.result?.selectedProvider).toBe("sandbox");
  });

  it("serves health without an API key", async () => {
    const app = createApp({ store: new MemoryTaskStore() });
    const response = await app.request("/health");
    expect(response.status).toBe(200);
    const body = (await response.json()) as { ok: boolean };
    expect(body.ok).toBe(true);
  });
});
