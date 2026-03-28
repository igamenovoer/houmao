# Roots And Ownership

This page explains where Houmao places its major filesystem roots, how override precedence works, and how to distinguish Houmao-owned paths from paths that Houmao only selects for another tool.

## Mental Model

Houmao uses one consistent precedence rule for its shared roots:

1. explicit override first,
2. environment override second,
3. built-in default last.

Current implementation detail that matters operationally: explicit overrides may be relative and are resolved from the caller-specific base directory, while environment overrides must be absolute paths.

There are now three different `.houmao` anchors to keep straight:

- `~/.houmao/` is the per-user shared Houmao home anchor for durable runtime, registry, and mailbox roots.
- `<repo>/.houmao/` is an optional repo-local project overlay created by `houmao-mgr project init`.
- `<working-directory>/.houmao/jobs/` is the workspace-local scratch root for per-session job output. If the working directory is also a project root, that scratch subtree lives under the same hidden `.houmao/` overlay but keeps a separate contract.

## Ownership Categories

| Category | Meaning | Examples |
| --- | --- | --- |
| Houmao-owned | Houmao creates the path family and owns the persisted contract for its contents. | Runtime session manifests, shared-registry `record.json`, launcher `ownership.json` |
| Houmao-selected | Houmao chooses the root path, but another tool owns the detailed contents under that root. | CAO `HOME` when launcher config omits `home_dir` |
| Repo-local project overlay | Houmao creates or discovers local operator state under one repo-local `.houmao/` root. | `.houmao/houmao-config.toml`, `.houmao/agents/tools/<tool>/auth/<name>/` |
| Workspace-local scratch | Houmao creates the path under the selected working directory for destructive or session-local work. | `<working-directory>/.houmao/jobs/<session-id>/` |

## Root Families

| Surface | Default path | Current override surfaces | Ownership | Contract level |
| --- | --- | --- | --- | --- |
| Houmao home anchor | `~/.houmao` | none as a first-class operator surface | Houmao-owned | Stable anchor derived from a platformdirs-aware home lookup |
| Project-local overlay | `<project-root>/.houmao` when initialized | nearest-ancestor `.houmao/houmao-config.toml`; explicit `--agent-def-dir` and `AGENTSYS_AGENT_DEF_DIR` still outrank discovery for agent-definition resolution | Repo-local project overlay | Stable local operator workflow |
| Runtime root | `~/.houmao/runtime` | explicit CLI/API/config override where supported, then `AGENTSYS_GLOBAL_RUNTIME_DIR` | Houmao-owned | Stable root family |
| Registry root | `~/.houmao/registry` | current operator-facing override `AGENTSYS_GLOBAL_REGISTRY_DIR` | Houmao-owned | Stable root family |
| Local jobs root | `<working-directory>/.houmao/jobs` | `AGENTSYS_LOCAL_JOBS_DIR` before default derivation | Workspace-local scratch | Stable root family |
| Launcher-selected CAO home | `<runtime-root>/cao_servers/<host>-<port>/home/` when `home_dir` is omitted | explicit launcher config or CLI `home_dir` override | Houmao-selected | Stable placement, opaque CAO-owned contents |
| Mailbox root | `~/.houmao/mailbox` | `AGENTSYS_GLOBAL_MAILBOX_DIR` or explicit mailbox-root override | Separate mailbox subsystem | Out of scope for this subtree |

## Root-Resolution Notes

### Houmao home anchor

The shared `~/.houmao` anchor is derived from a platformdirs-aware home lookup rather than from a hardcoded Linux-only `/home/<user>` assumption. Runtime, registry, and mailbox defaults hang off that anchor.

### Runtime root

The runtime root is where Houmao stores generated homes, generated manifests, runtime session roots, and launcher-managed CAO server trees. Different entrypoints expose the explicit override differently:

- `build-brain` exposes `--runtime-root`,
- launcher config exposes `runtime_root`,
- programmatic calls expose `runtime_root=...`,
- otherwise the runtime falls back to `AGENTSYS_GLOBAL_RUNTIME_DIR` and then `~/.houmao/runtime`.

### Registry root

Current operator-facing registry relocation happens through `AGENTSYS_GLOBAL_REGISTRY_DIR`. The internal shared-path helper also supports explicit roots, but the main operational contract today is the env-var override and the default `~/.houmao/registry`.

### Local jobs root

The local jobs root is derived from the selected working directory, not from the runtime root:

```text
<working-directory>/.houmao/jobs/<session-id>/
```

`AGENTSYS_LOCAL_JOBS_DIR` relocates that scratch area to an absolute path. When the runtime starts or resumes a managed session, it also publishes the concrete per-session directory to the launched environment as `AGENTSYS_JOB_DIR`.

If the selected working directory is also a project root initialized with `houmao-mgr project init`, the default jobs root becomes `<project-root>/.houmao/jobs/`. That path family is still scratch/runtime state, even though it lives under the same hidden repo-local overlay as `.houmao/houmao-config.toml` and `.houmao/agents/`.

### Launcher-selected CAO home

If launcher config provides `home_dir`, that absolute writable directory becomes `HOME` for the launched `cao-server` process. If config omits `home_dir`, Houmao derives a sibling path under the launcher server root:

```text
<runtime-root>/cao_servers/<host>-<port>/home/
```

Houmao owns that path selection, but CAO owns the contents it later writes under `HOME/.aws/cli-agent-orchestrator/`.

## Contract Strength

The system-files pages use these labels consistently:

- stable path and meaning: Houmao expects the path family and the artifact’s role to remain operator-facing,
- stable path with opaque contents: Houmao expects the root placement to remain stable, but another tool or an internal implementation detail owns the detailed payload,
- current implementation detail: useful to know today, but not presented as a compatibility promise.

## Out Of Scope: Mailbox

Mailbox remains documented in [Mailbox Reference](../mailbox/index.md). This subtree may mention mailbox only when clarifying that mailbox roots are separate from runtime, registry, and launcher roots.

## Source References

- [`src/houmao/owned_paths.py`](../../../src/houmao/owned_paths.py)
- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/cao/server_launcher.py`](../../../src/houmao/cao/server_launcher.py)
