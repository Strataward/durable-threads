import {
  condition,
  defineQuery,
  defineSignal,
  executeChild,
  isCancellation,
  proxyActivities,
  setHandler,
  workflowInfo,
} from "@temporalio/workflow";
import type * as activities from "./activities.js";
import type {
  AttemptResult,
  ExecutionAttemptInput,
  NormalizedTaskRunInput,
  ReviewDecision,
  TaskRunInput,
  TaskRunResult,
  WorkflowStatus,
} from "./contracts.js";
import { taskFromInput } from "./contracts.js";

const decisionActivities = proxyActivities<typeof activities>({
  startToCloseTimeout: "45 seconds",
  retry: { initialInterval: "1 second", backoffCoefficient: 2, maximumInterval: "10 seconds", maximumAttempts: 3 },
});

const readActivities = proxyActivities<typeof activities>({
  startToCloseTimeout: "2 minutes",
  retry: { initialInterval: "1 second", backoffCoefficient: 2, maximumInterval: "5 seconds", maximumAttempts: 2 },
});

export const reviewSignal = defineSignal<[ReviewDecision]>("review");
export const statusQuery = defineQuery<WorkflowStatus>("status");

function failedAttempt(provider: string, error: unknown): AttemptResult {
  const name = error instanceof Error ? error.name : "Error";
  const message = error instanceof Error ? error.message : String(error);
  return {
    provider,
    returnCode: 1,
    stdout: "",
    stderr: `child workflow failed: ${name}: ${message}`,
    sessionId: null,
    usage: null,
    verification: {
      complete: false,
      status: "child_failure",
      changedPaths: [],
      checks: [],
      remainingConcerns: ["Execution failed before verified completion."],
      actualPaths: [],
      error: name,
    },
    resultAssessment: {
      integrationReady: false,
      accepted: false,
      reviewRequired: true,
      intervention: "human_review",
      interventionCertainty: 1,
      semanticCompleteProbability: 0,
      evidenceSufficientProbability: 0,
    },
    accepted: false,
    reviewRequired: true,
  };
}

function attemptRank(attempt: AttemptResult): [number, number, number, number] {
  const semantic = attempt.resultAssessment;
  return [
    attempt.accepted ? 1 : 0,
    semantic.integrationReady ? 1 : 0,
    Number(semantic.semanticCompleteProbability ?? 0),
    Number(semantic.evidenceSufficientProbability ?? 0),
  ];
}

function betterAttempt(left: AttemptResult, right: AttemptResult): AttemptResult {
  const leftRank = attemptRank(left);
  const rightRank = attemptRank(right);
  for (let index = 0; index < leftRank.length; index += 1) {
    const diff = (rightRank[index] ?? 0) - (leftRank[index] ?? 0);
    if (diff > 0) {
      return right;
    }
    if (diff < 0) {
      return left;
    }
  }
  return left;
}

function strongerEffort(current: string): string {
  const ladder = ["none", "minimal", "low", "medium", "high", "xhigh", "max"];
  const index = ladder.indexOf(current);
  if (index < 0) {
    return "high";
  }
  return ladder[Math.min(index + 1, ladder.length - 1)]!;
}

export async function agentExecutionWorkflow(request: ExecutionAttemptInput): Promise<AttemptResult> {
  const timeoutSeconds = request.task.providerTimeoutSeconds + 60;
  const outcome = await proxyActivities<typeof activities>({
    startToCloseTimeout: `${timeoutSeconds} seconds`,
    heartbeatTimeout: "45 seconds",
    retry: { maximumAttempts: 1 },
  }).runExecutionActivity(request);
  const workspaceDir =
    typeof outcome.workspaceDir === "string" && outcome.workspaceDir ? outcome.workspaceDir : request.task.cwd;
  const verification = await readActivities.verifyExecutionActivity({
    cwd: workspaceDir,
    baseRef: request.task.baseRef,
    allowedPaths: request.task.allowedPaths,
    stdout: String(outcome.stdout ?? ""),
  });
  const assessment = await decisionActivities.assessResultActivity({
    task: request.task,
    provider: request.provider,
    riskClass: request.riskClass,
    returnCode: Number(outcome.returnCode ?? 0),
    stdout: String(outcome.stdout ?? ""),
    verification,
  });
  const usage = outcome.usage;
  return {
    provider: request.provider,
    returnCode: Number(outcome.returnCode ?? 0),
    stdout: String(outcome.stdout ?? ""),
    stderr: String(outcome.stderr ?? ""),
    sessionId: outcome.sessionId === undefined || outcome.sessionId === null ? null : String(outcome.sessionId),
    usage:
      usage && typeof usage === "object"
        ? Object.fromEntries(Object.entries(usage as Record<string, number>).map(([key, value]) => [key, Number(value)]))
        : null,
    verification,
    resultAssessment: assessment,
    accepted: Boolean(assessment.accepted),
    reviewRequired: Boolean(assessment.reviewRequired),
  };
}

export async function durableTaskWorkflow(input: TaskRunInput): Promise<TaskRunResult> {
  const task: NormalizedTaskRunInput = { ...taskFromInput(input) };
  let phase = "created";
  let risk: string | null = null;
  let round = 0;
  let activeProviders: string[] = [];
  let reviewDecision: ReviewDecision | null = null;

  setHandler(statusQuery, () => ({
    phase,
    risk,
    round,
    activeProviders: [...activeProviders],
    reviewPending: phase === "waiting_for_human_review",
  }));
  setHandler(reviewSignal, (decision) => {
    reviewDecision = decision;
  });

  async function waitForReview(): Promise<ReviewDecision> {
    phase = "waiting_for_human_review";
    reviewDecision = null;
    await condition(() => reviewDecision !== null);
    const decision = reviewDecision;
    if (!decision) {
      throw new Error("review wait resumed without a decision");
    }
    reviewDecision = null;
    return decision;
  }

  function finish(result: Omit<TaskRunResult, "status"> & { status: TaskRunResult["status"] }): TaskRunResult {
    phase = result.status;
    return result;
  }

  async function runChildren(
    current: NormalizedTaskRunInput,
    options: { risk: string; executionShape: string; providers: string[] },
  ): Promise<AttemptResult[]> {
    activeProviders = options.providers;
    const parentId = workflowInfo().workflowId;
    const results = await Promise.all(
      options.providers.map(async (provider, index) => {
        try {
          return await executeChild(agentExecutionWorkflow, {
            args: [
              {
                task: current,
                provider,
                riskClass: options.risk,
                attempt: round,
                executionShape: options.executionShape,
              },
            ],
            workflowId: `${parentId}:exec:${round}:${index}:${provider}`,
          });
        } catch (error) {
          if (isCancellation(error)) {
            throw error;
          }
          return failedAttempt(provider, error);
        }
      }),
    );
    activeProviders = [];
    return results;
  }

  phase = "assessing";
  const taskAssessment = await decisionActivities.assessTaskActivity(task);
  risk = String(taskAssessment.finalRisk);

  if (taskAssessment.humanGateRequired) {
    const decision = await waitForReview();
    if (!decision.approved) {
      return finish({
        status: "rejected",
        finalRisk: risk,
        selectedProvider: null,
        taskAssessment,
        attempts: [],
        reviewNote: decision.note,
      });
    }
  }

  const attempts: AttemptResult[] = [];
  const excluded: string[] = [];
  let preferred = [...task.preferredProviders];
  const executionShape = String(taskAssessment.executionShape);

  for (let roundIndex = 1; roundIndex <= task.maxAttempts; roundIndex += 1) {
    round = roundIndex;
    phase = "routing";
    const routes = await readActivities.routeExecutorsActivity({
      task,
      assessment: taskAssessment,
      excludedProviders: excluded,
      preferredProviders: preferred,
    });
    const providers: string[] = [];
    for (const route of routes) {
      const executor = route.executor as { provider?: string } | undefined;
      const provider = String(executor?.provider ?? "");
      if (provider && !providers.includes(provider)) {
        providers.push(provider);
      }
    }
    if (!providers.length) {
      break;
    }
    phase = "executing";
    const current = await runChildren(task, { risk, executionShape, providers });
    attempts.push(...current);
    const best = current.reduce((left, right) => betterAttempt(left, right));
    const semantic = best.resultAssessment;
    if (best.accepted) {
      return finish({
        status: "complete",
        finalRisk: risk,
        selectedProvider: best.provider,
        taskAssessment,
        attempts,
        reviewNote: null,
      });
    }
    const integrationReady = Boolean(semantic.integrationReady);
    const reviewRequired = Boolean(taskAssessment.reviewRequired) || best.reviewRequired;
    const intervention = String(semantic.intervention ?? "human_review");
    const needsReview =
      reviewRequired && (integrationReady || intervention === "human_review" || intervention === "accept");
    if (needsReview) {
      if (task.waitForHumanReview) {
        const decision = await waitForReview();
        return finish({
          status: decision.approved ? "complete" : "rejected",
          finalRisk: risk,
          selectedProvider: best.provider,
          taskAssessment,
          attempts,
          reviewNote: decision.note,
        });
      }
      return finish({
        status: "review_required",
        finalRisk: risk,
        selectedProvider: best.provider,
        taskAssessment,
        attempts,
        reviewNote: null,
      });
    }
    if (intervention === "switch_executor") {
      if (!excluded.includes(best.provider)) {
        excluded.push(best.provider);
      }
      preferred = [];
    } else if (intervention === "correct_same") {
      preferred = [best.provider];
    } else if (intervention === "stronger_model") {
      task.reasoningEffort = strongerEffort(task.reasoningEffort);
      preferred = [best.provider];
    } else {
      return finish({
        status: "review_required",
        finalRisk: risk,
        selectedProvider: best.provider,
        taskAssessment,
        attempts,
        reviewNote: null,
      });
    }
  }

  const selected = attempts.length
    ? attempts.reduce((left, right) => betterAttempt(left, right)).provider
    : null;
  return finish({
    status: "failed",
    finalRisk: risk ?? "R1",
    selectedProvider: selected,
    taskAssessment,
    attempts,
    reviewNote: null,
  });
}
