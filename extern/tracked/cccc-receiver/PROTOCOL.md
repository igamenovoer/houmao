# CCCC External Receiver Protocol v2

This tracked compatibility patch extends CCCC `d12732ebd6dfdbc260a59a286bd5e510d04d4832`. It is a provider interface, not an MCP server installed into the agent body.

## Actor RPC

`POST /api/v1/external-receiver/v2/rpc`, with `Authorization: Bearer <normal-Actor-grant>` and JSON `{ "operation": "binding", "arguments": {} }`. Request bodies reject unknown envelope fields and each operation rejects unsupported argument fields. Success is `{ "ok": true, "result": {} }`; failure is `{ "ok": false, "error": { "code": "...", "message": "CCCC external receiver request failed", "retryable": false } }` with HTTP 401, 403, 409, 422, or 503. The exact RPC and stream paths use dedicated Actor-grant authentication. Other CCCC Web authentication and read-only guards retain their behavior.

| Operation | Arguments | Result |
| --- | --- | --- |
| `binding` | `{}` | `protocol_version: 2`, `group_id`, `actor_id`, `actor_generation` |
| `capabilities` | `{}` | `protocol_version`, `operations`, `features`, `limits`, `recipient_scope`, `mail: true` |
| `members` | `{}` | `members` with public `id`, `title`, `role`, `enabled`, `receive_status` |
| `lease.acquire` | `transport: pull or push`, `receiver: gateway or direct`, optional `max_offer_bytes` | `lease_id`, integer `lease_generation`, `expires_in_seconds: 45` |
| `lease.renew` | `lease_id`, `lease_generation` | Refreshed lease fields |
| `lease.release` | `lease_id`, `lease_generation` | `released: true` |
| `lease.next` | `lease_id`, `lease_generation`, `limit`, `max_bytes`, optional `timeout_seconds` (0 to 20) | Ordered `offers`. Direct pull additionally returns an exact `receipt` or null, plus one `event_ref` per offer. |
| `lease.notice.next` | `lease_id`, `lease_generation` | `offer` or null for a typed Mail notice under a pull gateway lease |
| `lease.outcome` | `lease_id`, `lease_generation`, `attempt_id`, `outcome`, optional `retryable`, `error_code` | `settled`, `attempt_id`, `outcome` for a Mail notice |
| `lease.start` | `lease_id`, `lease_generation`, `dispatch_id`, ordered `attempt_ids` | `dispatch_id`, `attempt_ids`, decision `outcome` |
| `lease.settle` | `lease_id`, `lease_generation`, `dispatch_id`, `outcome`, optional `retryable`, `error_code` | `dispatch_id`, `attempt_ids`, settled `outcome` |
| `chat.ack` | `receipt` | `receipt`, `acknowledged`, exact `attempt_ids` |
| `chat.send` | `operation_id`, explicit `to` array, `text`, `mode` (`send` or `request_reply`) | `stored`, native `event`, `deliveries`, `duplicate` |
| `chat.reply` | `operation_id`, `event_id` or direct `event_ref`, `text`, optional `mode: send` | Same mutation result with native reply ancestry |
| `chat.retry` | `event_id`, explicit `actor_ids`, optional `allow_uncertain_retry` | Existing source event and new provider attempt receipts |
| `chat.history` | `limit` (1 to 100), optional `before_event_id` or exact `event_id` or direct `event_ref`, optional `max_bytes` | Native `messages`, `has_more`; exact lookup cannot mix filters |
| `chat.deliveries` | `event_id`, optional `limit` (1 to 100, default 50) | `event_id`, newest-first `deliveries`, `has_more` |

The `chat.deliveries` lookup selects retained attempts for the Actor-visible event in reverse creation order. The limit takes the newest matching attempts. `has_more: true` indicates older matching attempts were omitted. An accepted retry appears before its refused original, and both attempts reference the same event.

Each chat offer carries `attempt_id`, `event_id`, `group_id`, `actor_id`, `actor_generation`, `lease_generation`, `sequence`, `timestamp`, `message_mode`, `text`, `sender`, `reply_to`, and `remaining_seconds`. Sequence orders work for the selected recipient registration. Timestamp comes from the native event. Each nonempty pull selects one leading batch as a single snapshot. The advertised `max_batch_messages` and `max_batch_bytes` cap requests and `max_event_bytes` caps individual chat offers. A lease may negotiate a smaller `max_offer_bytes`. An offer exceeding that hard limit gets a permanent `event_too_large` receipt. A smaller pull or stream byte credit leaves an otherwise eligible head at CCCC.

A gateway dispatch uses a fresh `dispatch_id` to register the exact ordered attempts before submission. Each start has the advertised `max_handoff_seconds` time window. The receiver settles that start as `accepted`, `deferred`, `refused`, `failed`, or `uncertain`. Use `deferred` only after proving no handoff occurred. Retrying a start or settlement with the original identity reconciles that decision. Conflicting identities or decisions fail before changing any attempt. Gateway acceptance confirms ordinary handoff to the current ready body.

A direct pull records its retrieval before exposing the result. The same Actor registration can acknowledge that exact batch after releasing the lease. An unacknowledged exposure expires to `uncertain`. The Actor can use a direct message reference in a later exact history or reply operation. All calls still require the selected Actor grant and provider-advertised operation scope.

A native CCCC event has `id`, `kind`, `by`, `ts`, `group_id`, and `data` (including `text`, normalized `to`, `message_mode`, and `reply_to` when present). Delivery receipts carry `id` (attempt ID), `event_id`, `actor_id`, `actor_generation`, `lease_generation`, `state`, `retryable`, and a safe optional `error_code`. The provider distinguishes durable storage, pending and staged deliveries, confirmed gateway handoff, and acknowledged direct reads from the agent's later work.

The provider retains unstarted chat while no receiver is connected or the agent is busy. Lease retirement makes unstarted work available again. Unresolved started handoffs become uncertain. Only a fresh sender-authorized retry creates another attempt for terminal work. Normal Actor credentials cannot take over an unexpired lease. After a gateway crash a replacement waits for expiry unless a CCCC operator retires that lease. Houmao holds only the bounded current staged batch data.

## Actor Push Stream

Use `GET /api/v1/external-receiver/v2/stream` with the selected Actor bearer and a current push gateway lease. Query fields are `lease_id`, `lease_generation`, `kind` (`chat` or `mail_notice`), `limit`, `max_bytes`, and optional `after_sequence` (default 0). Each connection grants finite count and byte credit, capped by the advertised batch limits. Chat and Mail notices use independent streams and credit. The provider can close when credit runs out, a head item cannot fit the remaining credit, or the advertised `max_stream_seconds` expires. The receiver may reconnect with its highest staged sequence under the same lease. A sequence cursor is an intake filter and a receipt still requires explicit settlement.

The response is `application/x-ndjson` with records `{kind: "offer", offer: {...}}`, `{kind: "heartbeat"}`, and a terminal `{kind: "error", error: {code, retryable}}`. `capabilities` advertises the stream as `lease.stream`, and uses the `chat_pending`, `chat_batch_pull`, `chat_push_stream`, `chat_batch_settlement`, `chat_direct_pull`, and `chat_independent_notices` feature flags. Verify protocol, Actor generation, selected feature flags, and finite limits before enabling intake.

## Operator Provisioning

The following routes use existing CCCC Web operator authentication and never accept a normal Actor grant as operator authority, including on loopback:

- `POST /api/v1/external-receiver/v2/grants` with `group_id`, `actor_id`: explicitly converts an existing inactive/non-native Actor into a generic externally controlled receiver and returns `grant_id`, `token`, `group_id`, `actor_id`, `actor_generation`, `protocol_version`. Export the secret result directly to an owner-private credential file. Grant hashes, not plaintext tokens, are persisted by CCCC.
- `DELETE /api/v1/external-receiver/v2/grants/{grant_id}`: revoke the selected grant and its active lease.
- `POST /api/v1/external-receiver/v2/takeover` with `group_id`, `actor_id`: explicitly retire the current lease and fence old attempts so a replacement can acquire intake. It does not control the Houmao body or retry unsettled content.

For local passwordless Web administration, provide the selected Web origin header according to CCCC's existing CSRF policy. Normal plugin operations require only the private Actor credential document, never a management token. The plugin additionally validates its local document's agent ID and endpoint against its immutable owner binding.

## Deferred Mail Extension (Patch 0002)

Patch `0002-explicit-deferred-mail.patch` defines the qualified Mail cursor and read semantics. The v2 patch carries these operations under the same Actor grant. `capabilities` advertises `mail: true`, the six Mail operation names below, and `features` containing `mail_expected_cursor`, `mail_read_receipts`, `mail_read_crash_recovery`, and `mail_precommit_response_budget`, all `true`. Mail must remain unavailable when any required operation or feature is absent; ordinary CHAT remains usable against a CHAT-only provider.

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

Native Mail notices include only pending metadata and use a separate typed intake path. Offers add `kind: mail_notice` and integer `pending_count`; existing scope/attempt/deadline fields remain present, `message_mode` is `send`, and `event_id` is the native notice ID. The plugin renders its own content-free gateway inspection guidance and ignores native notice text. A current gateway receiver lease makes an Actor eligible for the native scheduled notice policy without identifying its process as CCCC-managed or its body as idle. Defaults remain the 1,800-second delay and no periodic repeat. Notice refusal, reconnect, takeover, and outcome acknowledgement never consume Mail or replay the original notice. Offline/online email reminder policies remain independent.

Patch 0002 also validates `lease.next.timeout_seconds` strictly as a finite numeric value from 0 through 20. Boolean/string values and values outside this range fail before polling. No production fault-injection endpoint or environment switch is installed. Native Rust journal tests inject interruptions only in test builds; isolated HTTP recovery tests replay genuine committed crash images against a fresh real daemon.
