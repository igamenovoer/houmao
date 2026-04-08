## 1. Profile And CLI Inputs

- [x] 1.1 Extend the shared launch-profile model and projections to store memory-directory configuration as exact path, disabled, or no stored preference.
- [x] 1.2 Add `--memory-dir`, `--no-memory-dir`, and `--clear-memory-dir` support to `houmao-mgr project agents launch-profiles` with absolute-path normalization and inspection output.
- [x] 1.3 Add `--memory-dir` and `--no-memory-dir` support to `houmao-mgr project easy profile create` and report stored memory configuration in easy profile inspection.

## 2. Runtime Resolution And Inspection

- [x] 2.1 Add launch-time and join-time memory-binding resolution for managed tmux-backed sessions, including the conservative default `<active-overlay>/memory/agents/<agent-id>/`.
- [x] 2.2 Create enabled memory directories on demand, persist the resolved binding in session-owned runtime state, and publish `HOUMAO_MEMORY_DIR` only when memory is enabled.
- [x] 2.3 Update managed relaunch to reuse the manifest-persisted resolved memory binding instead of deriving a new default from the new session id.
- [x] 2.4 Add `--memory-dir` and `--no-memory-dir` support to `houmao-mgr agents launch`, `houmao-mgr agents join`, and `houmao-mgr project easy instance launch`.
- [x] 2.5 Surface the resolved memory directory or `null` through supported `houmao-mgr` inspection outputs for managed agents and easy instances.

## 3. Lifecycle, Docs, And Tests

- [x] 3.1 Update cleanup behavior so managed-session stop or cleanup flows do not delete memory directories or treat them as `job_dir` scratch.
- [x] 3.2 Document the new memory-directory contract, including the conservative default location, explicit no-memory mode, shared exact-path behavior, and the fact that Houmao does not define internal directory structure.
- [x] 3.3 Add tests covering auto default resolution, explicit exact-path binding, disabled memory binding, launch-profile precedence, join adoption, relaunch reuse, inspection output, and cleanup preservation.
