# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning after the 1.0 release.

## [Unreleased]

### Changed

- Rewrite the model-economics article for a more natural engineering audience and replace fragile block math with GitHub-safe prose.
- Standardize primary diagrams on a hybrid layout: left-to-right system flow with top-to-bottom detail inside major planes.
- Rework reader-facing guidance so setup, customization, delegation, provider behavior, and model policy are easier to scan without losing technical precision.
- Refresh installation and OpenAI compatibility references against the current plugin/skill and Codex CLI sources.

### Added

- Markdown documentation validation for unclosed code fences, unsupported `$$` block-math delimiters, unfinished placeholders, and broken local links.

### Planned

- Expand matched model/effort benchmarks before making empirical routing automatic.
- Consider a guided `durable-threads init` only if real users need persistent project policy; zero-config use remains the default.

## [0.4.0] - 2026-09-12

### Changed

- Normalize Durable Threads as one product: a Codex plugin that bundles one canonical skill.
- Move the canonical skill to `plugins/durable-threads/skills/durable-threads/` and the plugin manifest to `plugins/durable-threads/.codex-plugin/plugin.json`.
- Add a repo/team marketplace at `.agents/plugins/marketplace.json` following the current Codex plugin layout.
- Replace parallel skill/plugin setup with one normal plugin installation path.
- Make rosters, the Python helper, multi-provider adapters, and benchmark controls advanced opt-in features rather than prerequisites.
- Simplify the bundled skill so normal use requires no project configuration.
- Bump package/plugin version to 0.4.0.

### Added

- Detailed installation guide with Codex CLI, interactive plugin, IDE fallback, and project-pinning paths.
- Progressive customization guide from zero-config use through explicit multi-provider rosters.
- Dated OpenAI compatibility audit separating documented product behavior from Durable Threads policy.
- Repository validation for canonical plugin layout, marketplace source, bundled skill, semver alignment, and obsolete install instructions.

### Compatibility

- Pre-simplification v0.3 state is preserved at `archive/pre-simplified-setup-2026-09-12`.
- Standalone skill users can install the same bundled skill directly; no duplicate skill implementation is maintained.

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

- Reference Codex roster defaults implementation and test/debug work to `efficient` + `xhigh`.
- Reference planner frontier effort drops from `high` to `low`.
- Reference first-line reviewer becomes `efficient` + `xhigh`; frontier review is recommended at R3+.
- Main doctrine explicitly separates decision work from execution work.

### Compatibility

- Schema-v1 rosters continue to load.
- Pre-v0.3 repository state is preserved at `archive/pre-model-economics-2026-09-12`.

## [0.2.0] - 2026-09-05

### Added

- Renamed the public project to Durable Threads.
- Added provider-aware rosters and packet metadata.
- Added custom command adapters for Claude Code, Grok Build, and Cursor Agent.
- Added provider diagnostics, command rendering, and explicit dispatch.
- Added multi-provider examples and provider research notes.

## [0.1.0] - 2026-09-04

### Added

- Initial alpha package.
