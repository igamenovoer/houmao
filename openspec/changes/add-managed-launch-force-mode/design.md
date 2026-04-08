## Context

Managed local launch currently resolves one authoritative managed identity, starts a new runtime session, and then publishes that live session to the shared registry. When another fresh live session already owns the same managed identity, the replacement launch fails on shared-registry ownership rather than on tmux naming, and the current local flow does not provide an explicit takeover path. At the same time, brain construction already has a reuse-capable home builder, and runtime session roots and job roots are already per-session artifacts, so the missing piece is coordinated predecessor takeover rather than a new registry model.

This change is cross-cutting because it affects CLI option parsing, runtime takeover sequencing, brain-home reuse behavior, cleanup ownership boundaries, and easy-launch delegation. The requested operator contract is also intentionally asymmetric: bare `--force` must be non-destructive by default through `keep-stale`, while explicit `clean` must delete only Houmao-managed predecessor artifacts and leave unrelated operator-owned state alone.

## Goals / Non-Goals

**Goals:**

- Add an explicit launch-time force takeover path for managed local launch and easy instance launch.
- Make bare `--force` default to `keep-stale`, which leaves untouched stale artifacts in place and reuses the predecessor managed home.
- Support explicit `clean`, which removes predecessor-owned replaceable launch artifacts and recreates the managed home from a clean state.
- Preserve strict shared-registry ownership by making the predecessor stand down before the replacement launch publishes.
- Keep force mode launch-owned only and avoid persisting it into reusable launch profiles or easy profiles.

**Non-Goals:**

- Overwrite or weaken shared-registry ownership rules.
- Delete arbitrary caller-owned directories, source repositories, or shared mailbox roots.
- Extend takeover to server-owned or pair-managed remote authority in this phase.
- Guarantee rollback to the old live session if replacement launch fails after takeover has started.

## Decisions

### Force is managed-identity takeover, not registry overwrite

The runtime will continue to treat the shared registry as a strict ownership layer. A force launch resolves the predecessor that currently owns the target managed identity, stops that predecessor, and only then allows the replacement session to publish. This preserves the existing registry contract and avoids introducing in-place record mutation semantics that would blur the ownership boundary.

The rejected alternative was a direct registry overwrite flag. That would make the registry responsible for arbitration and would leave the old live session still running unless additional teardown logic were added afterward, which is backwards from the intended authority model.

### `keep-stale` is the default force mode

Bare `--force` normalizes to `keep-stale`. This is safer than defaulting to destructive cleanup and matches the requested operator posture: Houmao resolves the live-owner conflict but does not promise to scrub leftover disk state.

The rejected alternative was bare `--force clean`. That is simpler conceptually, but it makes the shortest operator spelling also the most destructive one.

### `keep-stale` reuses the predecessor managed home and leaves untouched files alone

`keep-stale` only makes sense if the replacement launch reuses the predecessor managed home identity and path. The builder will therefore reuse the predecessor home in place and overwrite only the projection targets touched by the new build, such as setup, selected skills, auth projections, model projections, and launch helper outputs. Untouched files remain as stale leftovers and are not validated or remediated.

The rejected alternative was to leave stale artifacts somewhere else while still creating a fresh managed home for the replacement launch. That would preserve old files without actually making them part of the new run, which does not satisfy the requested semantics.

### `clean` removes predecessor-owned replaceable artifacts before rebuilding

`clean` will stop the predecessor, remove the predecessor-managed home, remove predecessor-owned session-local runtime artifacts that are safe to replace, and then rebuild the managed home from an empty directory. Cleanup scope will include the predecessor session root, job directory, and predecessor-owned private mailbox or per-session mailbox-secret directories when ownership is provable. Shared mailbox message stores and other shared roots remain intact.

The rejected alternative was a broader recursive delete against all paths referenced by the old session. That is too risky because some launch inputs, such as workdir or shared mailbox roots, are operator-owned and must not be treated as disposable.

### Takeover targeting is identity-driven, not tmux-name-driven

Force takeover will resolve the predecessor by authoritative managed identity. If `--agent-id` is explicit, that id is authoritative. Otherwise the resolved managed identity name for the current launch becomes the lookup key. A tmux session-name collision alone is never enough to choose a takeover target.

The rejected alternative was to treat `--session-name` reuse as takeover intent. That would let a force launch kill unrelated sessions that merely share a tmux name.

### Force mode remains launch-owned only

The CLI surfaces may accept `--force` for the current invocation, but launch profiles and easy profiles will not store force mode. The runtime may record the effective force mode in ephemeral session metadata for diagnostics, but reusable profile state will remain unchanged.

The rejected alternative was to persist force mode into profiles. That would make a destructive or stale-tolerant takeover policy silently reusable in future launches, which is not appropriate as stored default behavior.

### Replacement failure is non-rollback after takeover begins

The launch path will perform preflight validation before stopping the predecessor where practical, but once takeover starts the system will not attempt to resurrect the old live session automatically. If replacement launch fails after cleanup or predecessor stop, the operator receives an explicit failure that identifies the selected force mode and the cleanup boundary already crossed.

The rejected alternative was automatic rollback to the predecessor session. That is brittle because the old runtime may already have been partially stopped, cleaned, or replaced on disk.

### Public CLI semantics stay compact even if parsing is normalized internally

The public contract is `--force [keep-stale|clean]`, with bare `--force` meaning `keep-stale`. Internally the implementation may normalize this into an enum or equivalent parser representation if the CLI library makes optional-value flags awkward, but the user-facing semantics stay the same.

The rejected alternative was a separate required `--force-mode` flag. That would be easier to parse, but it does not match the desired operator surface.

## Risks / Trade-offs

- [Stale leftover state breaks `keep-stale` launch] → Document that `keep-stale` leaves untouched artifacts in place by design, and add tests that confirm Houmao does not silently clean those leftovers.
- [Destructive cleanup targets the wrong path] → Restrict cleanup to predecessor-owned Houmao-managed artifacts derived from the resolved predecessor metadata and avoid deleting caller-owned roots such as workdir or shared mailbox roots.
- [Replacement launch fails after predecessor is gone] → Perform validation before takeover where practical and return explicit post-stop failure details instead of implying rollback.
- [CLI parsing ambiguity for bare `--force`] → Add command-surface tests for bare mode, explicit `keep-stale`, explicit `clean`, and invalid values on both launch entrypoints.

## Migration Plan

1. Extend the local launch and easy instance CLI surfaces to parse the force option and normalize it into a launch-owned takeover mode.
2. Add runtime takeover resolution and cleanup sequencing so a replacement launch can stop the predecessor before publishing.
3. Extend brain-home construction to support explicit managed-home reuse or scrub-and-recreate behavior.
4. Update docs and help text for both launch entrypoints and add unit/runtime tests for conflict, takeover, cleanup, and non-persistence behavior.

No stored-data migration is required because force mode is not persisted into launch profiles or easy profiles. Rollback is code rollback only; there is no compatibility promise for stale artifacts created during failed force launches.

## Open Questions

None blocking for this proposal phase. The scope is intentionally limited to local managed launch entrypoints and excludes server-owned takeover.
