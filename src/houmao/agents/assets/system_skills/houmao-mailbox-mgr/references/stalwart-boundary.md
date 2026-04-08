# Stalwart Boundary

Use this reference when a mailbox-admin task mentions the `stalwart` transport.

The maintained mailbox-admin CLI in v1 is filesystem-oriented for:

- `houmao-mgr mailbox ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents mailbox ...`

What this means:

- mailbox-root lifecycle, mailbox account lifecycle, structural message inspection, and late managed-agent binding in this skill all route through filesystem mailbox surfaces
- Stalwart is still part of Houmao's supported mailbox story, but it is currently documented as runtime/session bootstrap rather than as a peer mailbox-root/account administration CLI family

When the task is specifically about Stalwart-backed mailbox setup or first-session workflow, use:

- `docs/reference/mailbox/operations/stalwart-setup-and-first-session.md`

Guardrail:

- Do not invent unsupported `houmao-mgr mailbox ...` root or account CRUD for Stalwart roots or accounts.
