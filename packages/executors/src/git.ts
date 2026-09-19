import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { EvidenceError } from "@durable-threads/policy";

export function gitChangedPaths(repository: string, baseRef: string | null = null): string[] {
  if (!existsSync(repository)) {
    throw new EvidenceError(`repository not found: ${repository}`);
  }
  const diffArgs = ["diff", "--name-only", "--no-renames"];
  if (baseRef) {
    if (baseRef.startsWith("-")) {
      throw new EvidenceError("base ref must not be an option");
    }
    diffArgs.push(baseRef, "--");
  } else {
    diffArgs.push("HEAD", "--");
  }
  const diff = spawnSync("git", diffArgs, { cwd: repository, encoding: "utf8" });
  if (diff.status !== 0) {
    throw new EvidenceError(diff.stderr.trim() || "could not inspect the git diff");
  }
  const staged = spawnSync("git", ["diff", "--cached", "--name-only", "--no-renames"], {
    cwd: repository,
    encoding: "utf8",
  });
  if (staged.status !== 0) {
    throw new EvidenceError(staged.stderr.trim() || "could not inspect the staged diff");
  }
  const untracked = spawnSync("git", ["ls-files", "--others", "--exclude-standard"], {
    cwd: repository,
    encoding: "utf8",
  });
  if (untracked.status !== 0) {
    throw new EvidenceError(untracked.stderr.trim() || "could not inspect untracked files");
  }
  const paths = new Set<string>();
  for (const output of [diff.stdout, staged.stdout, untracked.stdout]) {
    for (const line of output.split("\n")) {
      const path = line.trim().replaceAll("\\", "/");
      if (path) {
        paths.add(path);
      }
    }
  }
  return [...paths].sort();
}
