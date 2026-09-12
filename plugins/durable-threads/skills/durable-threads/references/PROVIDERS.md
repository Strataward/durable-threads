# Provider adapters

Durable Threads treats each provider as a separate session system. The helper
builds provider-specific argument arrays. It does not build shell strings.

## Capability matrix

| Provider | Local entry point | Durable session control | Structured output | Effort control |
| --- | --- | --- | --- | --- |
| Codex | Codex app actions | Native task ID and title | App result | Native runtime |
| Claude | `claude` | `--resume` or `--continue` | `--output-format json` | `--effort` |
| Grok | `grok` | `--session-id`, `--resume`, or `--continue` | `--output-format json` | `--effort` |
| Cursor | `agent` or `cursor-agent` | `--resume` or `resume` | `--output-format json` | Account and model specific |

The provider adapters do not check credentials. Run the provider's own login
command or set the provider's environment variable before dispatch.

## Claude Code

Claude Code supports headless print mode. It supports JSON output. It supports
session resume by ID or name. Its current CLI also supports effort values.

Use stable aliases when the role is abstract:

| Durable Threads role | Claude selector |
| --- | --- |
| `frontier` | `opus` |
| `balanced` | `sonnet` |
| `efficient` | `haiku` |

Use a full Claude model ID only when the current Anthropic catalog confirms it.
Anthropic retires model IDs. Do not commit retired IDs to a roster.

Example:

```bash
durable-threads provider-command \
  --provider claude \
  --model sonnet \
  --effort low \
  --prompt "Run the focused tests and report changed paths and exact results."
```

Resume an existing session by adding `--session-id`. The adapter emits
`claude -p`, `--output-format json`, `--model`, `--effort`, and `--resume`.
It does not emit `--dangerously-skip-permissions`.

Official references:

- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-usage)
- [Claude model deprecations](https://docs.anthropic.com/en/docs/about-claude/model-deprecations)

## Grok Build

Grok Build supports headless prompts. It supports named sessions. It supports
JSON and streaming JSON output. It supports model and effort selection.

Use `default` when the local Grok configuration owns model selection. Use a
model name from `grok inspect` when the roster needs an explicit model. The
adapter rejects generic role names such as `frontier` because it cannot map
them without guessing.

Example:

```bash
durable-threads provider-command \
  --provider grok \
  --model default \
  --effort medium \
  --prompt "Review the current diff for one concrete regression."
```

The adapter adds `--no-auto-update` for automation. It uses `--resume` when a
provider session ID exists. It does not add `--always-approve`.

Grok Build also exposes ACP through `grok agent stdio`. The current adapter
uses the documented headless CLI because it is portable across scripts and
does not require a JSON-RPC permission loop. An ACP adapter can be added when a
host needs live session updates and interactive permission decisions.

Official references:

- [Grok Build overview](https://docs.x.ai/build/overview)
- [Headless and scripting](https://docs.x.ai/build/cli/headless-scripting)
- [CLI reference](https://docs.x.ai/build/cli/reference)
- [Grok Build settings](https://docs.x.ai/build/settings)
- [Grok 4.6 model guide](https://docs.x.ai/developers/grok-4-6)

## Cursor Agent

Cursor Agent supports print mode, JSON output, model selection, and session
resume. Current installations use `agent`. Older installations use
`cursor-agent`. The adapter checks both names. Use `--binary cursor-agent` when
the local installation needs the older name.

Use `default` when Cursor should select the account default. Use an account
visible model ID for an explicit choice. Do not map `frontier`, `balanced`, or
`efficient` to a guessed Cursor model.

Example:

```bash
durable-threads provider-command \
  --provider cursor \
  --model default \
  --prompt "Review the current diff and report only actionable findings."
```

The Cursor model catalog is account-specific. The Cursor SDK documents model
parameters and the `auto-smart` router. The CLI adapter does not invent those
parameters. Use the Cursor CLI or SDK to discover a valid model before adding
it to a roster.

Cursor also supports ACP. ACP uses JSON-RPC over standard input and output. It
has `session/new`, `session/load`, `session/prompt`, update events, and
permission requests. Use ACP when a host needs those events. Use the CLI
adapter for a simple headless worker.

Official references:

- [Cursor CLI overview](https://cursor.com/docs/cli/overview)
- [Cursor CLI parameters](https://cursor.com/docs/cli/reference/parameters)
- [Cursor ACP](https://cursor.com/docs/cli/acp)
- [Cursor Python SDK](https://prod.cursor.com/docs/sdk/python)

## Provider commands

Render a command without running it:

```bash
durable-threads provider-command \
  --provider claude \
  --model sonnet \
  --effort medium \
  --prompt "Complete the bounded task."
```

Run one provider call only after the user authorizes it:

```bash
durable-threads dispatch \
  --provider grok \
  --model default \
  --effort medium \
  --cwd /path/to/repository \
  --prompt "Complete the bounded task."
```

The dispatch command uses an argument array. It does not use a shell. It
captures bounded output. It returns a session ID when the provider emits one.
It extracts common token counters when the provider emits them. With
`--ledger` and `--task-id`, it records start and finish state without writing a
transcript. It blocks a second local writer and rejects a provider or session
ID change during a follow-up.

Codex is the deliberate exception. The helper returns a native-app action
description for Codex. Use the Codex task actions for list, send, wait, read,
and provider-side writer checks. The Python CLI does not launch a Codex task.

## Session ID handling

The roster `threadId` field stores the provider session ID. It is local state.
Do not commit it. After a first run, record the returned ID in the local roster
or ledger. Use the same provider and working directory when resuming.

Do not resume an active writer. Inspect the provider status first. Stop on an
authorization failure, quota failure, or ambiguous session state.
