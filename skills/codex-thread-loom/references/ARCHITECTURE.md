# Architecture

## Components

### Planner and reviewer

The current Codex task owns the user contract. It decides the work split,
selects roles, reviews evidence, and integrates changes. It remains the final
authority for scope and acceptance.

Use a frontier model such as Astra for difficult planning and review when the
runtime makes it available. The role is a capability choice. The exact model ID
comes from live discovery.

### Durable workers

Each worker has a stable human title and a purpose. Typical workers are:

| Worker | Typical use | Default role |
| --- | --- | --- |
| implementation | Bounded code changes | efficient |
| test-debug | Regression tests and focused diagnosis | balanced |
| research-docs | Repository research and docs | efficient |
| security-review | Threat review and hardening | frontier or balanced |

The roster stores a title and an optional provider thread ID. The ID stays in
local ignored state. The title remains the stable human handle.

### Packet builder

The helper library validates a small packet. It does not launch a model. This
keeps the provider boundary in the Codex app and lets the parent inspect each
delegation before it leaves the current task.

### Evidence ledger

The local ledger stores task IDs, thread IDs, status, usage counters, and a
short redacted result. It uses an atomic replace. It writes with mode `0600`.
It does not store full prompts or transcripts.

## Control flow

```text
request
  -> planner reads project and live runtime
  -> planner creates compact packets
  -> exact named threads receive packets
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
