import { describe, expect, it } from "vitest";
import {
  HeuristicDecisionEngine,
  JevDecisionEngine,
  StaticDecisionEngine,
  decisionEngineFromEnv,
  type DecisionAnswer,
} from "../src/decisions.js";
import { assessResult, assessTask } from "../src/intelligence.js";

describe("heuristic and static intelligence", () => {
  it("uses a single worker for a docs objective", async () => {
    const assessment = await assessTask(new HeuristicDecisionEngine(), {
      objective: "Update the docs README",
      allowedPaths: ["docs/README.md"],
      acceptance: ["the documentation is accurate"],
    });
    expect(assessment.finalRisk).toBe("R0");
    expect(assessment.executionShape).toBe("single_worker");
    expect(assessment.reviewRequired).toBe(false);
  });

  it("requires review for auth work without a default human gate", async () => {
    const assessment = await assessTask(new HeuristicDecisionEngine(), {
      objective: "Implement auth token rotation",
      allowedPaths: ["docs/README.md"],
      acceptance: ["the documentation is accurate"],
    });
    const gated = await assessTask(new HeuristicDecisionEngine(), {
      objective: "Implement auth token rotation",
      allowedPaths: ["docs/README.md"],
      acceptance: ["the documentation is accurate"],
      humanGateAt: "R3",
    });
    expect(assessment.finalRisk).toBe("R3");
    expect(assessment.executionShape).toBe("worker_plus_review");
    expect(assessment.reviewRequired).toBe(true);
    expect(assessment.humanGateRequired).toBe(false);
    expect(gated.humanGateRequired).toBe(true);
  });

  it("accepts verified success and switches on failure", async () => {
    const accepted = await assessResult(new HeuristicDecisionEngine(), {
      objective: "Update the docs README",
      riskClass: "R1",
      provider: "scripted",
      exitCode: 0,
      evidenceComplete: true,
      workerResult: "complete",
      checks: ["pytest -q: passed"],
    });
    const failed = await assessResult(new HeuristicDecisionEngine(), {
      objective: "Update the docs README",
      riskClass: "R1",
      provider: "scripted",
      exitCode: 1,
      evidenceComplete: false,
      workerResult: "failed",
    });
    expect(accepted.accepted).toBe(true);
    expect(failed.intervention).toBe("switch_executor");
    expect(failed.accepted).toBe(false);
  });

  it("does not let semantic risk lower the deterministic floor", async () => {
    const answer = (
      name: string,
      kind: DecisionAnswer["kind"],
      value: DecisionAnswer["value"],
      certainty: number,
      probabilities: Record<string, number>,
    ): DecisionAnswer => ({
      name,
      kind,
      value,
      certainty,
      probabilities,
      providerConfidence: null,
    });
    const engine = new StaticDecisionEngine({
      risk: answer("risk", "choice", "R1", 0.9, { R1: 0.9 }),
      delegate: answer("delegate", "noul", true, 0.9, { true: 0.9, false: 0.1 }),
      ambiguous: answer("ambiguous", "noul", false, 0.9, { true: 0.1, false: 0.9 }),
      execution_shape: answer("execution_shape", "choice", "single_worker", 0.9, {
        single_worker: 0.9,
      }),
      independent_review: answer("independent_review", "noul", false, 0.9, { true: 0.1, false: 0.9 }),
    });
    const result = await assessTask(engine, {
      objective: "Fix authorization and refresh-token replay handling.",
      allowedPaths: ["src/auth/session.py"],
      acceptance: ["Unauthorized replay is rejected."],
    });
    expect(result.heuristicRisk).toBe("R3");
    expect(result.semanticRisk).toBe("R1");
    expect(result.finalRisk).toBe("R3");
    expect(result.reviewRequired).toBe(true);
    expect(result.executionShape).toBe("worker_plus_review");
  });

  it("builds engines from the environment", () => {
    expect(decisionEngineFromEnv({})).toBeInstanceOf(HeuristicDecisionEngine);
    expect(decisionEngineFromEnv({ TYPESAFE_API_KEY: "x" })).toBeInstanceOf(JevDecisionEngine);
    expect(() => decisionEngineFromEnv({ DURABLE_THREADS_DECISION_ENGINE: "bogus" })).toThrow(
      /jev, heuristic/,
    );
  });
});
