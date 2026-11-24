# Logical Agent Peer Grants

The target owner grants access to a logical agent principal and enrolls a revocable public signing key for it. Peer grants are valid across OS accounts, containers, and hosts independently of the source agent's running context. The existing managed self credential continues to prove the current generation for operations on its own target.

## Status

Accepted.

## Consequences

The target verifies SSHSIG against its enrollment without contacting the source runtime. It relies on enrollment and explicit revocation or expiry to manage a peer's authority. For versioned edits, the target gateway records the authenticated requesting agent as Git author and the target as committer. The push receipt records who authorized publication through their own admitted authority.
