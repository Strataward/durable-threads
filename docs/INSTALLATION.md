# Installation

Last verified: **2026-09-12**.

Durable Threads has one normal distribution path: install the **Durable Threads plugin**. The plugin bundles the canonical `durable-threads` skill, so plugin users do not install a second copy of the skill.

## Codex CLI — recommended

This repository exposes a repo marketplace at `.agents/plugins/marketplace.json` and the plugin under `plugins/durable-threads`.

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Start a **new Codex session** before using the newly installed plugin. OpenAI's current plugin guidance notes that bundled skills/tools become available to new sessions after installation.

You can also install through the interactive browser:

1. Run `/plugins` in Codex CLI.
2. Choose **Add Marketplace**.
3. Enter `Strataward/durable-threads`.
4. Install **Durable Threads** from the `Strataward` marketplace.
5. Start a new session.

No JSON roster or Python helper is required for this path.

## ChatGPT and other plugin surfaces

OpenAI currently uses plugins as the reusable distribution surface shared by ChatGPT and Codex. Public availability depends on how a plugin is distributed and which surface supports installation.

This repository is directly usable as a Codex marketplace source. Durable Threads does **not** claim a public Plugin Directory listing until one exists; if the plugin is later published there, use the normal Plugin Directory flow instead of maintaining a separate skill installation.

## IDE / standalone skill fallback

OpenAI currently documents that the Codex IDE extension does **not** support plugins. Standalone skills are supported, so IDE users can install the same canonical skill that the plugin bundles.

Canonical skill source:

```text
https://github.com/Strataward/durable-threads/tree/main/plugins/durable-threads/skills/durable-threads
```

Use Codex's `$skill-installer` to install that directory, or place the skill in a supported `.agents/skills/` location. Codex discovers local skills from repository, user, admin, and system locations; see the current OpenAI skill documentation for the complete search order.

This is a compatibility fallback, not a second implementation.

## Repository-pinned skill

If a repository intentionally wants to pin a standalone copy, place it at:

```text
<repo>/.agents/skills/durable-threads/
```

Only do this when repository pinning is useful. A normal plugin user should not maintain another copy.

## Optional Python helper

The Python package in this repository supports deterministic rosters, provider adapters, evidence ledgers, and benchmark workflows. It is not required for the plugin or standalone skill.

For development from a checkout:

```bash
python3 -m pip install -e '.[dev]'
```

Use `examples/roster.json` or `examples/multi-provider-roster.json` only when you need explicit routing, persistent provider sessions, or multi-provider experiments.

## Sources checked for this release

- OpenAI Plugins: https://learn.chatgpt.com/docs/plugins
- OpenAI Build Skills: https://learn.chatgpt.com/docs/build-skills
- OpenAI plugin creator/spec: https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/plugin-creator
- Codex marketplace CLI: https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs
- Codex plugin CLI: https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs

See [OpenAI compatibility](OPENAI_COMPATIBILITY.md) for the boundary between upstream product behavior and Durable Threads policy.
