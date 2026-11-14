# Normal-Account Stalwart Client Qualification

This utility exercises the actual raw JMAP client against explicitly selected normal accounts. It never loads management credentials, creates accounts/domains/mailboxes, rotates passwords, or retries uncertain mutations. Prepare service fixtures separately through the service's administrative or normal-user setup workflow.

## Run Read-Only Checks

Keep credentials and generated reports outside the checkout. Select every credential source explicitly:

```bash
pixi run python scripts/qualification/stalwart-mail/client.py \
  --discovery-url http://127.0.0.1:10080/.well-known/jmap \
  --login test-agent \
  --address test-agent@example.com \
  --credential-file "$HOME/.local/state/houmao/mail-credentials/test-agent.json" \
  --service-release 0.15.5 \
  --output "$HOME/.local/state/houmao/qualification/stalwart-client.json"
```

The script validates the requested account/address, retrieves a finite metadata page, reads explicitly selected content, calls both change APIs, and validates a fresh connection against the same account/checkpoint. Its JSON output contains no credentials or message bodies.

## Exercise Send, Reply, Read, and Archive

Use two deliberately prepared local test accounts. Both need an authorized sending identity and the inbox, sent, and archive mailbox roles. The script sends a uniquely named sandbox message to the peer, reads it, replies to the sender, and archives the two delivered inbox messages:

```bash
pixi run python scripts/qualification/stalwart-mail/client.py \
  --discovery-url http://127.0.0.1:10080/.well-known/jmap \
  --login test-agent \
  --address test-agent@example.com \
  --credential-file "$HOME/.local/state/houmao/mail-credentials/test-agent.json" \
  --service-release 0.15.5 \
  --exercise-mail \
  --peer-login test-agent-peer \
  --peer-address test-agent-peer@example.com \
  --peer-credential-file "$HOME/.local/state/houmao/mail-credentials/test-agent-peer.json" \
  --output "$HOME/.local/state/houmao/qualification/stalwart-client.json"
```

Delivery observation uses finite metadata pages and a fifteen-second deadline. A failed round exits with a safe error. A confirmed or uncertain mutation is never automatically submitted again. A fresh invocation creates a separate sandbox subject; inspect and reconcile prior outcomes before deciding to run another round.

## Recorded Representative Run

On 2026-11-14, this script passed against the project's loopback Stalwart **0.15.5** service with **two normal accounts and two submitted sandbox messages**. The complete sequence used **41 JMAP methods** and took **0.182 seconds** in this local run. That elapsed time describes one representative check, not a latency distribution or a capacity claim.

The run established body-free metadata, complete explicitly selected text, confirmed send and reply, read/answered parent flags, archive removal from inbox, bounded object/query changes, and a fresh connection accepting the same account/identity/checkpoint. The first metadata page returned two entries and used three methods, including an exhaustion probe. The generated sanitized report was stored outside the checkout at `/tmp/houmao-mail-02-qualification/client.json`.

Fixture setup was separate from attachment. The operator added `example.com` test aliases through the local service's administrative workflow without changing the existing sender password. Normal-user setup created missing Archive mailbox roles before the successful round. Neither action is part of client validation or an implicit attach operation.

Two release-specific observations changed the qualification setup:

- Stalwart 0.15.5's identity validator rejects the `example.test` suffix. The reserved `example.com` test aliases authorize the same normal accounts and pass identity validation. The 0.16.26 source reference differs from the running release.
- Same-account self-delivery was suppressed as a duplicate because the submitted message already existed in Sent. Distinct accounts verify actual recipient inbox delivery. The first self-delivery experiment timed out after a confirmed submission and did not resend it.

This raw-client check does not establish gateway restart, live binding refresh/detach, notifier behavior, or target-scale capacity. Those need their separate runtime and load-plan evidence. See the [client contract](../../../docs/reference/mailbox/contracts/stalwart-client.md) for wire semantics and limitations.

## Qualify Live Binding Controls and Reminders

The runtime utility uses the real selected Stalwart account, an in-process ASGI gateway fixture, and a fake body subprocess. It does not launch an LLM CLI. Select a new external work directory for every run:

```bash
pixi run python scripts/qualification/stalwart-mail/runtime.py \
  --discovery-url http://127.0.0.1:10080/.well-known/jmap \
  --login test-agent \
  --address test-agent@example.com \
  --credential-file "$HOME/.local/state/houmao/mail-credentials/test-agent.json" \
  --service-release 0.15.5 \
  --work-dir "$HOME/.local/state/houmao/qualification/runtime-round-01"
```

The recorded 2026-11-14 run passed attach, metadata list, same-account refresh, reconnect, gateway reconstruction with sync recovery, and detach. The fake body kept its PID and conversation marker. Unchanged inbox work admitted two periodic reminders across two due cycles; a repeated cycle was deduplicated. The runtime created one uniquely named fixture message, explicitly moved its owned Sent item into Inbox, and archived that fixture during cleanup. Its sanitized report is `/tmp/houmao-mail-02-runtime-01/runtime-report.json`.

## Measure Bounded Observation

The read-only observer utility requires both credentials and its cache/report directory outside the checkout:

```bash
pixi run python scripts/qualification/stalwart-mail/observe.py \
  --discovery-url http://127.0.0.1:10080/.well-known/jmap \
  --login test-agent \
  --address test-agent@example.com \
  --credential-file "$HOME/.local/state/houmao/mail-credentials/test-agent.json" \
  --agent-id qualification-agent \
  --binding-id qualification-binding \
  --service-release 0.15.5 \
  --cycles 5 \
  --work-dir "$HOME/.local/state/houmao/qualification/observer-round-01"
```

The recorded five-cycle run passed and reported method counts, actual request/response body byte counts, cycle latency, peak process RSS, and bootstrap recovery time. Its private report is `/tmp/houmao-mail-02-observe-01/report.json`. The [change qualification record](../../../openspec/changes/mail-02-attach-online-mail-and-sync-stalwart/qualification.md) gives measured values and limits. These representative checks do not establish capacity for the unexecuted 100-agent, million-message workload in the [load plan](../../../docs/reference/mailbox/operations/stalwart-qualification.md).
