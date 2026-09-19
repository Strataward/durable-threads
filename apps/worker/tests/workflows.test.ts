import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import { Worker } from "@temporalio/worker";
import { TestWorkflowEnvironment } from "@temporalio/testing";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import * as activities from "../src/activities.js";
import { durableTaskWorkflow, reviewSignal, statusQuery } from "../src/workflows.js";
import type { TaskRunInput } from "../src/contracts.js";

function gitRepo(root: string): void {
  spawnSync("git", ["init", root], { encoding: "utf8" });
  writeFileSync(join(root, "README.md"), "initial\n");
  writeFileSync(join(root, ".gitignore"), ".durable-threads/\n");
  spawnSync("git", ["add", "README.md", ".gitignore"], { cwd: root });
  spawnSync(
    "git",
    ["-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
    { cwd: root },
  );
}

function scenario(
  root: string,
  options: { writes: Record<string, string>; changedPaths: string[]; returnCode?: number; status?: string },
): void {
  mkdirSync(join(root, ".durable-threads"), { recursive: true });
  writeFileSync(
    join(root, ".durable-threads", "scripted.json"),
    JSON.stringify({
      writes: options.writes,
      result: {
        status: options.status ?? "complete",
        changedPaths: options.changedPaths,
        checks: ["python -m pytest -q: passed"],
        remainingConcerns: [],
      },
      returnCode: options.returnCode ?? 0,
      delaySeconds: 0,
      stderr: "",
      extraStdout: "",
    }),
  );
}

function task(root: string, extra: Partial<TaskRunInput> = {}): TaskRunInput {
  return {
    objective: extra.objective ?? "Update a bounded file",
    allowedPaths: ["src/**"],
    acceptance: ["the file is updated"],
    cwd: root,
    preferredProviders: ["scripted"],
    requiredCapabilities: ["code", "filesystem", "git"],
    maxAttempts: extra.maxAttempts ?? 2,
    providerTimeoutSeconds: 60,
    ...extra,
  };
}

describe("Temporal TypeScript workflows", () => {
  let env: TestWorkflowEnvironment;

  beforeAll(async () => {
    process.env.DURABLE_THREADS_DECISION_ENGINE = "heuristic";
    process.env.DURABLE_THREADS_ENABLE_SCRIPTED = "1";
    env = await TestWorkflowEnvironment.createTimeSkipping();
  }, 120_000);

  afterAll(async () => {
    await env?.teardown();
  });

  async function execute(input: TaskRunInput) {
    const taskQueue = `durable-test-${randomUUID()}`;
    const worker = await Worker.create({
      connection: env.nativeConnection,
      taskQueue,
      workflowsPath: fileURLToPath(new URL("../src/workflows.ts", import.meta.url)),
      activities,
    });
    return worker.runUntil(
      env.client.workflow.execute(durableTaskWorkflow, {
        args: [input],
        workflowId: `workflow-${randomUUID()}`,
        taskQueue,
      }),
    );
  }

  it("completes a happy-path scripted task", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-wf-"));
    gitRepo(root);
    scenario(root, { writes: { "src/result.py": "result = True\n" }, changedPaths: ["src/result.py"] });
    const result = await execute(task(root));
    expect(result.status).toBe("complete");
    expect(result.selectedProvider).toBe("scripted");
    expect(result.attempts).toHaveLength(1);
    expect(result.attempts[0]?.verification.complete).toBe(true);
  });

  it("does not complete when evidence mismatches the diff", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-wf-"));
    gitRepo(root);
    scenario(root, { writes: { "src/a.py": "value = 1\n" }, changedPaths: ["src/b.py"] });
    const result = await execute(task(root));
    expect(result.status).not.toBe("complete");
    expect(["review_required", "failed"]).toContain(result.status);
    expect(result.attempts.length).toBeLessThanOrEqual(2);
  });

  it("falls back to the sandbox executor after scripted is excluded", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-wf-"));
    gitRepo(root);
    scenario(root, {
      writes: { "src/failure.py": "value = False\n" },
      changedPaths: ["src/failure.py"],
      returnCode: 1,
      status: "failed",
    });
    const result = await execute(task(root, { maxAttempts: 2 }));
    expect(result.status).toBe("complete");
    expect(result.attempts.length).toBe(2);
    expect(result.attempts[0]?.provider).toBe("scripted");
    expect(result.selectedProvider).toBe("sandbox");
  });

  it("waits at the human gate and records a rejection", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-wf-"));
    gitRepo(root);
    const taskQueue = `durable-test-${randomUUID()}`;
    const worker = await Worker.create({
      connection: env.nativeConnection,
      taskQueue,
      workflowsPath: fileURLToPath(new URL("../src/workflows.ts", import.meta.url)),
      activities,
    });
    const handlePromise = env.client.workflow.start(durableTaskWorkflow, {
      args: [task(root, { objective: "Design a distributed architecture control plane" })],
      workflowId: `workflow-${randomUUID()}`,
      taskQueue,
    });
    const result = await worker.runUntil(async () => {
      const handle = await handlePromise;
      let status = await handle.query(statusQuery);
      for (let attempt = 0; attempt < 100 && status.phase !== "waiting_for_human_review"; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 20));
        status = await handle.query(statusQuery);
      }
      expect(status.phase).toBe("waiting_for_human_review");
      await handle.signal(reviewSignal, { approved: false, note: "Not approved offline." });
      return handle.result();
    });
    expect(result.status).toBe("rejected");
    expect(result.reviewNote).toBe("Not approved offline.");
  });
});
