# Contributing

Thank you for improving Durable Threads.

## Before you start

Read `README.md`, `SECURITY.md`, `AGENTS.md`, and `docs/OPENAI_COMPATIBILITY.md`. Open an issue before a large change. Small bug fixes may go straight to a pull request.

## Development

Use Python 3.10 or newer.

```text
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
python3 -m pytest
ruff check .
python3 scripts/validate_repo.py
```

Keep changes small. Add a test for changed behaviour. Update the relevant reference document when operating policy changes.

## Packaging rule

Durable Threads is one product:

- `plugins/durable-threads/` is the plugin distribution root;
- `plugins/durable-threads/skills/durable-threads/` is the canonical workflow source;
- `.agents/plugins/marketplace.json` exposes that plugin from this repository.

Do not add a duplicate top-level skill as a second public installation path. Standalone-skill users should install the bundled skill directory itself.

## Pull requests

Describe the user problem and design choice. Include test evidence. List any behaviour that remains unverified. Do not include secrets, real thread IDs, private source, or raw model transcripts.

If a PR changes installation claims or plugin layout, cite the current OpenAI docs/source used to verify them and update the compatibility audit date.

## Commit messages

Use an imperative subject with a scope when useful:

```text
Simplify plugin installation
Fix secret redaction in local ledger
Docs: update Codex compatibility audit
```

## Releases

Use semantic versioning. Update `CHANGELOG.md`. Create a signed or protected tag in the form `vMAJOR.MINOR.PATCH`. The release workflow builds an archive and runs the complete validation suite.
