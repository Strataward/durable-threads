# Codex Thread Loom

[![CI](https://github.com/waleeddogar/codex-thread-loom/actions/workflows/ci.yml/badge.svg)](https://github.com/waleeddogar/codex-thread-loom/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Codex Thread Loom is a Codex skill and small helper library for work that needs
more than one durable worker thread.

It uses a simple operating model:

```text
current planner thread
        |
        | compact packets
        v
named durable worker threads
  implementation  test/debug  research/docs  security
        |
        | structured evidence
        v
current reviewer thread
```

The planner and reviewer keep the high-reasoning work. Workers use the lowest
model and effort that can meet the acceptance checks. The system discovers live
model IDs. It does not rely on stale names such as a hard-coded Astra or Luna
identifier.

## Why this exists

Codex can do strong work in one long task. A durable thread roster adds value
when a project has repeated work areas, independent tasks, or a need to resume
the same specialist later. The roster preserves role memory without copying a
full conversation into every new prompt.

The design combines the useful parts of the approaches we evaluated:

- Native Codex threads keep task history and allow later steering.
- A frontier role plans and reviews. It does not perform every routine edit.
- Efficient roles handle bounded implementation, tests, and documentation.
- Compact packets reduce repeated context.
- A result contract forces evidence instead of a success claim.
- A local ledger records task IDs and redacted evidence without storing a transcript.
- Failure states such as quota exhaustion and active writers stop blind retries.

This repository is an independent Apache-2.0 implementation. It is not a fork
of `backnotprop/orchestrator`.

## Install the skill

Install the skill from the public repository:

```text
npx skills add waleeddogar/codex-thread-loom --skill codex-thread-loom
```

Add `-g` for a user-level installation. The repository also works as a
project-local skill. Copy
`skills/codex-thread-loom` into `.agents/skills/` when a project needs a pinned
version.

## Install the plugin package

The repository includes a validated `.codex-plugin/plugin.json` manifest. Codex
builds that support remote plugin marketplaces can add the repository with:

```text
codex plugin marketplace add waleeddogar/codex-thread-loom
codex plugin list
```

If the build expects a marketplace manifest instead of a plugin-root
repository, use the skill install above. The skill and plugin contain the same
operating policy.

## Use the skill

Invoke it with `$codex-thread-loom`, or let Codex select it when the request
needs durable worker threads.

```text
$codex-thread-loom

Plan the billing work in this repository. Route implementation to the named
implementation thread, send tests to the test thread, and review the diff in
this thread. Use live model discovery. Keep packets compact. Do not push.
```

The skill uses native Codex app actions when they are available:

- `list_threads` resolves existing named workers.
- `send_message_to_thread` sends a bounded packet to an idle worker.
- `wait_threads` waits for up to eight workers in one call.
- `read_thread` retrieves only the evidence needed for integration.
- `set_thread_archived` retires a worker only when the user asks.

The skill does not create duplicate workers. It creates a new thread only when
the user authorizes that action and no matching worker exists.

## Configure a roster

Start from [`examples/roster.json`](examples/roster.json). Keep real thread IDs
in a local ignored file. Do not commit them.

Validate a roster:

```bash
python3 -m pip install -e '.[dev]'
codex-thread-loom validate-roster examples/roster.json
```

Create compact packets before sending them:

```bash
codex-thread-loom plan \
  --roster examples/roster.json \
  --objective "Fix the reading-level fallback and add regression tests." \
  --allowed-path packages/shared/src/reading-level.ts \
  --allowed-path packages/shared/src/reading-level.test.ts \
  --acceptance "Known profile labels keep their current mapping." \
  --acceptance "Inherited property names return the safe fallback." \
  --acceptance "The focused test and type check pass." \
  --constraint "Do not read environment files or credentials." \
  --run-id storibuk-reading-level
```

The helper only plans packets. It does not start threads, execute model output,
or call a provider API. This boundary makes local automation easier to audit.

## Model and token policy

The skill treats model names as live runtime data:

1. Inspect the current catalog and runtime limits.
2. Resolve `frontier`, `balanced`, and `efficient` role selectors against that catalog.
3. Use Astra for difficult planning and review when the runtime exposes Astra.
4. Use an efficient model for bounded implementation and test work.
5. Increase reasoning effort only when the task or an evaluation supports the cost.
6. Keep Fast mode and extra-high effort opt-in because they can consume an allowance faster.
7. Do not set a hard goal token budget unless the user asks for a cap.

Read [`skills/codex-thread-loom/references/ASTRA.md`](skills/codex-thread-loom/references/ASTRA.md)
for the detailed policy.

## Persistent thread policy

Use exact thread titles and keep the provider thread ID in local state. Do not
send a follow-up while the provider reports an active writer. If a worker hits a
usage limit, record the failure and stop. Resume after the limit resets or use a
declared fallback. Do not repeat the same request blindly.

Read [`skills/codex-thread-loom/references/PERSISTENT_THREADS.md`](skills/codex-thread-loom/references/PERSISTENT_THREADS.md)
for the lifecycle and recovery rules.

## Evidence from the StoriBuk trial

The first live trial on StoriBuk showed that a persistent worker can complete a
small bounded code task with focused tests and type checks. The follow-up turn
hit the account usage limit. A later resume attempt found an active writer.
That result shaped the default policy: use persistent threads, but treat quota
and writer state as explicit failure states. Do not hide them behind retries.

This was a practical smoke test, not a benchmark. See
[`skills/codex-thread-loom/references/COMPARISON.md`](skills/codex-thread-loom/references/COMPARISON.md)
for the decision record.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
python3 -m pytest
ruff check .
python3 -m compileall -q src scripts
```

The package uses no runtime dependencies. It never starts a Codex thread from
the Python helper.

## Project documents

- [`ARCHITECTURE.md`](skills/codex-thread-loom/references/ARCHITECTURE.md) explains the control plane.
- [`OPERATING_POLICY.md`](skills/codex-thread-loom/references/OPERATING_POLICY.md) defines limits and stop rules.
- [`RESULT_SCHEMA.md`](skills/codex-thread-loom/references/RESULT_SCHEMA.md) defines worker evidence.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) explains development and releases.
- [`SECURITY.md`](SECURITY.md) explains the security boundary.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
