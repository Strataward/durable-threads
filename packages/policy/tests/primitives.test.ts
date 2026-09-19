import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseRoster } from "../src/config.js";
import { parseWorkerResult, validateEvidence } from "../src/evidence.js";
import { HeuristicDecisionEngine } from "../src/decisions.js";
import { assessTask } from "../src/intelligence.js";
import { classifyRisk } from "../src/risk.js";
import { selectWorkers } from "../src/routing.js";

const ROOT = fileURLToPath(new URL("../../..", import.meta.url));
const ROSTER = JSON.parse(readFileSync(join(ROOT, "examples/roster.json"), "utf8"));

describe("primitive cost regression", () => {
  const roster = parseRoster(ROSTER);
  const evidence = parseWorkerResult(
    JSON.stringify({
      status: "complete",
      provider: "scripted",
      changedPaths: ["src/example.py"],
      checks: ["python -m pytest -q: passed"],
      remainingConcerns: ["None known"],
    }),
  );

  it("keeps deterministic primitives under 10 ms", async () => {
    const classifyStarted = performance.now();
    classifyRisk({
      objective: "Fix a spelling typo in the README",
      allowedPaths: ["README.md"],
      acceptance: ["Docs are accurate"],
    });
    expect(performance.now() - classifyStarted).toBeLessThan(10);

    const routeStarted = performance.now();
    selectWorkers(roster, {
      objective: "Fix one bounded behaviour.",
      allowedPaths: ["src/example.py"],
      acceptance: ["The focused test passes."],
    });
    expect(performance.now() - routeStarted).toBeLessThan(10);

    const evidenceStarted = performance.now();
    validateEvidence(evidence, { allowedPaths: ["src/**"], actualPaths: ["src/example.py"] });
    expect(performance.now() - evidenceStarted).toBeLessThan(10);

    const heuristicStarted = performance.now();
    await assessTask(new HeuristicDecisionEngine(), {
      objective: "Implement auth token rotation",
      allowedPaths: ["src/auth.ts"],
      acceptance: ["Replay is rejected"],
    });
    expect(performance.now() - heuristicStarted).toBeLessThan(50);
  });
});
