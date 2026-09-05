# Worker result contract

A worker result must use this shape:

```text
Status: complete | blocked | failed
Changed paths:
- path/to/file
Checks:
- `command`: passed (N tests)
- `command`: failed (short reason)
Remaining concerns:
- None known
```

## Rules

- `Status` must be explicit.
- `Changed paths` must list only real paths.
- `Checks` must include exact commands and results.
- A failed check must remain visible.
- `Remaining concerns` must state uncertainty.
- Do not include a full transcript.
- Do not include credentials, private data, or unredacted logs.

The planner verifies the result against the working tree. A well-formed result
is useful evidence. It is not independent acceptance.
