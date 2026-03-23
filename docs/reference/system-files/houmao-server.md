# Houmao Server

This page describes the filesystem layout owned by `houmao-server` for one public listener and how that layout is split between durable contracts, internal child-CAO support state, and memory-primary live tracking.

## Server Layout

For one configured public base URL, `houmao-server` derives a stable root under the effective runtime root:

```text
<runtime-root>/houmao_servers/<host>-<port>/
  logs/
  run/
    current-instance.json
    houmao-server.pid
  state/
    managed_agents/<tracked-agent-id>/
      authority.json
      active_turn.json
      turns/<turn-id>.json
  sessions/<session-name>/registration.json
  child_cao/
    launcher.toml
    runtime/
```

The child CAO endpoint remains internal. Its port is always derived as `public_port + 1`.

## Artifact Inventory

| Path pattern | Created by | Later written by | Purpose | Contract level | Notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/houmao_servers/<host>-<port>/` | `houmao-server` config resolution | `houmao-server` | Stable per-public-listener root | Stable path family | Public listener identity drives the path |
| `<server-root>/logs/` | `houmao-server` startup | `houmao-server` and child CAO runtime helpers | Log directory for server-owned artifacts | Stable placement | Log content is operational, not schema-stable |
| `<server-root>/run/current-instance.json` | `houmao-server` startup | `houmao-server` | Current live instance metadata | Stable operator-facing artifact | Compatibility/debug view of the live process |
| `<server-root>/run/houmao-server.pid` | `houmao-server` startup | `houmao-server` | Live pid file | Stable operator-facing artifact | Remove only after confirmed stop |
| `<server-root>/state/managed_agents/<tracked_agent_id>/authority.json` | native headless launch | `houmao-server` | Server-owned authority record for one managed headless agent | Stable v1 headless control-plane artifact | Stores tracked-agent identity, runtime manifest pointer, session root, tmux session name, and identity hints |
| `<server-root>/state/managed_agents/<tracked_agent_id>/active_turn.json` | first accepted headless turn | `houmao-server` | Active-turn admission and interrupt target for one managed headless agent | Stable v1 headless control-plane artifact | Restart reconciliation reads this before admitting a later turn |
| `<server-root>/state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json` | headless turn acceptance | `houmao-server` | Durable coarse per-turn server record | Stable v1 headless inspection artifact | Points at runtime-owned turn artifacts without copying them into server state |
| `<server-root>/sessions/<session-name>/registration.json` | `houmao-srv-ctrl launch` registration | registration updates | Delegated-launch registration payload | Stable v1 bridge artifact | Server-local view of delegated launch metadata |
| `<server-root>/child_cao/launcher.toml` | child manager | child manager | Generated child launcher config | Internal support artifact | Not a user-facing configuration contract |
| `<server-root>/child_cao/runtime/` | child manager | child CAO launcher/runtime | Hidden child CAO runtime root | Internal support path family | Contains child-owned support files |

## Ownership Boundary

Houmao owns the entire `<server-root>/` tree and the rule that maps one public listener to that tree.

Within that tree:

- `child_cao/` is internal Houmao-managed support state for the supervised child CAO process
- `run/` exposes operator-facing instance metadata
- `sessions/` exposes the v1 delegated-launch bridge
- `state/managed_agents/` exposes the native headless authority and restart-recovery bridge

The server-owned live tracker is memory-primary:

- tracked-session registry entries are rebuilt from `sessions/<session-name>/registration.json`
- tmux/process probe results, parsed surfaces, stability timing, and recent transitions stay in server memory
- `/houmao/terminals/{terminal_id}/state` and `/houmao/terminals/{terminal_id}/history` read that in-memory authority directly

The watch-plane implementation for that memory-primary tracker now lives in the dedicated `src/houmao/server/tui/` module family. The filesystem contract stays under `<server-root>/sessions/`, while the reducer host, worker lifecycle, probe/parse adapters, and tracker assembly remain process memory concerns rather than persisted server artifacts.

For native headless agents, the server-owned control-plane truth is split cleanly:

- `state/managed_agents/<tracked_agent_id>/authority.json` identifies the managed headless session
- `state/managed_agents/<tracked_agent_id>/active_turn.json` gates single-active-turn semantics and best-effort interrupt targeting across restart
- `state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json` provides durable coarse per-turn inspection metadata
- runtime-owned turn artifacts remain under the runtime session root and are exposed through `/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/*`

The shared `/houmao/agents/{agent_ref}/history` route is intentionally bounded and coarse. Durable headless detail lives on the per-turn routes and their artifact pointers instead of being duplicated into a second append-only server history store.

The detailed contents written under `child_cao/runtime/` are intentionally not treated as a public contract. They exist so the internal child CAO adapter can run.

## Related References

- [Houmao Server Pair](../houmao_server_pair.md)
- [System Files Reference](index.md)
- [Shared Registry](shared-registry.md)
- [CAO Server](cao-server.md)

## Source References

- [`src/houmao/server/config.py`](../../../src/houmao/server/config.py)
- [`src/houmao/server/child_cao.py`](../../../src/houmao/server/child_cao.py)
- [`src/houmao/server/managed_agents.py`](../../../src/houmao/server/managed_agents.py)
- [`src/houmao/server/service.py`](../../../src/houmao/server/service.py)
