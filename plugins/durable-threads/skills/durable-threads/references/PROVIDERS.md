# Provider adapters

Durable Threads prefers the host's native agent runtime when it is capable enough. On current Codex, that means native subagents should be the default execution path for normal interactive work.

The optional Python helper still supports provider-neutral planning and bounded calls to other coding-agent CLIs. Each provider remains its own session system; Durable Threads does not pretend their lifecycle semantics are identical.

Adapters build argument arrays rather than shell strings. They do not check credentials or silently weaken provider permission controls.

## Capability matrix

| Provider/runtime | Preferred integration | Session reuse | Multi-agent / isolation | Effort control |
| --- | --- | --- | --- | --- |
| Codex | native subagents and project agent roles | native task/session identity | native agents; worktrees for isolated writers when supported | native runtime |
| OpenAI Agents API | optional managed/headless backend | managed sessions | managed subagents with concurrency cap | API agent reasoning config |
| Claude Code | CLI adapter | `--resume` / `--continue` | provider-specific | `--effort` |
| Grok Build | CLI adapter | `--resume` / session IDs | provider-specific | `--effort` |
| Cursor Agent | CLI adapter | `--resume` | provider-specific | adapter does not set it |

Provider installation and authentication are out of scope. Configure an external provider with its own login/environment mechanism before dispatch.

## Codex — preferred native runtime

Do not launch a second Codex process just to emulate workers that native Codex can already represent. Use the host's native child lifecycle and map Durable Threads policy onto it:

- `explorer` for specific codebase questions and read-heavy discovery;
- `worker` for bounded implementation, debugging, and test work;
- project-defined read-only roles for stable reviewer/security behavior when useful;
- native wait/resume instead of repeated parent polling;
- worktrees for independent parallel writers when supported;
- serialization for overlapping writers.

The optional helper's `durable_threads.native` module exposes provider-neutral execution hints but intentionally does not spawn Codex.

## OpenAI Agents API — optional managed backend

The Agents API exposes the managed Codex harness for cloud/headless use and supports multi-agent configuration with a concurrency cap. Durable Threads does not require it for ordinary plugin use.

A future managed adapter should preserve the same policy boundary: Durable Threads chooses delegation/risk/model economics; the API owns session lifecycle, subagent execution, and platform telemetry.

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

When a provider session ID is supplied, the adapter emits `--resume`. It does **not** emit unsafe permission-bypass flags.

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

## Rendering and dispatch

Render an external-provider command without running it:

```bash
durable-threads provider-command \
  --provider claude \
  --model sonnet \
  --effort medium \
  --prompt "Complete the bounded task."
```

Run one external provider call only when that execution is intentionally selected:

```bash
durable-threads dispatch \
  --provider grok \
  --model default \
  --effort medium \
  --cwd /path/to/repository \
  --prompt "Complete the bounded task."
```

`dispatch` uses an argument array, captures bounded output, extracts a session ID and common usage counters when the provider emits them, and can record redacted start/finish state in the ledger.

Codex remains the deliberate exception: the helper returns a native-app action description rather than launching Codex as a subprocess.

## Session IDs

The roster `threadId` field is local provider state. Do not commit it. Resume with the same provider and working directory, and do not resume an active writer blindly. Stop on authentication failures, quota failures, or ambiguous session state until the real provider state is understood.
