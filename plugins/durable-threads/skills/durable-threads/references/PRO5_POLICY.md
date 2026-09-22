# Optional Python and TypeScript allowance tools

Use [PRO5.md](PRO5.md) for the native workflow. It is the canonical allowance policy.

The optional TypeScript adviser uses a 15% reserve and a 64-generation budget. The native Node adviser uses a 10% reserve and a 60-generation budget. These are separate experiment defaults. Neither tool enforces account limits. Do not combine their counters or treat either reserve as a service limit.

The Python helper can inspect one configuration file or print example profiles. Keep the user's current model and effort unless the user requests a change. The experimental TypeScript adapter requires tests on the exact runtime before use.

## Optional local tools

The installed skill includes `scripts/pro5.py`:

```bash
python3 scripts/pro5.py profile
python3 scripts/pro5.py audit --config "$HOME/.codex/config.toml"
python3 scripts/pro5.py probe --codex codex
python3 scripts/pro5.py schema --codex codex
```

Run these from this skill directory, or use the discovered full script path. `profile` prints TOML to merge, never overwrites configuration. `audit` reads one file, not all effective configuration layers. `probe` requests account type, model catalog and quota metadata through Codex; it requests no model turn, performs no login, and prints no account email/ID. `schema` checks the binary's experimental schema without starting inference. Neither proves a live effort transition, billing savings or 5x entitlement.
