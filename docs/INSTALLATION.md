# Installation

Last verified: **2026-09-12**.

Durable Threads has one normal distribution path: the **Durable Threads plugin**. The plugin bundles the canonical `durable-threads` skill. You do not need to install both.

## Codex CLI: recommended

This repository contains a Codex marketplace at `.agents/plugins/marketplace.json` and the plugin at `plugins/durable-threads`.

Install from GitHub:

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Then start a **new Codex session** so the newly installed bundled skill is available.

You can do the same interactively:

1. Run `/plugins`.
2. Choose **Add Marketplace**.
3. Enter `Strataward/durable-threads`.
4. Select **Durable Threads** from the `Strataward` marketplace and install it.
5. Start a new session.

No JSON roster or Python helper is needed for this path.

## ChatGPT / Codex app surfaces

OpenAI's current plugin documentation describes plugins as the reusable distribution surface across ChatGPT and Codex. Availability can depend on product surface and how the plugin is distributed. This GitHub repository is directly usable as a Codex marketplace source; if/when Durable Threads is published into the ChatGPT Plugin Directory, use the normal Plugin Directory installation flow there instead of maintaining a separate skill installation.

We do not claim a Plugin Directory listing until one actually exists.

## IDE / standalone skill fallback

OpenAI currently documents that the Codex IDE extension does **not** support plugins. The workflow itself is a standard skill, so IDE users can install the bundled skill directly.

Canonical skill source:

```text
https://github.com/Strataward/durable-threads/tree/main/plugins/durable-threads/skills/durable-threads
```

Use Codex's `$skill-installer` with that GitHub directory, or copy the `durable-threads` skill directory into a supported `.agents/skills/` location. Start a new session after installation if the running surface has not picked up the new skill.

This fallback does not create a second implementation: it installs the same skill that the plugin bundles.

## Project pinning

If a project intentionally wants a pinned standalone copy, copy the canonical skill directory to:

```text
<repo>/.agents/skills/durable-threads/
```

Only do this when project pinning is useful. A normal plugin user should not maintain a second copy.

## Optional Python helper

The Python package in this repository supports deterministic rosters, provider adapters, evidence ledgers, and benchmark workflows. It is not required for the plugin or skill.

For development from a checkout:

```bash
python3 -m pip install -e '.[dev]'
```

Use `examples/roster.json` or `examples/multi-provider-roster.json` only when you need explicit routing or multi-provider sessions.

## Current OpenAI sources

The installation model above is based on current OpenAI documentation and Codex source:

- Skills: https://developers.openai.com/codex/skills/
- Plugins: https://developers.openai.com/codex/plugins/
- Plugin building: https://developers.openai.com/codex/plugins/build/
- Codex plugin creator sample/spec: https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/plugin-creator
- Marketplace CLI implementation: https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs

See [OpenAI compatibility](OPENAI_COMPATIBILITY.md) for what we treat as official product behavior versus Durable Threads policy.
