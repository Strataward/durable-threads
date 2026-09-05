# Repository instructions

## Scope

Codex Thread Loom is a small, provider-neutral skill and helper library. It
coordinates durable Codex threads. It does not store prompts, source files,
credentials, or child and family data.

## Required checks

Run these checks before a pull request:

```text
python3 -m pytest
ruff check .
python3 -m compileall -q src scripts
```

Run the skill and plugin validators when you change their package files.

## Safety rules

- Keep architecture and security decisions in the parent thread.
- Use live model discovery. Do not invent a model identifier.
- Do not add real thread IDs to examples or committed files.
- Do not log secrets or copy full conversation transcripts into task packets.
- Do not merge, push, deploy, or create a thread without explicit user intent.
- Preserve unrelated work in a target repository.

## Style

Use short sentences. Use active voice. Use one term for one meaning. Keep
examples complete and runnable.
