/** Provider catalog parsing. Unknown capabilities stay unknown, never guessed. */
export interface ModelInfo {
  modelId: string;
  displayName: string;
  tier: string;
  isDefault: boolean;
  supportedReasoningEfforts?: string[];
  defaultReasoningEffort?: string | null;
}
export interface Resolution {
  model: ModelInfo | null;
  reason: string;
  matched: boolean;
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
export function catalogPageFromPayload(payload: unknown): {
  models: ModelInfo[];
  nextCursor: string | null;
} {
  const root = isRecord(payload) && "result" in payload ? payload.result : payload;
  const values = Array.isArray(root) ? root : isRecord(root) ? root.data ?? root.models : undefined;
  if (!Array.isArray(values)) throw new Error("model catalog must contain a data or models array");
  const cursor = isRecord(root) ? root.nextCursor ?? null : null;
  if (cursor !== null && (typeof cursor !== "string" || !cursor)) throw new Error("invalid model catalog cursor");
  const models = values.map((item): ModelInfo => {
    if (!isRecord(item)) throw new Error("invalid model catalog entry");
    // Codex model/list's `model` is the request slug; `id` may be a UI/catalog identity.
    const id = item.model ?? item.id ?? item.slug;
    if (typeof id !== "string" || !id.trim()) throw new Error("model catalog entries need an id");
    const advertised = item.supportedReasoningEfforts ?? item.supported_reasoning_levels;
    const supported = advertised === undefined ? undefined : (() => {
      if (!Array.isArray(advertised)) throw new Error("invalid supported reasoning efforts");
      return [...new Set(advertised.map((entry) => {
        const level = typeof entry === "string" ? entry : isRecord(entry) ? entry.reasoningEffort ?? entry.effort : undefined;
        if (typeof level !== "string" || !level.trim()) throw new Error("invalid reasoning effort entry");
        return level.trim();
      }))];
    })();
    const defaultEffort = item.defaultReasoningEffort ?? item.default_reasoning_level ?? null;
    if (defaultEffort !== null && typeof defaultEffort !== "string") throw new Error("invalid default reasoning effort");
    const result: ModelInfo = {
      modelId: id.trim(),
      displayName: String(item.displayName ?? item.display_name ?? id).trim(),
      tier: String(item.tier ?? item.costTier ?? "unknown").trim().toLowerCase(),
      isDefault: (item.isDefault ?? item.default ?? false) === true,
    };
    if (supported !== undefined) result.supportedReasoningEfforts = supported;
    if (defaultEffort !== null) result.defaultReasoningEffort = defaultEffort;
    return result;
  });
  return { models, nextCursor: cursor as string | null };
}

/** Existing complete-catalog API: partial pages must not masquerade as all available models. */
export function catalogFromPayload(payload: unknown): ModelInfo[] {
  const page = catalogPageFromPayload(payload);
  if (page.nextCursor !== null) throw new Error("model catalog is paginated; use readModelCatalog");
  return page.models;
}
export async function readModelCatalog(
  fetchPage: (cursor: string | null) => Promise<unknown>,
): Promise<ModelInfo[]> {
  const all: ModelInfo[] = [];
  const cursors = new Set<string>();
  let cursor: string | null = null;
  for (let i = 0; i < 20; i++) {
    const page = catalogPageFromPayload(await fetchPage(cursor));
    all.push(...page.models);
    if (page.nextCursor === null) return all;
    if (cursors.has(page.nextCursor)) throw new Error("repeated model catalog cursor");
    cursor = page.nextCursor;
    cursors.add(cursor);
  }
  throw new Error("model catalog exceeded page budget");
}
function normal(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replaceAll("-", " ").trim().split(/\s+/).join(" ");
}
export function resolveModel(catalog: Iterable<ModelInfo>, selector: string): Resolution {
  const models = [...catalog];
  const wanted = normal(selector);
  if (!wanted) return { model: null, matched: false, reason: "empty model selector" };
  const exact = models.filter(m => normal(m.modelId) === wanted || normal(m.displayName) === wanted);
  const aliases = exact.length ? exact : models.filter(m =>
    [...normal(m.modelId).split(" "), ...normal(m.displayName).split(" ")].includes(wanted));
  if (aliases.length === 1) return { model: aliases[0]!, reason: `unique catalog match for '${selector}'`, matched: true };
  if (aliases.length > 1) return { model: null, reason: `ambiguous model selector '${selector}'; use an exact model slug`, matched: false };
  const tierGroups: Record<string, Set<string>> = {
    frontier: new Set(["frontier", "flagship", "high"]),
    balanced: new Set(["balanced", "standard", "medium"]),
    efficient: new Set(["efficient", "low", "mini"]),
  };
  if (Object.hasOwn(tierGroups, wanted)) {
    const candidates = models.filter(m => tierGroups[wanted]!.has(m.tier));
    if (candidates.length) return { model: candidates.find(m => m.isDefault) ?? candidates[0]!, reason: `${wanted} role matched live catalog metadata`, matched: true };
    const defaultModel = models.find(m => m.isDefault);
    if (defaultModel) return { model: defaultModel, reason: `${wanted} role was unavailable; using the runtime default without guessing`, matched: false };
  }
  return { model: null, reason: `no live model matched selector '${selector}'`, matched: false };
}
export function resolveReasoningEffort(model: ModelInfo, requested: string): {
  effort: string | null;
  matched: boolean;
  reason: string;
} {
  const supported = model.supportedReasoningEfforts;
  return supported?.includes(requested)
    ? { effort: requested, matched: true, reason: "advertised by the selected model" }
    : { effort: null, matched: false, reason: "unknown or unsupported effort; retain settings and inspect capabilities" };
}
