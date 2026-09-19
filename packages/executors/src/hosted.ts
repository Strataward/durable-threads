import { HeadlessHttpExecutionBackend, headlessHttpPlugin } from "./headless-http.js";
import { IsolatedHostedBackend } from "./isolated.js";
import { ExecutionRegistry } from "./registry.js";
import { SandboxExecutionBackend, sandboxPlugin } from "./sandbox.js";
import { scriptedExecutorPlugin, ScriptedExecutionBackend } from "./scripted.js";
import type { ExecutionBackend, ExecutorPlugin } from "./types.js";

export interface HostedRegistryOptions {
  enableScripted?: boolean;
  headlessUrl?: string | null;
  sandbox?: boolean;
}

function wrapIsolated(plugin: ExecutorPlugin, isolate: boolean): ExecutorPlugin {
  if (!isolate || !plugin.backendFactory) {
    return plugin;
  }
  const factory = plugin.backendFactory;
  return {
    ...plugin,
    backendFactory: () => new SandboxExecutionBackend(factory()),
  };
}

export function createHostedRegistry(options: HostedRegistryOptions = {}): ExecutionRegistry {
  const registry = new ExecutionRegistry();
  const enableScripted = options.enableScripted ?? process.env.DURABLE_THREADS_ENABLE_SCRIPTED === "1";
  const headlessUrl = options.headlessUrl ?? process.env.DURABLE_THREADS_HEADLESS_URL ?? null;
  const isolate =
    options.sandbox ?? (process.env.DURABLE_THREADS_SANDBOX === "0" ? false : true);

  registry.register(sandboxPlugin(new IsolatedHostedBackend()));
  if (enableScripted) {
    registry.register(wrapIsolated(scriptedExecutorPlugin(), isolate));
  }
  if (headlessUrl) {
    registry.register(wrapIsolated(headlessHttpPlugin(headlessUrl), isolate));
  }
  return registry;
}

export function defaultExecutionRegistry(): ExecutionRegistry {
  return createHostedRegistry();
}

export function wrapSandbox(inner: ExecutionBackend): ExecutionBackend {
  return new SandboxExecutionBackend(inner);
}

export { HeadlessHttpExecutionBackend, ScriptedExecutionBackend, sandboxPlugin };
