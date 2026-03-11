---
name: email-via-mail-system
description: Describe how the filesystem-first mailbox protocol maps to a future true email system while staying semantically compatible. Use when Codex needs header mapping, reserved env-name guidance, or compatibility checks for a future mail-system adapter; do not use it as an implementation skill for this change.
---

# Email Via Mail System

## Overview

Use this skill to reason about how the filesystem-first mailbox protocol should map to a future true email system. This change does not implement that transport, so treat this skill as compatibility guidance rather than an operational runtime workflow.

## References

- Read [references/env-vars.md](references/env-vars.md) when checking reserved future env names for a mail-system adapter.
- Read [references/email-headers.md](references/email-headers.md) when you need exact header mapping or canonical threading rules for future true-email adaptation.

## Compatibility Checks

- Use the reserved common and mail-system-compatible env names defined in [references/env-vars.md](references/env-vars.md) when documenting or designing a future adapter.
- Do not assume those `AGENTSYS_MAILBOX_EMAIL_*` env vars are populated by the current runtime implementation in this change.

## Compatibility Rules

- Keep the canonical mailbox semantics primary and treat true-email fields as an adaptation layer.
- Preserve canonical reply ancestry using standard headers such as `Message-ID`, `In-Reply-To`, and `References`.
- Preserve canonical `thread_id` through explicit protocol metadata rather than subject-line heuristics.
- Keep the body Markdown-compatible and preserve attachment reference metadata so a future adapter can normalize back into the canonical mailbox model.
- Use the exact mapping rules in [references/email-headers.md](references/email-headers.md) instead of inventing mail-only semantics.

## Guardrails

- Do not claim that this change implements a working mail server, SMTP adapter, or IMAP adapter.
- Do not hardcode SMTP or IMAP hosts, ports, or mailbox addresses into instructions, prompts, or generated files.
- Do not use subject lines alone to determine thread identity.
- Do not drop canonical attachment reference metadata just because the transport is a real mail service.
- Do not treat reserved `AGENTSYS_MAILBOX_EMAIL_*` names as currently populated runtime bindings unless a future change explicitly implements them.
