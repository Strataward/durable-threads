export class ExecutionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ExecutionError";
  }
}

export interface ExecutorDescriptor {
  executorId: string;
  provider: string;
  runtime: string;
  capabilities: Set<string>;
  persistentSessions: boolean;
  headless: boolean;
  structuredOutput: boolean;
  supportsEffort: boolean;
  metadata: Record<string, string>;
}

export interface ExecutionRequirements {
  capabilities: Set<string>;
  headless: boolean;
  persistentSession: boolean;
  structuredOutput: boolean;
  effortControl: boolean;
  preferredProviders: string[];
  excludedProviders: string[];
}

export interface ExecutionSelection {
  descriptor: ExecutorDescriptor;
  score: number;
  reasons: string[];
}

export interface ExecutionRequest {
  provider: string;
  prompt: string;
  cwd: string;
  modelSelector?: string;
  reasoningEffort?: string;
  sessionId?: string | null;
  sessionName?: string | null;
  timeoutSeconds?: number;
  maxOutputChars?: number;
  allowedPaths?: string[];
}

export interface ExecutionOutcome {
  provider: string;
  returnCode: number;
  stdout: string;
  stderr: string;
  sessionId: string | null;
  usage: Record<string, number> | null;
  workspaceDir?: string;
}

export interface ExecutionBackend {
  execute(request: ExecutionRequest): Promise<ExecutionOutcome>;
}

export interface ExecutorPlugin {
  descriptor: ExecutorDescriptor;
  backendFactory?: () => ExecutionBackend;
  availabilityProbe?: () => boolean;
}

export function descriptorToDict(descriptor: ExecutorDescriptor): Record<string, unknown> {
  return {
    executorId: descriptor.executorId,
    provider: descriptor.provider,
    runtime: descriptor.runtime,
    capabilities: [...descriptor.capabilities].sort(),
    persistentSessions: descriptor.persistentSessions,
    headless: descriptor.headless,
    structuredOutput: descriptor.structuredOutput,
    supportsEffort: descriptor.supportsEffort,
    metadata: { ...descriptor.metadata },
  };
}

export function selectionToDict(selection: ExecutionSelection): Record<string, unknown> {
  return {
    executor: descriptorToDict(selection.descriptor),
    score: selection.score,
    reasons: [...selection.reasons],
  };
}

export function outcomeToDict(outcome: ExecutionOutcome): Record<string, unknown> {
  return {
    provider: outcome.provider,
    returnCode: outcome.returnCode,
    stdout: outcome.stdout,
    stderr: outcome.stderr,
    sessionId: outcome.sessionId,
    usage: outcome.usage ? { ...outcome.usage } : null,
    workspaceDir: outcome.workspaceDir ?? null,
  };
}

export function bounded(value: string, limit: number): string {
  if (value.length <= limit) {
    return value;
  }
  const marker = "\n[output truncated]\n";
  const head = Math.max(1, Math.floor((limit - marker.length) / 2));
  const tail = Math.max(1, limit - marker.length - head);
  return value.slice(0, head) + marker + value.slice(-tail);
}
