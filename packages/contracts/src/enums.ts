export const RISK_LEVELS = ["R0", "R1", "R2", "R3", "R4"] as const;
export type RiskClass = (typeof RISK_LEVELS)[number];

export const EXECUTION_CLASSES = ["decision", "workhorse", "review", "specialist"] as const;
export type ExecutionClass = (typeof EXECUTION_CLASSES)[number];

export const REASONING_EFFORTS = [
  "none",
  "minimal",
  "low",
  "medium",
  "high",
  "xhigh",
  "max",
] as const;
export type ReasoningEffort = (typeof REASONING_EFFORTS)[number];

export const TASK_STATUSES = [
  "created",
  "assessing",
  "routing",
  "executing",
  "waiting_for_human_review",
  "complete",
  "review_required",
  "rejected",
  "failed",
] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const RESULT_STATUSES = ["complete", "blocked", "failed"] as const;
export type ResultStatus = (typeof RESULT_STATUSES)[number];

export const EXECUTION_SHAPES = [
  "single_worker",
  "worker_plus_review",
  "parallel_workers",
] as const;
export type ExecutionShape = (typeof EXECUTION_SHAPES)[number];

export const INTERVENTIONS = [
  "accept",
  "correct_same",
  "switch_executor",
  "stronger_model",
  "human_review",
] as const;
export type Intervention = (typeof INTERVENTIONS)[number];
