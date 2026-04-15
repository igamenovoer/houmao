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

All four `runtime` subcommands accept the same shared `--runtime-root` option (project-aware default; falls back to `HOUMAO_GLOBAL_RUNTIME_DIR` or the active project overlay's runtime root when omitted). They each accept `--older-than-seconds` and `--dry-run`. Runtime session cleanup removes session envelopes only; it does not remove managed-agent memory roots under `<active-overlay>/memory/agents/<agent-id>/`.

#### `runtime sessions`

```
houmao-mgr admin cleanup runtime sessions [OPTIONS]
```

| Option | Description |
|---|---|
| `--runtime-root PATH` | Optional runtime root override. Defaults to the project-aware runtime root. |
| `--older-than-seconds INTEGER` | Only remove removable session envelopes older than this threshold. Default: `0`. Must be ≥ 0. |
| `--dry-run` | Preview removable session envelopes without deleting them. |

#### `runtime builds`

```
houmao-mgr admin cleanup runtime builds [OPTIONS]
```

| Option | Description |
|---|---|
| `--runtime-root PATH` | Optional runtime root override. Defaults to the project-aware runtime root. |
| `--older-than-seconds INTEGER` | Only remove unreferenced build artifacts older than this threshold. Default: `0`. Must be ≥ 0. |
| `--dry-run` | Preview removable build artifacts without deleting them. |

#### `runtime logs`

```
houmao-mgr admin cleanup runtime logs [OPTIONS]
```

| Option | Description |
|---|---|
| `--runtime-root PATH` | Optional runtime root override. Defaults to the project-aware runtime root. |
| `--older-than-seconds INTEGER` | Only remove runtime log artifacts older than this threshold. Default: `0`. Must be ≥ 0. |
| `--dry-run` | Preview removable runtime log artifacts without deleting them. |

#### `runtime mailbox-credentials`

```
houmao-mgr admin cleanup runtime mailbox-credentials [OPTIONS]
```

| Option | Description |
|---|---|
| `--runtime-root PATH` | Optional runtime root override. Defaults to the project-aware runtime root. |
| `--older-than-seconds INTEGER` | Only remove unreferenced credential files older than this threshold. Default: `0`. Must be ≥ 0. |
| `--dry-run` | Preview removable credential files without deleting them. |

In plain and fancy output modes, populated cleanup buckets are rendered line by line so operators can see the exact artifacts and reasons without switching to JSON. Use `--print-json` when you need the full machine-readable cleanup payload.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
