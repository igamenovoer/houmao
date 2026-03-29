## Context

`houmao-mgr project easy` currently exposes `specialist launch` as the action that materializes a runtime instance from a compiled specialist, but that places a runtime lifecycle command under the configuration-oriented specialist group. It also does not currently let the operator bind the launched instance to a mailbox account at that same seam.

That gap matters because the mailbox stack already has meaningful lifecycle choices that ordinary `project easy` users should not have to reconstruct manually after launch:

- a filesystem mailbox account can live directly under the shared mailbox root,
- a filesystem mailbox account can also be represented by a symlink entry under the shared mailbox root that points at a private mailbox directory elsewhere,
- a real email transport already exists at lower layers, but the `project easy` UX is not ready to expose transport-specific server settings.

The current implementation also has an architectural mismatch that this change needs to correct instead of papering over:

- `project easy specialist launch` is a thin wrapper over the existing managed-agent launch callback, so mailbox setup done after launch would create partial-success states,
- runtime mailbox startup for filesystem transport currently bootstraps the standard in-root registration path,
- low-level filesystem mailbox registration already knows how to create or validate symlink-backed registrations, but that lifecycle currently resets mailbox-local SQLite state for a newly inserted registration, which is unsafe for a reused non-empty private mailbox directory.

The design therefore needs to do three things together:

- move the launch verb to the runtime-oriented `instance` group,
- add mailbox association at launch time,
- keep the launch result atomic while tightening the filesystem registration contract for user-supplied private mailbox directories.

## Goals / Non-Goals

**Goals:**

- Move easy launch to `houmao-mgr project easy instance launch` so `specialist` stays configuration-only and `instance` owns runtime lifecycle actions.
- Add `houmao-mgr project easy instance stop` as a project-scoped wrapper over the canonical managed-agent stop path so users can stay within the `instance` lifecycle surface.
- Add launch-time mailbox association to `houmao-mgr project easy instance launch`.
- Let the operator choose between a filesystem-backed mailbox account and a reserved future real-email path.
- Require a mailbox root for filesystem-backed easy launch.
- Allow an optional private mailbox directory for filesystem-backed launch, represented in the shared root as a symlink-backed mailbox account.
- Reject ambiguous or conflicting filesystem mailbox bindings up front, including private mailbox directories that resolve inside the shared mailbox root.
- Preserve existing mailbox-local state in a reused private mailbox directory rather than silently wiping it.
- Report the effective mailbox association from the `project easy instance` view using runtime-derived state.
- Avoid introducing a second persisted per-instance config layer under `.houmao/easy/`.

**Non-Goals:**

- Implementing the real-email `project easy` path in this change.
- Changing the public `houmao-mgr agents launch` contract to become mailbox-aware.
- Defining new stop semantics for `project easy instance stop` that diverge from the existing managed-agent stop contract.
- Generalizing this change into a transport-generic mailbox administration workflow outside `project easy`.
- Importing, migrating, or reconciling arbitrary existing mailbox contents beyond the defined filesystem merge rules for the requested account directory.
- Backfilling easy-layer mailbox identity override flags in the same change unless later scope requires them.

## Decisions

### Decision: Keep mailbox association as launch-time runtime state, not a new easy instance config

The mailbox binding belongs to the launched managed-agent session and should be derived from runtime state in the same way that `project easy instance` already derives its view from managed-agent state.

This change will not introduce `.houmao/easy/instances/<name>.toml` or any other second per-instance source of truth. The authoritative persisted state remains the managed session manifest plus the shared mailbox registration state.

Rationale:

- The current `project easy` design already treats instances as a view over runtime state.
- Adding another persisted instance contract would create split-brain launch inputs immediately.
- Mailbox association failure should prevent the session from starting, not leave a partially-described easy-layer instance behind.

Alternative considered:

- Persist a new easy instance config that stores mailbox settings independently of runtime state.
  Rejected because it duplicates the launch contract and makes instance inspection harder to reason about.

### Decision: `specialist` remains configuration-only and `instance` owns launch, stop, plus runtime lifecycle

This change moves the easy launch verb from:

- `project easy specialist launch`

to:

- `project easy instance launch`

The specialist group remains the place for reusable configuration and compilation-oriented metadata. The instance group becomes the place for runtime lifecycle actions and runtime inspection. `instance launch` will accept a required specialist selector, derive the provider from that specialist, and materialize one managed runtime instance. `instance stop` will stop one runtime instance by delegating to the existing managed-agent stop path after project-overlay ownership checks.

This keeps the command model aligned with the underlying concepts:

- `specialist` = reusable blueprint and config,
- `instance` = concrete runtime object.

Rationale:

- Launch creates a runtime instance, so `instance launch` is the more honest noun/verb pairing.
- Future runtime verbs such as `stop`, `restart`, or `remove` belong naturally under `instance`.
- Mailbox association is instance state, so coupling it to `instance launch` is cleaner than treating it as a specialist action.

Alternative considered:

- Keep `specialist launch` for discoverability because launch starts from a specialist.
  Rejected because it keeps mixing runtime lifecycle into the configuration group and makes later `instance` growth less coherent.

### Decision: `instance stop` wraps the canonical managed-agent stop path instead of killing tmux directly

`project easy instance stop --name <instance>` will:

1. resolve the managed-agent target from the instance name,
2. verify that the resolved manifest belongs to the current project overlay,
3. delegate to the existing managed-agent stop implementation.

This change will not introduce a second stop engine in `project easy`, and it will not define stop as a raw `tmux kill-session` shortcut.

That wrapper design keeps the command conceptually consistent for `project easy` users while preserving one canonical runtime-control implementation for gateway detach, manifest persistence, shared-registry cleanup, and any tmux cleanup behavior already owned by the existing managed-agent stop path.

Rationale:

- Users who adopt `project easy instance` as the runtime lifecycle surface should not need to switch command families just to stop an instance.
- Managed stop already does more than kill tmux, so duplicating or bypassing that control path in the project CLI would be incorrect and fragile.
- Project ownership validation belongs in `project easy instance stop`, but runtime teardown semantics belong in the canonical managed-agent controller path.

Alternative considered:

- Implement `instance stop` by killing the tmux session directly.
  Rejected because that bypasses managed runtime teardown such as gateway detach, manifest persistence, and shared-registry cleanup.

### Decision: The easy-layer mail transport contract is `filesystem|email`

`project easy instance launch` will expose a high-level mail transport choice:

- `filesystem` for the implemented local mailbox flow in this change,
- `email` as a reserved future real-email option.

In this change, `--mail-transport email` fails fast with a clear "not implemented yet" error and a non-zero exit status before any managed-agent session is created.

This is intentionally an easy-layer abstraction. Lower runtime layers may continue to use a more specific transport identifier such as `stalwart`, but the `project easy` UX should not yet require provider-specific mail-server configuration.

Rationale:

- The user need is to distinguish local filesystem mailboxes from real email accounts, not to choose a concrete email backend yet.
- Reserving the easy-layer branch now gives the CLI a stable user-facing shape without prematurely exposing server-specific knobs.

Alternative considered:

- Expose `stalwart` directly on `project easy instance launch`.
  Rejected because it leaks lower-level provider choices into a higher-level UX before the real-email path is usable.

### Decision: Mail-enabled easy launch requires an explicit instance identity

When mail association is requested, the operator must provide the instance name at `project easy instance launch` unless a future change introduces explicit mail identity overrides.

The default mailbox identity for this change is derived from the launched instance rather than only from the specialist. The effective principal and address therefore stay unique per launched instance instead of collapsing every launch of one specialist onto the same mailbox address.

Rationale:

- A mailbox account is an instance-level resource, not just a specialist-level resource.
- Reusing specialist identity as the mailbox identity would create avoidable collisions when the same specialist is launched multiple times.

Alternative considered:

- Derive mailbox identity from specialist name when the operator omits the explicit instance name.
  Rejected because it makes mailbox collisions the default behavior for repeated launches.

### Decision: Filesystem launch supports either an in-root account or a symlink-backed private mailbox directory

For filesystem mail transport:

- `--mail-root <dir>` is required,
- `--mail-account-dir <dir>` is optional.

If `--mail-account-dir` is omitted, the runtime creates or confirms the standard in-root mailbox account under `mailboxes/<address>/`.

If `--mail-account-dir` is provided, the runtime treats that directory as the concrete mailbox account path and creates or confirms a symlink entry under `mailboxes/<address>` that points to that directory.

The target mailbox directory must contain the standard mailbox placeholder directories required by the filesystem mailbox contract. At minimum, that includes `inbox/`, `sent/`, `archive/`, and `drafts/`.

Rationale:

- This keeps the operator surface small while still covering both the shared-root and private-dir cases.
- It reuses the mailbox lifecycle model that already exists in the lower-level mailbox code instead of inventing a second filesystem concept.

Alternative considered:

- Restrict easy launch to in-root mailbox accounts only.
  Rejected because the user requirement explicitly includes private mailbox directories that are symlinked into the shared root.

### Decision: Easy launch must perform mailbox setup atomically with runtime startup

This change will keep `houmao-mgr agents launch` mailbox-agnostic and instead introduce or reuse an internal launch helper that lets `project easy instance launch` pass specialist selection plus mailbox startup intent into runtime startup directly.

The runtime startup path must be able to materialize filesystem mailbox bindings in either of these shapes before the session is considered started:

- in-root registration,
- symlink-backed registration targeting a private mailbox directory.

If mailbox validation or registration fails, the managed-agent session must not be created.

Rationale:

- Launching first and registering later would produce partial-success states that are hard to recover from and hard to present in `project easy instance`.
- The existing runtime startup flow already owns manifest creation, session bootstrap, and mailbox binding projection, so it is the correct atomic seam.

Alternative considered:

- Launch the session first and then run a separate mailbox registration step from the easy CLI.
  Rejected because it would allow "agent launched but mailbox association failed" outcomes.

### Decision: Private mailbox directories must obey strict path and conflict validation

For `--mail-account-dir`, the runtime must resolve both the mailbox root and the requested account directory before registration and apply these checks:

- reject the request if the resolved account directory is inside the resolved mailbox root,
- reject the request if the shared-root entry for `mailboxes/<address>` already exists as a real directory,
- reject the request if the shared-root entry already exists as a symlink to a different target,
- allow idempotent reuse when the shared-root entry already exists as a symlink to the same resolved target,
- reject the request if another active mailbox address already owns the same concrete private mailbox path.

These checks apply before session startup commits any mailbox association state.

Rationale:

- A private mailbox directory inside the shared root collapses the distinction between in-root and symlink-backed storage and invites recursive or ambiguous path handling.
- Conflicting symlink or directory occupancy under `mailboxes/<address>` must fail clearly rather than silently rewrite somebody else's mailbox entry.
- Reusing one private mailbox directory for multiple active addresses would make ownership and local state ambiguous.

Alternative considered:

- Normalize conflicting entry states into the requested shape automatically.
  Rejected because it can silently detach or overwrite an existing mailbox account.

### Decision: Preparing a pre-existing private mailbox directory must be merge-oriented and non-destructive

When the operator provides `--mail-account-dir` and that directory already exists, the runtime must prepare it by creating any missing mailbox placeholder directories and required mailbox-local state artifacts without silently deleting existing mailbox-local state.

The safe preparation contract for this change is:

- create the target directory if it does not yet exist,
- create any missing reserved mailbox directories,
- preserve unrelated existing files,
- reuse existing mailbox-local SQLite state when it is already present and readable,
- only prompt before overwriting a managed file when the process has an interactive TTY,
- fail clearly instead of overwriting when a conflicting managed file would need replacement in a non-interactive run.

This change specifically must not keep using the "new registration implies reset mailbox-local database" behavior for a pre-existing private mailbox directory that is being adopted safely.

Rationale:

- The user requirement is merge, not wipe-and-reseed.
- Existing mailbox-local state such as `mailbox.sqlite` may already contain useful read/unread or thread-summary state that should not be thrown away by a safe launch-time association.

Alternative considered:

- Reuse the current new-registration reset path for all symlink-backed mailbox registrations.
  Rejected because it silently destroys mailbox-local state in exactly the reuse case this change introduces.

### Decision: `project easy instance` reports mailbox association from runtime-derived state

`project easy instance get` must report the effective mailbox association for a mailbox-bound instance, including the high-level transport, mailbox address, shared mailbox root, mailbox kind, and resolved mailbox directory.

`project easy instance list` may stay compact, but it must expose enough mailbox summary to distinguish mailbox-bound from mailbox-less instances.

Rationale:

- Operators need a way to confirm what was actually bound at launch time.
- Reporting runtime-derived mailbox state avoids inventing a separate easy-layer cache for mailbox metadata.

Alternative considered:

- Keep mailbox details visible only in low-level managed-agent inspection commands.
  Rejected because it would force `project easy` users back into a lower-level command family just to inspect their own launch result.

## Risks / Trade-offs

- [Atomic easy launch requires a refactor rather than a thin CLI callback] -> Accept the refactor so mailbox association can fail before session creation instead of after it.
- [`project easy` command shape changes from `specialist launch` to `instance launch`] -> Accept the move so the long-term CLI model stays consistent, and document the new noun boundary clearly in help text and docs.
- [`project easy instance stop` inherits current managed-agent stop semantics, including tmux cleanup behavior] -> Keep the wrapper thin for now, and defer any easy-specific `--keep-tmux` or stop-mode surface to a later change if operators need it.
- [The easy-layer `email` name differs from the current lower-level `stalwart` transport name] -> Document that `email` is a user-facing abstraction and keep provider-specific mapping internal until that path is implemented.
- [Pre-existing private mailbox directories may contain unreadable or partially-corrupt local state] -> Keep safe launch non-destructive, reuse readable state, and fail clearly when recovery would require destructive replacement.
- [Prompt-before-overwrite is incompatible with automation] -> Only prompt when a TTY is present and fail explicitly in non-interactive mode.
- [One physical private mailbox directory could be pointed at by multiple addresses] -> Add explicit path-uniqueness validation for active registrations.

## Migration Plan

1. Move easy launch to `project easy instance launch`, add `project easy instance stop` as a project-scoped wrapper over managed stop, and extend that runtime-oriented surface plus `project easy instance` inspection with the new mailbox-aware contract.
2. Refactor the easy launch path so mailbox-aware startup uses runtime-owned launch plumbing rather than a post-launch registration step.
3. Extend filesystem mailbox startup and registration helpers to support symlink-backed launch-time account preparation with the new validation rules.
4. Add regression coverage for conflict detection, private-dir validation, non-destructive preparation, and easy-instance mailbox reporting.
5. Leave the real-email easy-launch branch stubbed with an explicit not-implemented failure until a later change defines that transport's UX and runtime bindings.

Rollback risk is low because the change is additive at the CLI contract level and does not introduce a new persisted easy-instance format.

## Open Questions

- Should `project easy instance list` include the resolved mailbox directory directly, or should the full path remain visible only in `instance get`?
- Should a later follow-up add explicit easy-layer mail identity override flags for advanced cases where mailbox identity must differ from instance identity?
