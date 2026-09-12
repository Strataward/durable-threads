# Provider adapters

The optional Python helper can render and dispatch bounded calls to several coding-agent CLIs. Each provider remains its own session system; Durable Threads does not pretend their lifecycle semantics are identical.

Adapters build argument arrays rather than shell strings. They do not check credentials or silently weaken provider permission controls.

## Capability matrix

| Provider | Local entry point | Session reuse | Structured output | Effort control |
| --- | --- | --- | --- | --- |
| Codex | native Codex task actions | native task/session identity | native result | native runtime |
| Claude Code | `claude` | `--resume` / `--continue` | `--output-format json` | `--effort` |
| Grok Build | `grok` | `--resume` / session IDs | `--output-format json` | `--effort` |
| Cursor Agent | `agent` (legacy `cursor-agent`) | `--resume` | `--output-format json` | adapter does not set it |

Provider installation and authentication are out of scope. Configure the provider with its own login/environment mechanism before dispatch.

## Claude Code

The adapter uses Claude Code's non-interactive print mode (`-p`), JSON output, model selection, effort selection, and session resume.

Stable Durable Threads role mappings are:

| Durable Threads role | Claude selector |
| --- | --- |
| `frontier` | `opus` |
| `balanced` | `sonnet` |
| `efficient` | `haiku` |

Use a full Claude model ID only when the current Anthropic catalog confirms it. Stable aliases reduce churn as concrete IDs are retired.

Example:

```bash
durable-threads provider-command \
  --provider claude \
  --model sonnet \
  --effort low \
  --prompt "Run the focused tests and report changed paths and exact results."
```

When a provider session ID is supplied, the adapter emits `--resume`. It does **not** emit `--dangerously-skip-permissions`.

Official references:

- https://code.claude.com/docs/en/cli-usage
- https://code.claude.com/docs/en/headless

## Grok Build

The adapter uses Grok Build's headless prompt mode, JSON output, model/effort selection, and resumable sessions. It adds `--no-auto-update` for automation.

Use `default` when local Grok configuration should own model selection. For an explicit model, use a name the local Grok installation exposes. The adapter intentionally rejects generic `frontier`/`balanced`/`efficient` selectors because mapping them without a live catalog would be guesswork.

Example:

```bash
durable-threads provider-command \
  --provider grok \
  --model default \
  --effort medium \
  --prompt "Review the current diff for one concrete regression."
```

Grok Build also exposes ACP via `grok agent stdio`. The current helper uses the documented headless CLI because it is simpler for bounded scripted work; an ACP integration would make sense for hosts that need live session events and permission decisions.

Official references:

- https://docs.x.ai/build/overview
- https://docs.x.ai/build/cli/headless-scripting
- https://docs.x.ai/build/cli/reference
- https://docs.x.ai/build/settings

## Cursor Agent

Current Cursor CLI installations use `agent`; older environments may still expose `cursor-agent`. The adapter checks both and allows an explicit `--binary` override.

Use `default` when Cursor should select the account default. For explicit routing, pass an account-visible model ID. The adapter does not guess mappings for `frontier`, `balanced`, or `efficient`, and it does not set Cursor effort because that capability is account/model-specific rather than represented safely by the current adapter.

Example:

```bash
durable-threads provider-command \
  --provider cursor \
  --model default \
  --prompt "Review the current diff and report only actionable findings."
```

Cursor also exposes ACP through `agent acp`. ACP is the better integration point when a host needs live events, session methods, or interactive permission handling; the current adapter intentionally stays with the simpler headless CLI contract.

Official references:

- https://cursor.com/docs/cli/overview
- https://cursor.com/docs/cli/reference/parameters
- https://cursor.com/docs/cli/acp

## Rendering and dispatch

Render a provider command without running it:

```bash
durable-threads provider-command \
  --provider claude \
  --model sonnet \
  --effort medium \
  --prompt "Complete the bounded task."
```

Run one provider call only when that external execution is authorized:

```bash
durable-threads dispatch \
  --provider grok \
  --model default \
  --effort medium \
  --cwd /path/to/repository \
  --prompt "Complete the bounded task."
```

`dispatch` uses an argument array, captures bounded output, extracts a session ID and common usage counters when the provider emits them, and can record redacted start/finish state in the ledger. With a ledger/task ID, it also guards against a second local writer and provider/session identity drift during a follow-up.

Codex is the deliberate exception: the helper returns a native-app action description rather than launching a Codex task. Use native Codex task actions for list/send/wait/read and provider-side writer checks.

## Session IDs

The roster `threadId` field is local provider state. Do not commit it. Resume with the same provider and working directory, and do not resume an active writer blindly. Stop on authentication failures, quota failures, or ambiguous session state until the real provider state is understood.
