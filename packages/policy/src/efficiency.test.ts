import { describe, expect, it } from "vitest";
import { completionGate, PRO5_BUDGET, quotaGate, recommendCompute, UsageLedger } from "./efficiency.js";
import type { ComputeState, UsageReceipt } from "./efficiency.js";

const receipt: UsageReceipt = {
  executionId: "example-execution", requestId: "example-request", provider: "openai",
  model: "gpt-6-astra", kind: "generation", inputTokens: 100000,
  cachedInputTokens: 90000, outputTokens: 1000, reasoningTokens: 500, serviceTier: "default",
};
const state: ComputeState = {
  risk: "R1", currentEffort: "medium", supportedEfforts: ["low", "medium", "high", "xhigh", "max"],
  generations: 1, noProgressGenerations: 0, repeatedFailures: 0, elapsedSeconds: 10,
  stableGenerations: 0, difficultReasoning: false, unresolvedCriticalFinding: false,
  waitingForExternalEvent: false, unknownWriterState: false,
};

describe("Pro 5x usage accounting", () => {
  it("deduplicates deltas without double counting cached input or reasoning", () => {
    const ledger = new UsageLedger();
    expect(ledger.record(receipt)).toBe("recorded");
    expect(ledger.record({ ...receipt, privatePrompt: "never store" } as UsageReceipt)).toBe("duplicate");
    expect(ledger.summary()).toMatchObject({ requests: 1, uncachedInputTokens: 10000,
      outputTokens: 1000, reasoningTokens: 500, estimatedCredits: 6,
      accounting: "published-credit-estimate-not-subscription-quota" });
  });
  it("prices Fast separately and counts prewarm/compaction, not only visible turns", () => {
    const ledger = new UsageLedger();
    ledger.record({ ...receipt, serviceTier: "fast" });
    ledger.record({ ...receipt, requestId: "prewarm", kind: "prewarm" });
    ledger.record({ ...receipt, requestId: "compact", kind: "compaction" });
    expect(ledger.summary()).toMatchObject({ requests: 3, generations: 1, prewarms: 1,
      compactions: 1, estimatedCredits: 27 });
  });
  it("never calls unknown providers free or hides conflicting receipts", () => {
    const ledger = new UsageLedger();
    ledger.record({ ...receipt, provider: "another-provider" });
    expect(ledger.summary()).toMatchObject({ pricingComplete: false, unpricedRequests: 1 });
    expect(() => ledger.record({ ...receipt, provider: "another-provider", inputTokens: 100001 })).toThrow();
  });
  it.each([NaN, Infinity, -1, 1.5])("rejects invalid tokens %s", (inputTokens) => {
    expect(() => new UsageLedger().record({ ...receipt, inputTokens })).toThrow();
  });
  it("rejects contradictory subset counters", () => {
    expect(() => new UsageLedger().record({ ...receipt, cachedInputTokens: 100001 })).toThrow();
    expect(() => new UsageLedger().record({ ...receipt, reasoningTokens: 1001 })).toThrow();
  });
});

describe("quota is server-observed, not token-estimated", () => {
  const snapshot = { observedAt: 1000, reached: false, windows: [
    { usedPercent: 10, resetsAt: 1100, windowDurationMins: 300 },
    { usedPercent: 86, resetsAt: 1500, windowDurationMins: 10080 },
  ] };
  it("respects the tighter weekly window and review reserve", () => {
    expect(quotaGate(snapshot, 1001)).toEqual({ action: "pause", remainingPercent: 14 });
    expect(quotaGate({ ...snapshot, windows: snapshot.windows.slice(0, 1) }, 1001).action).toBe("allow");
  });
  it("refreshes missing/stale/expired snapshots rather than assuming a refill", () => {
    expect(quotaGate(null, 1001).action).toBe("refresh");
    expect(quotaGate(snapshot, 1400).action).toBe("refresh");
    expect(quotaGate(snapshot, 1100).action).toBe("refresh");
    expect(quotaGate(snapshot, 999).action).toBe("refresh");
  });
  it("honors exhaustion and rejects invalid reserve", () => {
    expect(quotaGate({ ...snapshot, reached: true }, 1001).action).toBe("pause");
    expect(() => quotaGate(snapshot, 1001, NaN)).toThrow();
  });
});

describe("Astra-first bounded compute", () => {
  it("does nothing for routine medium; does not invoke a decision model", () => {
    expect(recommendCompute(state).action).toBe("hold");
  });
  it("raises on hard reasoning or critical risk without switching providers", () => {
    expect(recommendCompute({ ...state, difficultReasoning: true }).effort).toBe("high");
    expect(recommendCompute({ ...state, risk: "R3" }).action).toBe("set_effort");
  });
  it("downshifts only after stable evidence and preserves explicit maximum", () => {
    expect(recommendCompute({ ...state, currentEffort: "high", stableGenerations: 2 }).action).toBe("hold");
    expect(recommendCompute({ ...state, currentEffort: "high", stableGenerations: 3 }).effort).toBe("medium");
    expect(recommendCompute({ ...state, currentEffort: "max", stableGenerations: 30 }).action).toBe("hold");
    expect(recommendCompute({ ...state, currentEffort: "high", unresolvedCriticalFinding: true, stableGenerations: 30 }).effort).toBe("high");
  });
  it("pauses instead of sacrificing verification when budgets run out", () => {
    expect(recommendCompute({ ...state, risk: "R4", generations: 64 }).action).toBe("pause");
    expect(recommendCompute({ ...state, noProgressGenerations: 6 }).action).toBe("pause");
    expect(recommendCompute({ ...state, repeatedFailures: 3 }).action).toBe("pause");
    expect(recommendCompute({ ...state, unknownWriterState: true }).action).toBe("pause");
  });
  it("waits without inference and refuses unsupported effort", () => {
    expect(recommendCompute({ ...state, waitingForExternalEvent: true }).action).toBe("wait");
    expect(recommendCompute({ ...state, risk: "R3", supportedEfforts: ["medium"] }).action).toBe("pause");
    expect(() => recommendCompute(state, { ...PRO5_BUDGET, maxGenerations: -1 })).toThrow();
  });
});

describe("completion authority", () => {
  it.each([true, false])("approval=%s cannot replace evidence", (reviewApproved) => {
    expect(completionGate({ integrationReady: false, taskReviewRequired: true,
      resultReviewRequired: false, reviewApproved })).toBe("unverified");
  });
  it("task-level review survives a worker's acceptance", () => {
    expect(completionGate({ integrationReady: true, taskReviewRequired: true,
      resultReviewRequired: false, reviewApproved: false })).toBe("review_required");
    expect(completionGate({ integrationReady: true, taskReviewRequired: true,
      resultReviewRequired: false, reviewApproved: true })).toBe("complete");
  });
});
