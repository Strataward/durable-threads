import { RISK_LEVELS, type RiskClass } from "@durable-threads/contracts";

const RISK_RANK: Record<RiskClass, number> = {
  R0: 0,
  R1: 1,
  R2: 2,
  R3: 3,
  R4: 4,
};

const R4 = /\b(architecture|architectural|distributed|multi[- ]region|consensus|disaster recovery|cross[- ]service|systemic|platform migration|control plane|data plane)\b/i;
const R3 =
  /\b(auth|authentication|authorization|permission|payment|billing|crypto|cryptograph|secret|credential|privacy|pii|production|database migration|schema migration|delete data|destructive|concurren|race condition|locking|idempotency|security|vulnerab)\w*\b/i;
const R2 =
  /\b(api|integration|webhook|queue|cache|database|schema|migration|cross[- ]module|multiple modules|public contract|backward compat|dependency upgrade|release)\w*\b/i;
const R0 = /\b(typo|spelling|formatting|comment|comments|readme|documentation|docs only|rename only)\b/i;
const CHANGE =
  /\b(add|build|change|create|debug|fix|implement|migrate|modify|refactor|remove|repair|update)\b/i;

export interface RiskAssessment {
  riskClass: RiskClass;
  reasons: string[];
  explicit: boolean;
}

export function validateRisk(value: string): RiskClass {
  const risk = value.toUpperCase().trim();
  if (!(risk in RISK_RANK)) {
    throw new Error(`risk must be one of: ${RISK_LEVELS.join(", ")}`);
  }
  return risk as RiskClass;
}

export function meetsThreshold(risk: string, threshold: string): boolean {
  return RISK_RANK[validateRisk(risk)] >= RISK_RANK[validateRisk(threshold)];
}

export function classifyRisk(input: {
  objective: string;
  allowedPaths?: Iterable<string>;
  acceptance?: Iterable<string>;
  explicit?: string | null;
  default?: string;
}): RiskAssessment {
  if (input.explicit) {
    return {
      riskClass: validateRisk(input.explicit),
      reasons: ["risk explicitly supplied by the planner"],
      explicit: true,
    };
  }

  const defaultRisk = validateRisk(input.default ?? "R1");
  const allowedPaths = [...(input.allowedPaths ?? [])];
  const acceptance = [...(input.acceptance ?? [])];
  const items = [input.objective, ...allowedPaths, ...acceptance];
  const context = items
    .filter((item): item is string => typeof item === "string" && Boolean(item.trim()))
    .map((item) => item.trim())
    .join(" ");

  if (R4.test(context)) {
    return {
      riskClass: "R4",
      reasons: ["systemic or architecture-level signal detected"],
      explicit: false,
    };
  }
  if (R3.test(context)) {
    return {
      riskClass: "R3",
      reasons: ["critical security, data, production, or concurrency signal detected"],
      explicit: false,
    };
  }
  if (R2.test(context)) {
    return {
      riskClass: "R2",
      reasons: ["integration or public-contract signal detected"],
      explicit: false,
    };
  }
  if (R0.test(context) && !CHANGE.test(context)) {
    return {
      riskClass: "R0",
      reasons: ["mechanical or documentation-only signal detected"],
      explicit: false,
    };
  }
  const codePaths = allowedPaths.some(
    (path) => path.startsWith("src/") || path.startsWith("app/") || path.startsWith("packages/"),
  );
  if (R0.test(context) && !codePaths) {
    return {
      riskClass: "R0",
      reasons: ["mechanical or documentation-only signal detected"],
      explicit: false,
    };
  }
  return {
    riskClass: defaultRisk,
    reasons: [`no higher-risk signal detected; using default ${defaultRisk}`],
    explicit: false,
  };
}
