## Why

The initial central agent registry change established the shared discovery model, but implementation review found several contract and runtime gaps that would make the registry brittle in real recovery flows. We need a focused hardening change so the shared registry behaves like a resilient secondary locator layer instead of introducing new failure paths into primary session control.

## What Changes

- Broaden name-based runtime resolution so shared-registry fallback applies not only when a tmux session is missing, but also when tmux-local discovery pointers such as `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_DEF_DIR` are missing or stale.
- Treat malformed shared-registry records as unusable or stale during resolution instead of aborting lookup, while keeping strict validation for diagnostics and cleanup behavior.
- Tighten the live-agent registry timestamp contract so persisted `published_at` and `lease_expires_at` values must be timezone-aware.
- Isolate shared-registry publication and teardown failures from otherwise successful prompt, control, mailbox-refresh, and stop flows, while preserving the existing runtime-owned publication hooks.
- Harden registry storage behavior by cleaning up orphaned temp files after failed atomic writes and by allowing stale-record cleanup to continue past per-directory removal failures with explicit reporting.
- Update tests and operator-facing docs to pin the refined fallback, freshness, cleanup, and error-isolation behavior.

## Capabilities

### New Capabilities

- `agent-discovery-registry`: Hardened shared-registry resolution, freshness validation, and cleanup semantics for live-agent discovery across runtime roots.

### Modified Capabilities

- `brain-launch-runtime`: Name-based tmux-backed session control changes so registry-backed recovery covers unavailable tmux-local discovery pointers and registry-side publication or cleanup failures do not incorrectly fail primary runtime actions.

## Impact

- Affected code: `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, registry-related CLI reporting, and targeted unit/integration tests.
- Affected systems: tmux-backed runtime session recovery, shared live-agent registry lookup, lease freshness validation, and stale-registry cleanup operations.
- Dependencies: no new external dependency is required; the change should reuse the existing registry storage, manifest validation, and runtime lifecycle integration surfaces.
