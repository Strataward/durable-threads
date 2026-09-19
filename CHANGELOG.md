# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning after the 1.0 release.

## [Unreleased]

### Added

- Add `HeuristicDecisionEngine` and `DURABLE_THREADS_DECISION_ENGINE` for deterministic offline decisions.
- Add the `scripted` test executor behind `DURABLE_THREADS_ENABLE_SCRIPTED`.
- Add Temporal workflow tests with a time-skipping environment.
- Add `scripts/bench_durable.py` and the durable-mode overhead report.
- Add the `ops/temporal` self-hosted development compose stack.

### Fixed

- Fix the worker entrypoint so sync Activities receive a thread-pool `activity_executor`.
- Fix verification so it reads the existing `concerns` field instead of a non-existent `remaining_concerns` attribute.
- Fix routing so no remaining executor returns a failed task after `switch_executor`.
- Fix evidence validation so runtime-extensible provider IDs are accepted.

### Planned

- Add an optional OpenAI Agents API backend for headless/CI/SaaS execution and normalized subagent telemetry.
- Expand matched model/effort benchmarks before making empirical routing automatic.
- Compare single Codex, native multi-agent Codex, and native multi-agent + Durable Threads policy on the same task corpus.

## [0.6.0] - 2026-09-19

### Added

- Optional Temporal durable mode with crash-resilient task and child-execution workflows.
- TypeSafe Jev decision engine for typed risk, delegation, ambiguity, execution-shape, evidence, and intervention judgments.
- Deterministic uncertainty gates where probabilistic confidence informs policy but never authorizes side effects by itself.
- Provider-neutral `ExecutionRegistry` with capability routing and `durable_threads.executors` entry points.
- Durable human-review signals, workflow status queries, execution heartbeats, and evidence verification against the actual git diff.
- `jev`, `temporal`, and `durable` optional dependency groups plus Temporal worker/client CLIs.

### Changed

- Provider IDs in advanced rosters are now runtime-extensible rather than restricted to a closed built-in enum.
- R0-R4 deterministic risk is a floor: semantic classification may raise consequence but cannot silently lower it.
- Shared-checkout writers remain serialized; parallel mutation requires isolated workspaces.
- Bump package/plugin version to 0.6.0.

## [0.5.0] - 2026-09-12

### Changed

- Reposition Durable Threads as a risk- and cost-aware **policy layer** for native coding-agent runtimes rather than a replacement for Codex's own subagent lifecycle.
- Prefer native Codex subagents for normal interactive execution.
- Map read-heavy discovery to Codex `explorer` and bounded implementation/debugging to `worker`.
- Define the parallelism rule: **subagents for parallel cognition, worktrees for parallel mutation**.
- Prefer native wait/resume behavior over parent-agent polling loops.
- Keep external Claude Code, Grok Build, and Cursor adapters as explicit opt-in runtimes rather than default workers.
- Bump package/plugin version to 0.5.0.

### Added

- `docs/NATIVE_MULTI_AGENT.md` with the policy/runtime/verification architecture, native role mapping, worktree guidance, and Agents API boundary.
- `durable_threads.native` execution hints for built-in Codex role mapping and shared-write/read-only/worktree/serial workspace recommendations.
- Tests for native role mapping, read-only sharing, worktree recommendations, and overlapping-writer serialization.
- Optional read-only native Codex role examples under `examples/codex-agents/`.
- Explicit plugin update documentation using:

  ```bash
  codex plugin marketplace upgrade strataward && codex plugin add durable-threads@strataward
  ```

### Compatibility

- Pre-native-multi-agent v0.4 state is preserved at `archive/pre-native-multi-agent-2026-09-12`.
- Normal plugin use remains zero-config; custom `.codex/agents/` roles and the Python helper are optional.
- The OpenAI Agents API is documented as an optional future/headless backend, not a requirement for plugin users.

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
