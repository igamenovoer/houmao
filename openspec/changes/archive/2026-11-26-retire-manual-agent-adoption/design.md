# Design

## Context

[Proposal](proposal.md) defines the cutoff. The current adoption command builds an ordinary managed runtime envelope around an existing provider process. It uses the normal backend and registry types. The v6 manifest records the distinction in `agent_launch_authority.session_origin` and repeats the marker in launch-plan metadata. It also retains adopted launch options and the captured terminal binding. [Adoption materialization](../../../src/houmao/srv_ctrl/commands/runtime_artifacts.py)

The normal manifest loader validates v6 before owner reconstruction. Some consumers deliberately recover from missing or unreadable manifests using registry and terminal evidence. For example, manager recovery can stop a degraded terminal. Bulk session cleanup marks an unparseable envelope as non-live and considers it removable. A generic validation failure at the loader would send a retired record into those paths. [Manifest authority](../../../src/houmao/agents/realm_controller/manifest.py) [Manager recovery](../../../src/houmao/srv_ctrl/commands/managed_agents.py) [Runtime cleanup](../../../src/houmao/srv_ctrl/commands/runtime_cleanup.py)

## Goals / Non-Goals

**Goals**

- Identify a retired origin consistently before any path grants active runtime authority.
- Keep native v6 manifests valid through the upgrade, including the explicit null fields emitted by current writers.
- Remove the adoption-specific launch and resume rules before sharing TUI observation code.

**Non-Goals**

- In-place conversion or transfer of an adopted provider conversation into a Houmao-launched runtime.
- Automatic teardown, release, or cleanup of manual provider processes and artifacts.
- A new manifest version or a broader runtime capability refactor.

## Decisions

### Recognize Retirement at the Manifest Boundary

Classify the saved `joined_tmux` marker at the manifest boundary, before validating or reconstructing a native runtime. Check saved launch metadata for the same marker so a partially written or inconsistent adoption envelope cannot be interpreted as a native launch. Expose retirement as a distinct outcome that callers can preserve through fallback handling. Backend, run mode, tmux liveness, and the registry's ordinary owner fields occur in native records too. A path convention is a locator and cannot establish origin or ownership. [Runtime manifest requirement](specs/brain-launch-runtime/spec.md)

A single rejection at manifest load covers normal resume. Callers that otherwise treat errors as a cache miss need to carry retirement explicitly. Local selectors and stopped-runtime fallback must refuse a selected retired owner. Inventory scans must continue processing other records. A read-only view may expose an inert address where its contract supports offline entries. Any active presentation, cached endpoint, managed relaunch claim, gateway admission, or passive relay requires supported runtime authority.

### Keep Native v6 Compatibility

Preserve the v6 schema identifier and accept explicit null or omitted adoption fields for native records. Current manifest writers serialize optional null fields, including in ordinary native tmux records. Deleting those fields from the strict parser would invalidate records unrelated to adoption. Keep any compatibility handling limited to the persisted schema boundary. Remove joined launch reconstruction, inherited adoption env bindings, and adopted-window selection from managed resume and relaunch. Native terminal handoff, gateway attachment, and native headless latest or exact chat continuation keep their existing paths. [Manifest serialization](../../../src/houmao/agents/realm_controller/manifest.py) [Headless continuation](../../../src/houmao/agents/realm_controller/backends/headless_base.py)

### Fence Fallback and Cleanup Before Removing Adoption Code

Keep the retired outcome visible where callers currently fall back to raw registry or tmux data. Guard local stop and relaunch, selected cleanup including registry purge, runtime-root scans, gateway bootstrap from derived state, and passive discovery and routing. A degraded pane or a missing registry record does not establish that the manual runtime is safe to mutate. Bulk cleanup should report the envelope as preserved without treating retirement as general proof that it is stopped. Keep diagnostics and historical files available without reopening prompt admission, polling mailbox contents, or advertising usable gateway coordinates.

Apply the runtime rejection and fallback guards before deleting the specialized adopted execution paths. Remove the public CLI and packaged skill entrypoints in the same change, along with the sole materializer, the managed-join install lane, and obsolete product guidance. This ordering lets tests establish the cutoff using saved fixtures before the old writer disappears. Merge the change before starting shared TUI observation work in `refactor-managed-runtime-boundaries`.

## Risks / Trade-offs

- Fallback could grant ownership from a live tmux name or derived gateway artifact. Verify retirement before managed fallback or mutation, and use fixtures with valid-looking registry and attach pointers.
- Bulk cleanup could discard a retired envelope when no registry record is present. Preserve retired outcomes in the runtime-root scan and test dry-run and applied cleanup against adjacent ordinary stale envelopes.
- A schema simplification could reject still-supported native v6 records. Verify loading and writing native manifests with both explicit nulls and omitted adoption fields, and keep the packaged schema aligned with the reader.
- A gateway or worker started by the owning release can outlive installation of the new release. Treat the cutover as an operator transition across running versions.

## Migration Plan

1. Identify existing adopted sessions and their live gateways using the owning release. Use that release to wind down Houmao control before upgrading. Operators who keep a manually started provider running retain its process and files outside managed control.
2. Upgrade manager and passive server together. The new release declines management of saved adopted instances and leaves their artifacts in place. Use a supported managed launch when managed control is required.
3. If the operator needs to wind down an adoption after upgrading, use the owning release for that operation. The cutoff leaves prior artifacts intact. Native v6 records continue through the normal supported path.
