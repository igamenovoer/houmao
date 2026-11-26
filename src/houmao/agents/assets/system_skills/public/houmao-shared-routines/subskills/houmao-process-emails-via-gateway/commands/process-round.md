---
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

# Process One Notifier Mail Round

## Workflow

1. **Validate prompt bootstrap fail-closed**: require exact `gateway_base_url`, `channel` (`offline|online`), and `expected_binding_id` from the current prompt; if any is missing, stop and report a notifier contract error without calling `resolve-live`. Confirm via `houmao-mgr agents self mail status` when needed and abort immediately if the binding changed or was replaced.
2. **List open inbox metadata**: call `houmao-mgr agents self mail list` or `POST /v1/mail/{channel}/list` with `"schema_version": 3`, `expected_binding_id`, finite `limit: 50` (max `200`), and the prompt's notifier mode filter (`unread_only` -> unread unarchived inbox mail; `any_inbox` -> open unarchived inbox mail including read/answered). Inspect one page unless the prompt grants a paging budget; stop on a stale `next_cursor` rather than mixing snapshots.
3. **Prioritize stalled work first**: triage metadata (`message_ref`, `thread_ref`, sender, subject, timestamps, read/answered state). Resume any open email representing stalled or interrupted work from an earlier round before selecting unrelated new mail; defer out-of-scope emails to later rounds.
4. **Read selected messages and verify completeness**: inspect only selected messages via `peek` or `read` with `expected_binding_id` (see `houmao-shared-routines->houmao-agent-email-comms` for exact `/v1/mail/*` shapes). Check `content_complete` and content-limit fields; report truncated or missing content rather than assuming full inspection.
5. **Record reply obligations and optional hardening**: identify every selected `message_ref` that requires a reply before starting work; if the prompt requests reply hardening, create one `one_off` lowest-priority reminder (`--after-all`, default `start_after_seconds: 15`) per [../references/reply-hardening.md](../references/reply-hardening.md) and record its `reminder_id`.
6. **Execute work, send replies, and reconcile compact receipts**: complete the work for each selected email, then send required replies via `POST /v1/mail/{channel}/reply` (or `houmao-mgr agents self mail reply`) carrying `expected_binding_id`. Confirm delivery from the compact write receipt's top-level `message_ref` (and optional `peek` on the same binding rather than expecting legacy full-body echoes).
7. **Handle reply or attachment permission denials fail-closed**: if `mail.reply` or `mail.attachment.owner_file` authorization is refused, report the exact denial, do not archive that message, and leave it open in the inbox for follow-up.
8. **Clean up reminders, archive completed items, and stop**: remove any unfired reply-hardening `reminder_id` (`houmao-mgr agents self gateway reminders remove --reminder-id <id>` or `DELETE /v1/reminders/{reminder_id}`) once its normal reply succeeds, archive only messages whose work and required reply both succeeded, and end the turn without polling.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded round plan from [../references/reply-hardening.md](../references/reply-hardening.md) and the notifier prompt, then execute the plan.

## Guardrails

- DO NOT pass `"include_body"` on `/v1/mail/{channel}/list` or treat `has_more` page samples as full inbox totals.
- DO NOT archive a message before its task and any required reply succeed, or after a `mail.reply` / `mail.attachment.owner_file` refusal.
- DO NOT poll for additional mail after the round finishes.
