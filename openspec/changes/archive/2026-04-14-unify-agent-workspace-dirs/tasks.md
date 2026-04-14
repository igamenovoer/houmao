## 1. Workspace Model And Manifest Contract

- [x] 1.1 Replace the memory-dir helper with an agent-workspace helper that resolves workspace root, memo file, scratch dir, persist binding, and optional persist dir from overlay root, agent id, and direct/stored persist options.
- [x] 1.2 Remove current `job_dir` path derivation as a managed-session runtime contract, including the `<active-overlay>/jobs/<session-id>/` default and `HOUMAO_LOCAL_JOBS_DIR` behavior where it only exists to support managed `job_dir`.
- [x] 1.3 Update runtime manifest request, payload, boundary, and validation models to store workspace root, memo file, scratch dir, persist binding, and optional persist dir instead of `job_dir`, `memory_binding`, and `memory_dir`.
- [x] 1.4 Define and export the new environment variable constants `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_MEMO_FILE`, `HOUMAO_AGENT_SCRATCH_DIR`, and `HOUMAO_AGENT_PERSIST_DIR`, and remove current publication of `HOUMAO_JOB_DIR` and `HOUMAO_MEMORY_DIR`.
- [x] 1.5 Update managed-agent state and detail response models to expose workspace root, memo file, scratch dir, persist binding, and persist dir while dropping the current `memory_dir` field.
- [x] 1.6 Ensure `houmao-memo.md` is created as a stable workspace-root file for each managed agent without overwriting existing memo content.

## 2. Runtime Launch Join Relaunch Behavior

- [x] 2.1 Update native managed launch startup to resolve and create the workspace root, memo file, and scratch lane for every tmux-backed managed agent, and create the persist lane only when persistence is enabled.
- [x] 2.2 Update managed join materialization to persist and publish the new workspace root, memo file, and lanes for adopted TUI and headless tmux sessions.
- [x] 2.3 Update runtime resume and relaunch paths to reuse the manifest-persisted workspace root, memo file, scratch lane, persist binding, and persist lane without deriving scratch from a new session id.
- [x] 2.4 Update launch-plan environment injection and tmux environment publication to publish only the new workspace environment variables.
- [x] 2.5 Update force-clean takeover and session cleanup internals so they do not treat scratch as a session-root-adjacent `job_dir` artifact.

## 3. CLI And Stored Profile Surfaces

- [x] 3.1 Rename `houmao-mgr agents launch` options from `--memory-dir` and `--no-memory-dir` to `--persist-dir` and `--no-persist-dir`, including parser validation and launch result output.
- [x] 3.2 Rename `houmao-mgr agents join` options from `--memory-dir` and `--no-memory-dir` to `--persist-dir` and `--no-persist-dir`, including join result output.
- [x] 3.3 Update explicit project launch-profile storage and commands to use persist binding and persist directory fields and CLI flags instead of memory binding and memory directory fields.
- [x] 3.4 Update easy profile and easy instance launch/get surfaces to use persist binding and persist directory naming and to report workspace root, memo file, and scratch dir.
- [x] 3.5 Add `houmao-mgr agents workspace` commands for resolving paths, showing/setting/appending the memo file, listing lane trees, reading files, writing files, appending files, deleting files, and clearing a scratch or persist lane.
- [x] 3.6 Replace `--include-job-dir` cleanup behavior with an explicit scratch-lane cleanup command that supports dry-run planning and preserves the persist lane.

## 4. Gateway And Pair Server Workspace APIs

- [x] 4.1 Add a shared workspace file-operation service that validates lane names, accepts only relative paths for lane operations, rejects traversal, prevents symlink escapes, and exposes fixed-path memo operations.
- [x] 4.2 Add live gateway workspace endpoints for summary, memo show/set/append, lane tree, file read, file write, append, delete, and lane clear operations.
- [x] 4.3 Add gateway client methods and CLI plumbing for the new workspace endpoints.
- [x] 4.4 Add passive-server proxy routes for the gateway workspace endpoints under the managed-agent gateway route family.
- [x] 4.5 Ensure persist-lane operations fail clearly when persistence is disabled and do not create a persist directory as a side effect.

## 5. Skills And Documentation

- [x] 5.1 Update `houmao-adv-usage-pattern` pairwise and relay-loop pattern docs so mutable ledgers use `HOUMAO_AGENT_SCRATCH_DIR`.
- [x] 5.2 Update any managed-agent system skills that mention `HOUMAO_JOB_DIR`, `HOUMAO_MEMORY_DIR`, `--memory-dir`, or `--no-memory-dir` to use the new workspace and persist terminology.
- [x] 5.3 Update `houmao-agent-loop-pairwise-v2` initialization guidance to write participant initialization memo content, delegation rules, task-handling rules, obligations, and forbidden actions to `houmao-memo.md`.
- [x] 5.4 Update system-files reference docs to remove current `jobs/` and single `memory_dir` contracts and document the workspace root, memo file, scratch lane, persist lane, and env names.
- [x] 5.5 Update getting-started docs and CLI reference docs to show `--persist-dir`, `--no-persist-dir`, memo usage, and the new workspace inspection/operation commands.

## 6. Tests And Validation

- [x] 6.1 Add unit tests for workspace path resolution, memo file creation, exact persist binding, disabled persistence, and lane creation behavior.
- [x] 6.2 Update runtime launch, join, resume, and relaunch tests to assert new manifest fields and new environment variables.
- [x] 6.3 Update CLI tests for launch/join/profile/easy option renames and for workspace path/reporting output.
- [x] 6.4 Add workspace CLI and gateway endpoint tests for memo show/set/append, tree/read/write/append/delete/clear operations, and disabled-persist errors.
- [x] 6.5 Add containment tests for absolute paths, `..` traversal, and symlink escape attempts.
- [x] 6.6 Update cleanup tests to cover removal of `--include-job-dir` and explicit scratch-lane cleanup behavior.
- [x] 6.7 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, and the targeted unit/runtime test suites for the touched modules.
