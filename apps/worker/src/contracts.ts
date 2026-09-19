import {
  normalizeTaskRunInput,
  type AttemptResult,
  type NormalizedTaskRunInput,
  type ReviewDecision,
  type TaskRunInput,
  type TaskRunResult,
  type WorkflowStatus,
} from "@durable-threads/contracts";

export type {
  AttemptResult,
  NormalizedTaskRunInput,
  ReviewDecision,
  TaskRunInput,
  TaskRunResult,
  WorkflowStatus,
};

export interface RouteExecutorsInput {
  task: NormalizedTaskRunInput;
  assessment: Record<string, unknown>;
  excludedProviders: string[];
  preferredProviders: string[];
}

export interface ExecutionAttemptInput {
  task: NormalizedTaskRunInput;
  provider: string;
  riskClass: string;
  attempt: number;
  executionShape: string;
}

export interface VerificationInput {
  cwd: string;
  baseRef: string | null;
  allowedPaths: string[];
  stdout: string;
}

export interface ResultDecisionInput {
  task: NormalizedTaskRunInput;
  provider: string;
  riskClass: string;
  returnCode: number;
  stdout: string;
  verification: Record<string, unknown>;
}

export function taskFromInput(input: TaskRunInput): NormalizedTaskRunInput {
  return normalizeTaskRunInput(input);
}
