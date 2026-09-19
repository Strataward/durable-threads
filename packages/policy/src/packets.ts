import type { DelegationPacket, WorkerConfig } from "@durable-threads/contracts";
import { classifyRisk, validateRisk } from "./risk.js";

export class PacketError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PacketError";
  }
}

const SECRET_MARKERS =
  /(?:sk-[A-Za-z0-9]{12,}|xai-[A-Za-z0-9_\-]{12,}|gh[pousr]_[A-Za-z0-9_\-]{12,}|github_pat_[A-Za-z0-9_\-]{12,}|(?:OPENAI|ANTHROPIC|GITHUB|AWS|XAI|CURSOR|GROK)_[A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET)\s*[=:])/i;

const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/;

function cleanText(value: string, field: string, limit: number): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new PacketError(`${field} must be a non-empty string`);
  }
  const trimmed = value.trim();
  if (trimmed.length > limit) {
    throw new PacketError(`${field} exceeds the compact packet limit of ${limit} characters`);
  }
  if (SECRET_MARKERS.test(trimmed)) {
    throw new PacketError(`${field} contains a credential-like value`);
  }
  return trimmed;
}

function cleanItems(values: Iterable<string> | null | undefined, field: string, limit: number): string[] {
  return [...(values ?? [])].map((item) => cleanText(item, field, limit));
}

export function buildPacket(
  worker: WorkerConfig,
  input: {
    runId: string;
    objective: string;
    allowedPaths: string[];
    acceptance: string[];
    constraints: string[];
    decisions?: string[] | null;
    invariants?: string[] | null;
    nonGoals?: string[] | null;
    riskClass?: string | null;
  },
): DelegationPacket {
  if (!input.runId || !RUN_ID.test(input.runId)) {
    throw new PacketError("run_id must be 3-64 characters and use safe identifier characters");
  }
  if (!input.allowedPaths.length) {
    throw new PacketError("allowed_paths must not be empty");
  }
  if (!input.acceptance.length) {
    throw new PacketError("acceptance must not be empty");
  }
  let risk;
  try {
    risk = input.riskClass
      ? validateRisk(input.riskClass)
      : classifyRisk({
          objective: input.objective,
          allowedPaths: input.allowedPaths,
          acceptance: input.acceptance,
        }).riskClass;
  } catch (error) {
    throw new PacketError(error instanceof Error ? error.message : String(error));
  }
  return {
    schemaVersion: 2,
    runId: input.runId,
    taskName: cleanText(worker.name, "task_name", 120),
    role: cleanText(worker.role, "role", 120),
    provider: cleanText(worker.provider, "provider", 40),
    objective: cleanText(`${input.objective} Purpose: ${worker.purpose}`, "objective", 4000),
    riskClass: risk,
    executionClass: worker.executionClass,
    decisions: cleanItems(input.decisions, "decision", 500),
    invariants: cleanItems(input.invariants, "invariant", 500),
    nonGoals: cleanItems(input.nonGoals, "non_goal", 500),
    allowedPaths: cleanItems(input.allowedPaths, "allowed_path", 240),
    acceptance: cleanItems(input.acceptance, "acceptance", 400),
    constraints: cleanItems(input.constraints, "constraint", 400),
    resultContract: [
      "Return changed paths.",
      "Return exact checks and results.",
      "Return remaining concerns or 'None known'.",
      "Do not claim an unexecuted check passed.",
      "Do not include secrets, private data, or a full transcript.",
    ],
    modelSelector: cleanText(worker.modelSelector, "model_selector", 120),
    reasoningEffort: worker.reasoningEffort,
    maxFollowups: worker.maxFollowups,
  };
}
