# Mailbox Reference

This section explains the runtime-owned mailbox system from two angles at once: how to use it safely, and how it works under the hood across the filesystem and `stalwart` transports.

If you are new to the subsystem, start with [Quickstart](quickstart.md). If you already know the workflow and need exact contracts, jump into the contract pages. If you are debugging or extending mailbox behavior, use the operations and internals pages.

## Mental Model

The mailbox system is an async message transport owned by the runtime, not a loose collection of helper scripts.

- The runtime resolves one mailbox binding for a session.
- Shared mailbox operations such as `check`, `send`, `post`, `reply`, and the single-message read-state update may flow through the live gateway `/v1/mail/*` facade when it is attached, and that shared facade becomes the preferred path for common mailbox work.
- The filesystem transport stores canonical messages as immutable Markdown documents under `messages/` and keeps mailbox-view state in SQLite.
- Newly derived managed-agent mailbox addresses use `<agentname>@houmao.localhost`, while `HOUMAO-*` locals under `houmao.localhost` are reserved for Houmao-owned system mailboxes such as `HOUMAO-operator@houmao.localhost`.
- The `stalwart` transport delegates delivery, unread state, reply ancestry, and mailbox access to Stalwart instead of recreating those invariants in Houmao-owned files.
- For filesystem-backed sessions, sensitive filesystem mutations are still funneled through managed scripts published into the mailbox-local `rules/` tree.
- `houmao-mgr mailbox cleanup` only removes inactive or stashed filesystem registrations and intentionally preserves canonical `messages/` history. Runtime-owned Stalwart credential cleanup lives under `houmao-mgr admin cleanup runtime mailbox-credentials`, and per-session Stalwart secret cleanup lives under `houmao-mgr agents cleanup mailbox`.

## Key Terms

- `canonical message`: The immutable Markdown document plus YAML front matter that represents one delivered message.
- `mailbox binding`: The resolved runtime config and env vars that tell a session which mailbox it belongs to.
- `message_ref`: The opaque shared target used by direct runtime flows and the gateway mailbox facade for reply and single-message read-state update.
- `mailbox registration`: The active, inactive, or stashed ownership record for one full mailbox address.
- `projection`: A filesystem-transport symlink in `mailboxes/<address>/inbox` or `sent` that points to a canonical message.
- `mailbox root`: The filesystem-transport tree that holds `messages/`, `mailboxes/`, `locks/`, `rules/`, `staging/`, and `index.sqlite`.

## Read By Goal

### Start here

- [Quickstart](quickstart.md): Enable mailbox support and run `mail check`, `mail send`, `mail post`, and `mail reply`.
- [Stalwart Setup And First Session](operations/stalwart-setup-and-first-session.md): Start a Stalwart-backed mailbox session, verify it directly, and understand when the gateway mailbox facade becomes the preferred shared path.
### Contracts

- [Canonical Model](contracts/canonical-model.md): Message schema, addressing, threading, attachments, and immutable versus mutable state.
- [Runtime Contracts](contracts/runtime-contracts.md): Declarative config, resolved bindings, projected skill behavior, and `mail` request/result envelopes.
- [Project Mailbox Skills](contracts/project-mailbox-skills.md): Native mailbox skill projection during the build phase — what skills are injected and how they differ per tool.
- [Managed Scripts](contracts/managed-scripts.md): Stable helper entrypoints, flags, validation behavior, dependencies, and JSON stdout.
- [Filesystem Layout](contracts/filesystem-layout.md): Durable tree structure, mailbox-local rules, projections, attachments, and placeholder directories.

### Operations

- [Common Workflows](operations/common-workflows.md): Bootstrap, read, send, post, reply, and when to inspect `rules/` first.
- [Stalwart Setup And First Session](operations/stalwart-setup-and-first-session.md): Prerequisites, first session, secret lifecycle, and the direct-versus-gateway reader path for Stalwart-backed sessions.
- [Registration Lifecycle](operations/registration-lifecycle.md): `safe`, `force`, `stash`, `deactivate`, `purge`, and cleanup of inactive or stashed registrations.
- [Repair And Recovery](operations/repair-recovery.md): What repair rebuilds, what it preserves, and what it cannot recover.

### Internals

- [Runtime Integration](internals/runtime-integration.md): How build, start, resume, refresh, and `mail` flows connect.
- [State And Locking](internals/state-and-locking.md): SQLite responsibilities, canonical-versus-mutable ownership, and lock ordering.

## Related References

- [houmao-mgr agents mail CLI](../cli/agents-mail.md): Managed-agent mailbox follow-up commands.
- [houmao-mgr agents mailbox CLI](../cli/agents-mailbox.md): Late filesystem mailbox registration for local managed agents.
- [Gateway Mailbox Facade](../gateway/operations/mailbox-facade.md): Shared `/v1/mail/*` routes, adapter selection, loopback-only availability, and notifier behavior through the gateway.
- [Agents And Runtime](../system-files/agents-and-runtime.md): Runtime-owned filesystem placement for manifests, gateway state, and Stalwart credential material.

## Source References

- [`src/houmao/agents/mailbox_runtime_support.py`](../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/agents/realm_controller/mail_commands.py`](../../../src/houmao/agents/realm_controller/mail_commands.py)
- [`src/houmao/agents/realm_controller/gateway_mailbox.py`](../../../src/houmao/agents/realm_controller/gateway_mailbox.py)
- [`src/houmao/mailbox/protocol.py`](../../../src/houmao/mailbox/protocol.py)
- [`src/houmao/mailbox/filesystem.py`](../../../src/houmao/mailbox/filesystem.py)
- [`src/houmao/mailbox/managed.py`](../../../src/houmao/mailbox/managed.py)
- [`src/houmao/mailbox/stalwart.py`](../../../src/houmao/mailbox/stalwart.py)
