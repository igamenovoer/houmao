## Why

`houmao-mgr project easy` currently mixes one runtime action into the `specialist` group: `specialist launch` starts a managed instance from a compiled specialist. That shape is workable, but it blurs the intended boundary between reusable specialist configuration and concrete runtime instances. At the same time, the current launch surface has no way to associate the launched instance with a mailbox account at the same seam. Operators who want per-instance mailbox ownership must fall back to lower-level mailbox workflows after launch, and the higher-level `project easy` UX cannot express the important distinction between an in-root filesystem mailbox account and a private mailbox directory symlinked into the shared root.

This is the right time to close that gap because the `project easy` surface is still being refined, the mailbox stack already has filesystem registration and symlink-backed mailbox concepts, and deferring instance-level mailbox association will keep pushing ordinary users down into lower-level command families that `project easy` was meant to hide.

## What Changes

- Move easy launch from `houmao-mgr project easy specialist launch` to `houmao-mgr project easy instance launch` so the `specialist` group stays configuration-oriented and the `instance` group owns runtime lifecycle actions.
- Add `houmao-mgr project easy instance stop` as a project-scoped wrapper over the existing managed-agent stop path so operators can stay within the `instance` lifecycle surface.
- Extend `houmao-mgr project easy instance launch` with explicit mail-account association inputs for launch-time instance setup.
- Add a high-level mail transport choice for easy launch that distinguishes filesystem-backed mail accounts from future real email-backed accounts.
- Support filesystem-backed easy launch against a required mailbox root, with optional private mailbox-directory targeting that materializes as a symlink-backed mailbox registration under the shared root.
- Define filesystem validation and conflict rules for launch-time account association, including rejection when the requested private mailbox directory resolves inside the mailbox root, reuse for matching existing bindings, and explicit failure for conflicting existing mailbox entries.
- Define safe handling for pre-existing private mailbox directories so the runtime can create the required mailbox structure without silently clobbering mailbox-local state.
- Reserve the high-level real-email launch path in `project easy`, but make that branch fail fast as not implemented in this change instead of surfacing transport-specific server configuration there.
- Expose the effective mailbox association in the `project easy instance` view so operators can see which launched instance is bound to which mailbox transport and filesystem mailbox location.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: `project easy instance launch` becomes the runtime launch surface for specialists, `project easy instance stop` wraps the canonical managed-agent stop path, launch gains launch-time mail-account association behavior, and `project easy instance` reports the resulting mailbox association.
- `brain-launch-runtime`: runtime mailbox startup must support easy-launch filesystem mailbox association that can target either an in-root mailbox entry or a symlink-backed private mailbox directory.
- `agent-mailbox-registration-lifecycle`: filesystem mailbox registration rules gain the launch-time validation and conflict-handling requirements for private mailbox directories used as symlink targets.

## Impact

- Affected code:
  `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/mailbox_runtime_support.py`, and filesystem mailbox lifecycle helpers under `src/houmao/mailbox/`.
- Affected tests:
  project easy command coverage, including `instance stop`, runtime mailbox startup tests, and filesystem mailbox registration tests for symlink-backed directories and conflict cases.
- Affected operator surfaces:
  `houmao-mgr project easy instance launch|stop|list|get`.
- Affected persisted/runtime-visible state:
  managed-session manifests, live mailbox env bindings, and shared filesystem mailbox registrations.
- Dependencies and systems:
  project-overlay easy workflows, filesystem mailbox registration lifecycle, runtime mailbox bootstrap ordering, and the existing mailbox transport abstraction.
