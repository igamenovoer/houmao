# houmao-mgr admin cleanup

Grouped local cleanup commands for registry and runtime maintenance.

```
houmao-mgr admin cleanup [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `registry`

Clean stale shared-registry live-agent directories on the local host.

```
houmao-mgr admin cleanup registry [OPTIONS]
```

| Option | Description |
|---|---|
| `--grace-seconds INTEGER` | Extra grace period after lease expiry before removing stale directories. Default: `300`. Must be ≥ 0. |
| `--dry-run` | Preview stale shared-registry records without deleting them. |
| `--no-tmux-check` | Disable local tmux liveness checks for tmux-backed records; by default cleanup verifies the owning tmux session locally. |

### `runtime`

Host-scoped cleanup of runtime-owned local artifacts.

```
houmao-mgr admin cleanup runtime [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `sessions` | Clean stopped or malformed runtime session envelopes. |
| `builds` | Clean unreferenced or broken build manifest-home directories. |
| `logs` | Clean log-style runtime artifacts while preserving active sessions. |
| `mailbox-credentials` | Clean unreferenced runtime-owned Stalwart credential material. |

The compatibility alias `houmao-mgr admin cleanup-registry` remains available for the registry-only command.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
