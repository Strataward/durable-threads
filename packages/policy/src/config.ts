import {
  EXECUTION_CLASSES,
  REASONING_EFFORTS,
  type ExecutionClass,
  type ReasoningEffort,
  type Roster,
  type RoleConfig,
  type StrategyConfig,
  type WorkerConfig,
} from "@durable-threads/contracts";
import { validateRisk } from "./risk.js";

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

const PROFILES = new Set(["economy", "balanced", "frontier"]);
const PROVIDER_ID = /^[a-z0-9][a-z0-9._-]{0,63}$/;

function text(value: unknown, field: string, required = true): string | null {
  if (value === null || value === undefined) {
    if (!required) {
      return null;
    }
    throw new ConfigError(`${field} must be a non-empty string`);
  }
  if (typeof value !== "string" || !value.trim()) {
    throw new ConfigError(`${field} must be a non-empty string`);
  }
  return value.trim();
}

function integer(value: unknown, field: string, minimum = 0): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < minimum) {
    throw new ConfigError(`${field} must be an integer >= ${minimum}`);
  }
  return value;
}

function provider(value: unknown, field: string): string {
  const id = text(value, field);
  if (!id) {
    throw new ConfigError(`${field} must be a non-empty string`);
  }
  const folded = id.toLowerCase();
  if (!PROVIDER_ID.test(folded)) {
    throw new ConfigError(
      `${field} must be a lowercase provider id using letters, digits, '.', '_' or '-'`,
    );
  }
  return folded;
}

function executionClass(value: unknown, field: string, fallback: string): ExecutionClass {
  const item = text(value ?? fallback, field);
  if (!item || !EXECUTION_CLASSES.includes(item as ExecutionClass)) {
    throw new ConfigError(`${field} must be one of: ${[...EXECUTION_CLASSES].sort().join(", ")}`);
  }
  return item as ExecutionClass;
}

function roleFromDict(
  data: unknown,
  field: string,
  defaultExecutionClass: string,
): RoleConfig {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new ConfigError(`${field} must be an object`);
  }
  const record = data as Record<string, unknown>;
  const role = text(record.role, `${field}.role`);
  const modelSelector = text(record.modelSelector, `${field}.modelSelector`);
  const effort = text(record.reasoningEffort, `${field}.reasoningEffort`);
  if (!role || !modelSelector || !effort) {
    throw new ConfigError(`${field} has a missing required field`);
  }
  if (!REASONING_EFFORTS.includes(effort as ReasoningEffort)) {
    throw new ConfigError(
      `${field}.reasoningEffort must be one of: ${[...REASONING_EFFORTS].sort().join(", ")}`,
    );
  }
  return {
    role,
    provider: provider(record.provider ?? "codex", `${field}.provider`),
    modelSelector,
    reasoningEffort: effort as ReasoningEffort,
    executionClass: executionClass(record.executionClass, `${field}.executionClass`, defaultExecutionClass),
  };
}

function workerFromDict(data: unknown, index: number): WorkerConfig {
  const field = `workers[${index}]`;
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new ConfigError(`${field} must be an object`);
  }
  const record = data as Record<string, unknown>;
  const name = text(record.name, `${field}.name`);
  const role = text(record.role, `${field}.role`);
  const threadTitle = text(record.threadTitle, `${field}.threadTitle`);
  const purpose = text(record.purpose, `${field}.purpose`);
  const modelSelector = text(record.modelSelector, `${field}.modelSelector`);
  const reasoningEffort = text(record.reasoningEffort ?? "low", `${field}.reasoningEffort`);
  const threadId = text(record.threadId, `${field}.threadId`, false);
  if (!name || !role || !threadTitle || !purpose || !modelSelector || !reasoningEffort) {
    throw new ConfigError(`${field} has a missing required field`);
  }
  if (!REASONING_EFFORTS.includes(reasoningEffort as ReasoningEffort)) {
    throw new ConfigError(`${field}.reasoningEffort is not supported`);
  }
  const maxFollowups = integer(record.maxFollowups ?? 1, `${field}.maxFollowups`);
  if (maxFollowups > 3) {
    throw new ConfigError(`${field}.maxFollowups must be <= 3`);
  }
  const parallel = record.parallel ?? false;
  if (typeof parallel !== "boolean") {
    throw new ConfigError(`${field}.parallel must be a boolean`);
  }
  return {
    name,
    role,
    provider: provider(record.provider ?? "codex", `${field}.provider`),
    threadTitle,
    purpose,
    modelSelector,
    reasoningEffort: reasoningEffort as ReasoningEffort,
    executionClass: executionClass(record.executionClass, `${field}.executionClass`, "workhorse"),
    threadId,
    maxFollowups,
    parallel,
  };
}

const DEFAULT_ESCALATION: StrategyConfig["escalation"] = [
  { modelSelector: "efficient", reasoningEffort: "xhigh" },
  { modelSelector: "balanced", reasoningEffort: "medium" },
  { modelSelector: "frontier", reasoningEffort: "low" },
  { modelSelector: "frontier", reasoningEffort: "medium" },
];

function strategyFromDict(data: unknown): StrategyConfig {
  if (data === null || data === undefined) {
    return {
      profile: "economy",
      defaultRisk: "R1",
      frontierReviewAt: "R3",
      sleepingOrchestrator: true,
      escalation: DEFAULT_ESCALATION,
    };
  }
  if (typeof data !== "object" || Array.isArray(data)) {
    throw new ConfigError("strategy must be an object");
  }
  const record = data as Record<string, unknown>;
  const profile = text(record.profile ?? "economy", "strategy.profile");
  if (!profile || !PROFILES.has(profile)) {
    throw new ConfigError(`strategy.profile must be one of: ${[...PROFILES].sort().join(", ")}`);
  }
  let defaultRisk: StrategyConfig["defaultRisk"];
  let frontierReviewAt: StrategyConfig["frontierReviewAt"];
  try {
    defaultRisk = validateRisk(String(record.defaultRisk ?? "R1"));
    frontierReviewAt = validateRisk(String(record.frontierReviewAt ?? "R3"));
  } catch (error) {
    throw new ConfigError(error instanceof Error ? error.message : String(error));
  }
  const sleeping = record.sleepingOrchestrator ?? true;
  if (typeof sleeping !== "boolean") {
    throw new ConfigError("strategy.sleepingOrchestrator must be a boolean");
  }
  const rawEscalation = record.escalation;
  const escalation =
    rawEscalation === undefined || rawEscalation === null
      ? DEFAULT_ESCALATION
      : (rawEscalation as unknown[]).map((item, index) => {
          const field = `strategy.escalation[${index}]`;
          if (!item || typeof item !== "object" || Array.isArray(item)) {
            throw new ConfigError(`${field} must be an object`);
          }
          const step = item as Record<string, unknown>;
          const selector = text(step.modelSelector, `${field}.modelSelector`);
          const effort = text(step.reasoningEffort, `${field}.reasoningEffort`);
          if (!selector || !effort) {
            throw new ConfigError(`${field} has a missing required field`);
          }
          if (!REASONING_EFFORTS.includes(effort as ReasoningEffort)) {
            throw new ConfigError(`${field}.reasoningEffort is not supported`);
          }
          return { modelSelector: selector, reasoningEffort: effort as ReasoningEffort };
        });
  if (!escalation.length) {
    throw new ConfigError("strategy.escalation must not be empty");
  }
  return {
    profile: profile as StrategyConfig["profile"],
    defaultRisk,
    frontierReviewAt,
    sleepingOrchestrator: sleeping,
    escalation,
  };
}

export function parseRoster(data: unknown): Roster {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new ConfigError("roster must be a JSON object");
  }
  const record = data as Record<string, unknown>;
  const schemaVersion = record.schemaVersion ?? 1;
  if (schemaVersion !== 1 && schemaVersion !== 2) {
    throw new ConfigError("schemaVersion must be 1 or 2");
  }
  const project = record.project;
  if (!project || typeof project !== "object" || Array.isArray(project)) {
    throw new ConfigError("project must be an object");
  }
  const projectName = text((project as Record<string, unknown>).name, "project.name");
  const defaults = record.defaults;
  if (!defaults || typeof defaults !== "object" || Array.isArray(defaults)) {
    throw new ConfigError("defaults must be an object");
  }
  const defaultsRecord = defaults as Record<string, unknown>;
  const planner = roleFromDict(defaultsRecord.planner, "defaults.planner", "decision");
  const reviewer = roleFromDict(defaultsRecord.reviewer, "defaults.reviewer", "review");
  const strategy = strategyFromDict(record.strategy);
  const rawWorkers = record.workers;
  if (!Array.isArray(rawWorkers) || rawWorkers.length === 0) {
    throw new ConfigError("workers must be a non-empty array");
  }
  const workers = rawWorkers.map((item, index) => workerFromDict(item, index));
  const names = workers.map((worker) => worker.name);
  const titles = workers.map((worker) => worker.threadTitle);
  if (new Set(names).size !== names.length) {
    throw new ConfigError("worker names must be unique");
  }
  if (new Set(titles).size !== titles.length) {
    throw new ConfigError("worker threadTitle values must be unique");
  }
  const policy = record.policy ?? {};
  if (!policy || typeof policy !== "object" || Array.isArray(policy)) {
    throw new ConfigError("policy must be an object");
  }
  const policyRecord = policy as Record<string, unknown>;
  const maxParallel = integer(policyRecord.maxParallelWorkers ?? 2, "policy.maxParallelWorkers", 1);
  const maxSelected = integer(
    policyRecord.maxSelectedWorkers ?? Math.min(2, workers.length),
    "policy.maxSelectedWorkers",
    1,
  );
  if (maxSelected > workers.length) {
    throw new ConfigError("policy.maxSelectedWorkers cannot exceed the worker count");
  }
  const resultMaxChars = integer(policyRecord.resultMaxChars ?? 2000, "policy.resultMaxChars", 200);
  const allowCreation = policyRecord.allowThreadCreation ?? false;
  if (typeof allowCreation !== "boolean") {
    throw new ConfigError("policy.allowThreadCreation must be a boolean");
  }
  if (!projectName) {
    throw new ConfigError("project.name must be a non-empty string");
  }
  return {
    schemaVersion,
    projectName,
    planner,
    reviewer,
    strategy,
    workers,
    maxParallelWorkers: maxParallel,
    maxSelectedWorkers: maxSelected,
    resultMaxChars,
    allowThreadCreation: allowCreation,
  };
}
