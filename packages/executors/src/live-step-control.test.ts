import { describe, expect, it, vi } from "vitest";
import { CodexLiveStepControl } from "./live-step-control.js";
const target = { executionId: "example-execution", threadId: "example-thread", turnId: "example-turn" };
const capabilities = { experimentalApi: true, stepModelSwitching: true, runtimeVerified: true,
  buildId: "test-build", supportedEfforts: ["medium", "high"], compactionCompatible: true };

describe("experimental live-step control", () => {
  it.each(["experimentalApi", "stepModelSwitching", "runtimeVerified", "compactionCompatible"] as const)(
    "requires %s, not just a schema match", async (key) => {
      const rpc = vi.fn();
      const control = new CodexLiveStepControl(target, { ...capabilities, [key]: false }, rpc);
      await expect(control.updateEffort("decision", "high")).rejects.toThrow("not runtime-qualified");
      expect(rpc).not.toHaveBeenCalled();
    },
  );
  it("uses the exact turn, effort-only sparse patch and distinguishes publication from use", async () => {
    const rpc = vi.fn().mockResolvedValue({ status: "applied" });
    const control = new CodexLiveStepControl(target, capabilities, rpc);
    const receipt = await control.updateEffort("decision", "high");
    expect(receipt).toMatchObject({ status: "applied", effectiveGenerationObserved: false });
    expect(rpc).toHaveBeenCalledWith("turn/settings/update", {
      threadId: target.threadId, turnId: target.turnId, effort: "high",
    });
    await control.updateEffort("decision", "high");
    expect(rpc).toHaveBeenCalledTimes(1);
    await expect(control.updateEffort("decision", "medium")).rejects.toThrow();
  });
  it("does not retarget unavailable turns or retry uncertain publication", async () => {
    for (const status of ["targetUnavailable", "unexpected"]) {
      const rpc = vi.fn().mockResolvedValue({ status });
      const control = new CodexLiveStepControl(target, capabilities, rpc);
      await control.updateEffort("decision", "high");
      await expect(control.updateEffort("another", "high")).rejects.toThrow("reconcile");
      expect(rpc).toHaveBeenCalledTimes(1);
    }
  });
  it("quarantines transport errors and rejects unadvertised effort", async () => {
    const rpc = vi.fn().mockRejectedValue(new Error("sensitive transport details"));
    const control = new CodexLiveStepControl(target, capabilities, rpc);
    await expect(control.updateEffort("unsupported", "max")).rejects.toThrow("not advertised");
    expect(await control.updateEffort("decision", "high")).toMatchObject({ status: "unknown" });
    await expect(control.updateEffort("another", "medium")).rejects.toThrow("reconcile");
    expect(rpc).toHaveBeenCalledTimes(1);
  });
  it("does not queue stale concurrent decisions", async () => {
    let finish!: (value: { status: string }) => void;
    const rpc = vi.fn(() => new Promise<{ status: string }>((resolve) => { finish = resolve; }));
    const control = new CodexLiveStepControl(target, capabilities, rpc);
    const first = control.updateEffort("first", "high");
    await expect(control.updateEffort("second", "medium")).rejects.toThrow("serialize");
    finish({ status: "applied" });
    await first;
  });
});
