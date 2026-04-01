## Why

The project-aware roots work is implemented, but several maintained CLI help strings, error messages, and JSON-facing status/details still describe older shared-root or "discovered overlay" behavior. That leaves operators and automation with inconsistent guidance about which root was selected, when a command stayed non-creating, and when Houmao implicitly bootstrapped an overlay.

## What Changes

- Refresh maintained operator-facing help text across project, launch, mailbox, cleanup, and server surfaces so they describe selected overlay roots and overlay-local defaults consistently.
- Refresh maintained project and project-easy failure text so non-creating commands explain the selected or would-bootstrap overlay clearly instead of using stale "discovered project overlay" wording.
- Refresh maintained success and JSON-facing payload wording where project-aware flows can implicitly bootstrap or select overlay-local runtime or mailbox roots, so operators can tell what happened without inferring it from filesystem state.
- Keep legacy compatibility entrypoints, archived demos, and historical docs out of scope for this wording pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Align build and launch result wording with overlay-local runtime and jobs defaults plus implicit bootstrap notices.
- `houmao-mgr-cleanup-cli`: Align runtime-cleanup help text and result wording with active project runtime roots versus explicit overrides.
- `houmao-mgr-mailbox-cli`: Align generic mailbox help and root-resolution wording with active project mailbox roots versus explicit shared roots.
- `houmao-mgr-project-cli`: Align selected-overlay, non-creating failure, and implicit-bootstrap wording for project status and project-agent flows.
- `houmao-mgr-project-easy-cli`: Align easy specialist and instance inspection or stop wording with the selected-overlay, non-creating contract.
- `houmao-mgr-project-mailbox-cli`: Align project-mailbox help and failure wording with the selected overlay mailbox root rather than a hard-coded local `.houmao/mailbox` path.
- `houmao-mgr-server-group`: Align server runtime-root help and startup or status wording with active project runtime-root defaults.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/admin.py`, `src/houmao/srv_ctrl/commands/brains.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/runtime_artifacts.py`, `src/houmao/server/commands/common.py`, `src/houmao/passive_server/cli.py`, and related shared render/output helpers.
- Affected APIs: operator-facing CLI help text, `ClickException` message text, and maintained JSON payload wording for the touched command families.
- Affected tests: focused CLI and payload assertions for project, mailbox, cleanup, launch, and server command surfaces.
