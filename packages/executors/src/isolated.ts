import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { ExecutionError, type ExecutionBackend, type ExecutionOutcome, type ExecutionRequest } from "./types.js";

function globToRegExp(pattern: string): RegExp {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replaceAll("*", ".*").replaceAll("?", ".");
  return new RegExp(`^${escaped}$`);
}

function pathAllowed(path: string, allowedPaths: string[]): boolean {
  const normalized = path.replaceAll("\\", "/");
  return allowedPaths.some((raw) => {
    const rule = raw.replaceAll("\\", "/").replace(/\/$/, "");
    return normalized === rule || normalized.startsWith(`${rule}/`) || globToRegExp(rule).test(normalized);
  });
}

function safeWritePath(cwd: string, rawPath: string): string {
  if (isAbsolute(rawPath) || rawPath.split("/").includes("..") || rawPath.split("\\").includes("..")) {
    throw new ExecutionError(`write path escapes cwd: '${rawPath}'`);
  }
  const path = resolve(cwd, rawPath);
  const rel = relative(resolve(cwd), path);
  if (rel.startsWith("..") || isAbsolute(rel)) {
    throw new ExecutionError(`write path escapes cwd: '${rawPath}'`);
  }
  return path;
}

export function isolatedWritePath(allowedPaths: string[]): string {
  for (const raw of allowedPaths) {
    const rule = raw.replaceAll("\\", "/").trim().replace(/\/$/, "");
    if (!rule || rule.startsWith("/") || rule.split("/").includes("..")) {
      continue;
    }
    if (!rule.includes("*") && !rule.includes("?")) {
      return rule;
    }
    const prefix = rule.replace(/\/+\*\*?$/, "").replace(/\*+$/, "").replace(/\/$/, "");
    if (prefix && !prefix.includes("*") && !prefix.includes("?")) {
      const candidate = `${prefix}/sandbox-result.txt`;
      if (pathAllowed(candidate, allowedPaths)) {
        return candidate;
      }
    }
  }
  throw new ExecutionError("no writable allowed path");
}

export class IsolatedHostedBackend implements ExecutionBackend {
  async execute(request: ExecutionRequest): Promise<ExecutionOutcome> {
    if (!existsSync(request.cwd)) {
      throw new ExecutionError(`provider working directory not found: ${request.cwd}`);
    }
    const relativePath = isolatedWritePath(request.allowedPaths ?? []);
    const path = safeWritePath(request.cwd, relativePath);
    mkdirSync(dirname(path), { recursive: true });
    const summary = request.prompt.trim().slice(0, 200) || "bounded hosted write";
    writeFileSync(path, `Isolated sandbox write\n${summary}\n`, "utf8");
    const result = {
      status: "complete",
      provider: request.provider,
      changedPaths: [relativePath],
      checks: ["sandbox isolation: writes limited to allowed paths"],
      remainingConcerns: ["None known"],
    };
    return {
      provider: request.provider,
      returnCode: 0,
      stdout: JSON.stringify(result),
      stderr: "",
      sessionId: `sandbox-${request.sessionName ?? "session"}`,
      usage: { inputTokens: 0, outputTokens: 0 },
    };
  }
}
