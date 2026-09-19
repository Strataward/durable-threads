import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { normalizeTaskRunInput } from "../src/validate.js";

const ROOT = fileURLToPath(new URL("../../..", import.meta.url));

describe("contract schemas", () => {
  it("keeps the skill RESULT schema as the contracts source of truth", () => {
    const skill = readFileSync(
      join(ROOT, "plugins/durable-threads/skills/durable-threads/references/RESULT.schema.json"),
      "utf8",
    );
    const contracts = readFileSync(join(ROOT, "packages/contracts/schemas/result.schema.json"), "utf8");
    expect(contracts).toBe(skill);
    const schema = JSON.parse(skill) as { properties: { provider: { pattern?: string; enum?: string[] } } };
    expect(schema.properties.provider.pattern).toBe("^[a-z0-9][a-z0-9._-]{0,63}$");
    expect(schema.properties.provider.enum).toBeUndefined();
  });

  it("normalizes a hosted task without a preferred CLI provider", () => {
    const task = normalizeTaskRunInput({
      objective: "Fix a spelling typo in the README",
      allowedPaths: ["README.md"],
      acceptance: ["The README is accurate."],
      cwd: "/tmp/workspace",
    });
    expect(task.preferredProviders).toEqual([]);
    expect(task.requiredCapabilities).toEqual(["code", "filesystem", "git"]);
    expect(task.humanGateAt).toBe("R4");
  });
});
