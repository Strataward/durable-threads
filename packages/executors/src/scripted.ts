import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { ExecutionError, type ExecutionBackend, type ExecutionOutcome, type ExecutionRequest, type ExecutorPlugin } from "./types.js";

interface ScriptedScenario {
  writes: Record<string, string>;
  result: Record<string, unknown>;
  returnCode: number;
  delaySeconds: number;
  stderr: string;
  extraStdout: string;
}

function loadScenario(path: string): ScriptedScenario {
  let payload: unknown;
  try {
    payload = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new ExecutionError(`could not load scripted scenario ${path}: ${error}`);
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new ExecutionError("scripted scenario must be a JSON object");
  }
  const record = payload as Record<string, unknown>;
  const writes = record.writes ?? {};
  if (
    !writes ||
    typeof writes !== "object" ||
    Array.isArray(writes) ||
    Object.entries(writes).some(([key, value]) => typeof key !== "string" || typeof value !== "string")
  ) {
    throw new ExecutionError("scripted scenario writes must be an object of string paths to strings");
  }
  const result = record.result;
  if (!result || typeof result !== "object" || Array.isArray(result)) {
    throw new ExecutionError("scripted scenario result must be an object");
  }
  const returnCode = record.returnCode ?? 0;
  if (!Number.isInteger(returnCode)) {
    throw new ExecutionError("scripted scenario returnCode must be an integer");
  }
  const delaySeconds = record.delaySeconds ?? 0;
  if (typeof delaySeconds !== "number" || delaySeconds < 0) {
    throw new ExecutionError("scripted scenario delaySeconds must be a non-negative number");
  }
  const stderr = record.stderr ?? "";
  if (typeof stderr !== "string") {
    throw new ExecutionError("scripted scenario stderr must be a string");
  }
  const extraStdout = record.extraStdout ?? "";
  if (typeof extraStdout !== "string") {
    throw new ExecutionError("scripted scenario extraStdout must be a string");
  }
  return {
    writes: writes as Record<string, string>,
    result: result as Record<string, unknown>,
    returnCode: returnCode as number,
    delaySeconds,
    stderr,
    extraStdout,
  };
}

function safeWritePath(cwd: string, rawPath: string): string {
  if (isAbsolute(rawPath) || rawPath.split("/").includes("..") || rawPath.split("\\").includes("..")) {
    throw new ExecutionError(`scripted write path escapes cwd: '${rawPath}'`);
  }
  const path = resolve(cwd, rawPath);
  const rel = relative(resolve(cwd), path);
  if (rel.startsWith("..") || isAbsolute(rel)) {
    throw new ExecutionError(`scripted write path escapes cwd: '${rawPath}'`);
  }
  return path;
}

export class ScriptedExecutionBackend implements ExecutionBackend {
  async execute(request: ExecutionRequest): Promise<ExecutionOutcome> {
    if (request.provider !== "scripted") {
      throw new ExecutionError(`backend 'scripted' cannot execute provider '${request.provider}'`);
    }
    const scenarioPath = join(request.cwd, ".durable-threads", "scripted.json");
    if (!existsSync(scenarioPath)) {
      throw new ExecutionError(`scripted scenario not found: ${scenarioPath}`);
    }
    const scenario = loadScenario(scenarioPath);
    await new Promise((resolveWait) => setTimeout(resolveWait, scenario.delaySeconds * 1000));
    for (const [rawPath, content] of Object.entries(scenario.writes)) {
      const path = safeWritePath(request.cwd, rawPath);
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, content, "utf8");
    }
    const result = { provider: request.provider, ...scenario.result };
    return {
      provider: request.provider,
      returnCode: scenario.returnCode,
      stdout: `${scenario.extraStdout}\n${JSON.stringify(result)}`,
      stderr: scenario.stderr,
      sessionId: `scripted-${request.sessionName ?? "session"}`,
      usage: { inputTokens: 0, outputTokens: 0 },
    };
  }
}

export function scriptedExecutorPlugin(): ExecutorPlugin {
  return {
    descriptor: {
      executorId: "scripted",
      provider: "scripted",
      runtime: "Scripted test executor",
      capabilities: new Set(["code", "filesystem", "git", "shell", "structured-output"]),
      headless: true,
      structuredOutput: true,
      persistentSessions: false,
      supportsEffort: true,
      metadata: { protocol: "scripted" },
    },
    backendFactory: () => new ScriptedExecutionBackend(),
    availabilityProbe: () => process.env.DURABLE_THREADS_ENABLE_SCRIPTED === "1",
  };
}
