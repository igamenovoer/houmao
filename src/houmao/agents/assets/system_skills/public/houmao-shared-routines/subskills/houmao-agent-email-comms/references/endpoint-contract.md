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

# Shared Gateway Mail Contract, Receipts, and Policies

Use the exact `gateway_base_url` supplied by current context or returned by `houmao-mgr agents self mail resolve-live` (notifier rounds must already supply `gateway_base_url`, `channel`, and `expected_binding_id` fail-closed).

## Status and Lifecycle Routes (`schema_version: 3`)

`GET /v1/mail/status` reports `offline`, `online`, and `canonical_mail_identity` (`resolve-live` wraps slots under `mailboxes.offline` and `mailboxes.online`). Every channel-scoped lifecycle request body requires `"schema_version": 3` and `"expected_binding_id"` (including fresh `send` and `post`):

| Route | Required / Optional Fields | Notes |
| --- | --- | --- |
| `POST /v1/mail/{channel}/list` | `box`, optional read/answered/archived filters, `limit` (`50`, max `200`), `since`, `cursor` | Metadata-only (`messages`, `next_cursor`, `has_more`, `complete`); `include_body` is rejected. |
| `POST /v1/mail/{channel}/peek` | `message_ref`, optional `box` | Returns content + `content_complete` / limit fields without marking read. |
| `POST /v1/mail/{channel}/read` | `message_ref`, optional `box` | Returns content + `content_complete` / limit fields and marks read. |
| `POST /v1/mail/{channel}/send` | `to`, optional `cc`, `subject`, `body_content`, optional `attachments` | Managed-agent outbound send. The response contains `message.message_ref` and transport evidence. |
| `POST /v1/mail/{channel}/post` | `subject`, `body_content`, optional reply policy & `attachments` | Operator-origin note on supported offline backends. The response contains `message.message_ref`. |
| `POST /v1/mail/{channel}/reply` | `message_ref`, `body_content`, optional `attachments` | Replies in-thread. The response contains the new `message.message_ref`. |
| `POST /v1/mail/{channel}/mark` | `message_refs`, one or more `read`/`answered`/`archived` booleans | Updates flags on the pinned binding. The archived flag requires placement authority. |
| `POST /v1/mail/{channel}/move` | `message_refs`, `destination_box` | Moves messages between boxes when current placement capabilities permit it. |
| `POST /v1/mail/{channel}/archive` | `message_refs` | Archives completed messages where the binding permits ordinary archive. |

See [scoped-cli.md](scoped-cli.md) for CLI invocation and [managed-agent-fallback.md](managed-agent-fallback.md) when no gateway is attached.

## Compact Write Receipts

The CLI returns compact receipts with `status`, `authoritative`, top-level `message_ref`, and `parent_message_ref` on reply. The direct gateway HTTP response carries the reference at `message.message_ref`. Both expose `transport_evidence` on success. Inspect stored fields with `mail peek` on the same channel and binding. Reconcile a submission-only or uncertain write with same-binding `peek` or `mail list --box sent` before resending.

## Write Permissions

- **Sender gateway write actions**: the sender's gateway checks `mail.send`, `mail.reply`, or `mail.post` on the selected channel and binding; non-empty `attachments` additionally require `mail.attachment.owner_file` on that same binding.

## Backend Delivery and Placement

The selected mail backend owns recipient placement. A matching new arrival on a protected binding goes directly to Archive, including while the recipient gateway is stopped. Rule changes apply to subsequent deliveries. A verified `transport_evidence` value of `offline_deposit` confirms a deposit, and `provider_submission` confirms provider acceptance. Both preserve the sender's channel and binding and omit recipient rules and folder placement.

Check `GET /v1/mail/status` for the selected binding's current lifecycle operations. On protected bindings the mailbox owner handles placement through separately authorized backend access. Use permitted read and answered state changes independently of filing. Gateway and manager fallback both restrict archived-state marks, move, and archive on these bindings.
