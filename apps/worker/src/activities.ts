import { Context } from "@temporalio/activity";
import {
  createHostedRegistry,
  ExecutionError,
  gitChangedPaths,
  outcomeToDict,
  selectionToDict,
  type ExecutionRequest,
  type ExecutionRequirements,
} from "@durable-threads/executors";
import {
  EvidenceError,
  assessResult,
  assessTask,
  decisionEngineFromEnv,
  parseWorkerResult,
  resultAssessmentToDict,
  taskAssessmentToDict,
  validateEvidence,
} from "@durable-threads/policy";
import type {
  ExecutionAttemptInput,
  ResultDecisionInput,
  RouteExecutorsInput,
  VerificationInput,
} from "./contracts.js";
import { type NormalizedTaskRunInput } from "./contracts.js";

function registry() {
  return createHostedRegistry();
}

export async function assessTaskActivity(task: NormalizedTaskRunInput): Promise<Record<string, unknown>> {
  const engine = decisionEngineFromEnv();
  const assessment = await assessTask(engine, {
    objective: task.objective,
    allowedPaths: task.allowedPaths,
    acceptance: task.acceptance,
    context: {
      constraints: task.constraints,
      preferredProviders: task.preferredProviders,
      requiredCapabilities: task.requiredCapabilities,
      maxAttempts: task.maxAttempts,
      speculativeParallelism: task.speculativeParallelism,
    },
    humanGateAt: task.humanGateAt,
  });
  return taskAssessmentToDict(assessment);
}

export async function routeExecutorsActivity(request: RouteExecutorsInput): Promise<Record<string, unknown>[]> {
  const hosted = registry();
  const task = request.task;
  const preferred = request.preferredProviders.length ? request.preferredProviders : task.preferredProviders;
  const requirements: ExecutionRequirements = {
    capabilities: new Set(task.requiredCapabilities),
    headless: true,
    persistentSession: false,
    structuredOutput: true,
    effortControl: false,
    preferredProviders: preferred,
    excludedProviders: request.excludedProviders,
  };
  let count = 1;
  const mutatingCheckout = task.requiredCapabilities.some((item) => item === "filesystem" || item === "git");
  if (request.assessment.executionShape === "parallel_workers" && !mutatingCheckout) {
    count = task.speculativeParallelism;
  }
  try {
    return hosted.select(requirements, count, true).map((selection) => selectionToDict(selection));
  } catch (error) {
    if (error instanceof ExecutionError) {
      return [];
    }
    throw error;
  }
}

function runtimePrompt(request: ExecutionAttemptInput): string {
  const task = request.task;
  const constraints = task.constraints.map((item) => `- ${item}`).join("\n") || "- None supplied";
  const allowed = task.allowedPaths.map((item) => `- ${item}`).join("\n");
  const acceptance = task.acceptance.map((item) => `- ${item}`).join("\n");
  return `OBJECTIVE
${task.objective}

RISK
${request.riskClass}

ALLOWED PATHS
${allowed}

ACCEPTANCE
${acceptance}

CONSTRAINTS
${constraints}

EXECUTION RULES
- Work only inside the allowed paths unless a generated lockfile or required metadata
  change is unavoidable; report any such exception.
- Do not expose credentials, environment secrets, or private data.
- Run focused deterministic checks before claiming completion.
- Do not claim a check passed unless you executed it.

RESULT CONTRACT
Return a JSON object with exactly these semantic fields (additional diagnostic fields are allowed):
{
  "status": "complete|blocked|failed",
  "provider": "${request.provider}",
  "changedPaths": ["path"],
  "checks": ["exact command/check and result"],
  "remainingConcerns": ["concern or None known"]
}
`;
}

export async function runExecutionActivity(request: ExecutionAttemptInput): Promise<Record<string, unknown>> {
  const hosted = registry();
  const backend = hosted.backend(request.provider);
  const execution: ExecutionRequest = {
    provider: request.provider,
    prompt: runtimePrompt(request),
    cwd: request.task.cwd,
    modelSelector: request.task.modelSelector,
    reasoningEffort: request.task.reasoningEffort,
    sessionName: `dt-${request.attempt}-${request.provider}`,
    timeoutSeconds: request.task.providerTimeoutSeconds,
    maxOutputChars: request.task.maxOutputChars,
    allowedPaths: request.task.allowedPaths,
  };
  const task = backend.execute(execution);
  const heartbeatMs = 30_000;
  while (true) {
    const winner = await Promise.race([
      task.then((outcome) => ({ kind: "done" as const, outcome })),
      new Promise<{ kind: "beat" }>((resolve) => setTimeout(() => resolve({ kind: "beat" }), heartbeatMs)),
    ]);
    if (winner.kind === "beat") {
      Context.current().heartbeat({
        provider: request.provider,
        attempt: request.attempt,
        status: "running",
      });
      continue;
    }
    return outcomeToDict(winner.outcome);
  }
}

export async function verifyExecutionActivity(request: VerificationInput): Promise<Record<string, unknown>> {
  try {
    const evidence = parseWorkerResult(request.stdout);
    const actualPaths = gitChangedPaths(request.cwd, request.baseRef);
    const verified = validateEvidence(evidence, {
      allowedPaths: request.allowedPaths,
      actualPaths,
    });
    return {
      complete: verified.status === "complete",
      status: verified.status,
      changedPaths: [...verified.changedPaths],
      checks: [...verified.checks],
      remainingConcerns: [...verified.concerns],
      actualPaths,
      error: null,
    };
  } catch (error) {
    if (error instanceof EvidenceError || error instanceof Error) {
      return {
        complete: false,
        status: "invalid_evidence",
        changedPaths: [],
        checks: [],
        remainingConcerns: ["Evidence verification failed."],
        actualPaths: [],
        error: `${error.name}: ${error.message}`,
      };
    }
    throw error;
  }
}

export async function assessResultActivity(request: ResultDecisionInput): Promise<Record<string, unknown>> {
  const engine = decisionEngineFromEnv();
  const verification = request.verification;
  const assessment = await assessResult(engine, {
    objective: request.task.objective,
    riskClass: request.riskClass,
    provider: request.provider,
    exitCode: request.returnCode,
    evidenceComplete: Boolean(verification.complete),
    workerResult: request.stdout,
    checks: Array.isArray(verification.checks) ? (verification.checks as string[]) : [],
    remainingConcerns: Array.isArray(verification.remainingConcerns)
      ? (verification.remainingConcerns as string[])
      : [],
  });
  return resultAssessmentToDict(assessment);
}
