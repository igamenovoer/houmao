# Mailbox Common Workflows

This guide covers mail rounds after the agent and selected mailbox channel are configured. Use the [Quickstart](../quickstart.md) for local setup or [Offline Registry Setup](offline-registry.md) for remote enrollment.

## Resolve the Target and Channel

Select another agent by its stable ID, or use `agents self` from its owning session:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail resolve-live
pixi run houmao-mgr agents single --agent-id "$agent_id" mail status
```

Resolve-live reports both revisioned slots and an optional exact `gateway.base_url`. Choose `offline` or `online` explicitly and retain that channel's `binding_id` for the round. Canonical mail identity is an external identity preference; it never chooses a transport.

All lifecycle commands require `--channel`. Supplying `--expected-binding-id` pins the operation to the binding observed for this round. HTTP requests always contain `expected_binding_id` and mail `schema_version: 3`. A scope conflict ends the operation; do not retry against a replacement account automatically.

## Inspect Eligible Work

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail list \
  --channel offline --expected-binding-id "$binding_id" --box inbox --limit 10
pixi run houmao-mgr agents single --agent-id "$agent_id" mail peek \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref"
pixi run houmao-mgr agents single --agent-id "$agent_id" mail read \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref"
```

Obtain `message_ref` from a list result and keep it opaque. `peek` preserves read state; `read` intentionally marks read. Optional list filters include `--read-state`, `--answered-state`, `--archived/--not-archived`, and `--since`.

For gateway access, use `GET /v1/mail/status` followed by `POST /v1/mail/{channel}/list|peek|read`. A list request body is:

```json
{
  "schema_version": 3,
  "expected_binding_id": "registration-a",
  "box": "inbox",
  "limit": 10
}
```

List returns finite metadata pages. Retrieve bodies explicitly with `peek` or `read`; follow opaque continuation only while its account, binding, filters, and provider query state remain valid.

## Compose and Reply

Register offline recipients in the same selected registry before delivery. Online recipients use the online provider's address space:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail send \
  --channel offline --expected-binding-id "$binding_id" \
  --to orchestrator@houmao.localhost --subject "Review request" \
  --body-file body.md --attach notes.txt
pixi run houmao-mgr agents single --agent-id "$agent_id" mail reply \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref" \
  --body-content "Review completed."
```

Choose exactly one body source, `--body-file` or `--body-content`. Repeat `--to`, `--cc`, or `--attach` as needed. Replies preserve their original binding and ancestry. A successful reply marks the parent read and answered without archiving it.

Local filesystem `mail post --channel offline` creates an operator-origin note. The reserved sender is `HOUMAO-operator@houmao.localhost`, and reply-enabled posts use `reply_policy=operator_mailbox` by default. `--reply-policy none` disables replies to that note. `post` requires authoritative execution; unsupported backends fail explicitly.

Remote offline attachment handling uploads bounded content into registry-owned storage. Recipients download authorized content; neither host needs the other's filesystem path. Trusted local path references remain local-only.

## Complete a Round

Archive successfully processed work after any required reply succeeds:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail archive \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref"
```

Read and answered flags describe progress. They do not move a message out of the eligible inbox or substitute for archive completion. Periodic reminders for unchanged eligible work continue according to the selected notifier mode. `unread_only` additionally limits eligibility to unread mail; `any_inbox` keeps reminding about read inbox work.

A verified result has `authoritative: true`. A local TUI fallback remains submission-only and must be checked through manager or backend state. Do not interpret an optional transcript preview as confirmed delivery.

## Configure Channel Reminders

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway mail-notifier enable \
  --channel offline --interval-seconds 60 --mode any_inbox
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway mail-notifier status --channel offline
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway mail-notifier disable --channel offline
```

The HTTP surface is `/v1/mail-notifier/{channel}`. Channel configuration includes independent interval, mode, appendix, and compaction bookkeeping. Both channels share readiness and terminal admission safeguards. A canonical-address change does not reset the other channel's schedule or one-shot compaction state.

Notifier-driven agent prompts provide the exact gateway URL, channel, and expected binding. Use the installed agent entrypoint when its required siblings exist, otherwise follow the supplied API instructions. Complete one bounded round and stop.

## Inspect or Repair Filesystem State

On the registry host, canonical content lives under `messages/`, shared ownership and delivery catalogs in `index.sqlite`, and mailbox-view flags in each registration's `mailbox.sqlite`. Released private views remain registration-scoped history. Runtime presence cleanup does not release addresses.

Inspect `rules/README.md` and the shipped protocol note before direct repair or administrative script use. Ordinary agents use the supported manager or gateway APIs. Remote members cannot select registry filesystem or symlink targets. See [Registration Lifecycle](registration-lifecycle.md) and [Repair and Recovery](repair-recovery.md).
