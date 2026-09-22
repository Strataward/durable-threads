# Pro 5x: Astra-first efficiency

This is Durable Threads policy, not an OpenAI quota entitlement. Optimize verified work per allowance, not raw model uptime. Dated product facts and caveats are in the repository's `docs/PRO5_OPTIMIZATION.md`.

## Default shape

Keep one Astra planner/context owner. Start routine bounded work at Astra medium, standard speed, when supported and authorized. Reserve high for difficult diagnosis or consequential decisions. Preserve explicitly chosen xhigh/max; do not lower effort merely because quota is low. Use `/fast status` to inspect speed; standard speed is the allowance-oriented choice, not a promise of equal latency.

Do not mandate delegation. Reuse the user's named role threads when useful; do not keep all of them generating continuously. Delegate implementation to a smaller available worker only when a compact contract makes that cheaper than finishing locally. A short edit rarely justifies worker startup plus a second review. An independent R3/R4 reviewer is still required; do not reuse the implementation conversation as its own independent review.

## Spend less before changing intelligence

- Batch independent file reads and focused checks. Return filenames, relevant lines, exit codes and bounded failures, not repeated full files or successful logs. Do not hide errors with pipelines or run dependent mutations concurrently.
- Keep prompts, tool schemas and stable instructions concise. Load only relevant references/MCP tools. Preserve required safety tooling. Avoid repeating complete plans at every checkpoint.
- Prefer native blocking/event-driven waits. A local process waiting is not a reason to wake Astra or Jev. When native notification is unavailable, expose the limitation; a skill cannot promise an out-of-band wakeup.
- Reuse relevant context while it saves re-exploration. Do not force a maximum context window or disable compaction. Make a bounded handoff at a natural milestone when unrelated history dominates. Store it only in a user-approved location, without secrets.
- Use deterministic checks for mechanical facts. Jev is optional, separately authenticated/billed, and suitable for batched ambiguous judgments—not every tool result. Its probabilities need evaluation, not unconditional trust.

## Stop before spending the final review budget

Inspect `/status` or the supported App Server rate-limit metadata. Observe both the five-hour and weekly windows when supplied; a `pro` plan label does not prove the 5x multiplier. Never convert raw tokens or API-dollar rates into a guessed subscription percentage.

Keep a configurable 15% local reserve as an initial operating policy. Below reserve, avoid starting new work and checkpoint safely. Reserve is not a hard service limit or permission to waive review. Refresh expired/missing snapshots instead of assuming quota refilled. Already-running work follows the host's normal limits and cancellation semantics.

For one bounded task, initial diagnostic budgets are 64 internal generations, 45 minutes, 6 generations without meaningful progress, or 3 repetitions of the same failure. These are tunable DT defaults, not OpenAI limits. A skill cannot enforce invisible counters: report unknown values rather than inventing them. The TypeScript policy functions consume observed counters; native execution still needs a qualified event source for automatic enforcement.

## Reasoning control

First try supported between-turn model/effort selection. Mid-turn `turn/settings/update` is an experimental App Server surface, not a terminal shortcut or ordinary `config.toml` edit. Never assume it is installed, enabled, or applied to the next inference.

Use live switching only after build/feature/model and compaction tests. Keep updates effort-only in this efficiency track. Do not optimize by changing permission or reviewer authority. `applied` means published; already-captured steps do not change. On `targetUnavailable` or an ambiguous transport failure, reconcile; never retarget or retry blindly.

## Optional local tools

The installed skill includes `scripts/pro5.py`:

```bash
python3 scripts/pro5.py profile
python3 scripts/pro5.py audit --config "$HOME/.codex/config.toml"
python3 scripts/pro5.py probe --codex codex
python3 scripts/pro5.py schema --codex codex
```

Run these from this skill directory, or use the discovered full script path. `profile` prints TOML to merge, never overwrites configuration. `audit` reads one file, not all effective configuration layers. `probe` requests account type, model catalog and quota metadata through Codex; it requests no model turn, performs no login, and prints no account email/ID. `schema` checks the binary's experimental schema without starting inference. Neither proves a live effort transition, billing savings or 5x entitlement.
