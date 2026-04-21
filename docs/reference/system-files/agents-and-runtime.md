# Agents And Runtime

This page is the canonical filesystem inventory for runtime-managed agent storage: generated homes, generated manifests, runtime-owned loop-run recovery records, runtime session roots, nested gateway artifacts, runtime-owned Stalwart credential artifacts, and per-agent workspace directories.

## Runtime Root Overview

Representative default layout:

```text
<active-overlay>/runtime/
  homes/
    <home-id>/
      launch.sh
      ...
  manifests/
    <home-id>.yaml
  loop-runs/
    pairwise-v2/
      <run-id>/
        record.json
        events.jsonl
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
          gateway_manifest.json
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

<active-overlay>/
  memory/
    agents/
      <agent-id>/
        houmao-memo.md
        pages/
```

Use [Roots And Ownership](roots-and-ownership.md) for how the effective runtime root, mailbox root, and project memory root are chosen. If no project overlay exists yet and a maintained local-state command needs one, Houmao bootstraps the same layout under `<cwd>/.houmao/`.

## Build-Time Artifacts

`build-brain` materializes generated homes and secret-free manifests directly under the effective runtime root. The current flat layout is keyed by `home_id`; it does not create a per-tool directory layer under `homes/` or `manifests/`.

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/homes/<home-id>/` | `build-brain` / `build_brain_home()` | Houmao builder and projected tool/launch-policy helpers | Fresh generated runtime home for one built brain | Stable path family, partially tool-specific contents | Safe to delete and rebuild when no live session depends on it; `houmao-mgr admin cleanup runtime builds` enforces that preserved session manifests keep referenced homes |
| `<runtime-root>/homes/<home-id>/launch.sh` | Houmao builder | normally read-only after build | Launch helper that selects the home and either execs the tool directly or routes unattended mode through the shared launch-policy CLI | Stable operator-facing artifact | Recreated with the home |
| `<runtime-root>/manifests/<home-id>.yaml` | `build-brain` / `build_brain_home()` | normally read-only after build | Secret-free build manifest describing the generated home | Stable operator-facing artifact | Safe to regenerate with the same build inputs; `houmao-mgr admin cleanup runtime builds` removes only unreferenced or invalid manifest-home pairs |

Important boundary: Houmao owns the generated-home path family and the build manifest contract, but some generated-home contents are projections of tool configs, projected skills, or projected credential wrappers rather than a stable file-by-file contract.

Current manifest-level launch-policy artifacts:

- the build manifest carries secret-free `launch_policy.operator_prompt_mode` using the `unattended|as_is` policy vocabulary,
- unattended `launch.sh` helpers call `houmao.agents.launch_policy.cli` before the final tool exec,
- runtime-managed session manifests and redacted launch plans may persist typed `launch_policy_provenance` metadata describing requested mode, detected version, selected strategy, and override source,
- current build flows resolve omitted prompt mode to unattended before manifest write; `as_is` is the explicit pass-through opt-out.

Current manifest-level launch-override artifacts:

- build manifests now use `schema_version=4`,
- `runtime.launch_contract.adapter_defaults` snapshots adapter-owned default args and typed tool-param defaults,
- `runtime.launch_contract.requested_overrides` stores the secret-free recipe and direct-build `launch_overrides` layers separately,
- `runtime.launch_contract.tool_metadata` persists the declarative supported optional-launch metadata needed for runtime resolution,
- `runtime.launch_contract.construction_provenance` records builder-time source metadata without persisting secrets,
- build manifests intentionally do not store backend-resolved effective args because backend applicability is resolved later, at launch-plan time.

Operational note: the current runtime loader rejects any `schema_version` other than 4. Rebuild older brain homes with the current builder before starting or resuming sessions against them.

## Runtime-Owned Mailbox Credential Artifacts

Mailbox filesystem layout remains documented under [Mailbox Reference](../mailbox/index.md). This page only covers the runtime-owned credential artifacts that exist around a Stalwart-backed session.

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/mailbox-credentials/stalwart/` | Stalwart mailbox bootstrap | runtime mailbox provisioning helpers | Durable runtime-owned secret store for Stalwart credential material keyed by `credential_ref` | Stable path family, secret-bearing contents remain opaque | Do not delete while sessions may resume against those bindings; `houmao-mgr admin cleanup runtime mailbox-credentials` removes only unreferenced files |
| `<runtime-root>/mailbox-credentials/stalwart/<credential-ref>.json` | Stalwart mailbox bootstrap | runtime mailbox provisioning helpers when credentials are first created or intentionally rotated | Durable secret-bearing record containing the mailbox password and login metadata for one Stalwart binding | Stable path, secret-bearing payload | Treat as durable secret material rather than scratch; cleanup is safe only after preserved session manifests stop referencing the same `credential_ref` |

## Runtime-Owned Loop-Run Recovery Artifacts

Pairwise-v2 accepted runs may also persist one runtime-owned recovery envelope under the effective runtime root:

```text
<runtime-root>/loop-runs/pairwise-v2/<run-id>/
  record.json
  events.jsonl
```

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/loop-runs/pairwise-v2/<run-id>/` | accepted pairwise-v2 `start` guidance | pairwise-v2 `recover_and_continue`, `stop`, and `hard-kill` guidance | Runtime-owned envelope for one logical pairwise-v2 run across participant restarts | Stable path family | Do not delete while the run may still be inspected or recovered |
| `<runtime-root>/loop-runs/pairwise-v2/<run-id>/record.json` | accepted pairwise-v2 `start` guidance | pairwise-v2 `recover_and_continue`, `stop`, and `hard-kill` guidance | Latest durable recovery contract for one accepted logical run, including `run_id`, `recovery_epoch`, plan reference and freshness marker, participants, durable page references, mailbox bindings, declarative wakeup posture, and recoverable-versus-terminal state | Stable operator-facing artifact | Treat as durable runtime state rather than scratch |
| `<runtime-root>/loop-runs/pairwise-v2/<run-id>/events.jsonl` | accepted pairwise-v2 `start` guidance | pairwise-v2 `recover_and_continue`, `stop`, and `hard-kill` guidance | Append-only history of acceptance, recovery attempts, stop transitions, and terminal hard-kill transitions | Stable path, append-only payload | Safe to inspect; do not treat it as the authoritative latest record |

These recovery files live outside the authored plan bundle and outside participant-local memo or page files. They are the runtime-owned continuity record for the same logical `run_id`.

## Session-Time Artifacts

Runtime-managed sessions are centered on one runtime-owned session root:

```text
<runtime-root>/sessions/<backend>/<session-id>/
```

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<runtime-root>/sessions/<backend>/<session-id>/` | start/resume runtime flow | runtime and gateway helpers | Durable directory envelope for one runtime-managed session | Stable path family | Do not delete while the session is live; `houmao-mgr agents cleanup session` and `houmao-mgr admin cleanup runtime sessions` remove only stopped or otherwise malformed envelopes |
| `<session-root>/manifest.json` | `persist_manifest()` | runtime manifest persistence | Durable session record used for resume and control | Stable operator-facing artifact | Treat as durable state |
| `<session-root>/mailbox-secrets/` | Stalwart mailbox bootstrap or resume for Stalwart-backed sessions | runtime mailbox helpers | Session-local secret-material directory keyed by `credential_ref` | Stable path family, secret-bearing contents remain opaque | Remove only after the session is stopped and no direct or gateway-backed mailbox work depends on it; `houmao-mgr agents cleanup mailbox` exists for that exact scope |
| `<session-root>/mailbox-secrets/<credential-ref>.json` | Stalwart mailbox bootstrap or resume for Stalwart-backed sessions | runtime mailbox helpers | Materialized per-session credential file surfaced through `resolve-live.mailbox.stalwart.credential_file` | Stable path, secret-bearing payload | Treat as cleanup-sensitive session-local secret material rather than scratch |
| `<session-root>/gateway/` | gateway-capability publication | runtime and gateway lifecycle helpers | Session-owned gateway subtree | Stable path family for gateway-capable sessions | Subtree contents have mixed durability |
| `<session-root>/gateway/attach.json` | gateway-capability publication | runtime refresh | Internal bootstrap artifact used by runtime and gateway internals to seed startup, offline status, and metadata transfer for the same logical session | Internal runtime artifact | Durable |
| `<session-root>/gateway/gateway_manifest.json` | gateway-capability publication | runtime refresh and attach or detach lifecycle | Derived outward-facing gateway bookkeeping regenerated from manifest-backed authority plus current listener state | Derived operator-facing publication | Durable |
| `<session-root>/gateway/protocol-version.txt` | gateway-capability publication | runtime refresh if protocol changes | Local version marker for gateway artifacts | Stable path, simple payload | Durable |
| `<session-root>/gateway/desired-config.json` | gateway-capability publication | attach/detach lifecycle | Desired host/port reuse hints for later gateway starts | Stable operator-facing artifact | Durable |
| `<session-root>/gateway/state.json` | gateway-capability publication | gateway status refresh | Read-optimized last known gateway status, seeded before first live attach | Stable operator-facing artifact | Durable, but reflects current status |
| `<session-root>/gateway/queue.sqlite` | gateway-capability publication | live gateway process | Durable request queue state plus gateway-owned notifier audit history | Stable path, implementation-owned contents | Treat as durable while the session is active |
| `<session-root>/gateway/events.jsonl` | gateway-capability publication | live gateway process | Append-only gateway event log | Stable path, implementation-owned contents | Safe to inspect; not the source of truth for queue state |
| `<session-root>/gateway/logs/gateway.log` | live gateway process | live gateway process | Append-only running log for lifecycle, queue execution, and notifier polling | Stable operator-facing artifact | Log-style cleanup only after the session is stopped; `houmao-mgr agents cleanup logs` and `houmao-mgr admin cleanup runtime logs` remove this without deleting durable queue or manifest state |
| `<session-root>/gateway/run/current-instance.json` | live gateway lifecycle | live gateway lifecycle | Current live gateway process and listener snapshot, including the authoritative same-session tmux execution handle for `houmao_server_rest` auxiliary-window mode | Current implementation detail with active lifecycle semantics | Ephemeral; cleanup is valid only after the session is stopped |
| `<session-root>/gateway/run/gateway.pid` | live gateway lifecycle | live gateway lifecycle | Pidfile mirror for the live gateway process; same-session mode still writes it, but detach and cleanup rely on the current-instance execution handle rather than pid alone | Current implementation detail | Ephemeral; cleanup is valid only after the session is stopped |

Pair-managed `houmao_server_rest` notes:

- server-backed `houmao_server_rest` sessions seed the stable gateway subtree through the same runtime-owned gateway publication seam used by direct runtime flows
- that means internal bootstrap files such as `attach.json`, derived publication such as `gateway_manifest.json`, `state.json`, queue/bootstrap files, and manifest-first tmux discovery env can exist before any live gateway is attached
- current-session `houmao-mgr agents gateway attach` still remains invalid until the same logical session is registered under `/houmao/agents/*` on the persisted `api_base_url`
- tmux window `0` is the only contractual agent surface; non-zero windows remain auxiliary and non-contractual except for the exact live gateway handle recorded in `gateway/run/current-instance.json`

Joined-session notes:

- `houmao-mgr agents join` writes the same `<session-root>/manifest.json`, placeholder `agent_def/`, placeholder `brain_manifest.json`, session-local `gateway/` subtree, and per-agent memory metadata that native launches expect.
- For joined sessions, `manifest.json` becomes the source of truth for secret-free relaunch posture through `agent_launch_authority`, including `session_origin=joined_tmux`, explicit `posture_kind`, structured `launch_args`, and structured Docker-style `launch_env`.
- Joined headless resume posture is also persisted in `manifest.json`: omitted `--resume-id` stores `resume_selection_kind=none`, `--resume-id last` stores `resume_selection_kind=last`, and an exact selector stores `resume_selection_kind=exact` plus the exact value.
- The placeholder `brain_manifest.json` exists only to satisfy path and artifact invariants. Joined runtime control and relaunch do not treat it as behavioral truth.
- Shared-registry publication for joined sessions uses a long sentinel lease instead of a short renewable lease because `agents join` is a one-shot adoption command rather than a resident launcher.

## Mailbox Binding And Secret Lifecycle

For Stalwart-backed sessions, the runtime deliberately splits mailbox capability from secret material.

| Artifact | What it contains | Secret-free | Why it exists |
| --- | --- | --- | --- |
| `manifest.json` mailbox binding | `transport`, identity fields, endpoints, `login_identity`, `credential_ref`, `bindings_version` | yes | durable session record for resume, direct mailbox flows, and gateway adapter construction |
| `<runtime-root>/mailbox-credentials/stalwart/<credential-ref>.json` | durable password plus login metadata for one Stalwart mailbox binding | no | runtime-owned secret store reused across session starts and resumes |
| `<session-root>/mailbox-secrets/<credential-ref>.json` | session-local materialized copy of the credential record | no | direct or gateway-backed mailbox access for one live session |

The manifest is the operator-facing durable record. The secret-bearing files are runtime-owned implementation artifacts that matter for handling and cleanup, but their JSON contents are not the primary compatibility contract.

## Agent Memory Directories

Tmux-backed managed sessions create one memory root per managed agent under the active overlay by default:

```text
<active-overlay>/memory/agents/<agent-id>/
```

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<active-overlay>/memory/agents/<agent-id>/` | start/join runtime flow | Houmao for memo/page creation, then the managed agent and operator | Memory root for one managed agent | Stable path family | Do not delete while the agent is active; stop/session cleanup does not remove this directory |
| `<memory-root>/houmao-memo.md` | start/join runtime flow | operator and agent | Fixed memo file for initialization notes, durable instructions, and operator-visible context | Stable path | Created if missing without overwriting existing content |
| `<memory-root>/pages/` | start/join runtime flow | managed agent and operator | Contained page directory for readable operator-facing memory pages that may be linked from the memo | Stable path family | Page writes and deletes do not mutate the memo |

The runtime persists the resolved memory paths in `manifest.json` under `runtime.memory_root`, `runtime.memo_file`, and `runtime.pages_dir`.

The live tmux session publishes `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`.

## Contract Boundaries

- `manifest.json` is the durable runtime record for resume and control.
- `manifest.json` is also the supported durable authority for attach and relaunch on tmux-backed sessions.
- `manifest.json` stays secret-free for Stalwart-backed sessions and persists `credential_ref` instead of inline mailbox secrets.
- `manifest.json` may persist `launch_policy_provenance` when the session was built for unattended mode, and the nested redacted `launch_plan` may carry the same typed provenance for diagnostics.
- `<runtime-root>/loop-runs/pairwise-v2/<run-id>/record.json` is the durable runtime-owned recovery record for one accepted logical pairwise-v2 run.
- `<runtime-root>/loop-runs/pairwise-v2/<run-id>/events.jsonl` is append-only recovery history, not the authoritative latest record.
- Runtime-owned Stalwart credential material lives under the runtime root, while one session-local materialized copy lives under the session root when needed.
- `gateway/attach.json` is internal bootstrap state, not part of the supported external attach contract.
- `gateway/gateway_manifest.json` is derived outward-facing bookkeeping, not the authoritative input for attach or relaunch behavior.
- The gateway subtree belongs to the same logical runtime-managed session, but not every file under it has the same stability promise.
Important boundary: Houmao owns path selection, fixed memo creation, page-directory creation, manifest/env publication, inspection visibility, and page-scoped memory operations. Houmao does not generate, refresh, inspect, or remove page links inside `houmao-memo.md`, and does not define arbitrary file taxonomies or metadata sidecars inside `pages/`.

## Related References

- [Session Lifecycle](../run-phase/session-lifecycle.md): Behavior, targeting, and recovery semantics layered on top of these files.
- [Agent Gateway Reference](../gateway/index.md): Gateway protocol and queue behavior for the nested `gateway/` subtree.
- [Stalwart Setup And First Session](../mailbox/operations/stalwart-setup-and-first-session.md): Operator-facing mailbox path for the `stalwart` transport.
- [Managed Agent Memory](../../getting-started/managed-memory-dirs.md): Operator-facing guide for default paths, memo usage, and pages.
- [Operator Preparation](operator-preparation.md): Writable-path, ignore-rule, and cleanup guidance for these path families.

## Source References

- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/agents/launch_policy/`](../../../src/houmao/agents/launch_policy/)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/mailbox_runtime_support.py`](../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/mailbox/stalwart.py`](../../../src/houmao/mailbox/stalwart.py)
