# Shared Gateway Mail Contract

Use the exact gateway base URL supplied by the current context or returned by `houmao-mgr agents self mail resolve-live`. A notifier round must already supply its URL, channel, and expected binding ID. Missing round context is a contract error; do not rediscover it.

`GET /v1/mail/status` returns both optional channels (`offline`, `online`) and `canonical_mail_identity`. Each configured channel reports owner, binding ID, revision, address, availability, and backend limitations without credential material. Resolver output uses slot envelopes under `mailboxes.offline` and `mailboxes.online`.

Lifecycle routes require explicit channel selection:

| Route | Additional Fields |
| --- | --- |
| `POST /v1/mail/{channel}/list` | `box`, read/answered filters, archived filter, finite `limit` (default 50, max 200), optional `since` and opaque `cursor` |
| `POST /v1/mail/{channel}/peek` | `message_ref`, optional `box`; leaves read state unchanged |
| `POST /v1/mail/{channel}/read` | `message_ref`, optional `box`; marks read |
| `POST /v1/mail/{channel}/send` | `to`, optional `cc`, `subject`, `body_content`, optional attachments |
| `POST /v1/mail/{channel}/post` | operator-origin `subject`, `body_content`, optional reply policy; backend support required |
| `POST /v1/mail/{channel}/reply` | `message_ref`, `body_content`, optional attachments |
| `POST /v1/mail/{channel}/mark` | `message_refs`, one or more read/answered/archived flags |
| `POST /v1/mail/{channel}/move` | `message_refs`, `destination_box` |
| `POST /v1/mail/{channel}/archive` | `message_refs` |

Every lifecycle body includes `schema_version: 3` and `expected_binding_id`, including fresh send/post requests that have no message reference. Valid channels are `offline` and `online`. Message and thread handles remain opaque and scoped to owner, channel, and binding. Wrong scope or replacement targeting fails before backend effects. Stop on conflict; never re-resolve and resend automatically.

Offline and online delivery remain isolated. Canonical identity, provider outage, or an email domain cannot choose another channel. Peek, read, and answered status are separate from archive completion. See [scoped command examples](scoped-cli.md) for request construction and [manager fallback](managed-agent-fallback.md) when no gateway is attached.

List returns one metadata-only `messages` page, `next_cursor`, `has_more`, and `complete`. Counts describe that page; `total_count` is optional. Preserve filter, account, and binding scope on continuation. Stale cursors interrupt the page chain rather than silently joining incompatible snapshots. `include_body` is rejected. Peek/read return explicit content and disclose `content_complete` plus content-limit information when full retrieval is unavailable.
