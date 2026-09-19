# Repository instructions

## Scope

Durable Threads is one plugin whose canonical workflow is the bundled `durable-threads` skill. The Python helper and multi-provider adapters are optional advanced tooling.

Do not create a second copy of the skill as another installation surface. Keep the canonical source under `plugins/durable-threads/skills/durable-threads/`.

## Required checks

Run these checks before a pull request:

```text
python3 -m pytest
ruff check .
python3 -m compileall -q src scripts
python3 scripts/validate_repo.py
npm test
```

When installation or packaging changes, verify current OpenAI plugin/skill documentation and update `docs/OPENAI_COMPATIBILITY.md` with the audit date.

## Safety rules

- Keep architecture and security decisions in the parent/planner role.
- Use live model discovery. Do not invent a model identifier.
- Keep provider-specific session controls in the provider adapter.
- Do not add real thread IDs to examples or committed files.
- Do not log secrets or copy full conversation transcripts into task packets.
- Do not merge, push, deploy, or create provider sessions without explicit user intent.
- Preserve unrelated work in a target repository.

## Documentation style

Lead with the zero-config path. Put optional rosters, provider adapters, and benchmarking after the basic workflow. Clearly separate OpenAI product facts from Durable Threads policy.

Use short sentences. Use active voice. Use one term for one meaning. Keep examples complete and runnable.
