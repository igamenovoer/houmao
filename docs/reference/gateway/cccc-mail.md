# CCCC Deferred Mail

`houmao-cccc` version 0.2 adds explicit deferred Mail to the same owner-bound Actor connection used for [CCCC chat](cccc.md). Mail stays outside both Houmao email slots. It does not determine canonical email identity, use Stalwart credentials, or become an automatic fallback after an email error.

## Enable the Qualified Provider

The tracked provider series contains `0001-external-receiver.patch` for chat and `0002-explicit-deferred-mail.patch` for Mail. Keep their order and the pinned upstream revision in [upstream.json](../../../extern/tracked/cccc-receiver/upstream.json). [The protocol](../../../extern/tracked/cccc-receiver/PROTOCOL.md) defines the complete feature gate: Mail operations, count/byte limits, expected cursors, durable read receipts, and journal recovery must all be present. A chat-only provider keeps chat working and returns structured `mail_unsupported` errors for unqualified Mail operations.

Build/install the 0.2 wheel in the gateway environment, detach the gateway, then reattach the same plugin selection. The body, agent UUID, Actor generation, and canonical identity can remain unchanged. Rotating a same-registration credential still uses the selected private file and `connection refresh-credentials`; a new Actor registration needs a new binding. None of these actions consumes Mail.

When upgrading an existing prepared provider checkout, select a fresh output because the helper refuses to rewrite an earlier patch selection:

```bash
pixi run --manifest-path tools/cccc/pixi.toml prepare-receiver \
  --output "$HOME/.local/share/houmao-cccc/source-receiver-mail"
export HOUMAO_CCCC_SOURCE="$HOME/.local/share/houmao-cccc/source-receiver-mail"
export HOUMAO_CCCC_ROOT="$HOME/.local/share/houmao-cccc-receiver"
export HOUMAO_CCCC_PORT=8849
pixi run --manifest-path tools/cccc/pixi.toml build
pixi run --manifest-path tools/cccc/pixi.toml stop
pixi run --manifest-path tools/cccc/pixi.toml start
```

Back up the selected private provider state and source selection together before changing journal versions. A rollback must preserve committed read facts and must not rewind the cursor or reuse a completed operation as a fresh read.

## Send and Reply Explicitly

```bash
houmao-cccc --gateway-url "$GATEWAY_URL" mail send \
  --binding-id "$BINDING_ID" --operation-id UNIQUE_SEND_ID \
  --to PEER_ACTOR_ID --text 'Please review this when you read your next batch.'
houmao-cccc --gateway-url "$GATEWAY_URL" mail reply \
  --binding-id "$BINDING_ID" --operation-id UNIQUE_REPLY_ID \
  --event-ref "$EVENT_REF" --text 'Reviewed.'
```

These commands force native `mail` mode. Select explicit Actors in the bound Group. Human `user`, arbitrary email addresses, offline principals, and unsupported cross-Group recipients fail before mutation. A reply preserves the native `reply_to` event ID; replying alone does not consume the original batch.

`stored` confirms provider storage. It does not mean consumed, delivered as a direct prompt, or completed by the agent. The response identifies `backend=cccc-mail`. A lost send/reply response remains uncertain, with the original caller operation ID. Explicit reuse of the same normalized send operation recovers its stored result; the plugin does not resend automatically.

## Inspect Without Consuming

```bash
houmao-cccc --gateway-url "$GATEWAY_URL" mail status
houmao-cccc --gateway-url "$GATEWAY_URL" mail cursor
houmao-cccc --gateway-url "$GATEWAY_URL" mail peek --limit 20 --max-bytes 262144
```

`status` reads maintained metadata without provider I/O. It identifies unknown/stale observations, age, and count accuracy. An outage does not turn an old count into an authoritative empty inbox. Explicit `peek`, `cursor`, read-receipt lookup, and chat history are bounded provider reads. They do not consume Mail or schedule agent work.

The cursor response includes native provenance and an opaque `cursor_ref`. Use that exact owner-scoped handle for an explicit read. A foreign owner, replaced binding, recreated Actor, altered handle, or email-channel handle fails before provider access.

## Consume One Bounded Leading Batch

```bash
houmao-cccc --gateway-url "$GATEWAY_URL" mail read \
  --binding-id "$BINDING_ID" --operation-id UNIQUE_READ_ID \
  --expected-cursor "$CURSOR_REF" --limit 20 --max-bytes 262144
```

The default count is 50, with a maximum of 200. The default complete-response budget is 256 KiB; the supported maximum is 1 MiB. Provider and selected plugin limits can lower these values. `mail_limit` and `mail_max_bytes` configure the instance defaults/ceiling. Read effective limits through `capabilities` before selecting a larger request.

The provider selects a complete leading prefix of Actor-visible Mail in append order before committing. The serialized budget includes messages, receipt metadata, cursor handles, and plugin reference expansion. Direct chat is excluded. Later Mail remains pending when a count or byte bound splits the batch. An oversized first item fails without skipping, truncating, or consuming it. No convenience operation silently bypasses that limit.

The read request supplies the current cursor and a caller-owned operation ID. The provider compares that cursor under the same native lock used by other inbox consumers. Two distinct reads from one cursor cannot consume successive batches independently: one can succeed, while the other returns `cursor_conflict` without consuming more.

Results distinguish `consumed`, `empty`, and `already_completed`. A matching repeated operation resolves its original receipt before checking the now-stale cursor. It returns `already_completed`, with no newly consumed content. An empty read also commits a durable decision: repeating it after a new arrival leaves the new Mail pending. Reusing an operation ID with a different cursor/count/byte request returns a conflict.

## Recover a Lost Read Response

The plugin makes one consuming provider call per explicit read. It never changes the operation ID or retries a mutation automatically. If the response is lost, retain the operation ID and binding and inspect the original decision:

```bash
houmao-cccc --gateway-url "$GATEWAY_URL" mail reads --operation-id UNIQUE_READ_ID
houmao-cccc --gateway-url "$GATEWAY_URL" mail cursor
houmao-cccc --gateway-url "$GATEWAY_URL" chat history --event-ref "$CONSUMED_EVENT_REF"
```

Receipt lookup works with the caller's original operation ID even when no response handle arrived. An optional `--read-ref` validates a previously returned scoped receipt handle. The receipt records Actor generation, before/after cursor, exact event IDs, outcome, and the native `mail.read` fact ID. It provides scoped event references for explicit exact-history recovery. Fetch them within your own count/time budget; these reads leave the following batch untouched.

The native journal commits the operation decision with its read fact and effective cursor boundary. Recovery after a crash between fact append and cursor publication exposes the same decision. Empty decisions and completed IDs remain authoritative for the Actor registration; active-index changes cannot turn an old ID into a fresh read. A missing receipt during an unresolved timeout means unknown, rather than proof that the read failed.

## Keep Notices and Email Reminders Separate

CCCC decides when a content-free notice for a concrete pending batch is eligible. Its native policy uses a default 1,800-second busy delay and no periodic escalation. The notice identifies the Mail binding and suggests explicit inspection. It does not contain the Mail body or advance the read cursor.

Notices use ordinary immediate gateway admission. Busy, absent, or replaced bodies yield refusal/failure/uncertainty. The plugin retains no notice queue, and later idle state or reconnect does not replay an old attempt. Normal Actor credentials cannot force an unexpired receiver lease; an explicitly authenticated CCCC operator can fence it without consuming Mail or retrying unsettled notices.

Offline and online email retain their own periodic reminders, compaction eligibility, and archive completion rules. Explicit CCCC Mail remains usable when a selected Stalwart endpoint is unavailable. It does not contact Stalwart, mirror an uncertain email send, translate recipients, or change canonical identity. Move/archive, per-message mark-unread, attachments, and email submission are unsupported CCCC Mail operations and return structured errors.

See [agent instructions](../../../examples/cccc-gateway/agent-instructions.md) and [qualification tools](../../../scripts/qualification/cccc/README.md) for concrete workflows. Provider/journal, installed-wheel, real Stalwart coexistence, and two-real-agent Mail checks are separate acceptance gates. The chat smoke does not establish Mail acceptance.

The [35-scenario acceptance map](cccc-mail-acceptance.md) records the executed scope and provider identities.
