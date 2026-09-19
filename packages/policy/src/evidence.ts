export class EvidenceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EvidenceError";
  }
}

export interface WorkerEvidence {
  status: string;
  provider: string | null;
  changedPaths: string[];
  checks: string[];
  concerns: string[];
}

export const EXECUTOR_ID = /^[a-z0-9][a-z0-9._-]{0,63}$/;

const STATUS = new Set(["complete", "blocked", "failed"]);
const HEADINGS = /^(Status|Provider|Changed paths|Checks|Remaining concerns):\s*(.*)$/i;
const JSON_KEYS = new Set([
  "status",
  "provider",
  "changedPaths",
  "changed_paths",
  "checks",
  "remainingConcerns",
  "remaining_concerns",
  "concerns",
]);

function jsonValues(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item.trim())) {
    throw new EvidenceError(`${field} must be an array of nonempty strings`);
  }
  return value.map((item) => item.trim());
}

function jsonPayload(text: string): Record<string, unknown> | null {
  const candidates: unknown[] = [];
  for (const line of text.split("\n").reverse()) {
    try {
      candidates.push(JSON.parse(line));
    } catch {
      continue;
    }
  }
  try {
    candidates.push(JSON.parse(text));
  } catch {
    // Keep scanning structured fallbacks.
  }
  for (const candidate of candidates) {
    if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
      const keys = Object.keys(candidate);
      if (keys.some((key) => JSON_KEYS.has(key))) {
        return candidate as Record<string, unknown>;
      }
    }
  }
  return null;
}

function sectionValues(text: string, heading: string): string[] {
  const values: string[] = [];
  let active = false;
  for (const line of text.split("\n")) {
    const match = HEADINGS.exec(line.trim());
    if (match) {
      active = match[1]!.toLowerCase() === heading.toLowerCase();
      if (active && match[2]?.trim()) {
        values.push(match[2].trim().replace(/^-\s+/, ""));
      }
      continue;
    }
    if (active && line.trim()) {
      values.push(line.trim().replace(/^-\s+/, "").trim());
    }
  }
  return values.filter(Boolean);
}

export function parseWorkerResult(text: string): WorkerEvidence {
  if (typeof text !== "string" || !text.trim()) {
    throw new EvidenceError("worker result is empty");
  }
  const payload = jsonPayload(text);
  let status = "";
  let provider: string | null = null;
  let changed: string[] = [];
  let checks: string[] = [];
  let concerns: string[] = [];
  if (payload) {
    status = String(payload.status ?? "").trim().toLowerCase();
    provider = typeof payload.provider === "string" ? payload.provider.trim() : null;
    changed = jsonValues(payload.changedPaths ?? payload.changed_paths, "changedPaths");
    checks = jsonValues(payload.checks, "checks");
    concerns = jsonValues(
      payload.remainingConcerns ?? payload.remaining_concerns ?? payload.concerns,
      "remainingConcerns",
    );
    if (!concerns.length) {
      concerns = ["None known"];
    }
  } else {
    const statusMatch = /^Status:\s*(\S+)/im.exec(text);
    const providerMatch = /^Provider:\s*(\S+)/im.exec(text);
    status = statusMatch?.[1]?.trim().toLowerCase() ?? "";
    provider = providerMatch?.[1]?.trim() ?? null;
    changed = sectionValues(text, "Changed paths");
    checks = sectionValues(text, "Checks");
    concerns = sectionValues(text, "Remaining concerns");
  }
  if (!STATUS.has(status)) {
    throw new EvidenceError("worker result must declare status: complete, blocked, or failed");
  }
  return { status, provider, changedPaths: changed, checks, concerns };
}

function globToRegExp(pattern: string): RegExp {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replaceAll("*", ".*").replaceAll("?", ".");
  return new RegExp(`^${escaped}$`);
}

function pathMatches(path: string, allowed: string): boolean {
  const normalized = path.replaceAll("\\", "/");
  const rule = allowed.replaceAll("\\", "/").replace(/\/$/, "");
  return normalized === rule || normalized.startsWith(`${rule}/`) || globToRegExp(rule).test(normalized);
}

function validatePaths(paths: Iterable<string>, allowedPaths: Iterable<string>): string[] {
  const allowed = [...allowedPaths].map((item) => item.trim()).filter(Boolean);
  if (!allowed.length) {
    throw new EvidenceError("at least one allowed path is required");
  }
  const clean: string[] = [];
  for (const rawPath of paths) {
    const path = rawPath.replaceAll("\\", "/").trim();
    if (!path || path.startsWith("/") || path === "." || path.split("/").includes("..")) {
      throw new EvidenceError(`changed path is unsafe: '${rawPath}'`);
    }
    if (!allowed.some((item) => pathMatches(path, item))) {
      throw new EvidenceError(`changed path is outside the allowed paths: ${path}`);
    }
    if (!clean.includes(path)) {
      clean.push(path);
    }
  }
  return clean;
}

export function validateEvidence(
  evidence: WorkerEvidence,
  input: { allowedPaths: Iterable<string>; actualPaths?: Iterable<string> | null },
): WorkerEvidence {
  if (!evidence.provider) {
    throw new EvidenceError("worker result must declare a provider");
  }
  if (!EXECUTOR_ID.test(evidence.provider)) {
    throw new EvidenceError("worker result provider id is invalid");
  }
  const changed = validatePaths(evidence.changedPaths, input.allowedPaths);
  if (evidence.status === "complete" && !evidence.checks.length) {
    throw new EvidenceError("complete worker result must include exact checks");
  }
  if (evidence.status === "complete" && !evidence.concerns.length) {
    throw new EvidenceError("complete worker result must declare remaining concerns");
  }
  if (
    evidence.status === "complete" &&
    evidence.checks.some((check) => /\b(failed|skipped|not run)\b/i.test(check))
  ) {
    throw new EvidenceError("complete result contains an unsuccessful check");
  }
  if (input.actualPaths !== undefined && input.actualPaths !== null) {
    const actual = [
      ...new Set(
        [...input.actualPaths]
          .map((path) => path.replaceAll("\\", "/").trim())
          .filter(Boolean),
      ),
    ];
    validatePaths(actual, input.allowedPaths);
    const changedSet = new Set(changed);
    const actualSet = new Set(actual);
    if (changedSet.size !== actualSet.size || [...changedSet].some((path) => !actualSet.has(path))) {
      const missing = [...actualSet].filter((path) => !changedSet.has(path)).sort();
      const extra = [...changedSet].filter((path) => !actualSet.has(path)).sort();
      const details: string[] = [];
      if (missing.length) {
        details.push(`missing claims: ${missing.join(", ")}`);
      }
      if (extra.length) {
        details.push(`claims without diff: ${extra.join(", ")}`);
      }
      throw new EvidenceError(`worker paths do not match the actual diff (${details.join("; ")})`);
    }
  }
  return {
    status: evidence.status,
    provider: evidence.provider,
    changedPaths: changed,
    checks: evidence.checks,
    concerns: evidence.concerns,
  };
}

export function evidenceToDict(evidence: WorkerEvidence): Record<string, unknown> {
  return {
    status: evidence.status,
    provider: evidence.provider,
    changedPaths: [...evidence.changedPaths],
    checks: [...evidence.checks],
    remainingConcerns: [...evidence.concerns],
  };
}
