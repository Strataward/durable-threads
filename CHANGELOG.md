# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning after the 1.0 release.

## [Unreleased]

### Added

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
