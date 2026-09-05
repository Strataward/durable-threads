# Architecture

Durable Threads is a provider-neutral contract layer. It keeps planning,
routing, session identity, and evidence separate from provider execution.

It is not a workflow engine or a second daemon. It does not promise automatic
provider restart after a quota error or an active-writer conflict.

## Components

### Planner and reviewer

The current Codex task owns the user contract. It decides the work split,
selects roles, reviews evidence, and integrates changes. It remains the final
authority for scope and acceptance.

Use a frontier model such as Astra for difficult planning and review when the
Codex runtime makes it available. The role is a capability choice. The exact
model ID comes from live discovery.

### Durable workers

Each worker has a stable human title and a purpose. Typical workers are:

| Worker | Typical use | Default role |
| --- | --- | --- |
| implementation | Bounded code changes | efficient |
| test-debug | Regression tests and focused diagnosis | balanced |
| research-docs | Repository research and docs | efficient |
| security-review | Threat review and hardening | frontier or balanced |

The roster stores a title, a provider, and an optional provider session ID. The
ID stays in local ignored state. The title and provider remain the stable human
handle.

Durable means that the human handle and the local evidence record survive a
turn. It does not make the provider's private runtime durable. The planner must
inspect provider state before it resumes a session.

### Routing gate

The routing gate reads the objective and allowed paths. It selects only the
workers that match the task. It selects at most two workers by default. An
explicit `--worker` selection overrides keyword routing within the roster
limit.

The gate uses simple deterministic signals. It does not replace planner
judgement. The planner can override it when the task needs a different split.

### Packet builder

The helper library validates a small packet and builds a provider-specific
argument array. It does not choose a provider model by guesswork. The parent
can inspect each delegation before it leaves the current task.

### Evidence verifier

The verifier parses the worker result contract. It requires a status, provider,
changed paths, exact checks, and remaining concerns. It checks each path against
the allow-list. When a clean baseline is available, it checks the claims against
the actual git diff.

### Evidence ledger

The local ledger stores task IDs, thread IDs, status, usage counters, and a
short redacted result. It uses an atomic replace. It writes with mode `0600`.
It does not store full prompts or transcripts.

The ledger records common input and output token counters when a provider emits
them. It blocks a second local writer for the same task. It also blocks a
provider or session ID change during a follow-up. A provider-side active writer
still requires a manual stop.

## Control flow

```text
request
  -> planner reads project and live runtime
  -> routing gate selects 0-2 workers
  -> planner creates compact packets
  -> exact named provider sessions receive packets
  -> workers return structured evidence
  -> verifier checks evidence and the actual diff
  -> reviewer approves or sends one focused correction
  -> planner integrates the result
```

## Failure flow

```text
worker error
  -> record status and evidence
  -> classify: scope, test, writer, quota, or provider
  -> correct once when evidence supports a correction
  -> stop on quota or ambiguous writer state
```

The system does not treat a missing result as a successful result.

## Efficiency rule

Persistent context is not automatically cheaper. A resumed session can carry
irrelevant history and increase input tokens. The packet stays compact, but the
planner must rotate a session when the follow-up limit is reached or its context
no longer matches the task.

The default value rule is:

1. Keep the planner and integration owner in the current task.
2. Use one efficient worker for a bounded implementation.
3. Add one independent specialist only when it reduces expected rework.
4. Add frontier review for security, release, or high-risk changes.
5. Measure total tokens, follow-ups, rework, and correctness before changing
   the default fan-out.
