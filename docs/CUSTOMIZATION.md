# Customization

Durable Threads uses progressive disclosure. Start with zero project configuration and add policy only when it solves a real problem.

## Level 0 — use the defaults

Install the plugin and ask it to do the work.

```text
Use Durable Threads to implement this feature efficiently and verify it.
```

The bundled skill chooses a bounded workflow, classifies risk, prefers deterministic checks, and escalates only when evidence or consequence warrants it.

## Level 1 — override one task

State the exception in your prompt. Examples:

```text
Use Durable Threads. Keep implementation on the efficient high-reasoning model and require frontier review only if this becomes R3+.
```

```text
Treat this authentication change as R3 and require independent security review.
```

```text
Do not delegate this one; keep it in the current task.
```

No configuration file is needed for a one-off preference.

## Level 2 — repository policy in AGENTS.md

Use `AGENTS.md` when a preference should apply consistently in one repository. Keep it concise and state policy rather than volatile model IDs.

Example:

```markdown
## Durable Threads

- Use efficient high reasoning for bounded implementation.
- Treat auth, payments, permissions, privacy, destructive migrations, and concurrency as R3 or higher.
- Require deterministic checks before model review.
- Use frontier review at R3+.
- Do not poll healthy workers repeatedly.
```

This is usually enough for a team that wants stable behavior without introducing a roster.

## Level 3 — explicit roster and Python helper

Use the optional helper when you need one or more of these:

- reproducible routing for benchmarks;
- named persistent worker sessions;
- explicit parallel-worker limits;
- structured provider/session ledgers;
- deterministic provider command rendering;
- multi-provider Claude/Grok/Cursor workers.

Start from `examples/roster.json` for Codex-oriented work or `examples/multi-provider-roster.json` for explicit provider splits.

The helper is intentionally not part of the quick-start path.

## Model selection

Prefer roles over names in durable policy:

- `efficient` for sustained bounded execution;
- `balanced` for harder general reasoning;
- `frontier` for consequential decisions and review.

Reasoning effort is a separate dimension. An efficient model at high/XHigh reasoning can be an excellent implementor when the task packet is well specified. Frontier effort should rise only when task consequence or observed failure justifies it.

If the runtime exposes a live catalog, resolve against it. Do not bake a temporary model slug into durable policy unless you intentionally want a pinned experiment.

## Review policy

A useful default is:

```text
R0/R1 → deterministic checks; lightweight review only when useful
R2    → integration-focused review
R3/R4 → independent specialist/frontier review
```

Override risk explicitly when repository facts are stronger than keyword classification.

## Multi-provider setup

Installing Durable Threads does not install or authenticate Claude Code, Grok Build, or Cursor Agent. Those adapters are optional. Configure them only if you want them, then use the advanced roster/provider documentation.

See `plugins/durable-threads/skills/durable-threads/references/PROVIDERS.md`.
