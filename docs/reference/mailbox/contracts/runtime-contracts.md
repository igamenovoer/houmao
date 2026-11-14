# Mailbox Runtime Contracts

This reference describes mailbox configuration for contributors integrating Houmao's runtime, gateway, manager, or a mail backend. The agent's immutable `agent_id` owns its mail bindings. A display name, account login, email address, process ID, and session ID remain separate values.

## Two Independent Channels

Every runtime snapshot contains `launch_plan.mailboxes.offline` and `launch_plan.mailboxes.online`. Each slot holds a revision and an optional binding. Empty slots retain a revision so a writer from before detach cannot recreate an obsolete binding.

An agent can have either binding, both bindings, or neither. Offline mail uses the selected registry host's filesystem authority. Online mail uses an email provider, initially Stalwart. Connecting one channel never forwards mail from the other, and an outage never selects another channel.

Canonical mail identity is derived from the configured online address, otherwise the configured offline address, otherwise `null`. Its `{channel,address}` value describes how email-based external systems identify the agent. It does not select the delivery channel. Expired online credentials therefore leave canonical identity unchanged.

## Declarative and Resolved Configuration

Preset and brain configuration use two explicit declarations:

```yaml
mailboxes:
  offline:
    transport: filesystem
    address: alice@houmao.localhost
    filesystem_root: /srv/houmao/mail
  online:
    transport: stalwart
    address: alice@example.test
    base_url: http://127.0.0.1:10080
```

Either declaration may be `null`. Offline agent ownership uses the persisted agent ID. Full addresses remain mailbox routing values; Houmao does not generate an agent ID from an email header. Existing launch-time Stalwart provisioning populates the online slot independently of offline registration.

A persisted offline slot looks like this:

```json
{
  "revision": "revision-2",
  "binding": {
    "transport": "filesystem",
    "channel": "offline",
    "agent_id": "b498dd79-cbbc-41b2-a593-6263db66fe94",
    "binding_id": "registration-a",
    "principal_id": "b498dd79-cbbc-41b2-a593-6263db66fe94",
    "address": "alice@houmao.localhost",
    "bindings_version": "revision-2",
    "filesystem_root": "/srv/houmao/mail",
    "registry_root": "/srv/houmao/registry",
    "mailbox_kind": "in_root",
    "mailbox_path": "/srv/houmao/mail/mailboxes/alice@houmao.localhost"
  }
}
```

A remote offline binding uses `transport: registry`, a registry URL, and a protected credential reference. It contains no registry-host mailbox path for the client to open. The offline binding ID is the confirmed registration ID. An online binding records its provider and protected credential reference separately from the owning agent ID.

The current persisted formats are `launch_plan.v2`, `session_manifest.v5` (`schema_version: 5`), and managed registry record v4. Unsupported pre-change formats require an explicit operator backup and rebootstrap. Loading them never generates missing identity, resets mailbox history, or translates the former single mailbox union.

## Atomic Binding Authority

`manifest.py` owns one interprocess lock beside each session manifest. Writers validate a complete snapshot, flush a private temporary file, atomically replace the destination, and flush the directory.

Server-owned gateway routing fields and runtime-owned endpoint details also merge under this boundary. Ordinary session persistence preserves the latest mailbox envelopes under this lock. It cannot replace a live attachment with a stale controller copy. Binding mutation uses `mutate_session_mailbox_binding()` with the expected slot revision, agent ID, and session ID. A successful change advances only the selected slot revision and stamps the binding's `bindings_version` to match. A stale mutation raises `MailboxBindingConflict` before publication.

Prepare backend resources and credentials before entering this mutation boundary. Network requests, remote enrollment, and worker shutdown must remain outside the manifest lock. After a binding commit, refresh the controller from the committed result and publish discovery projections. A projection failure cannot reverse a confirmed registry claim; report the committed outcome and reconcile it on a later status or idempotent join.

## Discovery and Operations

Use `pixi run houmao-mgr agents self mail resolve-live` inside the owning session. Select another target with `pixi run houmao-mgr agents single --agent-id <id> mail resolve-live`. Both this resolver and `mail status` summarize the two channels and derived canonical mail identity. The resolver returns the exact live `gateway.base_url` when available.

Each channel summary contains its slot revision, optional owner/channel/binding/address scope, and availability. A failed channel remains visible independently of the other channel. Public discovery omits credential files, credential references, account login names, authorization headers, and secret resolution inputs.

Every lifecycle action selects `--channel offline|online`; the gateway equivalents use `/v1/mail/{channel}/list|peek|read|send|post|reply|mark|move|archive`. Each request also carries the expected binding ID resolved for that operation or supplied in the current agent round. Fresh sends and posts require this check even though they have no existing message reference.

Opaque message and thread references carry owner, channel, and binding scope. An old account's reference cannot target a new account with the same provider message ID. Replies stay in their original channel. Mixed-channel recipients fail before side effects. The canonical mail identity never overrides explicit scope.

`peek` leaves read state unchanged. `read` marks read; successful reply marks answered. Archive closes eligible inbox work. Reading or answering alone does not complete that work. Remote attachments transfer bounded content through the registry API rather than asking the registry host to open a sender-host path.

## Notifiers and Projected Skills

Notifier configuration, interval, appendix, audit, and one-shot compaction state belong to owner/channel/binding scope. Configure the selected channel through `/v1/mail-notifier/{channel}` or scoped manager notifier commands with `--channel`.

Unchanged eligible inbox work continues producing periodic reminders. Readiness, pending-input, hook, and terminal admission gates remain shared so simultaneous channel reminders cannot overlap terminal work. Changing canonical mail identity alone does not reset compaction state.

The installed agent skill pack routes ordinary mail through `$houmao-agent-entrypoint agent-email-comms` and notifier rounds through `$houmao-agent-entrypoint process-emails-via-gateway`. Each round carries its channel, expected binding, and exact gateway URL. When the required native skill siblings are absent, the maintained API instructions remain usable without relying on native skill hot reload. A submission-only TUI fallback remains non-authoritative until verified through supported mailbox state.

## Source References

- [Runtime Binding Models](../../../../src/houmao/agents/mailbox_runtime_models.py)
- [Binding Resolution](../../../../src/houmao/agents/mailbox_runtime_support.py)
- [Manifest Mutation Boundary](../../../../src/houmao/agents/realm_controller/manifest.py)
- [Registry Record and Layout](../../registry/contracts/record-and-layout.md)


## Managed Online Connections

Online account controls use `mailbox online status|attach|refresh|reconnect|detach` through an available gateway companion. Attachment validates an existing normal account before committing; management credentials are unnecessary. Explicit administrative provisioning remains a launch-only workflow. Resuming a controller reads its persisted binding without provisioning.

Each connection owns a private immutable credential copy, exact JMAP account/sending identity, binding revision, and shared persistent epoch. Same-account refresh advances revision and epoch while preserving the binding ID and account checkpoints. Reconnect changes only the epoch. Another account requires explicit replacement and a fresh binding ID.

Cross-process shared admission leases pin ordinary online operations through their bounded provider I/O. A separate control mutex publishes retirement intent before waiting for exclusive admission; a finite deadline prevents false activation while old work remains in flight. Manifest CAS occurs only after retirement, with admission-before-manifest lock ordering. Network calls never run under the manifest lock or gateway terminal lock.

Queued online prompts and notifier context actions acquire a shared effect lease through their actual body effect. A replacement cannot commit between a successful origin check and submission. Synchronous headless prompt submission can hold that lease for the current turn; a bounded retirement timeout preserves the old binding rather than reporting false activation.

Observers capture immutable connections and release admission before network polling. Their local metadata/checkpoint commit reacquires short shared admission and checks owner, session, binding, revision, epoch, and account. A late result from a superseded connection is discarded. OS-owned leases release after process death, and the next operation reconciles orphaned retirement intent against the authoritative manifest.

Detach cleans only retired Houmao-owned snapshots after draining admitted requests. Externally selected files and provider mail remain intact. Send/reply receipts retain their original scope and known provider identifiers. Explicit `uncertain` outcomes require caller reconciliation and never trigger automatic replay.
