# Worker result contract

A worker result must use this shape:

```text
Status: complete | blocked | failed
Provider: codex | claude | grok | cursor
Changed paths:
- path/to/file
Checks:
- `command`: passed (N tests)
- `command`: failed (short reason)
Remaining concerns:
- None known
```

The `verify-result` command accepts the same fields in JSON form:

```json
{
  "status": "complete",
  "provider": "claude",
  "changedPaths": ["src/example.py"],
  "checks": ["pytest tests/test_core.py: passed"],
  "remainingConcerns": ["None known"]
}
```

## Rules

- `Status` must be explicit.
- `Changed paths` must list only real paths.
- `Checks` must include exact commands and results.
- A failed check must remain visible.
- `Remaining concerns` must state uncertainty.
- Do not include a full transcript.
- Do not include credentials, private data, or unredacted logs.

The verifier also checks that every changed path is allowed. When the planner
provides a clean baseline, it checks that the claimed paths match the actual
git diff.

The planner verifies the result against the working tree. A well-formed result
is useful evidence. It is not independent acceptance.
