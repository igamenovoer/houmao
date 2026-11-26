---
name: houmao-process-emails-via-gateway
description: Use when a verified Houmao-managed agent receives a notifier prompt with an exact gateway base URL, channel, and expected binding ID and must process one bounded round of open inbox mail.
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

# Houmao Process Emails Via Gateway

## Overview

Execute one bounded, fail-closed round of notifier-delivered inbox mail through a prompt-supplied gateway URL, channel, and binding ID, then stop without polling.

## Workflow

1. **Answer explicit `help` first** from **Help** without probing bindings, listing mail, setting reminders, sending replies, or archiving.
2. **Enforce the Actor Frame Gate**: require `actor_kind=agent`, fresh verified self identity, and prompt-supplied `gateway_base_url`, `channel` (`offline|online`), and `expected_binding_id` (fail closed if any is missing or mismatched).
3. **Load and execute [commands/process-round.md](commands/process-round.md)** for `process-round`, loading [references/reply-hardening.md](references/reply-hardening.md) when the prompt requests reply hardening.
4. **Stop immediately after the round** and wait for the next gateway notification without polling.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded round plan from [commands/process-round.md](commands/process-round.md), [references/reply-hardening.md](references/reply-hardening.md), and the notifier prompt, then execute the plan.

## Actor Frame Gate

This parent-scoped routine is `agent`-only under `houmao-shared-routines`. Reject `admin` frames and fail closed whenever `gateway_base_url`, explicit `offline|online` `channel`, or `expected_binding_id` is absent or replaced. Use `houmao-shared-routines->houmao-agent-email-comms` for ordinary mail outside a notifier round (or exact `/v1/mail/*` field contracts), `houmao-shared-routines->houmao-agent-gateway` for notifier/reminder administration outside the round, and `houmao-shared-routines->houmao-adv-usage-pattern` for multi-round loop design.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `process-round` | Triage, resume stalled work, read, process, reply (`message_ref` receipt), and complete one bounded notifier round using the binding's authorized filing path. | [commands/process-round.md](commands/process-round.md) |
| `help` | Explain the fail-closed notifier-round contract and reply hardening read-only. | **Help** |

## Help

Explain that `process-round` validates prompt-supplied `gateway_base_url`, `channel`, and `expected_binding_id`, prioritizes stalled earlier-round work before unrelated new mail, optionally attaches `one_off` `--after-all` reply-hardening reminders ([references/reply-hardening.md](references/reply-hardening.md)), verifies compact `reply` receipts (`message_ref` + optional `peek`), aborts archiving on `mail.reply` or `mail.attachment.owner_file` denials, archives completed items only where the binding permits it, otherwise reports them for owner filing, and stops without polling. Concrete round prompts execute `process-round`.

## Guardrails

- DO NOT guess or rediscover a missing `gateway_base_url`, `channel`, or `expected_binding_id` (never call `resolve-live` to patch a broken notifier prompt or infer `channel` from `canonical_mail_identity`).
- DO NOT continue against a replaced or mismatched mailbox binding, cross `offline`/`online` channels, pass removed `include_body` to `/v1/mail/{channel}/list`, or drain unbounded cursor pages.
- DO NOT abandon stalled open-mail continuation work for newer unrelated mail, or archive unfinished, deferred, reply-pending, or authorization-denied (`mail.reply` / `mail.attachment.owner_file`) messages.
- DO NOT use `repeat` reminders or `interval_seconds` for reply hardening, rerank existing reminders, send duplicate hardening replies, or leave unfired hardening reminders active after normal reply succeeds.
- DO NOT poll, sleep, or re-list mail after completing the current round.
