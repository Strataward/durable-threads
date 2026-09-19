import { cpSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, sep } from "node:path";
import { ExecutionError, type ExecutionBackend, type ExecutionOutcome, type ExecutionRequest, type ExecutorPlugin } from "./types.js";

function copyWorkspace(source: string, destination: string): void {
  cpSync(source, destination, {
    recursive: true,
    filter: (src) => !src.split(sep).includes("node_modules"),
  });
}

export class SandboxExecutionBackend implements ExecutionBackend {
  constructor(private readonly inner: ExecutionBackend) {}

  async execute(request: ExecutionRequest): Promise<ExecutionOutcome> {
    if (!existsSync(request.cwd)) {
      throw new ExecutionError(`provider working directory not found: ${request.cwd}`);
    }
    const sandbox = mkdtempSync(join(tmpdir(), "dt-sandbox-"));
    copyWorkspace(request.cwd, sandbox);
    const outcome = await this.inner.execute({ ...request, cwd: sandbox });
    return { ...outcome, workspaceDir: sandbox };
  }
}

export function cleanupWorkspace(path: string): void {
  if (path.includes("dt-sandbox-") && existsSync(path)) {
    rmSync(path, { recursive: true, force: true });
  }
}

export function sandboxPlugin(inner: ExecutionBackend): ExecutorPlugin {
  return {
    descriptor: {
      executorId: "sandbox",
      provider: "sandbox",
      runtime: "Isolated workspace sandbox",
      capabilities: new Set(["code", "filesystem", "git", "shell", "structured-output"]),
      headless: true,
      structuredOutput: true,
      persistentSessions: false,
      supportsEffort: true,
      metadata: { protocol: "sandbox" },
    },
    backendFactory: () => new SandboxExecutionBackend(inner),
    availabilityProbe: () => true,
  };
}
