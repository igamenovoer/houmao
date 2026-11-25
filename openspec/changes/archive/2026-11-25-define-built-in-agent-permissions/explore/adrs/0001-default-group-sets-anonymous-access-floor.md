# Default Group Sets the Anonymous Access Floor

The target's configured default supplies permissions for eligible unsigned requests without requiring per-target enrollment or a shared identity provider. Explicit assignments apply to verified identities. A caller with a narrower assignment can make a separate unsigned request under the same default as any anonymous caller.

## Status

Accepted.

## Consequences

With the `agent-requester` default, Bob denies an identified work request from observer Alice and accepts an eligible unsigned request as anonymous. Bob can lower the target default if he wants less anonymous access. Ingress still rejects invalid proof and enforces each operation's sender verification and other prerequisites.
