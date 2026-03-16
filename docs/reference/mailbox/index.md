# Mailbox Reference

This section explains the runtime-owned filesystem mailbox from two angles at once: how to use it safely, and how it works under the hood.

If you are new to the subsystem, start with [Quickstart](quickstart.md). If you already know the workflow and need exact contracts, jump into the contract pages. If you are debugging or extending mailbox behavior, use the operations and internals pages.

## Mental Model

The mailbox system is an async message transport owned by the runtime, not a loose collection of helper scripts.

- The runtime resolves one mailbox binding for a session.
- The filesystem transport stores canonical messages as immutable Markdown documents under `messages/`.
- Mailbox-visible `inbox/` and `sent/` entries are projections that point back to those canonical files.
- Mutable per-recipient state such as read or starred lives in `index.sqlite`.
- Sensitive mutations are funneled through managed scripts published into the mailbox-local `rules/` tree.

## Key Terms

- `canonical message`: The immutable Markdown document plus YAML front matter that represents one delivered message.
- `mailbox binding`: The resolved runtime config and env vars that tell a session which mailbox it belongs to.
- `mailbox registration`: The active, inactive, or stashed ownership record for one full mailbox address.
- `projection`: A symlink in `mailboxes/<address>/inbox` or `sent` that points to a canonical message.
- `mailbox root`: The shared filesystem tree that holds `messages/`, `mailboxes/`, `locks/`, `rules/`, `staging/`, and `index.sqlite`.

## Read By Goal

### Start here

- [Quickstart](quickstart.md): Enable mailbox support and run `mail check`, `mail send`, and `mail reply`.
- [Mailbox Roundtrip Tutorial Pack](../../../scripts/demo/mailbox-roundtrip-tutorial-pack/README.md): Run the full two-agent CAO-backed roundtrip and verify the sanitized report contract.

### Contracts

- [Canonical Model](contracts/canonical-model.md): Message schema, addressing, threading, attachments, and immutable versus mutable state.
- [Runtime Contracts](contracts/runtime-contracts.md): Declarative config, resolved bindings, projected skill behavior, and `mail` request/result envelopes.
- [Managed Scripts](contracts/managed-scripts.md): Stable helper entrypoints, flags, validation behavior, dependencies, and JSON stdout.
- [Filesystem Layout](contracts/filesystem-layout.md): Durable tree structure, mailbox-local rules, projections, attachments, and placeholder directories.

### Operations

- [Common Workflows](operations/common-workflows.md): Bootstrap, read, send, reply, and when to inspect `rules/` first.
- [Registration Lifecycle](operations/registration-lifecycle.md): `safe`, `force`, `stash`, `deactivate`, and `purge`.
- [Repair And Recovery](operations/repair-recovery.md): What repair rebuilds, what it preserves, and what it cannot recover.

### Internals

- [Runtime Integration](internals/runtime-integration.md): How build, start, resume, refresh, and `mail` flows connect.
- [State And Locking](internals/state-and-locking.md): SQLite responsibilities, canonical-versus-mutable ownership, and lock ordering.

## Source References

- [`src/houmao/agents/mailbox_runtime_support.py`](../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/agents/realm_controller/mail_commands.py`](../../../src/houmao/agents/realm_controller/mail_commands.py)
- [`src/houmao/mailbox/protocol.py`](../../../src/houmao/mailbox/protocol.py)
- [`src/houmao/mailbox/filesystem.py`](../../../src/houmao/mailbox/filesystem.py)
- [`src/houmao/mailbox/managed.py`](../../../src/houmao/mailbox/managed.py)
