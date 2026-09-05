# When to use Durable Threads

The final local trial favored a direct retained session for three related
changes with the same model. Both approaches passed. The protocol used more
input tokens. Keep direct continuation as the default for that workload.

Use the simplest mode that meets the task requirements. A persistent session
is useful without an orchestration skill. The skill adds scope, evidence, and
stop rules when work crosses an ownership boundary.

| Situation | Starting mode | Reason |
| --- | --- | --- |
| Small fix, question, or one-file review | Current task | A handoff adds work. |
| Related edits; current task has the right model and context | Continue the current task | Keep context without another owner. |
| Bounded implementation that a cheaper model can complete | One worker, with this skill | Separate planning from routine execution. |
| Specialist work that benefits from narrower context | One worker, with this skill | Keep unrelated history out of the packet. |
| Independent changes with separate allowed paths | At most two workers | Parallel work must not create conflicting writers. |
| Quota, authentication failure, or uncertain writer state | Stop | A new session is not a recovery procedure. |

These are planner rules, not an automatic classifier. The helper's keyword
routing does not prove that a handoff will save tokens. Inspect each proposal.
Use `plan --local` when no worker is needed.

## Start a worker only for a stated benefit

State the benefit in one sentence: a cheaper suitable model, narrower context,
or independent ownership. If none applies, continue in the current task.
Use the frontier model for difficult decisions and final risk review, not for
every status check or routine edit. Model substitution benefits remain a
hypothesis until measured for that workload.

Give the worker the objective, allowed paths, acceptance commands, constraints,
and result shape. Do not send the full chat or the planner skill. Prefer one
worker for related implementation. Create a new app task only when the user
explicitly requests it. Otherwise use an authorized existing worker or work
in the current task.

## Before sending

Confirm the provider, model, session ID, working directory, idle state, and
permissions. Confirm that dependencies and acceptance commands work. Use a
clean isolated checkout when the worker will write files. Record the original
retry limit before execution. Do not change these settings during a comparison.

In Codex CLI evaluations, set the sandbox on the parent command for both new
and resumed execution: `codex exec --sandbox workspace-write resume ...`.
This is a tested CLI path, not a replacement for native app task actions.

## Accept work without needless corrections

Use the supplied JSON schema where supported. Then validate the result against
the actual changed paths. An explicit empty concerns array means no concerns.
A missing field remains an error. Do not ask a model to rewrite valid empty
arrays into prose.

Run acceptance commands independently. Do not accept code because its result
has the right format. Use at most one correction for a demonstrated defect.
If the correction fails, stop and report the unresolved issue. Do not change
task IDs to obtain more retries. New, distinct work can reuse an idle session.

## Judge value

Compare against a direct session that also retains context. A fresh session
for every edit is a separate baseline and can overstate the value of the skill.

Keep code correctness and allowed paths as gates. Then compare total calls,
corrections, elapsed time, and all provider counters. Show cached input
separately. Include planner and reviewer usage when available. Mark missing
usage and subscription cost as unknown.

Do not require a fixed saving percentage from every small task. Keep the skill
only where its scope and evidence controls justify the extra work. Do not claim
that raw token savings extend a subscription by the same percentage.
