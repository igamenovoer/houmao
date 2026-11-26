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

`GET /v1/mail/status` reports `offline`, `online`, and `canonical_mail_identity` (`resolve-live` wraps slots under `mailboxes.offline` and `mailboxes.online`). Every `POST /v1/mail/{channel}/*` request body requires `"schema_version": 3` and `"expected_binding_id"` (including fresh `send` and `post`):

| Route | Required / Optional Fields | Notes |
| --- | --- | --- |
| `POST /v1/mail/{channel}/list` | `box`, optional read/answered/archived filters, `limit` (`50`, max `200`), `since`, `cursor` | Metadata-only (`messages`, `next_cursor`, `has_more`, `complete`); `include_body` is rejected. |
| `POST /v1/mail/{channel}/peek` | `message_ref`, optional `box` | Returns content + `content_complete` / limit fields without marking read. |
| `POST /v1/mail/{channel}/read` | `message_ref`, optional `box` | Returns content + `content_complete` / limit fields and marks read. |
| `POST /v1/mail/{channel}/send` | `to`, optional `cc`, `subject`, `body_content`, optional `attachments` | Managed-agent outbound send; returns compact receipt with top-level `message_ref`. |
| `POST /v1/mail/{channel}/post` | `subject`, `body_content`, optional reply policy & `attachments` | Operator-origin note on supported offline backends; returns compact receipt. |
| `POST /v1/mail/{channel}/reply` | `message_ref`, `body_content`, optional `attachments` | Replies in-thread (`parent_message_ref` + new `message_ref` receipt). |
| `POST /v1/mail/{channel}/mark` | `message_refs`, one or more `read`/`answered`/`archived` booleans | Updates message flags on the pinned binding. |
| `POST /v1/mail/{channel}/move` | `message_refs`, `destination_box` | Moves messages between boxes inside the same binding. |
| `POST /v1/mail/{channel}/archive` | `message_refs` | Archives completed messages after required replies succeed. |

See [scoped-cli.md](scoped-cli.md) for CLI invocation and [managed-agent-fallback.md](managed-agent-fallback.md) when no gateway is attached.

## Compact Write Receipts

`send`, `reply`, and `post` return compact receipts (`status`, `authoritative`, top-level `message_ref`, and `parent_message_ref` on `reply`) rather than echoing full message bodies. When full stored fields are needed, run `mail peek` with `--channel` and `--expected-binding-id` for that `message_ref`. If `authoritative: false` is returned on a detached or uncertain write, reconcile read-only (`peek` or `mail list --box sent`) before resending.

## Write Permissions and Recipient Inbound Policy

- **Sender gateway write actions**: the sender's gateway checks `mail.send`, `mail.reply`, or `mail.post` on the selected channel and binding; non-empty `attachments` additionally require `mail.attachment.owner_file` on that same binding.
- **Recipient inbound mail policy**: peer mail delivery also evaluates the recipient agent's retained inbound mail policy at transport delivery time (independent of whether the recipient's gateway is currently attached or running). The default `agent-requester` group permits inbound peer mail, whereas tightening a recipient's `default-group` to `agent-observer` denies inbound peer mail unless an explicit grant/role allows the sender. Manage policy and grants via `houmao-shared-routines->houmao-agent-access`.
