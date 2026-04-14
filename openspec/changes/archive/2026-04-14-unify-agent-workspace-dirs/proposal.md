## Why

Houmao currently creates a per-session `job_dir`, but it is only a path binding: there is no first-class CLI or gateway entrypoint that makes the directory useful as an operator-addressable workspace. The managed memory directory already gives agents a durable path, but it blurs scratch and persistent state; this change makes those two lanes explicit under one per-agent workspace.

## What Changes

- **BREAKING** Replace the session-scoped `job_dir` model with a per-agent workspace envelope rooted at `<active-overlay>/memory/agents/<agent-id>/`.
- **BREAKING** Replace the default managed memory directory path with a lane layout:
  - `<active-overlay>/memory/agents/<agent-id>/scratch/` for short-lived scratch, transient job outputs, retry ledgers, temporary downloads, and destructive work.
  - `<active-overlay>/memory/agents/<agent-id>/persist/` for durable agent memory, source notes, extracted knowledge, and reusable artifacts.
- Add a first-class per-agent memo file at `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md` for live-agent rules, initialization notes, delegation constraints, task-handling rules, and loop bootstrap material.
- **BREAKING** Rename the live-session environment contract:
  - `HOUMAO_AGENT_STATE_DIR` points to the per-agent workspace envelope.
  - `HOUMAO_AGENT_SCRATCH_DIR` points to the scratch lane and replaces `HOUMAO_JOB_DIR`.
  - `HOUMAO_AGENT_PERSIST_DIR` points to the persist lane and replaces `HOUMAO_MEMORY_DIR` when persistent memory is enabled.
  - `HOUMAO_AGENT_MEMO_FILE` points to the agent memo file.
- **BREAKING** Remove the old `HOUMAO_JOB_DIR`, `HOUMAO_MEMORY_DIR`, `<active-overlay>/jobs/<session-id>/`, `job_dir`, and `memory_dir` as current runtime contracts. No backward compatibility or migration support is in scope.
- **BREAKING** Rename memory CLI concepts from "memory dir" to "persist dir":
  - `--memory-dir` becomes `--persist-dir`.
  - `--no-memory-dir` becomes `--no-persist-dir`.
  - Stored launch-profile and easy-profile fields follow the same persist naming.
- Add supported CLI workspace operations for resolving, listing, reading, writing/appending, deleting, and clearing files under the scratch or persist lane without requiring ad hoc filesystem access.
- Add supported CLI and gateway memo operations for reading, writing, and appending `houmao-memo.md` without opening arbitrary workspace-root file access.
- Add gateway workspace endpoints that expose the same lane-scoped file operations and memo operations through the live gateway, with relative-path containment validation.
- Update advanced usage patterns so mutable loop ledgers use `HOUMAO_AGENT_SCRATCH_DIR`, while long-lived notebooks and archives use `HOUMAO_AGENT_PERSIST_DIR`.
- Update the v2 pairwise loop skill so `initialize` can store participant initialization rules, delegation information, and task-handling constraints in each live agent's `houmao-memo.md`.

## Capabilities

### New Capabilities
- `agent-workspace-dirs`: Defines the per-agent workspace envelope, `houmao-memo.md`, scratch/persist lane semantics, environment variables, operator entrypoints, gateway workspace API, and path-containment behavior.

### Modified Capabilities
- `agent-memory-dir`: Replace the single optional memory-directory binding with persist-lane binding under the unified workspace.
- `brain-launch-runtime`: Replace job-dir and memory-dir runtime publication with workspace-root, scratch-lane, and persist-lane manifest/env publication.
- `houmao-owned-dir-layout`: Replace overlay-local `jobs/` placement with the per-agent workspace under `memory/agents/<agent-id>/`.
- `houmao-mgr-agents-launch`: Rename memory launch controls to persist controls and surface the new workspace paths in launch results.
- `houmao-mgr-agents-join`: Rename memory join controls to persist controls and publish workspace paths for adopted sessions.
- `agent-launch-profiles`: Rename stored memory configuration to stored persist-lane configuration.
- `houmao-mgr-project-agents-launch-profiles`: Rename explicit launch-profile memory controls to persist controls.
- `houmao-mgr-project-easy-cli`: Rename easy profile and easy instance memory controls to persist controls.
- `houmao-mgr-cleanup-cli`: Replace `--include-job-dir` cleanup behavior with lane-scoped workspace scratch cleanup.
- `agent-gateway`: Add lane-scoped workspace endpoints to the live gateway.
- `passive-server-gateway-proxy`: Proxy gateway workspace endpoints through the pair server.
- `managed-agent-detailed-state`: Report workspace root, scratch dir, persist binding, and persist dir instead of `memory_dir`.
- `houmao-adv-usage-pattern-skill`: Update scratch ledger guidance to use `HOUMAO_AGENT_SCRATCH_DIR`.
- `houmao-agent-loop-pairwise-v2-skill`: Add guidance for storing loop initialization memo material in `houmao-memo.md`.
- `system-files-reference-docs`: Update system-files documentation for the unified workspace layout and env names.
- `docs-getting-started`: Update the managed memory guide to describe scratch and persist lanes.

## Impact

- Runtime path helpers, manifest models, runtime controller start/resume/relaunch/join flows, launch-plan env injection, registry/state projection, managed-agent inspection payloads, and memo-file creation/publication.
- `houmao-mgr agents launch`, `houmao-mgr agents join`, project launch profile commands, easy profile/instance commands, and cleanup commands.
- Live gateway HTTP surface and pair-server proxy routes.
- System skills and docs that currently refer to `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR`.
- Tests around path derivation, manifest payload validation, env publication, CLI output, cleanup behavior, gateway routes, and docs/spec wording.
