# Registration and Retention Policy

Registration is an exclusive atomic claim. Same-owner retry is idempotent; another owner's occupied address conflicts. There are no force/stash takeover or overwrite-confirmation modes.

Explicit release supports `deactivate` to retire routing while retaining registration-owned history, and `purge` for the supported stronger local removal policy. A subsequent owner receives a fresh registration and private views. For a symlink-backed mailbox, release does not move or delete the external target.

Cleanup handles inactive registration state under its documented retention controls and preserves canonical message history. Repair restores structural projections; it cannot replace ownership or import another registration's private history. Use dedicated message-clearing operations when the request concerns delivered content rather than membership.
