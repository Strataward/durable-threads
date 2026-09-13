# Installation

Last verified: **2026-09-12**.

Durable Threads has one normal distribution path: install the **Durable Threads plugin**. The plugin bundles the canonical `durable-threads` skill, so plugin users do not install a second copy of the skill.

## Codex CLI — recommended

This repository exposes a repo marketplace at `.agents/plugins/marketplace.json` and the plugin under `plugins/durable-threads`.

```bash
codex plugin marketplace add Strataward/durable-threads --ref main
codex plugin add durable-threads@strataward
```

Start a **new Codex session** before using the newly installed plugin so the bundled skill is loaded into a fresh session.

You can also install through the interactive plugin browser:

1. Run `/plugins` in Codex CLI.
2. Choose **Add Marketplace**.
3. Enter `Strataward/durable-threads`.
4. Install **Durable Threads** from the `Strataward` marketplace.
5. Start a new session.

No JSON roster or Python helper is required for this path.

## Update an existing installation

The current Codex CLI exposes marketplace refresh through `codex plugin marketplace upgrade`; there is no separate `codex plugin update` subcommand. To update Durable Threads from the Git-backed `strataward` marketplace, refresh that marketplace and reinstall the plugin:

```bash
codex plugin marketplace upgrade strataward && codex plugin add durable-threads@strataward
```

Then start a **new Codex session** so the updated plugin metadata and bundled skill are picked up.

To inspect the installed state afterward:

```bash
codex plugin list --marketplace strataward
```

If your marketplace has a different configured name, substitute that name. `strataward` is the marketplace name declared by this repository's `.agents/plugins/marketplace.json`.

## Native Codex subagents

Modern Codex includes native multi-agent capabilities. Durable Threads v0.5 prefers those native subagents for ordinary Codex execution rather than launching a second Codex process or building its own polling loop.

No additional Durable Threads installation step is required. The bundled skill decides when delegation is useful and can use the runtime's built-in `explorer` and `worker` roles. Optional project-defined reviewer roles can live in `.codex/agents/`; examples are provided under `examples/codex-agents/`.

See [Native Codex multi-agent integration](NATIVE_MULTI_AGENT.md).

## ChatGPT and other plugin surfaces

OpenAI uses plugins as a reusable distribution surface shared across supported products. Public availability depends on how a plugin is distributed and which surface supports installation.

This repository is directly usable as a Codex marketplace source. Durable Threads does **not** claim a public Plugin Directory listing until one exists.

## IDE / standalone skill fallback

If plugin installation is unavailable on the Codex IDE surface you are using, install the same canonical skill directly.

Canonical skill source:

```text
https://github.com/Strataward/durable-threads/tree/main/plugins/durable-threads/skills/durable-threads
```

Use Codex's skill installer or place the skill in a supported `.agents/skills/` location. This is a compatibility fallback, not a second implementation.

## Repository-pinned skill

If a repository intentionally wants to pin a standalone copy, place it at:

```text
<repo>/.agents/skills/durable-threads/
```

Only do this when repository pinning is useful. A normal plugin user should not maintain another copy.

## Optional Python helper

The Python package supports deterministic rosters, provider adapters, native-runtime execution hints, evidence ledgers, and benchmark workflows. It is not required for the plugin or standalone skill.

For development from a checkout:

```bash
python3 -m pip install -e '.[dev]'
```

Use `examples/roster.json` or `examples/multi-provider-roster.json` only when you need explicit routing, persistent provider sessions, or multi-provider experiments.

## Sources checked for this release

- OpenAI Codex plugin creator/spec: https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/plugin-creator
- Codex marketplace CLI, including `marketplace upgrade`: https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs
- Codex plugin CLI: https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs
- Codex native agent-role implementation: https://github.com/openai/codex/blob/main/codex-rs/core/src/agent/role.rs
- OpenAI Agents API launch: https://openai.com/index/introducing-the-agents-api/

See [OpenAI compatibility](OPENAI_COMPATIBILITY.md) for the boundary between upstream product behavior and Durable Threads policy.
