# Security policy

## Supported versions

Only the latest release receives security fixes during the alpha period.

## Report a vulnerability

Do not open a public issue for a security vulnerability. Use GitHub private
vulnerability reporting for this repository. Include the affected version, a
minimal reproduction, impact, and a proposed mitigation when known.

Do not include credentials, private source, child or family data, or complete
agent transcripts in a report.

We will acknowledge a report within seven days. We will provide a status update
when we confirm the issue and after we release a fix.

## Security design

The project treats model output as untrusted data. The helper library does not
execute model output, call provider APIs, or read environment files. The skill
requires the parent agent to review task scope and evidence before it mutates a
repository.

The local ledger is best-effort state. It stores redacted summaries and task
metadata. It does not store full prompts or transcripts.
