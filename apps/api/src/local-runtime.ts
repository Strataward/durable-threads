import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { normalizeTaskRunInput, type ReviewDecision, type TaskRunInput, type TaskRunResult } from "@durable-threads/contracts";
import {
  createHostedRegistry,
  ExecutionError,
  gitChangedPaths,
  type ExecutionRequirements,
} from "@durable-threads/executors";
import {
  assessResult,
  assessTask,
  decisionEngineFromEnv,
  parseWorkerResult,
  resultAssessmentToDict,
  taskAssessmentToDict,
  validateEvidence,
} from "@durable-threads/policy";

export function initWorkspace(): string {
  const root = mkdtempSync(join(tmpdir(), "dt-task-"));
  spawnSync("git", ["init", root], { encoding: "utf8" });
  writeFileSync(join(root, "README.md"), "workspace\n");
  mkdirSync(join(root, "src"), { recursive: true });
  writeFileSync(join(root, "src", ".keep"), "");
  spawnSync("git", ["add", "README.md", "src"], { cwd: root });
  spawnSync(
    "git",
    ["-c", "user.name=Durable Threads", "-c", "user.email=durable@local", "commit", "-m", "workspace"],
    { cwd: root },
  );
  return root;
}

function strongerEffort(current: string): string {
  const ladder = ["none", "minimal", "low", "medium", "high", "xhigh", "max"];
  const index = ladder.indexOf(current);
  if (index < 0) {
    return "high";
  }
  return ladder[Math.min(index + 1, ladder.length - 1)]!;
}

async function verify(cwd: string, stdout: string, allowedPaths: string[], baseRef: string | null) {
  try {
    const evidence = parseWorkerResult(stdout);
    const actualPaths = gitChangedPaths(cwd, baseRef);
    const verified = validateEvidence(evidence, { allowedPaths, actualPaths });
    return {
      complete: verified.status === "complete",
      status: verified.status,
      changedPaths: [...verified.changedPaths],
      checks: [...verified.checks],
      remainingConcerns: [...verified.concerns],
      actualPaths,
      error: null as string | null,
    };
  } catch (error) {
    return {
      complete: false,
      status: "invalid_evidence",
      changedPaths: [] as string[],
      checks: [] as string[],
      remainingConcerns: ["Evidence verification failed."],
      actualPaths: [] as string[],
      error: error instanceof Error ? `${error.name}: ${error.message}` : String(error),
    };
  }
}

export interface LocalRuntimeHooks {
  onStatus(status: { phase: string; risk: string | null; reviewPending: boolean }): Promise<void>;
  waitForReview(): Promise<ReviewDecision>;
}

export async function runLocalTask(input: TaskRunInput, hooks: LocalRuntimeHooks): Promise<TaskRunResult> {
  const task = { ...normalizeTaskRunInput(input) };
  const engine = decisionEngineFromEnv();
  await hooks.onStatus({ phase: "assessing", risk: null, reviewPending: false });
  const assessment = await assessTask(engine, {
    objective: task.objective,
    allowedPaths: task.allowedPaths,
    acceptance: task.acceptance,
    humanGateAt: task.humanGateAt,
  });
  const taskAssessment = taskAssessmentToDict(assessment);
  await hooks.onStatus({
    phase: assessment.humanGateRequired ? "waiting_for_human_review" : "routing",
    risk: assessment.finalRisk,
    reviewPending: assessment.humanGateRequired,
  });
  if (assessment.humanGateRequired) {
    const decision = await hooks.waitForReview();
    if (!decision.approved) {
      return {
        status: "rejected",
        finalRisk: assessment.finalRisk,
        selectedProvider: null,
        taskAssessment,
        attempts: [],
        reviewNote: decision.note,
      };
    }
  }

  const registry = createHostedRegistry();
  const attempts: TaskRunResult["attempts"] = [];
  const excluded: string[] = [];
  let preferred = [...task.preferredProviders];

  for (let round = 1; round <= task.maxAttempts; round += 1) {
    await hooks.onStatus({ phase: "routing", risk: assessment.finalRisk, reviewPending: false });
    const requirements: ExecutionRequirements = {
      capabilities: new Set(task.requiredCapabilities),
      headless: true,
      persistentSession: false,
      structuredOutput: true,
      effortControl: false,
      preferredProviders: preferred,
      excludedProviders: excluded,
    };
    let routes;
    try {
      routes = registry.select(requirements, 1, true);
    } catch (error) {
      if (error instanceof ExecutionError) {
        break;
      }
      throw error;
    }
    const providers = [...new Set(routes.map((route) => route.descriptor.provider))];
    if (!providers.length) {
      break;
    }
    await hooks.onStatus({ phase: "executing", risk: assessment.finalRisk, reviewPending: false });
    for (const provider of providers) {
      const backend = registry.backend(provider);
      const outcome = await backend.execute({
        provider,
        prompt: task.objective,
        cwd: task.cwd,
        modelSelector: task.modelSelector,
        reasoningEffort: task.reasoningEffort,
        timeoutSeconds: task.providerTimeoutSeconds,
        maxOutputChars: task.maxOutputChars,
        allowedPaths: task.allowedPaths,
      });
      const cwd = outcome.workspaceDir ?? task.cwd;
      const verification = await verify(cwd, outcome.stdout, task.allowedPaths, task.baseRef);
      const result = await assessResult(engine, {
        objective: task.objective,
        riskClass: assessment.finalRisk,
        provider,
        exitCode: outcome.returnCode,
        evidenceComplete: Boolean(verification.complete),
        workerResult: outcome.stdout,
        checks: verification.checks,
        remainingConcerns: verification.remainingConcerns,
      });
      const attempt = {
        provider,
        returnCode: outcome.returnCode,
        stdout: outcome.stdout,
        stderr: outcome.stderr,
        sessionId: outcome.sessionId,
        usage: outcome.usage,
        verification,
        resultAssessment: resultAssessmentToDict(result),
        accepted: result.accepted,
        reviewRequired: result.reviewRequired,
      };
      attempts.push(attempt);
      if (result.accepted) {
        return {
          status: "complete",
          finalRisk: assessment.finalRisk,
          selectedProvider: provider,
          taskAssessment,
          attempts,
          reviewNote: null,
        };
      }
      const needsReview =
        result.reviewRequired &&
        (result.integrationReady || result.intervention === "human_review" || result.intervention === "accept");
      if (needsReview) {
        if (task.waitForHumanReview) {
          await hooks.onStatus({
            phase: "waiting_for_human_review",
            risk: assessment.finalRisk,
            reviewPending: true,
          });
          const decision = await hooks.waitForReview();
          return {
            status: decision.approved ? "complete" : "rejected",
            finalRisk: assessment.finalRisk,
            selectedProvider: provider,
            taskAssessment,
            attempts,
            reviewNote: decision.note,
          };
        }
        return {
          status: "review_required",
          finalRisk: assessment.finalRisk,
          selectedProvider: provider,
          taskAssessment,
          attempts,
          reviewNote: null,
        };
      }
      if (result.intervention === "switch_executor") {
        excluded.push(provider);
        preferred = [];
      } else if (result.intervention === "correct_same") {
        preferred = [provider];
      } else if (result.intervention === "stronger_model") {
        task.reasoningEffort = strongerEffort(task.reasoningEffort);
        preferred = [provider];
      } else {
        return {
          status: "review_required",
          finalRisk: assessment.finalRisk,
          selectedProvider: provider,
          taskAssessment,
          attempts,
          reviewNote: null,
        };
      }
    }
  }

  return {
    status: "failed",
    finalRisk: assessment.finalRisk,
    selectedProvider: attempts.at(-1)?.provider ?? null,
    taskAssessment,
    attempts,
    reviewNote: null,
  };
}
