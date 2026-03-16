# CAO Server

This page explains the filesystem layout that Houmao owns for standalone `cao-server` launch management and the adjacent CAO `HOME` subtree that Houmao may select but does not own internally.

## Launcher Layout

For one configured base URL, the launcher derives a per-server subtree under the effective runtime root:

```text
<runtime-root>/cao_servers/<host>-<port>/
  launcher/
    cao-server.pid
    cao-server.log
    ownership.json
    launcher_result.json
  home/                      # only when launcher config omits explicit home_dir
```

If launcher config provides an explicit `home_dir`, the `home/` sibling is not used and CAO instead receives the configured absolute directory as `HOME`.

## Artifact Inventory

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/cao_servers/<host>-<port>/` | launcher path resolution | launcher and CAO | Stable per-server root for one loopback base URL | Stable path family | Do not delete while the server is managed |
| `<server-root>/launcher/` | launcher | launcher | Houmao-owned launcher artifact directory | Stable path family | Durable while the launcher owns the service |
| `<server-root>/launcher/cao-server.pid` | launcher | launcher | Pidfile for the tracked `cao-server` process | Stable operator-facing artifact | Remove only after confirmed stop |
| `<server-root>/launcher/cao-server.log` | launcher-spawned process | running `cao-server` process | Process stdout/stderr log sink | Stable placement, log-style contents | Log cleanup only after stop |
| `<server-root>/launcher/ownership.json` | launcher | launcher on refresh/start/stop | Structured ownership metadata for the tracked process | Stable operator-facing artifact | Durable while the launcher owns the service |
| `<server-root>/launcher/launcher_result.json` | launcher | launcher on command completion | Most recent structured launcher result payload | Stable operator-facing artifact | Durable command result cache |
| `<server-root>/home/` when derived | launcher | CAO | Default `HOME` root selected by Houmao for CAO when config omits `home_dir` | Stable placement, opaque CAO-owned contents | Not scratch unless the operator explicitly treats that whole CAO profile as disposable |

## Houmao-Owned Versus CAO-Owned

Houmao owns the launcher subtree and the placement rule for the derived `home/` sibling. CAO owns the detailed contents it writes under the selected home, including:

```text
<home-dir>/.aws/cli-agent-orchestrator/
```

That CAO-owned subtree is intentionally not documented here file by file. The stable contract from Houmao’s side is:

- which directory is selected as `HOME`,
- that the directory must exist and be writable when configured explicitly,
- that CAO state is expected to appear underneath that home.

## Current Placement Notes

- The launcher root is derived from `<host>-<port>` under `cao_servers/`, not from the older `cao-server/` directory name.
- The older `runtime_root/cao-server/<host>-<port>/` layout is a legacy cleanup case rather than a compatibility path.
- Launcher `runtime_root` follows the same root-resolution rules documented in [Roots And Ownership](roots-and-ownership.md).

## Related References

- [CAO Server Launcher](../cao_server_launcher.md): Launcher CLI, health semantics, proxy policy, and command behavior.
- [Operator Preparation](operator-preparation.md): Writable-path, relocation, and cleanup guidance for launcher-managed CAO roots.

## Source References

- [`src/houmao/cao/server_launcher.py`](../../../src/houmao/cao/server_launcher.py)
- [`tests/unit/cao/test_server_launcher.py`](../../../tests/unit/cao/test_server_launcher.py)
