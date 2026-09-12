# OpenAI compatibility and documentation audit

Last audited: **2026-09-12**.

This document separates current OpenAI product behavior from Durable Threads policy. Product surfaces move quickly; re-check the linked sources when installation, packaging, or plugin semantics matter.

## Current OpenAI behavior used by this repository

### Skills author reusable workflows

OpenAI describes skills as reusable workflows made from instructions plus optional resources/scripts. Codex can discover local skills from supported `.agents/skills` locations, and skills can also be bundled inside plugins.

**Durable Threads consequence:** the workflow has one canonical `SKILL.md` tree under the plugin.

Source: https://learn.chatgpt.com/docs/build-skills

### Plugins distribute reusable capabilities

OpenAI recommends designing the workflow as a skill and packaging it as a plugin when other people should install it. Plugins can bundle skills and optional connector/MCP capabilities.

**Durable Threads consequence:** **plugin = distribution; bundled skill = workflow implementation**. They are not two products a normal user must install separately.

Sources:

- https://learn.chatgpt.com/docs/plugins
- https://learn.chatgpt.com/docs/build-skills

### Canonical plugin and marketplace layout

The current Codex plugin-creator scaffold uses:

```text
<plugin>/.codex-plugin/plugin.json
<plugin>/skills/...
<repo>/.agents/plugins/marketplace.json
<repo>/plugins/<plugin-name>/...
```

Repo/team marketplace entries point at a plugin path such as `./plugins/<plugin-name>`.

**Durable Threads consequence:** the repository layout follows this scaffold and keeps one bundled skill source.

Sources:

- https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/plugin-creator
- https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/plugin-json-spec.md

### Git repository marketplace sources

The current Codex CLI accepts marketplace sources including local paths, `owner/repo`, HTTPS Git URLs, and SSH Git URLs. Its help includes an `owner/repo --ref main` example.

**Durable Threads consequence:** the documented marketplace command is:

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
```

Source: https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs

### Direct plugin add syntax

The current Codex CLI exposes `codex plugin add` and accepts either `PLUGIN@MARKETPLACE` or `PLUGIN --marketplace MARKETPLACE`.

**Durable Threads consequence:** this install command is intentional and current:

```bash
codex plugin add durable-threads@strataward
```

Source: https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs

### New session after plugin install

OpenAI's plugin guidance instructs Codex CLI users to start a new session after installing from a configured marketplace before using bundled skills or tools.

Source: https://learn.chatgpt.com/docs/plugins

### IDE extension limitation

OpenAI currently documents that plugins are not supported in the Codex IDE extension. Standalone skills are the fallback for that surface.

Sources:

- https://learn.chatgpt.com/docs/plugins
- https://learn.chatgpt.com/docs/build-skills

## Durable Threads policy — not an OpenAI guarantee

The following are project choices or empirical strategies:

- efficient high/XHigh implementation as a preferred workhorse strategy;
- R0–R4 consequence classification;
- frontier/specialist review at R3+ by default;
- the sleeping-orchestrator invariant;
- one focused correction by default;
- escalation from efficient → balanced → frontier;
- any claim about relative quota efficiency or task-level model performance.

The docs should label these as policy, recommendation, or observed behavior rather than attributing them to OpenAI.

## Claims we intentionally avoid

We do not claim that Durable Threads is currently listed in the public Plugin Directory, that every ChatGPT surface can install directly from this GitHub repository, that plugin installation configures Claude/Grok/Cursor, that model names or allowance ratios are permanent, or that a packet path allow-list is a filesystem sandbox.

## Release audit checklist

Before changing installation or compatibility docs:

1. Re-read the current OpenAI plugin and skill pages.
2. Check the Codex plugin-creator manifest and marketplace spec.
3. Check the current `codex plugin marketplace add` and `codex plugin add` CLI source/help.
4. Confirm supported product surfaces, especially IDE behavior.
5. Run repository validation and CI.
6. Update the audit date.
