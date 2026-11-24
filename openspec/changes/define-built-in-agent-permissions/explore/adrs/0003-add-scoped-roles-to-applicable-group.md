# Add Scoped Roles to the Applicable Group

An exact-resource assignment adds permissions to the caller's applicable group. Bob can let Alice review one skill mount while she still uses his requester default for verified mail and work requests. Only a retained assignment to a `builtin:` peer group replaces the default for Alice's verified identity.

## Status

Accepted.

## Consequences

Bob can assign `builtin:agent-observer` alongside `skill-reviewer` to keep Alice's review access and narrow her verified contact rights. Expiry of the observer group keeps fallback suppressed until the assignment is removed. Inspection identifies the group and exact-role sources separately.
