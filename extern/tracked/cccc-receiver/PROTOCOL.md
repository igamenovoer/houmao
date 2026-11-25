# CCCC External Receiver Protocol v1

This tracked compatibility patch extends CCCC `d12732ebd6dfdbc260a59a286bd5e510d04d4832`. It is a provider interface, not an MCP server installed into the agent body.

## Actor RPC

`POST /api/v1/external-receiver/v1/rpc`, with `Authorization: Bearer <normal-Actor-grant>` and JSON `{ "operation": "binding", "arguments": {} }`. Request bodies reject unknown envelope fields and each operation rejects unsupported argument fields. Success is `{ "ok": true, "result": {} }`; failure is `{ "ok": false, "error": { "code": "...", "message": "CCCC external receiver request failed", "retryable": false } }` with HTTP 401, 403, 409, 422, or 503. Only this exact RPC path uses dedicated Actor-grant authentication. Other CCCC Web authentication and read-only guards retain their behavior.

| Operation | Arguments | Result |
| --- | --- | --- |
| `binding` | `{}` | `protocol_version: 1`, `group_id`, `actor_id`, `actor_generation` |
| `capabilities` | `{}` | `protocol_version`, `operations`, `limits`, `recipient_scope`, `mail: false` |
| `members` | `{}` | `members` with public `id`, `title`, `role`, `enabled`, `receive_status` |
| `lease.acquire` | `{}` | `lease_id`, integer `lease_generation`, `expires_in_seconds: 45` |
| `lease.renew` | `lease_id`, `lease_generation` | Refreshed lease fields |
| `lease.release` | `lease_id`, `lease_generation` | `released: true` |
| `lease.next` | `lease_id`, `lease_generation`, optional `timeout_seconds` (0 to 20) | `offer: null` or one bounded offer |
| `lease.outcome` | `lease_id`, `lease_generation`, `attempt_id`, `outcome`, optional `retryable`, `error_code` | `settled`, `attempt_id`, `outcome` |
| `chat.send` | `operation_id`, explicit `to` array, `text`, `mode` (`send` or `request_reply`) | `stored`, native `event`, `deliveries`, `duplicate` |
| `chat.reply` | `operation_id`, `event_id`, `text`, optional `mode: send` | Same mutation result with native reply ancestry |
| `chat.retry` | `event_id`, explicit `actor_ids`, optional `allow_uncertain_retry` | Existing source event and new provider attempt receipts |
| `chat.history` | `limit` (1 to 100), optional `before_event_id` or exact `event_id`, optional `max_bytes` | Native `messages`, `has_more`; exact lookup cannot mix filters |
| `chat.deliveries` | `event_id`, optional `limit` (1 to 100, default 50) | `event_id`, newest-first `deliveries`, `has_more` |

The `chat.deliveries` lookup selects retained attempts for the Actor-visible event in reverse creation order. The limit takes the newest matching attempts. `has_more: true` indicates older matching attempts were omitted. An accepted retry appears before its refused original, and both attempts reference the same event.

An offer has `attempt_id`, `event_id`, `group_id`, `actor_id`, `actor_generation`, `lease_generation`, `message_mode`, `text`, `sender`, `reply_to`, and `remaining_seconds`. The plugin must acknowledge only after actual ordinary handoff to the current ready body. Outcomes are `accepted`, `refused`, `failed`, or `uncertain`. Only the live lease/attempt may settle an outcome. Repeating settlement never invokes body dispatch again.

A native CCCC event has `id`, `kind`, `by`, `ts`, `group_id`, and `data` (including `text`, normalized `to`, `message_mode`, and `reply_to` when present). Delivery metadata carries `id` (attempt ID), `event_id`, `actor_id`, `actor_generation`, `lease_generation`, `state`, `retryable`, and a safe optional `error_code`. `stored` confirms CCCC ledger storage, not successful body handoff or completed agent work.

Only a fresh sender-authorized retry creates another attempt. Receiver reconnect never reoffers a prior attempt. An offered attempt unresolved after provider restart/lease retirement/deadline becomes uncertain. Normal Actor credentials cannot take over an unexpired lease; after a gateway crash a replacement waits for expiry. The daemon owns all retained messages and receipts, while the plugin has no deferred payload store.

## Operator Provisioning

The following routes use existing CCCC Web operator authentication and never accept a normal Actor grant as operator authority, including on loopback:

- `POST /api/v1/external-receiver/v1/grants` with `group_id`, `actor_id`: explicitly converts an existing inactive/non-native Actor into a generic externally controlled receiver and returns `grant_id`, `token`, `group_id`, `actor_id`, `actor_generation`, `protocol_version`. Export the secret result directly to an owner-private credential file. Grant hashes, not plaintext tokens, are persisted by CCCC.
- `DELETE /api/v1/external-receiver/v1/grants/{grant_id}`: revoke the selected grant and its active lease.
- `POST /api/v1/external-receiver/v1/takeover` with `group_id`, `actor_id`: explicitly retire the current lease and fence old attempts so a replacement can acquire intake. It does not control the Houmao body or retry unsettled content.

For local passwordless Web administration, provide the selected Web origin header according to CCCC's existing CSRF policy. Normal plugin operations require only the private Actor credential document, never a management token. The plugin additionally validates its local document's agent ID and endpoint against its immutable owner binding.

## Deferred Mail Extension (Patch 0002)

Patch `0002-explicit-deferred-mail.patch` extends the same protocol version and Actor grant. The qualified CHAT patch remains byte-for-byte unchanged. `capabilities` now advertises `mail: true`, the six Mail operation names below, and `features` containing `mail_expected_cursor`, `mail_read_receipts`, `mail_read_crash_recovery`, and `mail_precommit_response_budget`, all `true`. Mail must remain unavailable when any required operation or feature is absent; ordinary CHAT remains usable against a CHAT-only provider.

The additional `limits` fields are `default_mail_messages: 50`, `max_mail_messages: 200`, `default_mail_response_bytes: 262144`, and `max_mail_response_bytes: 1048576`. CHAT keeps its existing 256 KiB response limit. Native event/cursor identifiers used in this extension are ASCII alphanumeric or `_.:-`, at most 512 bytes; an empty cursor means no previous read boundary. Caller operation IDs have at most 128 bytes.

| Operation | Arguments | Result |
| --- | --- | --- |
| `mail.send` | `operation_id`, explicit `to`, `text` | Native mutation result with forced `message_mode: mail`, `stored`, `duplicate`, `consumed: false` |
| `mail.reply` | `operation_id`, `event_id`, `text` | Same deferred result, preserving native `reply_to`; no cursor change |
| `mail.cursor` | `{}` | `cursor: {event_id, ts, updated_at}` |
| `mail.peek` | Optional `limit`, `max_bytes`, `response_overhead_bytes`, `per_event_overhead_bytes` | Complete leading `messages`, current `cursor`, `has_more`, `count_accuracy: bounded`, `consumed: false` |
| `mail.read` | `operation_id`, `expected_cursor` (native ID string), optional limits/reserves as for peek | Complete selected `messages`, committed `cursor`, `has_more`, `outcome`, and authoritative `receipt` |
| `mail.read-receipts` | `operation_id` | `{found: false, operation_id}` or `{found: true, receipt}` |

A receipt contains `operation_id`, `actor_generation`, `before_cursor`, `after_cursor`, `event_ids`, `outcome` (`consumed` or `empty`), and `read_event_id`. Read `outcome` is `consumed`, `empty`, or `already_completed`. Matching repeated operations return the original receipt with an empty `messages` array and `already_completed`, without observing or consuming the current pending batch. Their `has_more: false` describes no returned page and must not refresh a maintained inbox status. A missing receipt means the caller cannot establish a completed decision, rather than proving its request failed.

`limit` is an integer from 1 through 200. `max_bytes` is an integer from 1,024 through 1,048,576 and defaults to 262,144. Reserves are nonnegative integers up to 1,048,576. Before committing, the provider serializes the entire candidate `{ok: true, result: ...}` response, then adds `response_overhead_bytes + selected_message_count * per_event_overhead_bytes`. This sum must fit `max_bytes`. The plugin computes conservative reserves for its identity wrapper and signed event/cursor/read references before making the request. Both native message contents and receipt metadata count toward this budget. A count or byte limit selects a complete leading prefix; an oversized first item returns `content_limit` without writing a read decision or advancing the cursor. The provider never skips a large head item. Native exact CHAT history is the supported non-consuming content-recovery path when its own 256 KiB complete-response limit permits it; larger unsupported items remain visible errors.

Read decisions use CCCC's existing Group `read_cursors.json.lock`, shared with native `inbox_read`. Under that lock the provider recovers a previous pending marker, resolves an existing Actor-generation/operation ID, compares the expected native cursor, selects the complete bounded prefix, and commits its decision. Normalized fingerprints include effective cursor, count, byte limit, and reference reserves. A different cursor returns `cursor_conflict`; reusing an operation ID with different normalized inputs returns `operation_conflict`. Neither conflict consumes another batch.

The native pending marker includes the complete payload-free decision and exact read-fact identity. Appending and syncing the `mail.read` fact commits the operation; the fact embeds its original cursor boundaries, exact native event IDs, outcome, and fingerprint. Cursor publication and marker cleanup follow that commit. Recovery accepts only the matching fact and publishes its committed cursor, preserving the original receipt if interrupted before cursor publication. Empty reads also append a durable decision fact while retaining the current cursor. Decisions remain in the retained native ledger for the Actor registration lifetime, including archived ledger segments; no active receipt cache expires them or permits ID reuse. CCCC source, cursor state, and retained ledger must be backed up and restored together. Restoring cursor state independently of its committed facts is unsupported.

Native Mail notices include only pending metadata and use ordinary external-receiver attempts. Offers add `kind: mail_notice` and integer `pending_count`; existing scope/attempt/deadline fields remain present, `message_mode` is `send`, and `event_id` is the native notice ID. The plugin renders its own content-free gateway inspection guidance and ignores native notice text. A current external lease makes an Actor eligible for the native scheduled notice policy without identifying its process as CCCC-managed or its body as idle. Defaults remain the 1,800-second delay and no periodic repeat. Notice refusal, reconnect, takeover, and outcome acknowledgement never consume Mail or replay the original notice. Offline/online email reminder policies remain independent.

Patch 0002 also validates `lease.next.timeout_seconds` strictly as a finite numeric value from 0 through 20. Boolean/string values and values outside this range fail before polling. No production fault-injection endpoint or environment switch is installed. Native Rust journal tests inject interruptions only in test builds; isolated HTTP recovery tests replay genuine committed crash images against a fresh real daemon.
