import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { ConfigError, parseRoster } from "../src/config.js";
import { PacketError, buildPacket } from "../src/packets.js";
import { EvidenceError, parseWorkerResult, validateEvidence } from "../src/evidence.js";
import { catalogFromPayload, resolveModel, selectWorkers } from "../src/routing.js";
import { classifyRisk } from "../src/risk.js";
import { codexAgentRole, recommendNativeExecution } from "../src/native.js";

const ROOT = fileURLToPath(new URL("../../..", import.meta.url));
const ROSTER = JSON.parse(readFileSync(join(ROOT, "examples/roster.json"), "utf8"));
const MULTI = JSON.parse(readFileSync(join(ROOT, "examples/multi-provider-roster.json"), "utf8"));

describe("roster and routing", () => {
  it("loads the example roster with unique workers", () => {
    const roster = parseRoster(ROSTER);
    expect(roster.projectName).toBe("example-project");
    expect(roster.workers.map((worker) => worker.name)).toEqual([
      "implementation",
      "test-debug",
      "research-docs",
      "security-review",
    ]);
    expect(new Set(roster.workers.map((worker) => worker.threadTitle)).size).toBe(4);
  });

  it("loads a multi-provider roster", () => {
    const roster = parseRoster(MULTI);
    expect(roster.planner.provider).toBe("codex");
    expect(roster.workers.map((worker) => worker.provider)).toEqual(["claude", "grok", "cursor", "codex"]);
  });

  it("rejects duplicate worker names", () => {
    const data = structuredClone(ROSTER);
    data.workers[1].name = data.workers[0].name;
    expect(() => parseRoster(data)).toThrow(ConfigError);
    expect(() => parseRoster(data)).toThrow(/worker names must be unique/);
  });

  it("rejects a selected-worker limit above the worker count", () => {
    const data = structuredClone(ROSTER);
    data.policy.maxSelectedWorkers = 99;
    expect(() => parseRoster(data)).toThrow(/cannot exceed the worker count/);
  });

  it("selects one worker for a bounded change", () => {
    const roster = parseRoster(ROSTER);
    const decision = selectWorkers(roster, {
      objective: "Fix one bounded behaviour.",
      allowedPaths: ["src/example.py"],
      acceptance: ["The focused test passes."],
    });
    expect(decision.selected.map((worker) => worker.name)).toEqual(["implementation"]);
    expect(decision.explicit).toBe(false);
    expect(decision.skipped.map((worker) => worker.name)).toContain("test-debug");
  });

  it("caps independent specialists", () => {
    const roster = parseRoster(ROSTER);
    const decision = selectWorkers(roster, {
      objective: "Fix a security regression and add regression tests.",
      allowedPaths: ["src/example.py"],
      acceptance: ["The security review and tests pass."],
    });
    expect(decision.selected.map((worker) => worker.name)).toEqual(["implementation", "security-review"]);
    expect(decision.reasons.some((reason) => reason.includes("maxSelectedWorkers"))).toBe(true);
  });

  it("rejects explicit routing above policy", () => {
    const roster = parseRoster(ROSTER);
    expect(() =>
      selectWorkers(roster, {
        objective: "Review the repository.",
        requestedWorkers: ["implementation", "test-debug", "research-docs"],
      }),
    ).toThrow(/maxSelectedWorkers/);
  });

  it("resolves live catalog metadata without guessing", () => {
    const catalog = catalogFromPayload({
      models: [
        { id: "astra-live", displayName: "GPT-6 Astra", tier: "frontier" },
        { id: "terra-live", displayName: "Balanced", tier: "balanced" },
        { id: "luna-live", displayName: "Efficient", tier: "efficient" },
      ],
    });
    expect(resolveModel(catalog, "frontier").model?.modelId).toBe("astra-live");
    expect(resolveModel(catalog, "Astra").model?.modelId).toBe("astra-live");
    expect(resolveModel(catalog, "astra-live").model?.displayName).toBe("GPT-6 Astra");
    const missing = resolveModel(catalog, "a-model-that-is-not-in-the-catalog");
    expect(missing.model).toBeNull();
    expect(missing.matched).toBe(false);
  });

  it("falls back to the runtime default when a tier is missing", () => {
    const resolution = resolveModel(
      [{ modelId: "default-live", displayName: "Runtime default", tier: "unknown", isDefault: true }],
      "frontier",
    );
    expect(resolution.model?.modelId).toBe("default-live");
    expect(resolution.matched).toBe(false);
  });
});

describe("packets and evidence", () => {
  it("builds a compact packet", () => {
    const packet = buildPacket(parseRoster(ROSTER).workers[0]!, {
      runId: "demo-run",
      objective: "Fix one bounded behaviour.",
      allowedPaths: ["src/example.py"],
      acceptance: ["The focused test passes."],
      constraints: ["Do not read environment files."],
    });
    expect(packet.schemaVersion).toBe(2);
    expect(packet.provider).toBe("codex");
    expect(packet.allowedPaths).toEqual(["src/example.py"]);
    expect(packet.resultContract).toContain("Return exact checks and results.");
  });

  it("rejects credential-like text", () => {
    expect(() =>
      buildPacket(parseRoster(ROSTER).workers[0]!, {
        runId: "demo-run",
        objective: "Inspect sk-12345678901234567890",
        allowedPaths: ["src/example.py"],
        acceptance: ["The focused test passes."],
        constraints: [],
      }),
    ).toThrow(PacketError);
  });

  it("parses text evidence and matches the diff", () => {
    const result = parseWorkerResult(
      "Status: complete\n" +
        "Provider: claude\n" +
        "Changed paths:\n" +
        "- src/example.py\n" +
        "Checks:\n" +
        "- `pytest tests/test_core.py`: passed\n" +
        "Remaining concerns:\n" +
        "- None known\n",
    );
    const verified = validateEvidence(result, {
      allowedPaths: ["src/**"],
      actualPaths: ["src/example.py"],
    });
    expect(verified.changedPaths).toEqual(["src/example.py"]);
  });

  it("accepts extensible provider ids and rejects invalid ones", () => {
    const good = parseWorkerResult(
      JSON.stringify({
        status: "complete",
        provider: "acme-runner",
        changedPaths: ["src/example.py"],
        checks: ["focused check passed"],
        remainingConcerns: ["None known"],
      }),
    );
    expect(validateEvidence(good, { allowedPaths: ["src/**"] }).provider).toBe("acme-runner");
    const bad = parseWorkerResult(
      JSON.stringify({
        status: "complete",
        provider: "Bad Provider!",
        changedPaths: ["src/example.py"],
        checks: ["focused check passed"],
        remainingConcerns: ["None known"],
      }),
    );
    expect(() => validateEvidence(bad, { allowedPaths: ["src/**"] })).toThrow(/provider id is invalid/);
  });

  it("rejects unsafe and unreported paths", () => {
    for (const path of ["../secret.txt", "/tmp/secret.txt", "docs/../secret.txt"]) {
      const result = parseWorkerResult(
        JSON.stringify({
          status: "complete",
          provider: "claude",
          changedPaths: [path],
          checks: ["focused check passed"],
          remainingConcerns: ["None known"],
        }),
      );
      expect(() =>
        validateEvidence(result, { allowedPaths: ["src/**"], actualPaths: [path] }),
      ).toThrow(/unsafe|outside/);
    }
    const mismatch = parseWorkerResult(
      JSON.stringify({
        status: "complete",
        provider: "claude",
        changedPaths: ["src/example.py"],
        checks: ["focused check passed"],
        remainingConcerns: ["None known"],
      }),
    );
    expect(() =>
      validateEvidence(mismatch, {
        allowedPaths: ["src/**"],
        actualPaths: ["src/example.py", "src/other.py"],
      }),
    ).toThrow(EvidenceError);
  });
});

describe("native hints", () => {
  const worker = (name: string) => parseRoster(ROSTER).workers.find((item) => item.name === name)!;

  it("maps Codex built-in roles", () => {
    expect(codexAgentRole(worker("implementation"))).toBe("worker");
    expect(codexAgentRole(worker("test-debug"))).toBe("worker");
    expect(codexAgentRole(worker("research-docs"))).toBe("explorer");
    expect(codexAgentRole(worker("security-review"))).toBe("default");
  });

  it("lets read-only review share a checkout", () => {
    const hint = recommendNativeExecution(worker("security-review"), { riskClass: "R3" });
    expect(hint.workspaceMode).toBe("shared-readonly");
    expect(hint.parallelSafe).toBe(true);
    expect(hint.frontierReviewRecommended).toBe(true);
  });

  it("prefers isolated worktrees for parallel writers", () => {
    const hint = recommendNativeExecution(worker("implementation"), {
      riskClass: "R2",
      concurrentWriters: 2,
    });
    expect(hint.workspaceMode).toBe("isolated-worktree");
    expect(hint.parallelSafe).toBe(true);
    expect(hint.frontierReviewRecommended).toBe(false);
  });

  it("serializes overlapping writers", () => {
    const hint = recommendNativeExecution(worker("implementation"), {
      riskClass: "R2",
      concurrentWriters: 2,
      overlappingWrites: true,
    });
    expect(hint.workspaceMode).toBe("serial");
    expect(hint.parallelSafe).toBe(false);
  });

  it("rejects a negative writer count", () => {
    expect(() =>
      recommendNativeExecution(worker("implementation"), { riskClass: "R1", concurrentWriters: -1 }),
    ).toThrow(/concurrent_writers/);
  });
});

describe("risk", () => {
  it("classifies docs as R0 and auth as R3", () => {
    expect(
      classifyRisk({
        objective: "Fix a spelling typo in the README",
        allowedPaths: ["README.md"],
        acceptance: ["Docs are accurate"],
      }).riskClass,
    ).toBe("R0");
    expect(
      classifyRisk({
        objective: "Implement auth token rotation",
        allowedPaths: ["src/auth.ts"],
        acceptance: ["Replay is rejected"],
      }).riskClass,
    ).toBe("R3");
  });
});
