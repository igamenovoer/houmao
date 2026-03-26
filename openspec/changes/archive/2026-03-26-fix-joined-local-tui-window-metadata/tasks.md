## 1. Resume-State Preservation

- [x] 1.1 Extend resumed local interactive backend state so joined TUI sessions retain `tmux_window_name` across `resume_runtime_session()` and later manifest persistence.
- [x] 1.2 Update the shared tmux-backed backend-state serializer used by `persist_manifest()` so local interactive manifest rewrites keep the adopted window name instead of dropping it.

## 2. Local Tracking Recovery

- [x] 2.1 Ensure local managed-agent TUI identity and tracking resolution continue to use the persisted adopted tmux window metadata for joined sessions after resume-time capability publication.
- [x] 2.2 Add a narrow defensive fallback for joined local TUI tracking when normalized manifest tmux window fields are unexpectedly missing but joined launch metadata still contains the adopted window name.

## 3. Regression Coverage

- [x] 3.1 Add regression coverage for successful join followed by local `agents state` and `agents show` on a joined TUI whose adopted window name is not `agent`.
- [x] 3.2 Add a manifest-persistence regression that proves the first resumed local control path does not rewrite joined `tmux_window_name` to `null`.
