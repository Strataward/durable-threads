# OpenAI compatibility and documentation audit

Last audited: **2026-09-12**.

This file distinguishes current OpenAI product behavior from Durable Threads policy. Product behavior can change; re-check the linked sources when installation or plugin semantics matter.

## What OpenAI currently documents

### Skills are the workflow authoring format

OpenAI describes skills as reusable workflows that package instructions and optional resources. Codex can invoke a skill explicitly or select it from its description.

Durable Threads consequence: the workflow lives in one canonical `SKILL.md` tree.

Source: https://developers.openai.com/codex/skills/

### Plugins are the reusable distribution surface

OpenAI describes plugins as bundles that can contain skills and other capabilities. Its skills guidance explicitly recommends designing the workflow as a skill, then packaging it as a plugin when other people should install it.

Durable Threads consequence: **plugin = distribution; bundled skill = implementation**. They are not presented as two products users must choose between.

Sources:

- https://developers.openai.com/codex/plugins/
- https://developers.openai.com/codex/skills/

### Plugin layout and marketplace layout

Current Codex plugin-creator references use:

```text
<plugin>/.codex-plugin/plugin.json
<plugin>/skills/...
<repo>/.agents/plugins/marketplace.json
<repo>/plugins/<plugin-name>/...
```

A repo/team marketplace entry points at `./plugins/<plugin-name>` and includes installation/authentication policy metadata.

Durable Threads follows that layout.

Source: https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/plugin-creator

### Git repository marketplace sources

The current Codex CLI accepts a marketplace source as a local path, `owner/repo`, HTTPS Git URL, or SSH Git URL. The CLI help includes an `owner/repo --ref main` example.

Durable Threads consequence: the documented GitHub install uses:

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Source: https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs

### Newly installed plugins/skills need a new session boundary

Current OpenAI plugin and skill docs recommend a new chat/session after installation or meaningful skill changes so the runtime discovers the new capability.

Sources:

- https://developers.openai.com/codex/plugins/
- https://developers.openai.com/codex/skills/

### IDE extension plugin support

OpenAI's current plugin docs state that the Codex IDE extension does not support plugins. Standalone skills remain the fallback for that surface.

Source: https://developers.openai.com/codex/plugins/

## What is Durable Threads policy, not an OpenAI guarantee

The following are project decisions or empirical strategies rather than promises from OpenAI:

- Luna/XHigh-like efficient implementation as a preferred workhorse strategy;
- R0-R4 consequence classification;
- frontier review at R3+;
- the sleeping-orchestrator invariant;
- one focused correction by default;
- the escalation ladder from efficient → balanced → frontier;
- any benchmark result or claim about relative quota efficiency.

We keep these policies separate from installation/product compatibility claims.

## Avoided claims

The docs intentionally do not claim:

- that Durable Threads is currently listed in the ChatGPT Plugin Directory;
- that every ChatGPT surface can install directly from this GitHub repo;
- that installing the plugin automatically configures Claude/Grok/Cursor;
- that model names, usage allowances, or quota ratios are permanent;
- that a path allow-list is a filesystem sandbox.

## Audit checklist for future releases

Before changing installation documentation:

1. Re-read the OpenAI skills and plugins pages.
2. Check the current plugin creator manifest and marketplace specs in `openai/codex`.
3. Check current `codex plugin marketplace add` CLI source/help.
4. Confirm supported product surfaces, especially the IDE extension.
5. Run repository validation and CI.
6. Date this document with the new audit date.
