# Implementation packet contract

A Durable Threads worker should receive the smallest complete contract that lets it execute without reconstructing the planner's conversation.

## Required information

Every implementation packet needs objective, allowed paths, acceptance checks, constraints, and a result contract requiring changed paths, exact checks, and remaining concerns.

## V2 economic fields

The v2 operating model adds:

- `riskClass`: R0–R4 consequence class;
- `executionClass`: decision, workhorse, review, or specialist;
- `decisions`: architecture/product choices already made;
- `invariants`: properties that must remain true;
- `nonGoals`: nearby work the worker must not expand into.

These fields are particularly important when an efficient model is used at high reasoning effort because they prevent re-solving decisions the planner already made.

## Example

```json
{
  "objective": "Implement refresh-token rotation.",
  "riskClass": "R3",
  "executionClass": "workhorse",
  "decisions": [
    "Redis remains the refresh-token state store.",
    "Replay invalidates the token family."
  ],
  "invariants": [
    "Existing access-token behavior is unchanged.",
    "Refresh tokens are not persisted in plaintext."
  ],
  "nonGoals": [
    "Do not redesign the JWT abstraction.",
    "Do not change session UI."
  ],
  "allowedPaths": ["src/auth/**", "tests/auth/**"],
  "acceptance": [
    "A refresh token succeeds exactly once.",
    "Replay is rejected.",
    "Replay invalidates descendants.",
    "Focused tests and type checking pass."
  ]
}
```

## What not to send

Do not send full planner transcripts, credentials, raw private customer data, unrelated architecture history, speculative future work, or huge logs when a redacted failure summary is enough.

## Decisions vs constraints

A decision says what design has already been chosen. A constraint says what the worker must not violate.

## Invariants vs acceptance

An invariant is a property that must remain true. Acceptance is how completion is checked. Whenever possible, turn invariants into executable checks.

## Non-goals

Non-goals prevent opportunistic scope expansion and preserve minimal, reviewable diffs.

## Result contract

A `complete` result is invalid without status, provider, changed paths, exact checks/outcomes, and explicit remaining concerns. A model statement such as "looks good" is not acceptance evidence.
