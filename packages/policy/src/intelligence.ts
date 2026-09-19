import { RISK_LEVELS, type RiskClass } from "@durable-threads/contracts";
import {
  batchToDict,
  choiceQuestion,
  DecisionPolicy,
  noulQuestion,
  type DecisionBatch,
  type DecisionEngine,
} from "./decisions.js";
import { classifyRisk, meetsThreshold, validateRisk } from "./risk.js";

const RISK_RANK: Record<RiskClass, number> = { R0: 0, R1: 1, R2: 2, R3: 3, R4: 4 };

function noulProbability(batch: DecisionBatch, name: string): number {
  const answer = batch.answers[name];
  if (!answer) {
    throw new Error(`decision answer not found: ${name}`);
  }
  if (typeof answer.probabilities.true === "number") {
    return answer.probabilities.true;
  }
  return answer.value === true ? 1 : 0;
}

function higherRisk(left: string, right: string): RiskClass {
  const leftRisk = validateRisk(left);
  const rightRisk = validateRisk(right);
  return RISK_RANK[leftRisk] >= RISK_RANK[rightRisk] ? leftRisk : rightRisk;
}

export interface TaskAssessment {
  heuristicRisk: RiskClass;
  semanticRisk: RiskClass;
  finalRisk: RiskClass;
  delegateProbability: number;
  ambiguityProbability: number;
  independentReviewProbability: number;
  executionShape: string;
  executionShapeCertainty: number;
  reviewRequired: boolean;
  humanGateRequired: boolean;
  batch: DecisionBatch;
}

export function taskAssessmentToDict(assessment: TaskAssessment): Record<string, unknown> {
  return {
    heuristicRisk: assessment.heuristicRisk,
    semanticRisk: assessment.semanticRisk,
    finalRisk: assessment.finalRisk,
    delegateProbability: assessment.delegateProbability,
    ambiguityProbability: assessment.ambiguityProbability,
    independentReviewProbability: assessment.independentReviewProbability,
    executionShape: assessment.executionShape,
    executionShapeCertainty: assessment.executionShapeCertainty,
    reviewRequired: assessment.reviewRequired,
    humanGateRequired: assessment.humanGateRequired,
    decision: batchToDict(assessment.batch),
  };
}

export interface ResultAssessment {
  semanticCompleteProbability: number;
  evidenceSufficientProbability: number;
  intervention: string;
  interventionCertainty: number;
  integrationReady: boolean;
  accepted: boolean;
  reviewRequired: boolean;
  batch: DecisionBatch;
}

export function resultAssessmentToDict(assessment: ResultAssessment): Record<string, unknown> {
  return {
    semanticCompleteProbability: assessment.semanticCompleteProbability,
    evidenceSufficientProbability: assessment.evidenceSufficientProbability,
    intervention: assessment.intervention,
    interventionCertainty: assessment.interventionCertainty,
    integrationReady: assessment.integrationReady,
    accepted: assessment.accepted,
    reviewRequired: assessment.reviewRequired,
    decision: batchToDict(assessment.batch),
  };
}

export async function assessTask(
  engine: DecisionEngine,
  input: {
    objective: string;
    allowedPaths: string[];
    acceptance: string[];
    context?: Record<string, unknown>;
    policy?: DecisionPolicy;
    humanGateAt?: string;
  },
): Promise<TaskAssessment> {
  const policy = input.policy ?? new DecisionPolicy();
  const humanGateAt = validateRisk(input.humanGateAt ?? "R4");
  const heuristic = classifyRisk({
    objective: input.objective,
    allowedPaths: input.allowedPaths,
    acceptance: input.acceptance,
  });
  const state = {
    objective: input.objective,
    allowedPaths: [...input.allowedPaths],
    acceptance: [...input.acceptance],
    runtime: { ...(input.context ?? {}) },
  };
  const questions = {
    risk: choiceQuestion("Classify consequence risk, not implementation difficulty.", {
      R0: "Mechanical or documentation-only change with negligible consequence.",
      R1: "Bounded isolated feature or bug fix with narrow blast radius.",
      R2: "Integration or contract change across components or external systems.",
      R3: "Critical security, auth, privacy, payments, destructive data, or concurrency work.",
      R4: "Systemic distributed architecture, control-plane, recovery, or platform migration work.",
    }),
    delegate: noulQuestion(
      "Would handing this bounded task to an execution worker improve throughput or isolation?",
      {
        true: "Delegation has a clear implementation/review boundary.",
        false: "The current planner should keep the work local because delegation adds ambiguity or overhead.",
      },
    ),
    ambiguous: noulQuestion(
      "Is the objective materially ambiguous such that execution risks solving the wrong problem?",
      {
        true: "Important requirements or acceptance conditions are unresolved.",
        false: "The task is bounded enough to execute against the supplied contract.",
      },
    ),
    execution_shape: choiceQuestion("Choose the smallest execution shape likely to produce reliable evidence.", {
      single_worker: "One bounded executor is sufficient.",
      worker_plus_review: "One executor followed by independent review is warranted.",
      parallel_workers:
        "Two independent executors are worth the extra cost because uncertainty is high.",
    }),
    independent_review: noulQuestion(
      "Should a successful implementation receive independent review before integration?",
      {
        true: "The consequence or ambiguity justifies a separate reviewer.",
        false: "Deterministic checks are sufficient at this consequence level.",
      },
    ),
  };
  const batch = await engine.decide({ state, questions });
  const riskAnswer = batch.answers.risk;
  if (!riskAnswer) {
    throw new Error("decision answer not found: risk");
  }
  const semanticRisk = String(riskAnswer.value);
  if (!RISK_LEVELS.includes(semanticRisk as RiskClass)) {
    throw new Error(`decision engine returned unsupported risk class: '${semanticRisk}'`);
  }
  const finalRisk = higherRisk(heuristic.riskClass, semanticRisk);
  const shape = batch.answers.execution_shape;
  if (!shape) {
    throw new Error("decision answer not found: execution_shape");
  }
  const independentReviewProbability = noulProbability(batch, "independent_review");
  const reviewRequired =
    meetsThreshold(finalRisk, "R3") ||
    independentReviewProbability >= policy.thresholdFor(finalRisk) ||
    shape.value === "worker_plus_review";
  let executionShape = String(shape.value);
  if (reviewRequired && executionShape === "single_worker") {
    executionShape = "worker_plus_review";
  }
  return {
    heuristicRisk: heuristic.riskClass,
    semanticRisk: semanticRisk as RiskClass,
    finalRisk,
    delegateProbability: noulProbability(batch, "delegate"),
    ambiguityProbability: noulProbability(batch, "ambiguous"),
    independentReviewProbability,
    executionShape,
    executionShapeCertainty: shape.certainty,
    reviewRequired,
    humanGateRequired: meetsThreshold(finalRisk, humanGateAt),
    batch,
  };
}

export async function assessResult(
  engine: DecisionEngine,
  input: {
    objective: string;
    riskClass: string;
    provider: string;
    exitCode: number;
    evidenceComplete: boolean;
    workerResult: string;
    checks?: string[];
    remainingConcerns?: string[];
    policy?: DecisionPolicy;
  },
): Promise<ResultAssessment> {
  const policy = input.policy ?? new DecisionPolicy();
  const risk = validateRisk(input.riskClass);
  const state = {
    objective: input.objective,
    riskClass: risk,
    provider: input.provider,
    exitCode: input.exitCode,
    evidenceComplete: input.evidenceComplete,
    checks: [...(input.checks ?? [])],
    remainingConcerns: [...(input.remainingConcerns ?? [])],
    workerResult: input.workerResult.slice(0, 6000),
  };
  const questions = {
    semantic_complete: noulQuestion(
      "Does the reported result satisfy the user's objective rather than merely completing some work?",
      {
        true: "The result substantively satisfies the objective and stated acceptance intent.",
        false: "Important requested behavior is missing, contradicted, or unresolved.",
      },
    ),
    evidence_sufficient: noulQuestion("Is the supplied evidence sufficient to justify the claimed result?", {
      true: "The checks and reported evidence are proportionate to the claim.",
      false: "The claim is under-evidenced, vague, or depends on unverified assumptions.",
    }),
    intervention: choiceQuestion("Choose the next intervention if this result cannot be integrated as-is.", {
      accept: "The result is complete enough to pass semantic review.",
      correct_same: "A focused correction by the same executor is likely sufficient.",
      switch_executor: "The failure suggests a capability or execution mismatch.",
      stronger_model: "The work needs materially stronger reasoning, not just another attempt.",
      human_review: "The remaining ambiguity or consequence requires a person.",
    }),
  };
  const batch = await engine.decide({ state, questions });
  const intervention = batch.answers.intervention;
  if (!intervention) {
    throw new Error("decision answer not found: intervention");
  }
  const threshold = policy.thresholdFor(risk);
  const semanticProbability = noulProbability(batch, "semantic_complete");
  const evidenceProbability = noulProbability(batch, "evidence_sufficient");
  const deterministicPass = input.exitCode === 0 && input.evidenceComplete;
  const reviewRequired = meetsThreshold(risk, "R3") || intervention.value === "human_review";
  const integrationReady =
    deterministicPass &&
    semanticProbability >= threshold &&
    evidenceProbability >= threshold &&
    intervention.value === "accept";
  return {
    semanticCompleteProbability: semanticProbability,
    evidenceSufficientProbability: evidenceProbability,
    intervention: String(intervention.value),
    interventionCertainty: intervention.certainty,
    integrationReady,
    accepted: integrationReady && !reviewRequired,
    reviewRequired,
    batch,
  };
}
