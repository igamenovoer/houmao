# Enhancement Proposal: Mailbox Join Should Support Explicit Name-Conflict Resolution Modes

## Status
Resolved on 2026-03-17.

## Resolution Summary
The mailbox registration lifecycle now documents and implements explicit `safe`, `force`, and `stash` join modes, with corresponding managed-script and test coverage.

## Summary
When an agent tries to join a mailbox group and its target mailbox entry is already taken, the join flow should expose explicit conflict-resolution modes instead of relying on one implicit behavior.

The proposed modes are:
- `safe join`
- `force join`
- `stash join`

This would make mailbox join behavior clearer and safer in cases such as crash recovery, stale directories, recycled agent names, or real naming conflicts.

## Why
Current behavior is only partially explicit:
- if the same `principal_id` is already registered in SQLite with the same address and mailbox path, bootstrap behaves idempotently,
- if the same `principal_id` is registered with a different address or mailbox path, bootstrap fails,
- if a mailbox directory already exists on disk but there is no conflicting SQLite registration row, the current bootstrap path can effectively adopt that directory.

That leaves an awkward gap:
- crash-recovery reuse is desirable,
- real naming conflicts should be handled deliberately,
- operators may sometimes want to replace a stale mailbox completely,
- operators may sometimes want to preserve the old mailbox as a stashed historical artifact while letting the new agent join cleanly.

Right now those cases are not modeled as explicit operator choices.

## Requested Enhancement
Add an explicit conflict-resolution mode to the mailbox join/bootstrap flow or managed join script.

### Mode 1: `safe join`
This should be the default mode and match the current safe behavior:
- if the existing mailbox identity matches the joining principal cleanly, reuse or inherit it,
- otherwise fail explicitly,
- do not delete or rename existing mailbox artifacts automatically.

This is the safe restart or crash-recovery mode.

### Mode 2: `force join`
This mode should let the joining agent take over the mailbox name cleanly:
- delete the existing mailbox entry for that principal,
- remove or replace the conflicting registration state,
- let the joining principal create a fresh mailbox entry and join cleanly.

This is intentionally destructive and should be explicit, never the default.

### Mode 3: `stash join`
This mode should preserve the previous mailbox artifact before the new agent joins:
- rename the existing mailbox directory or symlink target by suffixing it with a `uuid4` hex value,
- update `index.sqlite` accordingly so the stashed mailbox artifact is still represented consistently in registry/index state,
- let the new agent join with a fresh clean mailbox entry under the original principal name,
- do not rewrite existing canonical messages.

The stashed mailbox should preserve prior filesystem evidence, while canonical message content remains unchanged. Historical message ownership can still be understood from the immutable content, timestamps, and related protocol metadata rather than by rewriting old message bodies.

## Acceptance Criteria
1. Mailbox join/bootstrap exposes a clear conflict-resolution mode instead of one implicit behavior.
2. `safe join` is the default.
3. `safe join` reuses the mailbox only when identity, address, and expected registration state match; otherwise it fails explicitly.
4. `force join` performs an explicit destructive replacement and leaves the joining principal with a clean mailbox entry.
5. `stash join` preserves the old mailbox artifact by renaming it with a UUID4-based suffix and then creates a clean mailbox entry for the joining principal.
6. `stash join` updates relevant `index.sqlite` registration/index state consistently without rewriting canonical message content.
7. Docs explain when each mode should be used and which modes are destructive.
8. Tests cover at least:
   - idempotent same-principal safe join,
   - safe join failure on real conflict,
   - force join replacing an old mailbox,
   - stash join preserving the old mailbox artifact and creating a new clean one.

## Non-Goals
- No requirement to redesign canonical message content or rewrite historical message files.
- No requirement to solve broader leave-group or principal-deregistration semantics in the same enhancement.
- No requirement to make destructive join modes the default.
- No requirement to define behavior for multiple agents with the same principal name attempting to join the same mail group at the same time. That race is treated as out of scope here and left to user or operator manual coordination.

## Suggested Follow-Up
- Decide where this mode should live:
  bootstrap API, managed join script, runtime CLI, or a combination.
- Define exact SQLite update semantics for `force join` and `stash join`.
- Pair this with the mailbox principal deregistration/cleanup feature so lifecycle transitions are coherent across join, rejoin, and leave flows.
