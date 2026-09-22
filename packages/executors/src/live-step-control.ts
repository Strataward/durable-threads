/** Experimental adapter over an existing authorized Codex App Server connection.
 * No process startup, authentication, provider fallback, or permission changes.
 */
export interface StepControlCapabilities {
  experimentalApi: boolean;
  stepModelSwitching: boolean;
  /** Require an actual run against this build, not source/schema presence alone. */
  runtimeVerified: boolean;
  buildId: string;
  supportedEfforts: readonly string[];
  /** Verify the installed runtime's compaction path before enabling live control. */
  compactionCompatible: boolean;
}
export interface ActiveStepTarget { executionId: string; threadId: string; turnId: string }
export interface StepUpdateReceipt {
  decisionId: string;
  target: ActiveStepTarget;
  requestedEffort: string;
  status: "applied" | "targetUnavailable" | "unknown";
  /** Applied means published, NOT that a subsequent inference consumed the update. */
  effectiveGenerationObserved: false;
}
export type SettingsRpc = (method: "turn/settings/update", params: {
  threadId: string; turnId: string; effort: string;
}) => Promise<{ status: string }>;

export class CodexLiveStepControl {
  private readonly receipts = new Map<string, StepUpdateReceipt>();
  private busy = false;
  private quarantined = false;
  private closed = false;
  private readonly target: ActiveStepTarget;
  private readonly capabilities: StepControlCapabilities;

  constructor(target: ActiveStepTarget, capabilities: StepControlCapabilities, private readonly rpc: SettingsRpc) {
    if (Object.values(target).some((value) => typeof value !== "string" || !value.trim())) {
      throw new Error("an exact execution/thread/turn target is required");
    }
    this.target = { ...target };
    this.capabilities = { ...capabilities, supportedEfforts: [...capabilities.supportedEfforts] };
  }

  async updateEffort(decisionId: string, effort: string): Promise<StepUpdateReceipt> {
    if (!decisionId.trim()) throw new Error("a decision id is required");
    const previous = this.receipts.get(decisionId);
    if (previous) {
      if (previous.requestedEffort !== effort) throw new Error("decision id reused with a different patch");
      return { ...previous, target: { ...previous.target } };
    }
    const caps = this.capabilities;
    if (!caps.experimentalApi || !caps.stepModelSwitching || !caps.runtimeVerified
      || !caps.buildId || !caps.compactionCompatible) throw new Error("live control is not runtime-qualified");
    if (!caps.supportedEfforts.includes(effort)) throw new Error("effort not advertised by the current model");
    if (this.closed || this.quarantined) throw new Error("reconcile execution before further updates");
    if (this.busy) throw new Error("serialize updates; observe current state before another decision");
    if (this.receipts.size >= 64) throw new Error("step-update budget exhausted");
    this.busy = true;
    let status: StepUpdateReceipt["status"] = "unknown";
    try {
      const reply = await this.rpc("turn/settings/update", {
        threadId: this.target.threadId, turnId: this.target.turnId, effort,
      });
      if (reply.status === "applied" || reply.status === "targetUnavailable") status = reply.status;
    } catch {
      // A transport error can occur after publication. Never replay blindly.
      status = "unknown";
    } finally { this.busy = false; }
    this.quarantined = status === "unknown";
    this.closed = status === "targetUnavailable";
    const receipt: StepUpdateReceipt = {
      decisionId, target: { ...this.target }, requestedEffort: effort, status,
      effectiveGenerationObserved: false,
    };
    this.receipts.set(decisionId, receipt);
    return { ...receipt, target: { ...receipt.target } };
  }
}
