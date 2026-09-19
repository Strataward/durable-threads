import type { Intervention, RiskClass, TaskStatus } from "./enums.js";

export interface TaskRunInput {
  objective: string;
  allowedPaths: string[];
  acceptance: string[];
  cwd: string;
  constraints?: string[];
  preferredProviders?: string[];
  requiredCapabilities?: string[];
  modelSelector?: string;
  reasoningEffort?: string;
  baseRef?: string | null;
  maxAttempts?: number;
  speculativeParallelism?: number;
  humanGateAt?: RiskClass;
  waitForHumanReview?: boolean;
  providerTimeoutSeconds?: number;
  maxOutputChars?: number;
}

export interface NormalizedTaskRunInput {
  objective: string;
  allowedPaths: string[];
  acceptance: string[];
  cwd: string;
  constraints: string[];
  preferredProviders: string[];
  requiredCapabilities: string[];
  modelSelector: string;
  reasoningEffort: string;
  baseRef: string | null;
  maxAttempts: number;
  speculativeParallelism: number;
  humanGateAt: RiskClass;
  waitForHumanReview: boolean;
  providerTimeoutSeconds: number;
  maxOutputChars: number;
}

export interface ReviewDecision {
  approved: boolean;
  note: string;
}

export interface WorkflowStatus {
  phase: string;
  risk: string | null;
  round: number;
  activeProviders: string[];
  reviewPending: boolean;
}

export interface AttemptResult {
  provider: string;
  returnCode: number;
  stdout: string;
  stderr: string;
  sessionId: string | null;
  usage: Record<string, number> | null;
  verification: Record<string, unknown>;
  resultAssessment: Record<string, unknown>;
  accepted: boolean;
  reviewRequired: boolean;
}

export interface TaskRunResult {
  status: TaskStatus;
  finalRisk: string;
  selectedProvider: string | null;
  taskAssessment: Record<string, unknown>;
  attempts: AttemptResult[];
  reviewNote: string | null;
}

export interface TaskRecord {
  id: string;
  workflowId: string;
  objective: string;
  status: TaskStatus;
  risk: string | null;
  phase: string;
  reviewPending: boolean;
  result: TaskRunResult | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskRequest {
  objective: string;
  allowedPaths: string[];
  acceptance: string[];
  constraints?: string[];
  cwd?: string;
  preferredProviders?: string[];
  modelSelector?: string;
  reasoningEffort?: string;
  maxAttempts?: number;
  humanGateAt?: RiskClass;
  waitForHumanReview?: boolean;
}

export interface CreateTaskResponse {
  id: string;
  workflowId: string;
}

export type { Intervention };
