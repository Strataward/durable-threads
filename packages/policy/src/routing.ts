import type { Roster, WorkerConfig } from "@durable-threads/contracts";
import { classifyRisk, meetsThreshold, type RiskAssessment } from "./risk.js";

export interface ModelInfo {
  modelId: string;
  displayName: string;
  tier: string;
  isDefault: boolean;
}

export interface Resolution {
  model: ModelInfo | null;
  reason: string;
  matched: boolean;
}

export interface RouteDecision {
  selected: WorkerConfig[];
  skipped: WorkerConfig[];
  reasons: string[];
  explicit: boolean;
  risk: RiskAssessment;
  frontierReviewRecommended: boolean;
}

const CHANGE_SIGNAL =
  /\b(add|build|change|create|debug|fix|implement|migrate|modify|refactor|remove|repair|update)\b/i;

const ROLE_SIGNALS: Record<string, RegExp> = {
  "test-debug":
    /\b(coverage|debug|failure|failing|flaky|lint|regression|test|tests|testing|typecheck)\b/i,
  "research-docs":
    /\b(analy[sz]e|audit|compare|document|documentation|docs|investigate|research|readme)\b/i,
  "security-review":
    /\b(auth|authorization|hardening|permission|privacy|secret|security|threat|vulnerab)\w*\b/i,
};

export function selectWorkers(
  roster: Roster,
  input: {
    objective: string;
    allowedPaths?: Iterable<string>;
    acceptance?: Iterable<string>;
    requestedWorkers?: Iterable<string>;
    localOnly?: boolean;
    riskClass?: string | null;
  },
): RouteDecision {
  const allowedPaths = [...(input.allowedPaths ?? [])];
  const acceptance = [...(input.acceptance ?? [])];
  const risk = classifyRisk({
    objective: input.objective,
    allowedPaths,
    acceptance,
    explicit: input.riskClass,
    default: roster.strategy.defaultRisk,
  });
  const frontierReview = meetsThreshold(risk.riskClass, roster.strategy.frontierReviewAt);
  const workerNames = new Map(roster.workers.map((worker) => [worker.name, worker]));
  const requested = [...(input.requestedWorkers ?? [])]
    .map((name) => name.trim())
    .filter(Boolean);

  if (input.localOnly) {
    if (requested.length) {
      throw new Error("local work cannot select workers");
    }
    return {
      selected: [],
      skipped: [...roster.workers],
      reasons: ["keep work in the current task"],
      explicit: true,
      risk,
      frontierReviewRecommended: frontierReview,
    };
  }

  if (new Set(requested).size !== requested.length) {
    throw new Error("requested worker names must be unique");
  }
  const unknown = requested.filter((name) => !workerNames.has(name));
  if (unknown.length) {
    throw new Error(`unknown worker name(s): ${unknown.join(", ")}`);
  }
  if (requested.length > roster.maxSelectedWorkers) {
    throw new Error(
      `explicit worker selection exceeds policy.maxSelectedWorkers (${roster.maxSelectedWorkers})`,
    );
  }

  if (requested.length) {
    const selected = requested.map((name) => workerNames.get(name)!);
    const parallelCount = selected.filter((worker) => worker.parallel).length;
    if (parallelCount > roster.maxParallelWorkers) {
      throw new Error(
        `route selects ${parallelCount} parallel workers, but policy.maxParallelWorkers is ${roster.maxParallelWorkers}`,
      );
    }
    return {
      selected,
      skipped: roster.workers.filter((worker) => !requested.includes(worker.name)),
      reasons: ["explicit worker selection was requested"],
      explicit: true,
      risk,
      frontierReviewRecommended: frontierReview,
    };
  }

  const context = [input.objective, ...allowedPaths]
    .filter((item): item is string => typeof item === "string" && Boolean(item.trim()))
    .map((item) => item.trim())
    .join(" ");
  const changeRequested = CHANGE_SIGNAL.test(context);
  const signals = Object.fromEntries(
    Object.entries(ROLE_SIGNALS).map(([role, pattern]) => [role, pattern.test(context)]),
  );
  const specialized = Object.values(signals).some(Boolean);

  const desiredRoles: Array<[string, string]> = [];
  const implementationWorker = roster.workers.find((worker) => worker.role === "implementation");
  if (implementationWorker && (changeRequested || !specialized)) {
    desiredRoles.push(["implementation", "a code-change signal or no specialist signal"]);
  }
  const securityWorker = roster.workers.find((worker) => worker.role === "security-review");
  if (securityWorker && (signals["security-review"] || meetsThreshold(risk.riskClass, "R3"))) {
    desiredRoles.push(["security-review", `risk ${risk.riskClass} or security signal`]);
  }
  for (const role of ["test-debug", "research-docs"] as const) {
    const worker = roster.workers.find((item) => item.role === role);
    if (worker && ROLE_SIGNALS[role]?.test(context)) {
      desiredRoles.push([role, `the ${role} signal was detected`]);
    }
  }

  const selected: WorkerConfig[] = [];
  const reasons: string[] = [];
  for (const [role, reason] of desiredRoles) {
    const worker = roster.workers.find((item) => item.role === role)!;
    if (selected.includes(worker)) {
      continue;
    }
    if (selected.length >= roster.maxSelectedWorkers) {
      reasons.push(
        `skipped ${worker.name}: policy.maxSelectedWorkers is ${roster.maxSelectedWorkers}`,
      );
      continue;
    }
    selected.push(worker);
    reasons.push(`selected ${worker.name}: ${reason}`);
  }

  if (!selected.length) {
    selected.push(roster.workers[0]!);
    reasons.push(`selected ${roster.workers[0]!.name}: safe roster fallback`);
  }

  const parallelCount = selected.filter((worker) => worker.parallel).length;
  if (parallelCount > roster.maxParallelWorkers) {
    throw new Error(
      `route selects ${parallelCount} parallel workers, but policy.maxParallelWorkers is ${roster.maxParallelWorkers}`,
    );
  }
  const selectedNames = new Set(selected.map((worker) => worker.name));
  return {
    selected,
    skipped: roster.workers.filter((worker) => !selectedNames.has(worker.name)),
    reasons,
    explicit: false,
    risk,
    frontierReviewRecommended: frontierReview,
  };
}

export function catalogFromPayload(payload: unknown): ModelInfo[] {
  const rawModels = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object"
      ? (payload as Record<string, unknown>).models
      : undefined;
  if (!Array.isArray(rawModels)) {
    throw new Error("model catalog must contain a models array");
  }
  return rawModels
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => {
      const modelId = item.id ?? item.model;
      if (typeof modelId !== "string" || !modelId.trim()) {
        throw new Error("model catalog entries need an id");
      }
      const displayName = item.displayName ?? item.display_name ?? modelId;
      const tier = item.tier ?? item.costTier ?? "unknown";
      return {
        modelId: modelId.trim(),
        displayName: String(displayName).trim(),
        tier: String(tier).trim().toLowerCase(),
        isDefault: Boolean(item.isDefault ?? item.default ?? false),
      };
    });
}

function normal(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replaceAll("-", " ").split(/\s+/).join(" ");
}

export function resolveModel(catalog: Iterable<ModelInfo>, selector: string): Resolution {
  const models = [...catalog];
  const wanted = normal(selector);
  for (const model of models) {
    const names = new Set([
      normal(model.modelId),
      normal(model.displayName),
      ...normal(model.modelId).split(" "),
      ...normal(model.displayName).split(" "),
    ]);
    if (names.has(wanted)) {
      return { model, reason: `exact catalog match for '${selector}'`, matched: true };
    }
  }
  const tierGroups: Record<string, Set<string>> = {
    frontier: new Set(["frontier", "flagship", "high"]),
    balanced: new Set(["balanced", "standard", "medium"]),
    efficient: new Set(["efficient", "low", "mini"]),
  };
  if (wanted in tierGroups) {
    const candidates = models.filter((model) => tierGroups[wanted]!.has(model.tier));
    if (candidates.length) {
      const fallback = candidates.find((model) => model.isDefault) ?? candidates[0]!;
      return { model: fallback, reason: `${wanted} role matched live catalog metadata`, matched: true };
    }
    const defaultModel = models.find((model) => model.isDefault) ?? null;
    if (defaultModel) {
      return {
        model: defaultModel,
        reason: `${wanted} role was unavailable; using the runtime default without guessing`,
        matched: false,
      };
    }
  }
  return { model: null, reason: `no live model matched selector '${selector}'`, matched: false };
}
