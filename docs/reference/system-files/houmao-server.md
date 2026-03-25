# Houmao Server

This page describes the filesystem layout owned by `houmao-server` for one public listener and how that layout is split between durable pair contracts, internal compatibility storage, and memory-primary live tracking.

## Server Layout

For one configured public base URL, `houmao-server` derives a stable root under the effective runtime root:

```text
<runtime-root>/houmao_servers/<host>-<port>/
  logs/
  run/
    current-instance.json
    houmao-server.pid
  state/
    cao_compat/
      registry.json
      launch_projection/
        <session-name>/
          <terminal-id>/
            context.md
    managed_agents/<tracked-agent-id>/
      authority.json
      active_turn.json
      turns/<turn-id>.json
  sessions/<session-name>/registration.json
```

There is no supported child `cao-server` subtree in this pair design.

## Artifact Inventory

| Path pattern | Created by | Later written by | Purpose | Contract level | Notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/houmao_servers/<host>-<port>/` | `houmao-server` config resolution | `houmao-server` | Stable per-public-listener root | Stable path family | Public listener identity drives the path |
| `<server-root>/logs/` | `houmao-server` startup | `houmao-server` | Log directory for server-owned artifacts | Stable placement | Log content is operational, not schema-stable |
| `<server-root>/run/current-instance.json` | `houmao-server` startup | `houmao-server` | Current live instance metadata | Stable operator-facing artifact | Compatibility/debug view of the live process |
| `<server-root>/run/houmao-server.pid` | `houmao-server` startup | `houmao-server` | Live pid file | Stable operator-facing artifact | Remove only after confirmed stop |
| `<server-root>/state/cao_compat/registry.json` | compatibility-core startup | compatibility core | Persisted CAO-compatible sessions, terminals, and inbox messages | Stable v1 compatibility artifact | Schema is Houmao-owned |
| `<server-root>/state/cao_compat/launch_projection/<session>/<terminal>/context.md` | compatibility launch | compatibility launch | Launch-scoped profile/context projection for providers that require sidecars | Internal support path family | Materialized from native selector resolution at launch time |
| `<server-root>/state/managed_agents/<tracked_agent_id>/authority.json` | native headless launch | `houmao-server` | Server-owned authority record for one managed headless agent | Stable v1 headless control-plane artifact | Stores tracked-agent identity, runtime manifest pointer, session root, tmux session name, and identity hints |
| `<server-root>/state/managed_agents/<tracked_agent_id>/active_turn.json` | first accepted headless turn | `houmao-server` | Active-turn admission and interrupt target for one managed headless agent | Stable v1 headless control-plane artifact | Restart reconciliation reads this before admitting a later turn |
| `<server-root>/state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json` | headless turn acceptance | `houmao-server` | Durable coarse per-turn server record | Stable v1 headless inspection artifact | Points at runtime-owned turn artifacts without copying them into server state |
| `<server-root>/sessions/<session-name>/registration.json` | server-backed session registration | registration updates | Server-backed managed-session registration payload | Stable v1 bridge artifact | Server-local view of runtime-owned session metadata |

## Ownership Boundary

Houmao owns the entire `<server-root>/` tree and the rule that maps one public listener to that tree.

Within that tree:

- `run/` exposes operator-facing instance metadata
- `sessions/` exposes the delegated-launch bridge
- `state/cao_compat/` exposes persisted compatibility control-plane state plus launch-scoped projection sidecars for `/cao/*`
- `state/managed_agents/` exposes native headless authority and restart-recovery state

The server-owned live tracker is memory-primary:

- tracked-session registry entries are rebuilt from `sessions/<session-name>/registration.json`
- tmux/process probe results, parsed surfaces, stability timing, and recent transitions stay in server memory
- `/houmao/terminals/{terminal_id}/state` and `/houmao/terminals/{terminal_id}/history` read that in-memory authority directly

For native headless agents, the server-owned control-plane truth is split cleanly:

- `state/managed_agents/<tracked_agent_id>/authority.json` identifies the managed headless session
- `state/managed_agents/<tracked_agent_id>/active_turn.json` gates single-active-turn semantics and best-effort interrupt targeting across restart
- `state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json` provides durable coarse per-turn inspection metadata
- runtime-owned turn artifacts remain under the runtime session root and are exposed through `/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/*`

Detailed contents under `state/cao_compat/launch_projection/` are intentionally not treated as a public contract. They exist so the internal compatibility control core can preserve the supported pair surface while launching from native selectors.

## Related References

- [Houmao Server Pair](../houmao_server_pair.md)
- [System Files Reference](index.md)
- [Shared Registry](shared-registry.md)
- [Legacy CAO Server Layout](cao-server.md)

## Source References

- [`src/houmao/server/config.py`](../../../src/houmao/server/config.py)
- [`src/houmao/server/service.py`](../../../src/houmao/server/service.py)
- [`src/houmao/server/control_core/core.py`](../../../src/houmao/server/control_core/core.py)
- [`src/houmao/server/control_core/provider_adapters.py`](../../../src/houmao/server/control_core/provider_adapters.py)
- [`src/houmao/server/managed_agents.py`](../../../src/houmao/server/managed_agents.py)
