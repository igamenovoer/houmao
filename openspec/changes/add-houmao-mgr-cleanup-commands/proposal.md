## Why

`houmao-mgr` currently exposes only one narrow cleanup path: `admin cleanup-registry`. Operators still have to manually infer which runtime session roots, build artifacts, logs, mailbox registrations, and mailbox credential artifacts are safe to delete, even though Houmao already has manifest-backed identity and ownership metadata to make those decisions more safely.

The missing cleanup surface is especially awkward inside a managed tmux session. Houmao already knows how to resolve the current session through `AGENTSYS_MANIFEST_PATH` and shared-registry fallback, but operators cannot reuse that authority to clean session-local artifacts without spelling explicit paths or removing files by hand.

## What Changes

- Add a Houmao-owned cleanup command family to `houmao-mgr` for stale registry state, runtime artifacts, and mailbox-related stale state.
- Add `--dry-run` support to cleanup commands so operators can inspect planned removals, preserved paths, and blocked actions before deletion.
- Add agent-scoped cleanup commands that default to current-session manifest authority when run inside the tmux session hosting the managed agent, unless an explicit selector or path override is provided.
- Extend registry cleanup to classify stale shared-registry entries using both existing freshness rules and optional local liveness checks for tmux-backed agents.
- Add mailbox cleanup support for no-longer-relevant local mailbox registrations and runtime-owned mailbox credential artifacts without treating canonical message history as disposable scratch.
- Update operator-facing cleanup documentation so runtime, registry, log, scratch, and mailbox cleanup boundaries are explicit.

## Capabilities

### New Capabilities
- `houmao-mgr-cleanup-cli`: Host-scoped and agent-scoped cleanup commands, dry-run planning, and manifest-first current-session target resolution for cleanup operations.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: The native `houmao-mgr` tree gains cleanup subcommands under the supported command families.
- `agent-discovery-registry`: Shared-registry cleanup gains dry-run reporting and optional liveness-aware stale classification for tmux-backed records.
- `houmao-mgr-mailbox-cli`: Local mailbox administration gains cleanup behavior for inactive or stashed mailbox registrations and related cleanup reporting without deleting canonical message content.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/admin.py`
  - `src/houmao/srv_ctrl/commands/agents/`
  - `src/houmao/srv_ctrl/commands/mailbox.py`
  - `src/houmao/agents/realm_controller/registry_storage.py`
- Affected systems:
  - runtime session roots under the effective runtime root
  - shared-registry `live_agents/` cleanup
  - local filesystem mailbox administration
  - current-session tmux metadata resolution
- Affected docs:
  - native CLI reference
  - registry cleanup operations docs
  - system-files cleanup guidance
