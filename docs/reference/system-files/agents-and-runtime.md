# Agents And Runtime

This page is the canonical filesystem inventory for runtime-managed agent storage: generated homes, generated manifests, runtime session roots, nested gateway artifacts, and workspace-local job directories.

## Runtime Root Overview

Representative default layout:

```text
~/.houmao/runtime/
  homes/
    <home-id>/
      launch.sh
      ...
  manifests/
    <home-id>.yaml
  sessions/
    <backend>/
      <session-id>/
        manifest.json
        gateway/
          attach.json
          protocol-version.txt
          desired-config.json
          state.json
          queue.sqlite
          events.jsonl
          logs/
            gateway.log
          run/
            current-instance.json
            gateway.pid

<working-directory>/.houmao/
  jobs/
    <session-id>/
```

Use [Roots And Ownership](roots-and-ownership.md) for how the effective runtime root and local jobs root are chosen.

## Build-Time Artifacts

`build-brain` materializes generated homes and secret-free manifests directly under the effective runtime root. The current flat layout is keyed by `home_id`; it does not create a per-tool directory layer under `homes/` or `manifests/`.

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/homes/<home-id>/` | `build-brain` / `build_brain_home()` | Houmao builder and projected tool/bootstrap helpers | Fresh generated runtime home for one built brain | Stable path family, partially tool-specific contents | Safe to delete and rebuild when no live session depends on it |
| `<runtime-root>/homes/<home-id>/launch.sh` | Houmao builder | normally read-only after build | Launch helper that selects the home and bootstraps the tool | Stable operator-facing artifact | Recreated with the home |
| `<runtime-root>/manifests/<home-id>.yaml` | `build-brain` / `build_brain_home()` | normally read-only after build | Secret-free build manifest describing the generated home | Stable operator-facing artifact | Safe to regenerate with the same build inputs |

Important boundary: Houmao owns the generated-home path family and the build manifest contract, but some generated-home contents are projections of tool configs, projected skills, or projected credential wrappers rather than a stable file-by-file contract.

## Session-Time Artifacts

Runtime-managed sessions are centered on one runtime-owned session root:

```text
<runtime-root>/sessions/<backend>/<session-id>/
```

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/sessions/<backend>/<session-id>/` | start/resume runtime flow | runtime and gateway helpers | Durable directory envelope for one runtime-managed session | Stable path family | Do not delete while the session is live |
| `<session-root>/manifest.json` | `persist_manifest()` | runtime manifest persistence | Durable session record used for resume and control | Stable operator-facing artifact | Treat as durable state |
| `<session-root>/gateway/` | gateway-capability publication | runtime and gateway lifecycle helpers | Session-owned gateway subtree | Stable path family for gateway-capable sessions | Subtree contents have mixed durability |
| `<session-root>/gateway/attach.json` | gateway-capability publication | runtime refresh | Stable attachability contract for the same logical session | Stable operator-facing artifact | Durable |
| `<session-root>/gateway/protocol-version.txt` | gateway-capability publication | runtime refresh if protocol changes | Local version marker for gateway artifacts | Stable path, simple payload | Durable |
| `<session-root>/gateway/desired-config.json` | gateway-capability publication | attach/detach lifecycle | Desired host/port reuse hints for later gateway starts | Stable operator-facing artifact | Durable |
| `<session-root>/gateway/state.json` | gateway-capability publication | gateway status refresh | Read-optimized last known gateway status | Stable operator-facing artifact | Durable, but reflects current status |
| `<session-root>/gateway/queue.sqlite` | gateway-capability publication | live gateway process | Durable request queue state plus gateway-owned notifier audit history | Stable path, implementation-owned contents | Treat as durable while the session is active |
| `<session-root>/gateway/events.jsonl` | gateway-capability publication | live gateway process | Append-only gateway event log | Stable path, implementation-owned contents | Safe to inspect; not the source of truth for queue state |
| `<session-root>/gateway/logs/gateway.log` | live gateway process | live gateway process | Append-only running log for lifecycle, queue execution, and notifier polling | Stable operator-facing artifact | Log-style cleanup only after the session is stopped |
| `<session-root>/gateway/run/current-instance.json` | live gateway lifecycle | live gateway lifecycle | Current live gateway process/binding snapshot | Current implementation detail | Ephemeral |
| `<session-root>/gateway/run/gateway.pid` | live gateway lifecycle | live gateway lifecycle | Pidfile mirror for the live gateway process | Current implementation detail | Ephemeral |

## Workspace-Local Job Directories

Runtime-managed sessions also derive a per-session workspace-local job directory outside the runtime root:

```text
<working-directory>/.houmao/jobs/<session-id>/
```

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<working-directory>/.houmao/jobs/<session-id>/` or relocated equivalent | start/resume runtime flow | the launched session and tool-side work | Per-session scratch and job-local outputs for the selected working directory | Stable path family | Usually the safest directory family to treat as scratch |

The runtime persists this resolved path in the session manifest as `job_dir` and publishes it into the launched session environment as `AGENTSYS_JOB_DIR`.

## Contract Boundaries

- `manifest.json` is the durable runtime record for resume and control.
- The gateway subtree belongs to the same logical runtime-managed session, but not every file under it has the same stability promise.
- The workspace-local `job_dir` is intentionally separate from the durable runtime root so operators can redirect it to a scratch filesystem without relocating the runtime root itself.

## Related References

- [Runtime-Managed Agents Reference](../agents/index.md): Behavior, targeting, and recovery semantics layered on top of these files.
- [Agent Gateway Reference](../gateway/index.md): Gateway protocol and queue behavior for the nested `gateway/` subtree.
- [Operator Preparation](operator-preparation.md): Writable-path, ignore-rule, and cleanup guidance for these path families.

## Source References

- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
