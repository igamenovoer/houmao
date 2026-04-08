## 1. Relax cleanup target resolution

- [x] 1.1 Extend `src/houmao/srv_ctrl/commands/runtime_cleanup.py` so managed-session cleanup can represent manifest-optional partial targets recovered from explicit `--session-root`, runtime-owned `--manifest-path`, and fresh shared-registry `runtime.session_root` fallback when manifest pointers are stale.
- [x] 1.2 Add helper logic that derives live-session evidence from valid manifest tmux metadata first and matching fresh shared-registry `runtime.session_root` records second, without guessing non-runtime-owned paths.

## 2. Make cleanup best-effort per artifact

- [x] 2.1 Update `cleanup_managed_session()` so stopped session-root cleanup can proceed without a readable manifest, while unknown or already-absent `job_dir` work is skipped instead of raising.
- [x] 2.2 Update `cleanup_managed_session_logs()` and `cleanup_managed_session_mailbox()` so missing manifests and already-absent candidate artifacts are treated as non-fatal no-op cleanup work and remaining artifacts are still evaluated.
- [x] 2.3 Keep `src/houmao/srv_ctrl/commands/agents/cleanup.py` translating only true resolution or safety failures into CLI errors rather than missing-artifact cases.

## 3. Add regression coverage and verify

- [x] 3.1 Add unit tests in `tests/unit/srv_ctrl/test_cleanup_commands.py` for explicit session cleanup with missing or malformed manifests and skipped `job_dir` behavior.
- [x] 3.2 Add unit tests for explicit log and mailbox cleanup when `manifest.json` or candidate artifacts are already absent, plus stale shared-registry `runtime.session_root` fallback where applicable.
- [x] 3.3 Run targeted Pixi tests for the cleanup command suite and any affected registry/runtime helper paths.
