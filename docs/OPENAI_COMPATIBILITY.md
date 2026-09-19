# OpenAI compatibility and documentation audit

Last audited: **2026-09-19**.

This document separates current OpenAI product behavior from Durable Threads policy. Product surfaces move quickly; re-check the linked sources when installation, packaging, subagent, model, or worktree semantics matter.

## Current OpenAI behavior used by this repository

### Skills author reusable workflows

OpenAI describes skills as reusable workflows made from instructions plus optional resources/scripts. Codex can discover local skills from supported `.agents/skills` locations, and skills can also be bundled inside plugins.

**Durable Threads consequence:** the workflow has one canonical `SKILL.md` tree under the plugin.

### Plugins distribute reusable capabilities

Durable Threads follows the current Codex plugin layout: plugin manifest under `.codex-plugin/plugin.json`, bundled skills under `skills/`, and a repository marketplace under `.agents/plugins/marketplace.json`.

**Durable Threads consequence:** **plugin = distribution; bundled skill = workflow implementation**. They are not two products a normal user must install separately.

Sources:

- https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/plugin-creator
- https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/plugin-json-spec.md

### Git repository marketplace sources

The current Codex CLI accepts Git marketplace sources and exposes a marketplace refresh command.

Install:

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Update an installed copy:

```bash
codex plugin marketplace upgrade strataward && codex plugin add durable-threads@strataward
```

The CLI currently exposes `add`, `list`, `marketplace`, and `remove` at the plugin level; updating a Git-backed plugin is therefore modeled as refreshing the marketplace snapshot and reinstalling the plugin rather than calling a nonexistent `codex plugin update` command.

Sources:

- https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs
- https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs

### Native Codex agent roles

Current Codex includes built-in agent roles including `explorer` and `worker`. The runtime applies role-specific configuration to spawned children and exposes project/user-defined role configuration.

**Durable Threads consequence:** native Codex subagents are the preferred default execution mechanism. Durable Threads maps discovery to `explorer`, bounded implementation/debugging to `worker`, and independent review to a read-only custom/default role.

Source:

- https://github.com/openai/codex/blob/main/codex-rs/core/src/agent/role.rs

### Native agent configuration

Current Codex configuration includes agent-level controls such as:

- `agents.default_subagent_model`
- `agents.default_subagent_reasoning_effort`
- `agents.max_concurrent_threads_per_session`

**Durable Threads consequence:** model/effort and fan-out policy can compile into native runtime controls instead of requiring a second scheduler.

Sources:

- https://github.com/openai/codex/blob/main/codex-rs/config/src/config_toml.rs
- https://github.com/openai/codex/blob/main/codex-rs/core/config.schema.json

### Project-defined agents

Current Codex supports project agent-role files under `.codex/agents/`. Role configuration can constrain model/reasoning behavior, instructions, and sandbox mode.

**Durable Threads consequence:** the repository ships optional read-only reviewer/security examples under `examples/codex-agents/`, but normal users do not need to install them.

Sources:

- https://github.com/openai/codex/blob/main/codex-rs/external-agent-migration/src/scope.rs
- https://github.com/openai/codex/blob/main/codex-rs/core/src/agent/role.rs

### Worktree support

Recent Codex releases added experimental worktree support for isolated checkouts.

**Durable Threads consequence:** the policy is **subagents for parallel cognition, worktrees for parallel mutation**. Multiple independent writers should prefer isolated worktrees when supported; overlapping writers should be serialized.

Source:

- https://github.com/openai/codex/releases

### OpenAI Agents API

OpenAI announced the Agents API on September 10, 2026. It exposes the managed Codex harness for cloud/headless execution and supports multi-agent configuration with `enabled` plus `max_concurrent_subagents`.

**Durable Threads consequence:** the Agents API is a natural optional backend for CI/SaaS/automation and richer telemetry, but it is not required for normal plugin use.

Sources:

- https://openai.com/index/introducing-the-agents-api/
- https://developers.openai.com/api/reference/typescript/resources/beta/subresources/agents/methods/create
- https://developers.openai.com/api/reference/typescript/resources/beta/subresources/agents/subresources/sessions/subresources/subagents/methods/list

## Durable Threads policy — not an OpenAI guarantee

The following are project choices or empirical strategies:

- efficient high/XHigh implementation as a preferred workhorse strategy
- R0–R4 consequence classification
- frontier/specialist review at R3+ by default
- the sleeping-orchestrator invariant
- one focused correction by default
- escalation from efficient -> balanced -> frontier
- `explorer`/`worker` role mapping for our workflow
- the worktree isolation rule for parallel writers
- any claim about relative quota efficiency or task-level model performance

The docs should label these as policy, recommendation, or observed behavior rather than attributing them to OpenAI.

## Claims we intentionally avoid

We do not claim that Durable Threads is currently listed in the public Plugin Directory, that every ChatGPT surface can install directly from this GitHub repository, that plugin installation configures Claude/Grok/Cursor, that model names or allowance ratios are permanent, that worktrees make overlapping changes semantically safe, or that Durable Threads itself enforces the host sandbox.

## Release audit checklist

Before changing installation or compatibility docs:

1. Check the current Codex plugin creator/spec and plugin CLI.
2. Check native agent-role implementation and agent config fields.
3. Check current release notes for worktree/subagent behavior.
4. Check the current Agents API docs if managed execution is discussed.
5. Confirm supported product surfaces.
6. Run repository validation and CI.
7. Update the audit date.