# Durable Threads

[![CI](https://github.com/Strataward/durable-threads/actions/workflows/ci.yml/badge.svg)](https://github.com/Strataward/durable-threads/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Durable Threads is a provider-neutral skill and helper library for durable
software work. It gives one planner task a named set of worker sessions. It
keeps packets small. It keeps provider session IDs stable. It requires
evidence before integration.

Supported providers:

- OpenAI Codex through native Codex app actions.
- Anthropic Claude Code through its headless CLI.
- xAI Grok Build through its headless CLI.
- Cursor Agent through its headless CLI.

The project does not copy full transcripts into packets. It does not store
credentials. It does not enable dangerous auto-approval flags.

## Why this exists

One strong planner should not perform every routine edit. A durable roster lets
you keep separate worker context for implementation, tests, research, and
security review.

The design uses these controls:

- A planner and reviewer keep architecture and acceptance decisions.
- Workers handle bounded tasks with the lowest suitable model and effort.
- Provider adapters preserve each provider's session and model rules.
- Compact packets prevent repeated context transfer.
- A result contract requires changed paths and exact checks.
- A redacted local ledger records task state without storing transcripts.
- Quota, authorization, and active-writer failures stop blind retries.

This repository is an independent Apache-2.0 implementation. It is not a fork
of `backnotprop/orchestrator`.

## Install the skill

Install the public skill with:

```text
npx skills add Strataward/durable-threads --skill durable-threads
```

Add `-g` for a user-level installation. The repository also works as a project
skill. Copy `skills/durable-threads` into `.agents/skills/` when a project needs
a pinned version.

Invoke it with `$durable-threads`, or let Codex select it when a task needs
durable worker sessions.

```text
$durable-threads

Plan the billing work in this repository. Route implementation to the named
Claude worker, send research to Grok, use Cursor for a focused review, and keep
Codex for planning and integration. Inspect each result before integration.
```

## Install the plugin package

The repository includes a validated `.codex-plugin/plugin.json` manifest. Codex
builds that support remote plugin marketplaces can add the repository with:

```text
codex plugin marketplace add Strataward/durable-threads
codex plugin list
```

If the build expects a skill path, use the skill install command above. The
skill and plugin use the same operating policy.

## Configure a roster

Start from [`examples/roster.json`](examples/roster.json) for Codex-only work.
Use [`examples/multi-provider-roster.json`](examples/multi-provider-roster.json)
for a provider split.

Each worker can set a provider:

```json
{
  "name": "claude-implementation",
  "role": "implementation",
  "provider": "claude",
  "threadTitle": "Worker: Claude implementation",
  "purpose": "Make bounded code changes in the allowed paths.",
  "modelSelector": "sonnet",
  "reasoningEffort": "low",
  "maxFollowups": 1,
  "parallel": false
}
```

Keep real provider session IDs in a local ignored file. Do not commit them.
The `threadId` field stores the provider session ID after the first run.

Validate a roster:

```bash
python3 -m pip install -e '.[dev]'
durable-threads validate-roster examples/multi-provider-roster.json
```

Create compact packets before sending them:

```bash
durable-threads plan \
  --roster examples/multi-provider-roster.json \
  --objective "Fix the reading-level fallback and add regression tests." \
  --allowed-path packages/shared/src/reading-level.ts \
  --allowed-path packages/shared/src/reading-level.test.ts \
  --acceptance "Known profile labels keep their current mapping." \
  --acceptance "Inherited property names return the safe fallback." \
  --acceptance "The focused test and type check pass." \
  --constraint "Do not read environment files or credentials." \
  --run-id storibuk-reading-level
```

The plan command does not start a provider. It creates a reviewable packet.

## Provider commands

Render a provider-specific command without running it:

```bash
durable-threads provider-command \
  --provider claude \
  --model sonnet \
  --effort medium \
  --prompt "Complete the bounded task and report exact checks."
```

Run one provider session only after the user authorizes that action:

```bash
durable-threads dispatch \
  --provider grok \
  --model default \
  --effort medium \
  --cwd /path/to/repository \
  --prompt "Complete the bounded task and report exact checks."
```

Dispatch uses an argument array. It does not use a shell. It captures bounded
output. It returns a provider session ID when the provider emits one. It does
not write a transcript to the ledger.

Check local executable availability:

```bash
durable-threads doctor
durable-threads provider-doctor --provider claude
durable-threads provider-doctor --provider grok
durable-threads provider-doctor --provider cursor
```

The doctor commands do not check credentials. Use each provider's own login
flow or environment variable.

## Provider model policy

Use live provider data. Do not guess a volatile model ID.

- Claude maps `frontier`, `balanced`, and `efficient` to the stable aliases
  `opus`, `sonnet`, and `haiku`.
- Grok accepts `default` or a model name from `grok inspect`.
- Cursor accepts `default` or an account-visible model ID.
- Codex keeps its role selector for native runtime discovery.

Read [`skills/durable-threads/references/PROVIDERS.md`](skills/durable-threads/references/PROVIDERS.md)
for provider-specific commands, session rules, and official references.

## Persistent session policy

Use exact titles and providers. Reuse an idle matching session. Do not resume
an active writer. Stop on quota, authorization, or ambiguous writer state.

Codex uses native Codex app actions. Claude uses `--resume`. Grok uses
`--resume` or `--continue`. Cursor uses `--resume` or its `resume` command.

Read [`skills/durable-threads/references/PERSISTENT_THREADS.md`](skills/durable-threads/references/PERSISTENT_THREADS.md)
for lifecycle and recovery rules.

## Astra and token policy

Use Astra for difficult planning and review when the Codex runtime exposes it.
Keep routine edits and focused tests on an efficient model. Use higher effort
only when an evaluation shows a real quality gain.

The objective is total task value. A strong planner can reduce token use when
it prevents bad fan-out, repeated context, and correction loops.

Read [`skills/durable-threads/references/ASTRA.md`](skills/durable-threads/references/ASTRA.md)
for the full policy.

## Evidence from the StoriBuk trial

The first live trial on StoriBuk showed that a persistent worker can complete a
small bounded code task with focused tests and type checks. A follow-up turn
hit an account usage limit. A later resume attempt found an active writer.
That result shaped the default policy: use persistent sessions, but treat
quota and writer state as explicit failure states.

This was a practical smoke test, not a benchmark. See
[`skills/durable-threads/references/COMPARISON.md`](skills/durable-threads/references/COMPARISON.md)
for the decision record.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
python3 -m pytest
ruff check .
python3 -m compileall -q src scripts
python3 scripts/validate_repo.py
```

The package has no runtime Python dependencies. It uses installed provider
executables only when the explicit `dispatch` command runs.

## Project documents

- [`ARCHITECTURE.md`](skills/durable-threads/references/ARCHITECTURE.md) explains the control plane.
- [`PROVIDERS.md`](skills/durable-threads/references/PROVIDERS.md) explains provider adapters.
- [`OPERATING_POLICY.md`](skills/durable-threads/references/OPERATING_POLICY.md) defines limits and stop rules.
- [`RESULT_SCHEMA.md`](skills/durable-threads/references/RESULT_SCHEMA.md) defines worker evidence.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) explains development and releases.
- [`SECURITY.md`](SECURITY.md) explains the security boundary.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
