# Astra operating guide

This guide describes the role policy. It does not promise that an account or
runtime can use Astra.

## Availability

Check the live Codex catalog and the account allowance before selecting Astra.
Use the exact ID returned by the runtime. If Astra is absent, report that fact
and use the declared fallback. Do not guess a versioned slug.

## Role placement

Use Astra where its additional reasoning can reduce total work:

- define the plan for a complex change;
- choose the smallest safe task split;
- review a diff and test evidence;
- decide whether a correction is required.

Keep routine edits, focused tests, and simple documentation on an efficient
model. A strong planner should reduce repeated context and rework. It should
not turn every small task into a frontier-model call.

## Reasoning effort

Start with `high` for a complex planner or reviewer. Use `medium` when the
review is narrow. Use `low` for a bounded worker. Use `xhigh` or `max` only when
an evaluation shows a material quality gain.

Higher effort is not automatically better. Weak stopping criteria can cause
extra searching and extra tool calls. State the acceptance checks before the
worker starts.

## Context and notes

Use native Codex notes and searchable history when the current runtime provides
them. Ask Astra to record durable facts, failed approaches, and test evidence
in the worker or planner context. Do not duplicate a full old transcript in a
new packet.

Use a short handoff with:

1. the current objective;
2. the files or paths in scope;
3. the checks that prove completion;
4. the constraints that must remain true;
5. the one decision that the next thread must make.

## Usage policy

Fast mode and higher effort can consume a subscription allowance faster. Keep
them off by default when the goal is token longevity. Do not set a hard durable
goal budget unless the user asks for a cap. A hard cap can stop a useful task
before its evidence is complete.

Measure total task value, not only output tokens. A more capable planner can
save usage when it prevents a bad fan-out, repeated context, or correction
loop.

## Safety policy

Astra can perform powerful multi-step work. Keep the same path, approval, and
external-action boundaries that apply to every model. The planner must inspect
the final diff. The skill never treats a model claim as independent acceptance.

## Official references

- [GPT-6 Astra announcement](https://openai.com/index/gpt-6-astra/)
- [GPT-6 Astra model guide](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Codex durable-goal use case](https://developers.openai.com/codex/use-cases)
