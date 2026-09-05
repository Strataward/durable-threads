# Architecture

Durable Threads is a provider-neutral control plane. It keeps planning,
routing, session identity, and evidence separate from provider execution.

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

### Packet builder

The helper library validates a small packet and builds a provider-specific
argument array. It does not choose a provider model by guesswork. The parent
can inspect each delegation before it leaves the current task.

### Evidence ledger

The local ledger stores task IDs, thread IDs, status, usage counters, and a
short redacted result. It uses an atomic replace. It writes with mode `0600`.
It does not store full prompts or transcripts.

## Control flow

```text
request
  -> planner reads project and live runtime
  -> planner creates compact packets
  -> exact named provider sessions receive packets
  -> workers return structured evidence
  -> planner inspects diff and runs checks
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
