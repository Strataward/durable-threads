import { EXECUTOR_ID } from "@durable-threads/policy";
import {
  ExecutionError,
  type ExecutionBackend,
  type ExecutionRequirements,
  type ExecutionSelection,
  type ExecutorDescriptor,
  type ExecutorPlugin,
} from "./types.js";

function assertDescriptor(descriptor: ExecutorDescriptor): void {
  if (!EXECUTOR_ID.test(descriptor.executorId)) {
    throw new Error(`invalid executor_id: '${descriptor.executorId}'`);
  }
  if (!EXECUTOR_ID.test(descriptor.provider)) {
    throw new Error(`invalid provider id: '${descriptor.provider}'`);
  }
  if (!descriptor.runtime.trim()) {
    throw new Error("runtime must be non-empty");
  }
}

export class ExecutionRegistry {
  private readonly plugins = new Map<string, ExecutorPlugin>();

  register(plugin: ExecutorPlugin, replace = false): void {
    assertDescriptor(plugin.descriptor);
    const executorId = plugin.descriptor.executorId;
    if (this.plugins.has(executorId) && !replace) {
      throw new Error(`executor already registered: ${executorId}`);
    }
    this.plugins.set(executorId, plugin);
  }

  get(executorId: string): ExecutorPlugin {
    const direct = this.plugins.get(executorId);
    if (direct) {
      return direct;
    }
    for (const plugin of this.plugins.values()) {
      if (plugin.descriptor.provider === executorId) {
        return plugin;
      }
    }
    throw new ExecutionError(`executor not registered: ${executorId}`);
  }

  descriptors(): ExecutorDescriptor[] {
    return [...this.plugins.values()].map((plugin) => plugin.descriptor);
  }

  available(executorId: string): boolean {
    const plugin = this.get(executorId);
    return plugin.availabilityProbe ? plugin.availabilityProbe() : true;
  }

  backend(executorId: string): ExecutionBackend {
    const plugin = this.get(executorId);
    if (!plugin.backendFactory) {
      throw new ExecutionError(`executor '${executorId}' is native-only and has no headless backend`);
    }
    return plugin.backendFactory();
  }

  rank(requirements: ExecutionRequirements, availableOnly = true): ExecutionSelection[] {
    const preferred = new Map(
      requirements.preferredProviders.map((provider, index) => [
        provider,
        requirements.preferredProviders.length - index,
      ]),
    );
    const excluded = new Set(requirements.excludedProviders);
    const selections: ExecutionSelection[] = [];
    for (const plugin of this.plugins.values()) {
      const descriptor = plugin.descriptor;
      if (excluded.has(descriptor.provider)) {
        continue;
      }
      if (![...requirements.capabilities].every((item) => descriptor.capabilities.has(item))) {
        continue;
      }
      if (requirements.headless && !descriptor.headless) {
        continue;
      }
      if (requirements.persistentSession && !descriptor.persistentSessions) {
        continue;
      }
      if (requirements.structuredOutput && !descriptor.structuredOutput) {
        continue;
      }
      if (requirements.effortControl && !descriptor.supportsEffort) {
        continue;
      }
      if (availableOnly && !this.available(descriptor.executorId)) {
        continue;
      }
      let score = (preferred.get(descriptor.provider) ?? 0) * 100;
      const reasons = ["required capabilities satisfied"];
      if (preferred.has(descriptor.provider)) {
        reasons.push("preferred provider");
      }
      if (descriptor.structuredOutput) {
        score += 5;
        reasons.push("structured output");
      }
      if (descriptor.persistentSessions) {
        score += 3;
        reasons.push("persistent sessions");
      }
      if (descriptor.supportsEffort) {
        score += 1;
        reasons.push("reasoning effort control");
      }
      selections.push({ descriptor, score, reasons });
    }
    return selections.sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.descriptor.executorId.localeCompare(right.descriptor.executorId);
    });
  }

  select(requirements: ExecutionRequirements, count = 1, availableOnly = true): ExecutionSelection[] {
    if (count < 1) {
      throw new Error("count must be >= 1");
    }
    const ranked = this.rank(requirements, availableOnly);
    if (!ranked.length) {
      throw new ExecutionError("no registered executor satisfies the execution requirements");
    }
    return ranked.slice(0, count);
  }
}
