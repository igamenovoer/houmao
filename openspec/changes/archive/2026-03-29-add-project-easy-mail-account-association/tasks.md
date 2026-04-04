## 1. Extend The Easy Launch Surface

- [x] 1.1 Move easy launch from `project easy specialist launch` to `project easy instance launch`, with required `--specialist` and `--name` inputs so `specialist` stays config-only and `instance` owns runtime lifecycle actions.
- [x] 1.2 Add `project easy instance launch` mailbox flags for `--mail-transport`, required filesystem `--mail-root`, and optional filesystem `--mail-account-dir`.
- [x] 1.3 Make `--mail-transport email` fail fast with a clear not-implemented error before managed-agent startup begins.
- [x] 1.4 Refactor the easy launch path to use shared internal runtime launch plumbing instead of chaining the existing CLI callback so mailbox-enabled launch stays atomic.
- [x] 1.5 Add `project easy instance stop` as a project-scoped wrapper over the existing managed-agent stop path, including current-overlay ownership validation before delegation.

## 2. Carry Filesystem Mailbox Targeting Through Runtime Startup

- [x] 2.1 Extend the resolved filesystem mailbox configuration and persisted session manifest to preserve mailbox kind plus concrete mailbox directory for in-root versus symlink-backed startup.
- [x] 2.2 Update filesystem mailbox startup bootstrap to create or confirm the selected registration shape and to reject explicit private mailbox directories that resolve inside the shared mailbox root.
- [x] 2.3 Ensure session resume restores the same filesystem mailbox binding shape and mailbox env projection from the persisted manifest data.

## 3. Harden Symlink-Backed Mailbox Registration

- [x] 3.1 Extend managed filesystem mailbox registration checks so safe symlink-backed registration reuses same-target bindings idempotently and fails on real-directory or different-target occupancy at the address slot.
- [x] 3.2 Reject attempts to reuse one concrete private mailbox directory for multiple active mailbox addresses.
- [x] 3.3 Replace destructive safe-adoption behavior for pre-existing private mailbox directories with non-destructive preparation that creates missing placeholder directories and preserves existing mailbox-local SQLite state.
- [x] 3.4 Add overwrite-confirmation handling for any remaining managed-file replacement during private-dir preparation, and fail clearly when confirmation is required but no interactive TTY is available.

## 4. Expose Mailbox Association In Easy Instance Views

- [x] 4.1 Publish runtime-derived mailbox summary data needed by `project easy instance list|get`, including transport, mailbox address, mailbox root, mailbox kind, and concrete mailbox directory.
- [x] 4.2 Update `project easy instance` rendering so mailbox-bound instances display that mailbox summary without introducing a second persisted easy-instance config format.
- [x] 4.3 Update help text and operator-facing documentation so `specialist` is presented as configuration-only and `instance` as the launch/stop/runtime surface.

## 5. Verify And Document The Change

- [x] 5.1 Add `project easy` command tests covering `instance launch`, `instance stop`, required `--specialist` plus `--name` validation, filesystem in-root launch, symlink-backed private-dir launch, overlay ownership checks for stop, and the `email` not-implemented failure path.
- [x] 5.2 Add runtime and mailbox lifecycle tests covering private-dir-inside-root rejection, conflicting existing mailbox entries, duplicate private-dir reuse across addresses, and non-destructive adoption of an existing non-empty private mailbox directory.
- [x] 5.3 Add `project easy instance` tests covering mailbox summary reporting from runtime-derived state.
- [x] 5.4 Update the relevant CLI and mailbox documentation to describe the new easy-launch mailbox options, the current `email` stub behavior, and the filesystem private-dir conflict rules.
