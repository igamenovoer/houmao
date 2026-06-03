# Retired Houmao Server Filesystem Notes

This page is historical/internal reference for state shapes left by the retired standalone `houmao-server` surface. The current package no longer installs a `houmao-server` executable. Use `houmao-mgr` for local workflows and `houmao-passive-server` for the maintained server/API authority.

Some Python modules under `src/houmao/server/` remain as internal support for maintained manager and passive-server code. Retaining those modules does not make the old executable, `/cao/*` namespace, or old route contract a supported operator workflow.

## Server Layout

Historical old-server listener state used a stable root under the effective runtime root:

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
| `<runtime-root>/houmao_servers/<host>-<port>/` | retired old-server config resolution | retired old-server modules | Historical per-listener root | Legacy path family | Passive-server also uses the `houmao_servers/<host>-<port>/` family for its maintained listener metadata. |
| `<server-root>/logs/` | retired old-server startup | retired old-server modules | Log directory for old-server artifacts | Historical placement | Log content is operational, not schema-stable. |
| `<server-root>/run/current-instance.json` | retired old-server startup | retired old-server modules | Historical live instance metadata | Legacy debug artifact | Current maintained instance metadata is documented on passive-server. |
| `<server-root>/run/houmao-server.pid` | retired old-server startup | retired old-server modules | Historical live pid file | Legacy debug artifact | New workflows do not create this pid file. |
| `<server-root>/state/cao_compat/registry.json` | compatibility-core startup | compatibility core | Persisted CAO-compatible sessions, terminals, and inbox messages | Stable v1 compatibility artifact | Schema is Houmao-owned |
| `<server-root>/state/cao_compat/launch_projection/<session>/<terminal>/context.md` | compatibility launch | compatibility launch | Launch-scoped profile/context projection for providers that require sidecars | Internal support path family | Materialized from native selector resolution at launch time |
| `<server-root>/state/managed_agents/<tracked_agent_id>/authority.json` | old native headless launch | passive-server or retained internal modules | Authority record for one managed headless agent | Internal/shared shape | Maintained headless ownership is through passive-server. |
| `<server-root>/state/managed_agents/<tracked_agent_id>/active_turn.json` | first accepted old headless turn | passive-server or retained internal modules | Active-turn admission and interrupt target | Internal/shared shape | Passive-server is the maintained restart-reconciliation authority. |
| `<server-root>/state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json` | old headless turn acceptance | passive-server or retained internal modules | Durable coarse per-turn record | Internal/shared shape | Points at runtime-owned turn artifacts without copying them into server state. |
| `<server-root>/sessions/<session-name>/registration.json` | server-backed session registration | registration updates | Server-backed managed-session registration payload | Stable v1 bridge artifact | Server-local view of runtime-owned session metadata |

## Ownership Boundary

Retired old-server code owned the entire `<server-root>/` tree and the rule that mapped one public listener to that tree. Current maintained server/API behavior is owned by `houmao-passive-server`.

Within that tree:

- `run/` exposes operator-facing instance metadata
- `sessions/` exposes the delegated-launch bridge
- `state/cao_compat/` exposes persisted compatibility control-plane state plus launch-scoped projection sidecars for the retired `/cao/*` namespace
- `state/managed_agents/` contains headless authority and restart-recovery shapes now maintained through passive-server when used

The retired old-server live tracker was memory-primary:

- tracked-session registry entries are rebuilt from `sessions/<session-name>/registration.json`
- tmux/process probe results, parsed surfaces, stability timing, and recent transitions stay in server memory
- historical terminal state routes read that in-memory authority directly

For native headless agents, the retained internal control-plane truth is split cleanly:

- `state/managed_agents/<tracked_agent_id>/authority.json` identifies the managed headless session
- `state/managed_agents/<tracked_agent_id>/active_turn.json` gates single-active-turn semantics and best-effort interrupt targeting across restart
- `state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json` provides durable coarse per-turn inspection metadata
- runtime-owned turn artifacts remain under the runtime session root and are exposed through maintained passive-server turn artifact routes

Detailed contents under `state/cao_compat/launch_projection/` are intentionally not treated as a public contract. They exist only so retained internal compatibility code can recognize or clean old artifacts.

## Related References

- [Passive Server API](../cli/houmao-passive-server.md)
- [System Files Reference](index.md)
- [Shared Registry](shared-registry.md)
- [Legacy CAO Server Layout](cao-server.md)

## Source References

- [`src/houmao/server/config.py`](../../../src/houmao/server/config.py)
- [`src/houmao/server/service.py`](../../../src/houmao/server/service.py)
- [`src/houmao/server/control_core/core.py`](../../../src/houmao/server/control_core/core.py)
- [`src/houmao/server/control_core/provider_adapters.py`](../../../src/houmao/server/control_core/provider_adapters.py)
- [`src/houmao/server/managed_agents.py`](../../../src/houmao/server/managed_agents.py)
