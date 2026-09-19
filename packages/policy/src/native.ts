import type { NativeExecutionHint, WorkerConfig } from "@durable-threads/contracts";
import { meetsThreshold, validateRisk } from "./risk.js";

const NATIVE_AGENT_ROLES = new Set(["default", "explorer", "worker"]);
const WORKSPACE_MODES = new Set(["shared-readonly", "shared-write", "isolated-worktree", "serial"]);
const READ_ONLY_ROLES = new Set(["research-docs", "security-review"]);

export function codexAgentRole(worker: WorkerConfig): NativeExecutionHint["agentRole"] {
  if (worker.role === "research-docs") {
    return "explorer";
  }
  if (worker.executionClass === "workhorse" || worker.role === "implementation" || worker.role === "test-debug") {
    return "worker";
  }
  return "default";
}

export function recommendNativeExecution(
  worker: WorkerConfig,
  input: { riskClass: string; concurrentWriters?: number; overlappingWrites?: boolean },
): NativeExecutionHint {
  const risk = validateRisk(input.riskClass);
  const concurrentWriters = input.concurrentWriters ?? 1;
  if (concurrentWriters < 0) {
    throw new Error("concurrent_writers must be >= 0");
  }
  const agentRole = codexAgentRole(worker);
  if (!NATIVE_AGENT_ROLES.has(agentRole)) {
    throw new Error(`unsupported native agent role: ${agentRole}`);
  }
  const readOnly =
    READ_ONLY_ROLES.has(worker.role) || worker.executionClass === "review" || worker.executionClass === "specialist";
  let workspaceMode: NativeExecutionHint["workspaceMode"];
  let parallelSafe: boolean;
  let reason: string;
  if (readOnly) {
    workspaceMode = "shared-readonly";
    parallelSafe = true;
    reason = "read-only exploration/review can share the parent checkout";
  } else if (input.overlappingWrites) {
    workspaceMode = "serial";
    parallelSafe = false;
    reason = "overlapping write ownership must be serialized";
  } else if (concurrentWriters > 1) {
    workspaceMode = "isolated-worktree";
    parallelSafe = true;
    reason = "independent parallel writers should use isolated worktrees";
  } else {
    workspaceMode = "shared-write";
    parallelSafe = true;
    reason = "one bounded writer can use the shared checkout";
  }
  if (!WORKSPACE_MODES.has(workspaceMode)) {
    throw new Error(`unsupported workspace mode: ${workspaceMode}`);
  }
  return {
    agentRole,
    workspaceMode,
    parallelSafe,
    frontierReviewRecommended: meetsThreshold(risk, "R3"),
    reason,
  };
}
