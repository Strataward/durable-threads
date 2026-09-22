/** Subscription-aware policy. Credit estimates are NOT remaining ChatGPT quota. */
export const PRO5_POLICY_VERSION = "pro5-2026-09-22";
export const CREDIT_RATE_SOURCE = "https://learn.chatgpt.com/docs/pricing";
export const CREDIT_RATE_DATE = "2026-09-22";

export interface UsageReceipt {
  executionId: string;
  requestId: string;
  provider: string;
  model: string;
  kind: "generation" | "prewarm" | "compaction";
  /** Per-request deltas only; never pass a thread's cumulative usage. */
  inputTokens: number;
  cachedInputTokens: number;
  outputTokens: number;
  /** A subset of outputTokens, not an additional charge. */
  reasoningTokens: number;
  serviceTier: "default" | "fast";
}

const CREDIT_RATES: Record<string, readonly [number, number, number]> = {
  "gpt-6-astra": [250, 25, 1250],
  "gpt-5.6-sol": [100, 10, 500],
  "gpt-5.6-terra": [50, 5, 300],
  "gpt-5.6-luna": [5, 0.5, 30],
};

function nonnegativeInteger(value: number, name: string): void {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`${name} must be a nonnegative safe integer`);
}
function finiteRange(value: number, low: number, high: number, name: string): void {
  if (!Number.isFinite(value) || value < low || value > high) throw new Error(`invalid ${name}`);
}

/** Metadata-only ledger. Never store prompts, transcripts, credentials, or tool output here. */
export class UsageLedger {
  private readonly receipts = new Map<string, UsageReceipt>();

  record(receipt: UsageReceipt): "recorded" | "duplicate" {
    for (const key of ["executionId", "requestId", "provider", "model"] as const) {
      if (typeof receipt[key] !== "string" || !receipt[key].trim()) throw new Error(`missing ${key}`);
    }
    if (!["generation", "prewarm", "compaction"].includes(receipt.kind)) throw new Error("invalid receipt kind");
    if (!["default", "fast"].includes(receipt.serviceTier)) throw new Error("unknown service tier");
    for (const key of ["inputTokens", "cachedInputTokens", "outputTokens", "reasoningTokens"] as const) {
      nonnegativeInteger(receipt[key], key);
    }
    if (receipt.cachedInputTokens > receipt.inputTokens) throw new Error("cached input exceeds total input");
    if (receipt.reasoningTokens > receipt.outputTokens) throw new Error("reasoning exceeds total output");
    // Whitelist fields: callers may hand us transport objects containing private data.
    const clean: UsageReceipt = {
      executionId: receipt.executionId, requestId: receipt.requestId,
      provider: receipt.provider, model: receipt.model, kind: receipt.kind,
      inputTokens: receipt.inputTokens, cachedInputTokens: receipt.cachedInputTokens,
      outputTokens: receipt.outputTokens, reasoningTokens: receipt.reasoningTokens,
      serviceTier: receipt.serviceTier,
    };
    const key = JSON.stringify([receipt.provider, receipt.executionId, receipt.requestId]);
    const previous = this.receipts.get(key);
    if (previous) {
      if ((Object.keys(clean) as (keyof UsageReceipt)[]).some((field) => clean[field] !== previous[field])) {
        throw new Error("conflicting usage for an already recorded request");
      }
      return "duplicate";
    }
    this.receipts.set(key, clean);
    return "recorded";
  }

  summary() {
    let generations = 0, prewarms = 0, compactions = 0;
    let inputTokens = 0, cachedInputTokens = 0, outputTokens = 0, reasoningTokens = 0;
    let estimatedCredits = 0, unpricedRequests = 0;
    for (const item of this.receipts.values()) {
      if (item.kind === "generation") generations += 1;
      if (item.kind === "prewarm") prewarms += 1;
      if (item.kind === "compaction") compactions += 1;
      inputTokens += item.inputTokens;
      cachedInputTokens += item.cachedInputTokens;
      outputTokens += item.outputTokens;
      reasoningTokens += item.reasoningTokens;
      const rate = item.provider === "openai" ? CREDIT_RATES[item.model] : undefined;
      if (!rate) { unpricedRequests += 1; continue; }
      estimatedCredits += (
        (item.inputTokens - item.cachedInputTokens) * rate[0]
        + item.cachedInputTokens * rate[1] + item.outputTokens * rate[2]
      ) / 1_000_000 * (item.serviceTier === "fast" ? 2.5 : 1);
    }
    for (const total of [inputTokens, cachedInputTokens, outputTokens, reasoningTokens]) {
      nonnegativeInteger(total, "aggregate tokens");
    }
    return {
      requests: this.receipts.size, generations, prewarms, compactions,
      inputTokens, cachedInputTokens, uncachedInputTokens: inputTokens - cachedInputTokens,
      outputTokens, reasoningTokens, estimatedCredits, unpricedRequests,
      pricingComplete: unpricedRequests === 0, rateDate: CREDIT_RATE_DATE,
      accounting: "published-credit-estimate-not-subscription-quota" as const,
    };
  }
}

export interface QuotaWindow {
  usedPercent: number;
  resetsAt: number; // Unix seconds, as returned by Codex.
  windowDurationMins: number;
}
export interface QuotaSnapshot {
  observedAt: number; // Unix seconds recorded by the trusted receiver, not guessed from resetsAt.
  windows: QuotaWindow[]; // All applicable windows for the selected metered bucket.
  reached: boolean;
}

/** Never presume a timer reset refilled quota; fetch another server snapshot. */
export function quotaGate(snapshot: QuotaSnapshot | null, now: number, reservePercent = 15) {
  finiteRange(now, 0, Number.MAX_SAFE_INTEGER, "current time");
  finiteRange(reservePercent, 0, 99, "quota reserve");
  const refresh = { action: "refresh" as const, remainingPercent: null };
  if (!snapshot || !snapshot.windows.length) return refresh;
  if (!Number.isFinite(snapshot.observedAt) || now < snapshot.observedAt || now - snapshot.observedAt > 300) return refresh;
  if (snapshot.reached) return { action: "pause" as const, remainingPercent: 0 };
  let remainingPercent = 100;
  for (const window of snapshot.windows) {
    if (!Number.isFinite(window.usedPercent) || window.usedPercent < 0 || window.usedPercent > 100
      || !Number.isFinite(window.resetsAt) || window.resetsAt <= now
      || !Number.isFinite(window.windowDurationMins) || window.windowDurationMins <= 0) return refresh;
    remainingPercent = Math.min(remainingPercent, 100 - window.usedPercent);
  }
  return { action: remainingPercent <= reservePercent ? "pause" as const : "allow" as const, remainingPercent };
}

export interface ComputeState {
  risk: "R0" | "R1" | "R2" | "R3" | "R4";
  currentEffort: string;
  supportedEfforts: readonly string[];
  generations: number;
  noProgressGenerations: number;
  repeatedFailures: number;
  elapsedSeconds: number;
  stableGenerations: number;
  difficultReasoning: boolean;
  unresolvedCriticalFinding: boolean;
  waitingForExternalEvent: boolean;
  unknownWriterState: boolean;
}
export interface ComputeBudget {
  maxGenerations: number;
  maxNoProgressGenerations: number;
  maxRepeatedFailures: number;
  maxElapsedSeconds: number;
  downshiftAfter: number;
}
export const PRO5_BUDGET: Readonly<ComputeBudget> = Object.freeze({
  maxGenerations: 64, maxNoProgressGenerations: 6, maxRepeatedFailures: 3,
  maxElapsedSeconds: 2700, downshiftAfter: 3,
});

/** Caller supplies observed state. This does not introspect a running Codex agent. */
export function recommendCompute(state: ComputeState, budget: ComputeBudget = PRO5_BUDGET) {
  for (const [key, value] of Object.entries(budget)) {
    if (!Number.isSafeInteger(value) || value < 1) throw new Error(`invalid budget ${key}`);
  }
  for (const key of ["generations", "noProgressGenerations", "repeatedFailures", "elapsedSeconds", "stableGenerations"] as const) {
    nonnegativeInteger(state[key], key);
  }
  if (!["R0", "R1", "R2", "R3", "R4"].includes(state.risk)) throw new Error("invalid risk");
  const hold = (reason: string) => ({ action: "hold" as const, effort: state.currentEffort, reason });
  const pause = (reason: string) => ({ action: "pause" as const, effort: state.currentEffort, reason });
  if (state.unknownWriterState) return pause("reconcile-writer-before-resuming");
  if (state.generations >= budget.maxGenerations || state.elapsedSeconds >= budget.maxElapsedSeconds) return pause("budget-boundary");
  if (state.repeatedFailures >= budget.maxRepeatedFailures || state.noProgressGenerations >= budget.maxNoProgressGenerations) return pause("no-progress-circuit-breaker");
  if (state.waitingForExternalEvent) return { action: "wait" as const, effort: state.currentEffort, reason: "no-inference-while-idle" };
  if (!state.supportedEfforts.includes(state.currentEffort)) return pause("current-effort-not-advertised");
  const critical = state.risk === "R3" || state.risk === "R4" || state.unresolvedCriticalFinding;
  const desired = critical || state.difficultReasoning ? "high" : "medium";
  const rank = ["low", "medium", "high", "xhigh", "max"];
  const currentRank = rank.indexOf(state.currentEffort), desiredRank = rank.indexOf(desired);
  if (currentRank < 0) return hold("unknown-effort-semantics");
  if (!state.supportedEfforts.includes(desired)) return critical ? pause("required-effort-unavailable") : hold("no-supported-target");
  // Never silently undo an explicit xhigh/max selection or weaken unresolved critical work.
  if (currentRank >= 3 || (critical && currentRank >= desiredRank)) return hold("preserve-explicit-or-critical-effort");
  if (currentRank === desiredRank) return hold("no-change");
  if (currentRank > desiredRank && state.stableGenerations < budget.downshiftAfter) return hold("downshift-hysteresis");
  return { action: "set_effort" as const, effort: desired, reason: critical ? "risk-floor" : state.difficultReasoning ? "reasoning-needed" : "stable-bounded-work" };
}

/** Approval is not a substitute for observed acceptance evidence. */
export function completionGate(input: {
  integrationReady: boolean; taskReviewRequired: boolean; resultReviewRequired: boolean; reviewApproved: boolean;
}): "complete" | "review_required" | "unverified" {
  if (input.integrationReady !== true) return "unverified";
  if ((input.taskReviewRequired || input.resultReviewRequired) && input.reviewApproved !== true) return "review_required";
  return "complete";
}
