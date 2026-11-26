---
name: houmao-agent-email-comms
description: Use when ordinary Houmao mailbox work needs operator-origin posting, managed-agent `offline` or Stalwart `online` mail, gateway-backed `/v1/mail/*`, or a supported no-gateway transport fallback.
license: MIT
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Agent Email Comms

## Overview

Perform ordinary Houmao `offline` and Stalwart `online` mailbox operations (`resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, `archive`) with pinned `expected_binding_id` and compact receipt reconciliation.

## Workflow

1. **Answer explicit `help` first** from **Help** without probing bindings, listing messages, or mutating mail state.
2. **Enforce the Actor Frame Gate** and resolve live mailbox bindings (`houmao-mgr agents self mail resolve-live` for verified self; `houmao-mgr agents single --agent-id|--agent-name ... mail resolve-live` for an explicit target).
3. **Select `offline` or `online` explicitly** from `mailboxes.offline` / `mailboxes.online` and pin that slot's `binding.binding_id` (`--expected-binding-id`); `canonical_mail_identity` describes the preferred address and never chooses a channel.
4. **Execute the selected subcommand** via `houmao-mgr agents self|single ... mail <verb> --channel <offline|online> --expected-binding-id <binding_id>` (or exact `/v1/mail/{channel}/*` with `schema_version: 3`; see [references/endpoint-contract.md](references/endpoint-contract.md)). Stop immediately on admission/policy refusal or binding replacement.
5. **Reconcile writes and pagination cleanly**:
   - Triage with bounded metadata pages (`limit: 50`, max `200`, never `include_body`), check `content_complete` on `peek`/`read`, and check the binding's supported operations before filing completed work.
   - Confirm `send`, `reply`, and `post` from their compact write receipt (`status`, `authoritative`, top-level `message_ref`) and use `mail peek` on the same channel and binding when message details are needed; if `authoritative: false` leaves a detached write uncertain, verify read-only before retrying.
   - Treat confirmed offline deposit or provider submission as the sender's transport result. The recipient backend can file a matching new message directly into Archive. A receipt gives no recipient placement or reminder evidence.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **References**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed.

- **Admin branch**: require an explicit recipient or mailbox target and use operator-origin `post` (`commands/post.md`) rather than treating the operator shell as `agents self`.
- **Agent branch**: require fresh verified self identity and use `houmao-mgr agents self mail ...` by default (detached gateways or missing mail bindings never turn an agent into an operator). Route notifier-prompted unread rounds to `houmao-shared-routines->houmao-process-emails-via-gateway` first, `mailbox offline`/`mailbox online` attachment and root CRUD to `houmao-shared-routines->houmao-mailbox-mgr`, `mail-notifier`/reminders to `houmao-shared-routines->houmao-agent-gateway`, and `mail.*` / `mail.attachment.owner_file` grants to `houmao-shared-routines->houmao-agent-access`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `resolve-live` | Resolve `mailboxes.offline`, `mailboxes.online`, `binding_id`, and live `gateway.base_url`. | [Resolve Live](commands/resolve-live.md) |
| `status` | Inspect configured `offline`/`online` bindings, availability, and `canonical_mail_identity`. | [Status](commands/status.md) |
| `list` | List bounded metadata pages (`limit: 50`, max `200`, no `include_body`). | [List](commands/list.md) |
| `peek` | Read selected message content (`content_complete`) without changing read state. | [Read or Peek](commands/read.md) |
| `read` | Read selected message content (`content_complete`) and mark it read. | [Read or Peek](commands/read.md) |
| `send` | Send a managed-agent outbound message and verify its compact `message_ref` receipt. | [Send](commands/send.md) |
| `post` | Deliver an operator-origin note into an explicit target's `offline` mailbox. | [Post](commands/post.md) |
| `reply` | Reply to an opaque `message_ref` on the same channel and binding (`mail.reply`). | [Reply](commands/reply.md) |
| `mark` | Mutate `--read/--unread`, `--answered/--unanswered`, or `--archived/--unarchived` flags. | [Mark](commands/mark.md) |
| `move` | Move selected messages to `--destination-box` within the same binding. | [Move](commands/move.md) |
| `archive` | Archive processed mail after required replies succeed when the binding supports ordinary archive. | [Archive](commands/archive.md) |
| `help` | Read-only summary of `offline`/`online` channels, binding pinning, receipts, and backend placement. | **Help** |

## References and Help

- **Transports and contracts**: [references/endpoint-contract.md](references/endpoint-contract.md), [references/scoped-cli.md](references/scoped-cli.md), [references/managed-agent-fallback.md](references/managed-agent-fallback.md), [references/transports/filesystem.md](references/transports/filesystem.md), [references/transports/stalwart.md](references/transports/stalwart.md), [references/filesystem-resolver-fields.md](references/filesystem-resolver-fields.md), [references/stalwart-resolver-fields.md](references/stalwart-resolver-fields.md), and [references/filesystem-layout.md](references/filesystem-layout.md). For multi-step wakeup or loop compositions, see `houmao-shared-routines->houmao-adv-usage-pattern`.
- **Help**: summarize caller posture (`post` vs `self mail`), `offline` vs Stalwart `online` isolation, `expected_binding_id` pinning, compact receipts, backend delivery rules, and neighboring routines read-only.

## Guardrails

- DO NOT bridge `offline` and `online` channels, infer channel from `canonical_mail_identity`, translate addresses across transports, or retry against a replacement binding.
- DO NOT guess gateway URLs (use prompt context or `resolve-live`), scrape tmux for mail state, or route operator-origin notes through `send` instead of `post`.
- DO NOT parse opaque `message_ref`/`thread_ref` strings, pass removed `include_body`/`--include-body` flags, auto-drain cursors, or treat truncated `content_complete: false` bodies as complete.
- DO NOT archive messages before work and required replies succeed, or use this routine in place of `houmao-shared-routines->houmao-process-emails-via-gateway` for a notifier round.
