# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning after the 1.0 release.

## [Unreleased]

### Fixed

- Accept an explicit empty concerns array without a model correction. Missing fields still fail.

- Persist the original task retry limit. Reject changes and legacy records without a limit.
- Reject invalid JSON list fields instead of discarding invalid entries.

### Changed

- Prefer the current retained session when its model and context fit the work.
- Add an optional output schema and a guide for deciding when a handoff adds value.
- Record the final comparison against a direct retained session, not only fresh sessions.

- Keep routing instructions with the planner. Send only the task packet to workers.
- Prefer direct execution for small tasks and one persistent worker for related work.
- Keep subscription savings unproven until a matched evaluation supports them.

### Added

- Selective routing with explicit worker selection and a local-only route.
- Evidence parsing and comparison with changed repository paths.
- Optional dispatch records with usage counters and session identity checks.
- Exclusive ledger transaction locks and bounded follow-up indices.
- Failure tests for blocked states, session drift, and repeated calls.

### Limits

- Token savings remain unmeasured. Provider recovery remains manual.
- Evidence validation does not execute reported checks or sandbox file writes.

- Initial public release of the Codex Thread Loom skill and helper library.
- Durable-thread operating policy for planning, execution, review, and recovery.
- Model discovery and role-based routing contracts.
- Redacted local ledger support for task state and usage evidence.
- Mermaid architecture diagram in the README.

### Changed

- Moved the public repository to the Strataward organization.

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
