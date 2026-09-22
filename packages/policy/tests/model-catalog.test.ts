import { describe, expect, it } from "vitest";
import { catalogFromPayload, catalogPageFromPayload, readModelCatalog, resolveModel, resolveReasoningEffort } from "../src/routing.js";

describe("live model catalogs", () => {
  it("accepts the real Codex model/list data envelope and request slug", () => {
    const [model] = catalogFromPayload({ result: { data: [{ id: "ui-id", model: "actual-model", isDefault: true,
      supportedReasoningEfforts: [{ reasoningEffort: "medium" }, { reasoningEffort: "high" }], defaultReasoningEffort: "medium" }], nextCursor: null } });
    expect(model?.modelId).toBe("actual-model");
    expect(model?.supportedReasoningEfforts).toEqual(["medium", "high"]);
    expect(model?.defaultReasoningEffort).toBe("medium");
  });
  it("retains legacy array and models envelopes", () => {
    expect(catalogFromPayload([{ id: "old" }])[0]?.modelId).toBe("old");
    expect(catalogFromPayload({ models: [{ id: "old" }] })[0]?.modelId).toBe("old");
  });
  it("keeps absent capabilities unknown", () => {
    const model = catalogFromPayload([{ id: "old", default: "false" }])[0]!;
    expect(model.supportedReasoningEfforts).toBeUndefined();
    expect(model.isDefault).toBe(false);
    expect(resolveReasoningEffort(model, "high").matched).toBe(false);
  });
  it("does not invent unsupported reasoning levels", () => {
    const model = catalogFromPayload({ data: [{ model: "future", supportedReasoningEfforts: [{ reasoningEffort: "custom" }] }] })[0]!;
    expect(resolveReasoningEffort(model, "none").effort).toBeNull();
    expect(resolveReasoningEffort(model, "custom").effort).toBe("custom");
  });
  it("rejects malformed capabilities", () => {
    expect(() => catalogFromPayload({ data: [{ id: "x", supportedReasoningEfforts: {} }] })).toThrow();
    expect(() => catalogFromPayload({ data: [null] })).toThrow();
    expect(() => catalogFromPayload({ data: [{ id: "x", supportedReasoningEfforts: [123] }] })).toThrow();
  });
  it("does not claim a partial page is a complete model list", () => {
    const payload = { data: [{ id: "first" }], nextCursor: "next" };
    expect(catalogPageFromPayload(payload).nextCursor).toBe("next");
    expect(() => catalogFromPayload(payload)).toThrow(/paginated/);
  });
  it("follows opaque cursors", async () => {
    const cursors: Array<string | null> = [];
    const models = await readModelCatalog(async cursor => {
      cursors.push(cursor);
      return cursor === null ? { data: [{ id: "first" }], nextCursor: "opaque" } : { data: [{ id: "second" }], nextCursor: null };
    });
    expect(models.map(m => m.modelId)).toEqual(["first", "second"]);
    expect(cursors).toEqual([null, "opaque"]);
  });
  it("rejects repeated or excessive pagination", async () => {
    await expect(readModelCatalog(async () => ({ data: [], nextCursor: "again" }))).rejects.toThrow(/repeated/);
    let page = 0;
    await expect(readModelCatalog(async () => ({ data: [], nextCursor: String(++page) }))).rejects.toThrow(/budget/);
  });
  it("rejects ambiguous aliases instead of choosing the first Astra", () => {
    const models = catalogFromPayload([{ id: "astra-a", displayName: "Astra A" }, { id: "astra-b", displayName: "Astra B" }]);
    expect(resolveModel(models, "astra").model).toBeNull();
    expect(resolveModel(models, "astra-b").model?.modelId).toBe("astra-b");
  });
  it("never silently substitutes an explicitly missing model", () => {
    const models = catalogFromPayload([{ id: "other", isDefault: true }]);
    expect(resolveModel(models, "missing-astra").model).toBeNull();
    expect(resolveModel(models, "frontier").matched).toBe(false);
  });
});
