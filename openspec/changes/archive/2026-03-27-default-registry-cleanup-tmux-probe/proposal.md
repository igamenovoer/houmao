## Why

`houmao-mgr admin cleanup registry` currently preserves lease-fresh records unless the operator explicitly opts into local tmux probing. In practice that keeps obviously dead local registry entries around after cleanup, which is surprising for a local maintenance command and makes the registry look healthier than the host actually is.

The operator expectation for this command is now clear: local registry cleanup should verify the owning tmux session by default and remove lease-fresh records whose local tmux authority is gone, while still allowing an explicit opt-out when the operator wants lease-only behavior.

## What Changes

- Change `houmao-mgr admin cleanup registry` so local tmux liveness probing is enabled by default for tmux-backed records.
- Add `--no-tmux-check` as the explicit opt-out flag for lease-only cleanup behavior.
- Keep `--dry-run` behavior unchanged so operators can preview tmux-probe-based removals before applying them.
- Update cleanup help text and operator-facing documentation to describe tmux probing as the default local cleanup contract.
- **BREAKING**: the default registry-cleanup behavior becomes stricter, and the old `--probe-local-tmux` opt-in flag is replaced by `--no-tmux-check`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-discovery-registry`: Registry cleanup changes from lease-only-by-default to tmux-probe-by-default for local cleanup of tmux-backed records.
- `houmao-srv-ctrl-native-cli`: The native `houmao-mgr admin cleanup registry` surface changes its default behavior and flag contract to use `--no-tmux-check` as the opt-out path.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/admin.py`
  - `src/houmao/agents/realm_controller/registry_storage.py`
- Affected behavior:
  - local cleanup of shared-registry `live_agents/` directories for tmux-backed records
  - CLI help and JSON payload reporting for registry cleanup
- Affected docs:
  - native CLI reference
  - registry cleanup operations docs
  - system-files cleanup guidance where registry cleanup expectations are described
