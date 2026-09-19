import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";
import { ExecutionRegistry } from "../src/registry.js";
import { ScriptedExecutionBackend, scriptedExecutorPlugin } from "../src/scripted.js";
import { SandboxExecutionBackend, cleanupWorkspace } from "../src/sandbox.js";
import { HeadlessHttpExecutionBackend } from "../src/headless-http.js";
import { createHostedRegistry } from "../src/hosted.js";
import { ExecutionError, type ExecutionRequirements, type ExecutorPlugin } from "../src/types.js";

function gitRepo(root: string): void {
  spawnSync("git", ["init", root], { encoding: "utf8" });
  writeFileSync(join(root, "README.md"), "initial\n");
  spawnSync("git", ["add", "README.md"], { cwd: root });
  spawnSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"], {
    cwd: root,
  });
}

function writeScenario(root: string, writes: Record<string, string> = { "src/result.txt": "generated\n" }): void {
  mkdirSync(join(root, ".durable-threads"), { recursive: true });
  writeFileSync(
    join(root, ".durable-threads", "scripted.json"),
    JSON.stringify({
      writes,
      result: {
        status: "complete",
        changedPaths: Object.keys(writes),
        checks: ["python -m pytest -q: passed"],
        remainingConcerns: [],
      },
      returnCode: 0,
      delaySeconds: 0,
      stderr: "",
      extraStdout: "",
    }),
  );
}

const requirements = (): ExecutionRequirements => ({
  capabilities: new Set(["code", "filesystem", "git"]),
  headless: true,
  persistentSession: false,
  structuredOutput: true,
  effortControl: false,
  preferredProviders: ["future-ai"],
  excludedProviders: [],
});

describe("hosted executors", () => {
  it("accepts a third-party plugin without a closed provider enum", () => {
    const registry = new ExecutionRegistry();
    const plugin: ExecutorPlugin = {
      descriptor: {
        executorId: "future-agent",
        provider: "future-ai",
        runtime: "Future Agent",
        capabilities: new Set(["code", "filesystem", "git", "structured-output"]),
        persistentSessions: true,
        headless: true,
        structuredOutput: true,
        supportsEffort: true,
        metadata: {},
      },
      availabilityProbe: () => true,
    };
    registry.register(plugin);
    const selected = registry.select(requirements());
    expect(selected[0]?.descriptor.provider).toBe("future-ai");
    expect(selected[0]?.descriptor.executorId).toBe("future-agent");
  });

  it("writes a scripted result into the checkout", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-scripted-"));
    gitRepo(root);
    writeScenario(root);
    const outcome = await new ScriptedExecutionBackend().execute({
      provider: "scripted",
      prompt: "test",
      cwd: root,
      sessionName: "test-session",
    });
    expect(outcome.returnCode).toBe(0);
    expect(outcome.stdout).toContain("complete");
  });

  it("rejects a scripted path escape", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-scripted-"));
    gitRepo(root);
    writeScenario(root, { "../escape.txt": "unsafe" });
    await expect(
      new ScriptedExecutionBackend().execute({ provider: "scripted", prompt: "test", cwd: root }),
    ).rejects.toThrow(/escapes cwd/);
  });

  it("requires a scenario file", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-scripted-"));
    gitRepo(root);
    await expect(
      new ScriptedExecutionBackend().execute({ provider: "scripted", prompt: "test", cwd: root }),
    ).rejects.toThrow(ExecutionError);
  });

  it("does not register local CLI adapters on the hosted path", () => {
    const registry = createHostedRegistry({ enableScripted: true, sandbox: false });
    const ids = registry.descriptors().map((item) => item.executorId);
    expect(ids).toContain("sandbox");
    expect(ids).toContain("scripted");
    expect(ids).not.toContain("codex");
    expect(ids).not.toContain("claude");
    expect(ids).not.toContain("grok");
    expect(ids).not.toContain("cursor");
  });

  it("selects the sandbox executor when no scripted scenario exists", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-host-"));
    gitRepo(root);
    const original = "initial\n";
    const registry = createHostedRegistry({ enableScripted: false });
    const selected = registry.select({
      capabilities: new Set(["code", "filesystem", "git"]),
      headless: true,
      persistentSession: false,
      structuredOutput: true,
      effortControl: false,
      preferredProviders: [],
      excludedProviders: [],
    });
    expect(selected[0]?.descriptor.provider).toBe("sandbox");
    const outcome = await registry.backend("sandbox").execute({
      provider: "sandbox",
      prompt: "Fix a spelling typo in the README",
      cwd: root,
      allowedPaths: ["README.md"],
      sessionName: "hosted",
    });
    expect(outcome.returnCode).toBe(0);
    expect(outcome.workspaceDir).toBeTruthy();
    expect(outcome.workspaceDir).not.toBe(root);
    expect(outcome.stdout).toContain("README.md");
    expect(readFileSync(join(root, "README.md"), "utf8")).toBe(original);
    cleanupWorkspace(outcome.workspaceDir ?? "");
  });

  it("isolates hosted writes in a sandbox copy", async () => {
    const root = mkdtempSync(join(tmpdir(), "dt-host-"));
    gitRepo(root);
    writeScenario(root);
    const backend = new SandboxExecutionBackend(new ScriptedExecutionBackend());
    const outcome = await backend.execute({
      provider: "scripted",
      prompt: "test",
      cwd: root,
      sessionName: "sandbox",
    });
    expect(outcome.workspaceDir).toBeTruthy();
    expect(outcome.workspaceDir).not.toBe(root);
    expect(outcome.stdout).toContain("complete");
    cleanupWorkspace(outcome.workspaceDir ?? "");
  });

  it("calls a headless HTTP executor", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () =>
      new Response(
        JSON.stringify({
          returnCode: 0,
          stdout: '{"status":"complete"}',
          stderr: "",
          sessionId: "http-1",
        }),
        { status: 200 },
      )) as typeof fetch;
    try {
      const outcome = await new HeadlessHttpExecutionBackend("https://agents.example/run").execute({
        provider: "headless-http",
        prompt: "do the work",
        cwd: "/tmp/workspace",
      });
      expect(outcome.sessionId).toBe("http-1");
      expect(outcome.returnCode).toBe(0);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
