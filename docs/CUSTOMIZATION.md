# Customization

Durable Threads uses progressive disclosure: start with zero project configuration and add policy only when it solves a real problem.

```mermaid
flowchart LR
    L0["Level 0<br/>Install + native roles"] --> L1["Level 1<br/>Task override"] --> L2["Level 2<br/>AGENTS.md policy"] --> L3["Level 3<br/>Custom Codex agents"] --> L4["Level 4<br/>Roster + helper"]
```

Most users should remain at Level 0 or Level 1.

## Level 0 — use the defaults

Install the plugin and ask it to do the work:

```text
Use Durable Threads to implement this feature efficiently and verify it.
```

On current Codex, the bundled skill can use native `explorer` and `worker` subagents when delegation adds value. No worker roster or Python helper is required.

## Level 1 — override one task

Put the exception in the prompt. No configuration file is needed for a one-off preference.

```text
Use Durable Threads. Keep implementation on the efficient high-reasoning model and require frontier review only if this becomes R3+.
```

```text
Treat this authentication change as R3 and require independent security review.
```

```text
Do not delegate this one; keep it in the current task.
```

```text
Use parallel explorers for the two independent codebase questions, but keep all writes serialized.
```

## Level 2 — repository policy in AGENTS.md

Use `AGENTS.md` when a preference should apply consistently in one repository. Prefer durable roles and safety policy over temporary model IDs.

```markdown
## Durable Threads

- Prefer native Codex subagents when delegation helps.
- Use `explorer` for read-heavy codebase questions and `worker` for bounded execution.
- Use efficient high reasoning for bounded implementation.
- Treat auth, payments, permissions, privacy, destructive migrations, and concurrency as R3 or higher.
- Require deterministic checks before model review.
- Use frontier/specialist review at R3+.
- Parallelize read-only work freely when independent.
- Use isolated worktrees for independent parallel writers; serialize overlapping writers.
- Do not poll healthy workers repeatedly.
```

For many teams, this is enough structure without introducing a roster.

## Level 3 — custom native Codex agents

Use project-defined roles when you want persistent specialist behavior such as an independent read-only reviewer or security reviewer.

This repository includes examples:

```text
examples/codex-agents/dt-reviewer.toml
examples/codex-agents/dt-security.toml
```

Copy/adapt a role into:

```text
<repo>/.codex/agents/
```

The examples intentionally avoid pinning a model ID. Model/effort choice should remain a routing decision unless reproducibility requires a pin.

You can also configure native concurrency/default subagent effort in `.codex/config.toml` when the project needs stable runtime policy:

```toml
[agents]
max_concurrent_threads_per_session = 3
default_subagent_reasoning_effort = "high"
```

Do not raise concurrency merely because the runtime permits it. Fan-out should be justified by independent work.

## Level 4 — explicit roster and Python helper

Use the optional helper when you need reproducible routing for benchmarks, named persistent external-provider sessions, explicit parallel-worker limits, structured provider/session ledgers, deterministic provider command rendering, native-runtime execution hints, or multi-provider Claude/Grok/Cursor workers.

Start from `examples/roster.json` for Codex-oriented experiments or `examples/multi-provider-roster.json` for explicit provider splits.

The helper is intentionally outside the quick-start path.

## Model selection

Prefer durable roles over volatile names:

- `efficient` for sustained bounded execution;
- `balanced` for harder general reasoning;
- `frontier` for consequential decisions and independent review.

Reasoning effort is a separate dimension. An efficient model at high/XHigh reasoning can be a strong implementer when the contract is well specified. Raise frontier effort when consequence or observed failure justifies it—not because a task sounds important.

If the runtime exposes a live catalog, resolve against it. Pin a concrete model ID only when you intentionally want a reproducible experiment.

## Review policy

```mermaid
flowchart LR
    R["Risk class"] --> G{"Tier"}
    G -->|"R0-R1"| D["Deterministic checks"]
    G -->|"R2"| I["Integration review"]
    G -->|"R3-R4"| F["Frontier / specialist review"]
```

Override risk explicitly when repository facts are stronger than the classifier.

## Parallelism policy

Use the compact rule:

> **Subagents for parallel cognition. Worktrees for parallel mutation.**

Parallel explorers/reviewers are usually cheap to coordinate. Parallel writers should have disjoint ownership and isolated checkouts when supported. Overlapping writers should be serialized.

## Multi-provider setup

Installing Durable Threads does not install or authenticate Claude Code, Grok Build, or Cursor Agent. Those adapters are optional. Configure them only if you want external workers, then use `plugins/durable-threads/skills/durable-threads/references/PROVIDERS.md`.
