# Agents And Runtime

This page is the canonical filesystem inventory for runtime-managed agent storage: generated homes, generated manifests, runtime session roots, nested gateway artifacts, runtime-owned Stalwart credential artifacts, and workspace-local job directories.

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
  mailbox-credentials/
    stalwart/
      <credential-ref>.json
  sessions/
    <backend>/
      <session-id>/
        manifest.json
        mailbox-secrets/
          <credential-ref>.json
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
| `<runtime-root>/homes/<home-id>/` | `build-brain` / `build_brain_home()` | Houmao builder and projected tool/launch-policy helpers | Fresh generated runtime home for one built brain | Stable path family, partially tool-specific contents | Safe to delete and rebuild when no live session depends on it |
| `<runtime-root>/homes/<home-id>/launch.sh` | Houmao builder | normally read-only after build | Launch helper that selects the home and either execs the tool directly or routes unattended mode through the shared launch-policy CLI | Stable operator-facing artifact | Recreated with the home |
| `<runtime-root>/manifests/<home-id>.yaml` | `build-brain` / `build_brain_home()` | normally read-only after build | Secret-free build manifest describing the generated home | Stable operator-facing artifact | Safe to regenerate with the same build inputs |

Important boundary: Houmao owns the generated-home path family and the build manifest contract, but some generated-home contents are projections of tool configs, projected skills, or projected credential wrappers rather than a stable file-by-file contract.

Current manifest-level launch-policy artifacts:

- the build manifest carries secret-free `launch_policy.operator_prompt_mode`,
- unattended `launch.sh` helpers call `houmao.agents.launch_policy.cli` before the final tool exec,
- runtime-managed session manifests and redacted launch plans may persist typed `launch_policy_provenance` metadata describing requested mode, detected version, selected strategy, and override source.

## Runtime-Owned Mailbox Credential Artifacts

Mailbox filesystem layout remains documented under [Mailbox Reference](../mailbox/index.md). This page only covers the runtime-owned credential artifacts that exist around a Stalwart-backed session.

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/mailbox-credentials/stalwart/` | Stalwart mailbox bootstrap | runtime mailbox provisioning helpers | Durable runtime-owned secret store for Stalwart credential material keyed by `credential_ref` | Stable path family, secret-bearing contents remain opaque | Do not delete while sessions may resume against those bindings |
| `<runtime-root>/mailbox-credentials/stalwart/<credential-ref>.json` | Stalwart mailbox bootstrap | runtime mailbox provisioning helpers when credentials are first created or intentionally rotated | Durable secret-bearing record containing the mailbox password and login metadata for one Stalwart binding | Stable path, secret-bearing payload | Treat as durable secret material rather than scratch |

## Session-Time Artifacts

Runtime-managed sessions are centered on one runtime-owned session root:

```text
<runtime-root>/sessions/<backend>/<session-id>/
```

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/sessions/<backend>/<session-id>/` | start/resume runtime flow | runtime and gateway helpers | Durable directory envelope for one runtime-managed session | Stable path family | Do not delete while the session is live |
| `<session-root>/manifest.json` | `persist_manifest()` | runtime manifest persistence | Durable session record used for resume and control | Stable operator-facing artifact | Treat as durable state |
| `<session-root>/mailbox-secrets/` | Stalwart mailbox bootstrap or resume for Stalwart-backed sessions | runtime mailbox helpers | Session-local secret-material directory keyed by `credential_ref` | Stable path family, secret-bearing contents remain opaque | Remove only after the session is stopped and no direct or gateway-backed mailbox work depends on it |
| `<session-root>/mailbox-secrets/<credential-ref>.json` | Stalwart mailbox bootstrap or resume for Stalwart-backed sessions | runtime mailbox helpers | Materialized per-session credential file surfaced as `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE` | Stable path, secret-bearing payload | Treat as cleanup-sensitive session-local secret material |
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

## Mailbox Binding And Secret Lifecycle

For Stalwart-backed sessions, the runtime deliberately splits mailbox capability from secret material.

| Artifact | What it contains | Secret-free | Why it exists |
| --- | --- | --- | --- |
| `manifest.json` mailbox binding | `transport`, identity fields, endpoints, `login_identity`, `credential_ref`, `bindings_version` | yes | durable session record for resume, direct mailbox flows, and gateway adapter construction |
| `<runtime-root>/mailbox-credentials/stalwart/<credential-ref>.json` | durable password plus login metadata for one Stalwart mailbox binding | no | runtime-owned secret store reused across session starts and resumes |
| `<session-root>/mailbox-secrets/<credential-ref>.json` | session-local materialized copy of the credential record | no | direct or gateway-backed mailbox access for one live session |

The manifest is the operator-facing durable record. The secret-bearing files are runtime-owned implementation artifacts that matter for handling and cleanup, but their JSON contents are not the primary compatibility contract.

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
- `manifest.json` stays secret-free for Stalwart-backed sessions and persists `credential_ref` instead of inline mailbox secrets.
- `manifest.json` may persist `launch_policy_provenance` when the session was built for unattended mode, and the nested redacted `launch_plan` may carry the same typed provenance for diagnostics.
- Runtime-owned Stalwart credential material lives under the runtime root, while one session-local materialized copy lives under the session root when needed.
- The gateway subtree belongs to the same logical runtime-managed session, but not every file under it has the same stability promise.
- The workspace-local `job_dir` is intentionally separate from the durable runtime root so operators can redirect it to a scratch filesystem without relocating the runtime root itself.

## Related References

- [Runtime-Managed Agents Reference](../agents/index.md): Behavior, targeting, and recovery semantics layered on top of these files.
- [Agent Gateway Reference](../gateway/index.md): Gateway protocol and queue behavior for the nested `gateway/` subtree.
- [Stalwart Setup And First Session](../mailbox/operations/stalwart-setup-and-first-session.md): Operator-facing mailbox path for the `stalwart` transport.
- [Operator Preparation](operator-preparation.md): Writable-path, ignore-rule, and cleanup guidance for these path families.

## Source References

- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/agents/launch_policy/`](../../../src/houmao/agents/launch_policy/)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/mailbox_runtime_support.py`](../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/mailbox/stalwart.py`](../../../src/houmao/mailbox/stalwart.py)
