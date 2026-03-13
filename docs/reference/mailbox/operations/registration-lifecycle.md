# Mailbox Registration Lifecycle

This page explains how the v1 filesystem mailbox decides which mailbox artifact is active for a full mailbox address and what the lifecycle modes do when that artifact changes.

## Mental Model

Registrations are address-routed, not principal-routed.

- The key is the full mailbox address such as `AGENTSYS-research@agents.localhost`.
- At most one registration for that address may be `active`.
- Older registrations may remain as `inactive` or `stashed`.
- The registration record and the mailbox artifact can point either to an in-root mailbox directory or to a private mailbox directory reached through a symlink entry.

This design lets the transport keep canonical messages shared while still allowing address-specific mailbox locations to move.

## Join Modes

### `safe`

Use `safe` when you want the default behavior.

- Reuse the current active registration when it already matches the request.
- Reactivate a matching inactive registration when the mailbox artifact still matches.
- Fail if a different active registration already exists for the address.
- Fail if a preserved mailbox artifact still occupies the address path.

### `force`

Use `force` when you want the active registration replaced.

- The prior active or occupying registration becomes inactive or removed from active use.
- Registration-scoped mutable state for the replaced registration is purged.
- The address receives a fresh active registration id.

### `stash`

Use `stash` when you want to preserve the prior mailbox artifact before replacement.

- The prior mailbox artifact is renamed to `mailboxes/<address>--<uuid4hex>`.
- The prior registration becomes `stashed`.
- A new active registration is created for the original address entry.

```mermaid
sequenceDiagram
    participant Req as Register<br/>request
    participant Scr as register_mailbox.py
    participant DB as index.sqlite
    participant Box as mailboxes/<address>
    Req->>Scr: mode=safe|force|stash
    Scr->>DB: load active or occupying<br/>registration
    alt safe and matching
        Scr-->>Req: reuse existing active<br/>registration
    else force replace
        Scr->>DB: mark old inactive and<br/>purge registration state
        Scr->>Box: replace active artifact
        Scr->>DB: insert new active registration
        Scr-->>Req: replaced_registration_id
    else stash replace
        Scr->>Box: rename old artifact to<br/><address>--<uuid4hex>
        Scr->>DB: mark old registration stashed
        Scr->>DB: insert new active registration
        Scr-->>Req: stashed_registration_id
    end
```

## Leave Modes

### `deactivate`

Use `deactivate` when you want delivery to stop without deleting the registration record.

- The active registration becomes `inactive`.
- Historical canonical messages remain untouched.
- The registration record stays in SQLite for later inspection or possible reuse.

### `purge`

Use `purge` when you want to remove registration-scoped mutable state and shared-root registration artifacts.

- The registration row is deleted.
- Registration-scoped projection rows and mailbox state rows are removed.
- Shared-root registration artifacts are removed.
- Canonical messages under `messages/` are preserved.
- Historical recipient delivery records in canonical history remain meaningful even after the registration is gone.

```mermaid
sequenceDiagram
    participant Req as Deregister<br/>request
    participant Scr as deregister_mailbox.py
    participant DB as index.sqlite
    participant Box as mailbox artifact
    Req->>Scr: mode=deactivate|purge
    Scr->>DB: load active registration
    alt deactivate
        Scr->>DB: mark registration inactive
        Scr-->>Req: resulting_status=inactive
    else purge
        Scr->>DB: remove registration-scoped<br/>state and registration row
        Scr->>Box: remove shared-root entry
        Scr-->>Req: resulting_status=purged
    end
```

## Practical Examples

- Re-running bootstrap for the same session address usually resolves through `safe` and reuses the existing active registration.
- Replacing an in-root mailbox with a different owner uses `force` or `stash`.
- Moving an address to a private mailbox directory uses `mailbox_kind=symlink` with `safe`, `force`, or `stash` depending on whether a conflicting registration already exists.
- Purging a private mailbox registration removes the shared-root registration entry but does not delete canonical message history.

## Source References

- [`src/gig_agents/mailbox/filesystem.py`](../../../../src/gig_agents/mailbox/filesystem.py)
- [`src/gig_agents/mailbox/managed.py`](../../../../src/gig_agents/mailbox/managed.py)
- [`src/gig_agents/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md`](../../../../src/gig_agents/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md)
- [`tests/unit/mailbox/test_managed.py`](../../../../tests/unit/mailbox/test_managed.py)
