# Mailbox Quickstart

This guide is for an operator who already has a configured Houmao project and a launchable specialist. It sets up offline mail for an existing local agent, then shows how to choose a channel and perform a bounded mail round.

## Choose Channels

An agent can have one offline mailbox and one online mailbox simultaneously. Both belong to its immutable `agent_id`, which defaults to a UUID when the agent is created. Its canonical mail identity prefers the configured online address, otherwise offline, otherwise no address. That preference does not route messages or change during an outage.

| Channel | Authority | Setup |
| --- | --- | --- |
| `offline` | One selected registry host and its filesystem mail store | Continue below; use [Offline Registry Setup](operations/offline-registry.md) for remote members |
| `online` | An email provider, initially Stalwart | [Stalwart Setup and First Session](operations/stalwart-setup-and-first-session.md) |

Offline recipients must belong to the same selected registry. Online and offline mail never forward, translate addresses, or fall back to each other.

## Initialize the Offline Authority

Choose the registry and store explicitly. These examples use private directories outside the checkout:

```bash
export HOUMAO_GLOBAL_REGISTRY_DIR="$HOME/.local/share/houmao-dev/registry"
export HOUMAO_GLOBAL_MAILBOX_DIR="$HOME/.local/share/houmao-dev/offline-mail"
pixi run houmao-mgr mailbox init \
  --registry-root "$HOUMAO_GLOBAL_REGISTRY_DIR" \
  --mailbox-root "$HOUMAO_GLOBAL_MAILBOX_DIR"
```

Initialization associates that registry with one store. Later membership operations reject a different store. Project-aware root selection remains available when initializing project-local mail; it does not override an existing registry association.

Launch the prepared specialist. Replace `worker` with a specialist registered in your project:

```bash
pixi run houmao-mgr project agents launch \
  --specialist worker --name research --mode headless
```

Record the returned `agent_id` as `agent_id` in your shell. A friendly name is convenient metadata; use the stable ID when names are ambiguous. The default allocates a new UUID. Explicit `--agent-id-mode name-hash` is available when you deliberately manage name uniqueness yourself.

Attach offline mail without restarting the body:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox offline join \
  --mailbox-root "$HOUMAO_GLOBAL_MAILBOX_DIR" \
  --address research@houmao.localhost
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox offline status
pixi run houmao-mgr agents single --agent-id "$agent_id" mail status
```

Another agent cannot claim an occupied address. Repeating the same owner/address join preserves the confirmed registration. Explicit `mailbox offline leave` releases the address; stopping the body or attaching online mail does not.

## Resolve a Mail Round

Use `agents self` inside the owning managed session, or `agents single` with an explicit selector elsewhere:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail resolve-live
```

`resolve-live` returns `mailboxes.offline` and `mailboxes.online` slot summaries, their revisions, canonical mail identity, and an optional exact `gateway.base_url`. The gateway `GET /v1/mail/status` response has direct `offline` and `online` channel entries. For example:

```json
{
  "schema_version": 3,
  "agent_id": "b498dd79-cbbc-41b2-a593-6263db66fe94",
  "offline": {
    "agent_id": "b498dd79-cbbc-41b2-a593-6263db66fe94",
    "channel": "offline",
    "binding_id": "registration-a",
    "revision": "offline-revision-a",
    "address": "research@houmao.localhost",
    "transport": "filesystem",
    "available": true
  },
  "online": null,
  "canonical_mail_identity": {
    "channel": "offline",
    "address": "research@houmao.localhost"
  }
}
```

Record the selected channel's `binding_id` as `binding_id`. HTTP lifecycle requests always require `expected_binding_id`. The manager resolves it once when omitted; provide `--expected-binding-id` when continuing a round so a replaced mailbox cannot receive an old operation.

## List, Read, Reply, and Archive

The recipient in this example must already have an offline registration in the selected registry:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail list \
  --channel offline --expected-binding-id "$binding_id" --limit 10
pixi run houmao-mgr agents single --agent-id "$agent_id" mail send \
  --channel offline --expected-binding-id "$binding_id" \
  --to orchestrator@houmao.localhost --subject "Review request" \
  --body-content "Please review the current parser mismatch."
```

The send receipt gives the status and a top-level scoped reference. Use `mail peek` on the sender's binding to inspect the sent copy. In the processing commands below, set `message_ref` to the opaque reference from the inbox list. The reply receipt has its own reference for the new message.

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail peek \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref"
pixi run houmao-mgr agents single --agent-id "$agent_id" mail read \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref"
pixi run houmao-mgr agents single --agent-id "$agent_id" mail reply \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref" \
  --body-content "Review completed."
pixi run houmao-mgr agents single --agent-id "$agent_id" mail archive \
  --channel offline --expected-binding-id "$binding_id" --message-ref "$message_ref"
```

`peek` preserves read state. `read` marks read, and successful reply marks answered. Archive closes eligible inbox work after processing succeeds. Read or answered state alone does not complete the work.

Use `--body-file` instead of `--body-content` for a file-backed body and repeat `--attach` for attachments. Remote offline attachment content transfers through the registry API; the registry never opens a sender-host path as its own path.

Local filesystem mail also supports operator-origin `mail post --channel offline`. Its sender is the reserved `HOUMAO-operator@houmao.localhost`; online providers and remote member backends report unsupported operations explicitly.

## Gateway Requests and Reminders

Use the exact gateway URL from discovery. Mail schema version 3 requires the selected binding even for a fresh send or post:

```json
{
  "schema_version": 3,
  "expected_binding_id": "registration-a",
  "box": "inbox",
  "limit": 10
}
```

Send that body to `POST /v1/mail/offline/list`. Other lifecycle actions use `/v1/mail/{channel}/...`; references remain scoped to the same owner, channel, and binding.

Enable periodic reminders separately for a channel:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway mail-notifier enable \
  --channel offline --interval-seconds 60 --mode any_inbox
```

Eligible unchanged inbox work keeps producing reminders while the body is ready. Agent rounds carry the channel, expected binding, and exact gateway URL. They process one round and stop; they do not start their own polling loop. Independent channel settings use `/v1/mail-notifier/{channel}`.

Verified manager or gateway execution returns `authoritative: true`. A TUI fallback returns submission-only results with `authoritative: false`; verify those outcomes through supported mailbox state before treating the action as complete.

Continue with [Common Workflows](operations/common-workflows.md), [Runtime Contracts](contracts/runtime-contracts.md), or [Offline Registry Setup](operations/offline-registry.md).
