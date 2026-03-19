## Why

The `add-houmao-server-official-tui-tracker` implementation established the right server-owned watch architecture, but review of the shipped code found several hardening gaps in the registration and worker lifecycle paths. Those gaps can let registration escape the server-owned `sessions/` root, let one unexpected exception permanently stop background tracking, keep dead tracked sessions queryable after tmux exits, and watch the wrong pane immediately after registration because tmux window identity is dropped.

These are not cosmetic issues. They weaken the server's trust boundary and make the "continuous background tracking of live known sessions" contract less reliable than the change artifacts claim.

## What Changes

- Tighten the `houmao-server` registration contract so server-owned registration paths remain contained under the configured `sessions/` root and invalid session identifiers are rejected before any filesystem write or delete.
- Harden the TUI tracking supervisor and per-session worker lifecycle so unexpected runtime exceptions do not permanently disable continuous background tracking.
- Align tracker eviction with live known-session authority so sessions removed from the live registry or lost from tmux no longer remain indefinitely queryable only from stale in-memory aliases and trackers.
- Preserve tracked pane identity across registration, including tmux window metadata when available, so the first live tracking cycles do not fall back to whichever pane happens to be active.
- Add verification for the hardening cases above, including invalid registration identifiers, worker and supervisor exception handling, live-session eviction on tmux loss, and registration-to-pane resolution fidelity.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `houmao-server`: strengthen server-owned registration safety, continuous worker resilience, live-session eviction semantics, and registration-derived tracked-pane identity

## Impact

- `src/houmao/server/models.py`
- `src/houmao/server/app.py`
- `src/houmao/server/service.py`
- `src/houmao/server/tui/supervisor.py`
- `src/houmao/server/tui/registry.py`
- `src/houmao/server/tui/transport.py`
- unit coverage under `tests/unit/server/`
- follow-up alignment with `openspec/changes/add-houmao-server-official-tui-tracker/`
