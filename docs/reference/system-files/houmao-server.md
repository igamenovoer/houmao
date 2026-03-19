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
| `<server-root>/sessions/<session-name>/registration.json` | `houmao-srv-ctrl launch` registration | registration updates | Delegated-launch registration payload | Stable v1 bridge artifact | Server-local view of delegated launch metadata |
| `<server-root>/child_cao/launcher.toml` | child manager | child manager | Generated child launcher config | Internal support artifact | Not a user-facing configuration contract |
| `<server-root>/child_cao/runtime/` | child manager | child CAO launcher/runtime | Hidden child CAO runtime root | Internal support path family | Contains child-owned support files |

## Ownership Boundary

Houmao owns the entire `<server-root>/` tree and the rule that maps one public listener to that tree.

Within that tree:

- `child_cao/` is internal Houmao-managed support state for the supervised child CAO process
- `run/` exposes operator-facing instance metadata
- `sessions/` exposes the v1 delegated-launch bridge

The server-owned live tracker is memory-primary:

- tracked-session registry entries are rebuilt from `sessions/<session-name>/registration.json`
- tmux/process probe results, parsed surfaces, stability timing, and recent transitions stay in server memory
- `/houmao/terminals/{terminal_id}/state` and `/houmao/terminals/{terminal_id}/history` read that in-memory authority directly

The detailed contents written under `child_cao/runtime/` are intentionally not treated as a public contract. They exist so the internal child CAO adapter can run.

## Related References

- [Houmao Server Pair](../houmao_server_pair.md)
- [System Files Reference](index.md)
- [Shared Registry](shared-registry.md)
- [CAO Server](cao-server.md)

## Source References

- [`src/houmao/server/config.py`](../../../src/houmao/server/config.py)
- [`src/houmao/server/child_cao.py`](../../../src/houmao/server/child_cao.py)
- [`src/houmao/server/service.py`](../../../src/houmao/server/service.py)
