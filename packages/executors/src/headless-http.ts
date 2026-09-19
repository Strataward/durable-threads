import { bounded, ExecutionError, type ExecutionBackend, type ExecutionOutcome, type ExecutionRequest, type ExecutorPlugin } from "./types.js";

export class HeadlessHttpExecutionBackend implements ExecutionBackend {
  constructor(private readonly endpoint: string) {}

  async execute(request: ExecutionRequest): Promise<ExecutionOutcome> {
    const timeoutSeconds = request.timeoutSeconds ?? 3600;
    const maxOutputChars = request.maxOutputChars ?? 20_000;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutSeconds * 1000);
    let response: Response;
    try {
      response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          provider: request.provider,
          prompt: request.prompt,
          cwd: request.cwd,
          modelSelector: request.modelSelector ?? "default",
          reasoningEffort: request.reasoningEffort ?? "medium",
          sessionId: request.sessionId ?? null,
          sessionName: request.sessionName ?? null,
          allowedPaths: request.allowedPaths ?? [],
          timeoutSeconds,
        }),
        signal: controller.signal,
      });
    } catch (error) {
      throw new ExecutionError(
        `headless executor failed: ${error instanceof Error ? error.message : String(error)}`,
      );
    } finally {
      clearTimeout(timer);
    }
    if (!response.ok) {
      throw new ExecutionError(`headless executor returned HTTP ${response.status}`);
    }
    const payload = (await response.json()) as {
      returnCode?: number;
      stdout?: string;
      stderr?: string;
      sessionId?: string | null;
      usage?: Record<string, number> | null;
    };
    return {
      provider: request.provider,
      returnCode: Number(payload.returnCode ?? 1),
      stdout: bounded(String(payload.stdout ?? ""), maxOutputChars),
      stderr: bounded(String(payload.stderr ?? ""), maxOutputChars),
      sessionId: payload.sessionId ?? request.sessionId ?? null,
      usage: payload.usage ?? null,
    };
  }
}

export function headlessHttpPlugin(endpoint: string): ExecutorPlugin {
  return {
    descriptor: {
      executorId: "headless-http",
      provider: "headless-http",
      runtime: "Headless HTTP coding-agent API",
      capabilities: new Set(["code", "filesystem", "git", "shell", "structured-output"]),
      headless: true,
      structuredOutput: true,
      persistentSessions: true,
      supportsEffort: true,
      metadata: { protocol: "http", endpoint },
    },
    backendFactory: () => new HeadlessHttpExecutionBackend(endpoint),
    availabilityProbe: () => Boolean(endpoint),
  };
}
