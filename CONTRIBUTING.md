# Contributing

Thank you for improving Codex Thread Loom.

## Before you start

Read `README.md`, `SECURITY.md`, and `AGENTS.md`. Open an issue before a large
change. Small bug fixes may go straight to a pull request.

## Development

Use Python 3.10 or newer.

```text
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
python3 -m pytest
ruff check .
```

Keep changes small. Add a test for changed behaviour. Update the relevant
reference document when the operating policy changes.

## Pull requests

Describe the user problem. Describe the design choice. Include test evidence.
List any behaviour that remains unverified. Do not include secrets, real thread
IDs, private source, or raw model transcripts.

The maintainer checks the patch, the tests, the skill validator, the plugin
manifest, and the security boundary before merge.

## Commit messages

Use an imperative subject with a scope when useful:

```text
Add durable-thread recovery policy
Fix secret redaction in local ledger
Docs: explain Astra role selection
```

## Releases

Use semantic versioning. Update `CHANGELOG.md`. Create a signed or protected
tag in the form `vMAJOR.MINOR.PATCH`. The release workflow builds an archive
and runs the complete validation suite.
