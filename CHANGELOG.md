# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning after the 1.0 release.

## [Unreleased]

### Planned

- Add CLI flags for explicit `decisions`, `invariants`, `non-goals`, and risk override; the Python packet API already carries these fields.
- Expand matched model/effort benchmarks before making empirical routing automatic.

## [0.3.0] - 2026-09-12

### Added

- Model-economic orchestration strategy with `economy`, `balanced`, and `frontier` profiles.
- Execution classes: `decision`, `workhorse`, `review`, and `specialist`.
- Deterministic R0-R4 task-risk classification and risk-aware security routing.
- Frontier-review threshold and evidence-gated model escalation policy.
- Sleeping-orchestrator policy to prevent repeated unchanged-state parent polling.
- Rich implementation packets with frozen decisions, invariants, non-goals, risk, and execution class.
- Detailed model-economics, risk-routing, packet-contract, architecture, benchmarking, and migration documentation.
- Long-form article: `docs/articles/frontier-decisions-cheap-execution.md`.
- Tests for economy defaults, risk classification, high-risk routing, and enriched packets.

### Changed

- Reference Codex roster now defaults implementation and test/debug work to `efficient` + `xhigh`.
- Reference planner frontier effort drops from `high` to `low`.
- Reference first-line reviewer becomes `efficient` + `xhigh`; frontier review is recommended at R3+.
- Main doctrine now explicitly separates decision work from execution work.
- README and plugin metadata now point to the Strataward repository.
- Package and plugin version bumped to 0.3.0.

### Compatibility

- Schema-v1 rosters continue to load.
- Pre-v0.3 repository state is preserved at `archive/pre-model-economics-2026-09-12`.

### Evidence note

- Current OpenAI usage figures and model guidance are linked as dated references, not encoded as permanent constants.
- Community telemetry is treated as observational evidence rather than an official quota guarantee.

## [0.2.0] - 2026-09-05

### Added

- Renamed the public project to Durable Threads.
- Added provider-aware rosters and packet metadata.
- Added custom command adapters for Claude Code, Grok Build, and Cursor Agent.
- Added provider diagnostics, command rendering, and explicit dispatch.
- Added multi-provider examples and provider research notes.

### Changed

- Kept `codex-thread-loom` as a compatibility CLI entry point.
- Kept model selection provider-specific when a safe generic mapping is not available.

## [0.1.0] - 2026-09-04

### Added

- Initial alpha package.
