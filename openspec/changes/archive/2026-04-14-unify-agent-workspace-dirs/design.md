## Context

The current runtime has two separate filesystem concepts for managed agents:

- `job_dir`, resolved as `<active-overlay>/jobs/<session-id>/` and published as `HOUMAO_JOB_DIR`.
- `memory_dir`, resolved as `<active-overlay>/memory/agents/<agent-id>/` or an explicit path and published as `HOUMAO_MEMORY_DIR` when enabled.

`job_dir` is scratch by intent, but it is only discoverable through manifest/env state and cleanup flags. There is no supported CLI or gateway workspace API for listing, reading, or writing files under it, so current agents and operators must invent ad hoc usage. The memory directory is durable and discoverable, but it has no first-class scratch/persist separation.

This change is intentionally breaking. The repository is unstable, and the user explicitly requested no backward compatibility or migration work.

## Goals / Non-Goals

**Goals:**

- Make the managed-agent filesystem contract one per-agent workspace envelope under `<active-overlay>/memory/agents/<agent-id>/`.
- Give agents and operators two explicit lanes: `scratch/` for former job-dir work and `persist/` for durable memory.
- Add one first-class per-agent memo file for live-agent instructions and loop initialization material.
- Rename environment variables and CLI flags so the contract reads as scratch/persist instead of job/memory.
- Add supported CLI and gateway surfaces for lane-scoped workspace file operations.
- Keep lane internals mostly opaque: Houmao owns path resolution, env/manifest publication, containment, and transport; agents own file layout inside each lane.

**Non-Goals:**

- No compatibility aliases for `HOUMAO_JOB_DIR`, `HOUMAO_MEMORY_DIR`, `--memory-dir`, `--no-memory-dir`, `job_dir`, or `memory_dir`.
- No migration of existing `.houmao/jobs/` or `.houmao/memory/agents/<agent-id>/` contents.
- No cross-agent sharing semantics beyond explicit operator-provided persist paths.
- No indexing/search/database layer for workspace contents.

## Decisions

### Use one per-agent workspace envelope

Default layout:

```text
<active-overlay>/memory/agents/<agent-id>/
  houmao-memo.md
  scratch/
  persist/
```

Rationale: path discovery becomes stable across relaunches, and scratch/persist are both addressable under one agent identity. This also removes the session-id-derived `jobs/` family that currently has no practical API.

Alternative considered: keep per-session scratch at `scratch/sessions/<session-id>/`. That preserves the old cleanup mental model, but it keeps forcing operators and agents to chase session ids. Use explicit scratch clear operations instead.

### Make `houmao-memo.md` the workspace-root instruction file

Houmao should create one memo file at:

```text
<agent-workspace-root>/houmao-memo.md
```

This file is the per-agent operational instruction file, similar in role to `AGENTS.md` for Codex or `CLAUDE.md` for Claude, but scoped to one managed live agent. It is intended for initialization notes, delegation authority, task-handling rules, loop obligations, forbidden actions, and other agent-local rules that need to be easy to re-open across turns.

Rationale: this material is not scratch, because it should remain available throughout a live run and relaunches; it is also not ordinary durable archive content, because it should be a known instruction surface rather than one arbitrary file inside `persist/`. Keeping it as a named root file gives launch, gateway, loop skills, and operator tools one stable target without opening arbitrary writes at the workspace root.

Alternative considered: store the memo at `persist/houmao-memo.md`. Rejected because `persist/` can be disabled or exact-bound to a shared external directory, while the live-agent memo should stay per-agent and always available.

### Rename environment variables around lanes

The live session environment SHALL publish:

- `HOUMAO_AGENT_STATE_DIR=<workspace-root>`
- `HOUMAO_AGENT_SCRATCH_DIR=<workspace-root>/scratch`
- `HOUMAO_AGENT_MEMO_FILE=<workspace-root>/houmao-memo.md`
- `HOUMAO_AGENT_PERSIST_DIR=<persist-dir>` only when persistent memory is enabled

Rationale: the names describe ownership and lifetime. `HOUMAO_AGENT_STATE_DIR` gives an anchor for humans and future tooling, while the lane-specific variables guide agents away from writing arbitrary files under the envelope root.

Alternative considered: keep `HOUMAO_MEMORY_DIR` for persist. That would reduce churn, but it makes the new split harder to understand and conflicts with the explicit no-compatibility direction.

### Make scratch always available and persist optional

The scratch lane is always created for managed sessions. The memo file is always created for managed sessions. The persist lane is created only when persistent memory is enabled. Disabling persistence omits `HOUMAO_AGENT_PERSIST_DIR` but still leaves `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_SCRATCH_DIR` available.

Rationale: every managed agent needs a temporary file lane even if durable memory is intentionally disabled.

Alternative considered: disable both scratch and persist with one flag. That preserves the old `--no-memory-dir` shape, but it would recreate the original gap where agents have no supported scratch entrypoint.

### Rename CLI controls to persist controls

Operator-facing controls should be:

- `--persist-dir <path>`
- `--no-persist-dir`
- stored `persist_binding` / `persist_dir` fields on launch profiles and easy profiles

The explicit path binds the persist lane, not the whole workspace. The workspace root and scratch lane remain agent-local unless a later change adds a dedicated `--agent-state-dir` override.

Rationale: operators usually want to share or relocate durable memory, not scratch bookkeeping. Keeping scratch under the agent envelope makes cleanup and containment predictable.

Alternative considered: add `--agent-state-dir` now. That is useful but expands scope. This proposal can reserve the manifest concept while deferring the CLI override unless implementation finds a strong need.

### Add lane-scoped CLI and gateway APIs

CLI should expose workspace operations equivalent to:

```text
houmao-mgr agents workspace path --kind root|scratch|persist
houmao-mgr agents workspace tree scratch [path]
houmao-mgr agents workspace cat scratch <path>
houmao-mgr agents workspace put scratch <local> <path>
houmao-mgr agents workspace append scratch <path>
houmao-mgr agents workspace rm scratch <path>
houmao-mgr agents workspace clear scratch
houmao-mgr agents workspace memo path
houmao-mgr agents workspace memo show
houmao-mgr agents workspace memo set <local-or-stdin>
houmao-mgr agents workspace memo append <text-or-stdin>
```

Gateway should expose lane-scoped routes equivalent to:

```text
GET    /v1/workspace
GET    /v1/workspace/{lane}/tree?path=...
GET    /v1/workspace/{lane}/files/{path:path}
PUT    /v1/workspace/{lane}/files/{path:path}
POST   /v1/workspace/{lane}/append/{path:path}
DELETE /v1/workspace/{lane}/files/{path:path}
POST   /v1/workspace/{lane}/clear
GET    /v1/workspace/memo
PUT    /v1/workspace/memo
POST   /v1/workspace/memo/append
```

Pair-server gateway proxy routes should mirror the gateway surface under `/houmao/agents/{agent_ref}/gateway/workspace/...`.

Rationale: the original `job_dir` was not useful because it lacked entrypoints. The new workspace contract must be operable through the same control planes that operators already use.

Alternative considered: only publish env vars and leave filesystem access manual. That repeats the original failure mode.

### Use strict containment for lane paths

All lane file operations MUST accept relative paths only, reject absolute paths and `..`, and verify resolved targets stay under the lane root after symlink resolution. Persist operations must fail clearly when persistence is disabled.

Rationale: gateway and pair-server routes turn local files into remote API resources, so containment is the core safety requirement.

Alternative considered: allow arbitrary absolute paths for operator convenience. That is too broad for a gateway surface and does not match the lane abstraction.

## Risks / Trade-offs

- [Risk] Scratch changes from per-session to per-agent, so stale scratch can accumulate across relaunches. -> Mitigate with explicit `workspace clear scratch` CLI/gateway operations and docs that define scratch as operator-clearable state.
- [Risk] Removing old names breaks existing prompts, skills, docs, tests, and user scripts. -> Accept as a deliberate breaking change and update in-repo skills/docs/tests in the same implementation.
- [Risk] Gateway file APIs can expose filesystem data if containment is weak. -> Centralize lane resolution and target validation, reject path traversal, and cover symlink escape cases in tests.
- [Risk] Exact persist paths may be shared intentionally by multiple agents. -> Treat exact persist sharing as operator intent, but keep scratch rooted under each agent workspace.
- [Risk] The workspace envelope root may become a dumping ground. -> Publish lane env vars prominently and document that `houmao-memo.md` is the only first-class root-level file; agents should write other files to `scratch/` or `persist/`.
- [Risk] `houmao-memo.md` can accumulate stale loop rules across unrelated runs for the same agent. -> Treat the memo as editable operator/agent-owned instruction state and provide memo set/append operations so initialization can replace or explicitly update it.
