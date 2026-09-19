import type { RiskClass } from "./enums.js";
import type { NormalizedTaskRunInput, TaskRunInput } from "./temporal.js";

export function normalizeTaskRunInput(input: TaskRunInput): NormalizedTaskRunInput {
  const objective = input.objective.trim();
  if (!objective) {
    throw new Error("objective must not be empty");
  }
  if (!input.allowedPaths.length) {
    throw new Error("allowed_paths must not be empty");
  }
  if (!input.acceptance.length) {
    throw new Error("acceptance must not be empty");
  }
  const cwd = input.cwd.trim();
  if (!cwd) {
    throw new Error("cwd must not be empty");
  }
  const maxAttempts = input.maxAttempts ?? 2;
  if (maxAttempts < 1) {
    throw new Error("max_attempts must be >= 1");
  }
  const speculativeParallelism = input.speculativeParallelism ?? 2;
  if (speculativeParallelism < 1 || speculativeParallelism > 4) {
    throw new Error("speculative_parallelism must be between 1 and 4");
  }
  const providerTimeoutSeconds = input.providerTimeoutSeconds ?? 3600;
  if (providerTimeoutSeconds < 1) {
    throw new Error("provider_timeout_seconds must be >= 1");
  }
  const maxOutputChars = input.maxOutputChars ?? 8000;
  if (maxOutputChars < 200) {
    throw new Error("max_output_chars must be >= 200");
  }
  return {
    objective,
    allowedPaths: [...input.allowedPaths],
    acceptance: [...input.acceptance],
    cwd,
    constraints: [...(input.constraints ?? [])],
    preferredProviders: [...(input.preferredProviders ?? [])],
    requiredCapabilities: [...(input.requiredCapabilities ?? ["code", "filesystem", "git"])],
    modelSelector: input.modelSelector ?? "default",
    reasoningEffort: input.reasoningEffort ?? "medium",
    baseRef: input.baseRef ?? null,
    maxAttempts,
    speculativeParallelism,
    humanGateAt: (input.humanGateAt ?? "R4") as RiskClass,
    waitForHumanReview: Boolean(input.waitForHumanReview),
    providerTimeoutSeconds,
    maxOutputChars,
  };
}
