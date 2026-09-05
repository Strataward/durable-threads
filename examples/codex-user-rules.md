# Optional Codex user rule

Add this section to your Codex user instructions if you want the same routing
boundary across projects. Preserve your other instructions. The skill does
not install or change user rules automatically.

## Durable Threads: use only for useful handoffs

Continue in the current task when its model and context fit the work. Do not
use `durable-threads` merely to retain context or continue related edits.
Use the skill when a cheaper suitable model, narrower context, or independent
owner justifies a handoff. State that benefit before sending work.
Prefer one authorized existing worker. Create a new Codex task only when the
user explicitly requests it. Keep packets small. Verify the diff and acceptance
checks. Allow at most one correction by default. Stop on quota, authentication
failure, uncertain writer state, or exhausted retries. Do not rotate task IDs
to bypass a stop. Do not claim subscription savings from token counts alone.
