import type { ExecutionClass, ReasoningEffort, RiskClass } from "./enums.js";

export interface RoleConfig {
  role: string;
  provider: string;
  modelSelector: string;
  reasoningEffort: ReasoningEffort;
  executionClass: ExecutionClass;
}

export interface WorkerConfig {
  name: string;
  role: string;
  provider: string;
  threadTitle: string;
  purpose: string;
  modelSelector: string;
  reasoningEffort: ReasoningEffort;
  executionClass: ExecutionClass;
  threadId: string | null;
  maxFollowups: number;
  parallel: boolean;
}

export interface EscalationStep {
  modelSelector: string;
  reasoningEffort: ReasoningEffort;
}

export interface StrategyConfig {
  profile: "economy" | "balanced" | "frontier";
  defaultRisk: RiskClass;
  frontierReviewAt: RiskClass;
  sleepingOrchestrator: boolean;
  escalation: EscalationStep[];
}

export interface Roster {
  schemaVersion: 1 | 2;
  projectName: string;
  planner: RoleConfig;
  reviewer: RoleConfig;
  strategy: StrategyConfig;
  workers: WorkerConfig[];
  maxParallelWorkers: number;
  maxSelectedWorkers: number;
  resultMaxChars: number;
  allowThreadCreation: boolean;
}

export interface DelegationPacket {
  schemaVersion: 2;
  runId: string;
  taskName: string;
  role: string;
  provider: string;
  objective: string;
  riskClass: RiskClass;
  executionClass: ExecutionClass;
  decisions: string[];
  invariants: string[];
  nonGoals: string[];
  allowedPaths: string[];
  acceptance: string[];
  constraints: string[];
  resultContract: string[];
  modelSelector: string;
  reasoningEffort: ReasoningEffort;
  maxFollowups: number;
}

export interface WorkerResult {
  status: "complete" | "blocked" | "failed";
  provider: string;
  changedPaths: string[];
  checks: string[];
  remainingConcerns: string[];
}

export interface NativeExecutionHint {
  agentRole: "default" | "explorer" | "worker";
  workspaceMode: "shared-readonly" | "shared-write" | "isolated-worktree" | "serial";
  parallelSafe: boolean;
  frontierReviewRecommended: boolean;
  reason: string;
}
