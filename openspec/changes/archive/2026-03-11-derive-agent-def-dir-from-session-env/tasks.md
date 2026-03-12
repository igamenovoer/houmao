## 1. Publish tmux session environment pointers

- [x] 1.1 Update tmux-backed start/resume plumbing to carry the effective `agent_def_dir` into backend session objects and publish or re-publish `AGENTSYS_AGENT_DEF_DIR` alongside `AGENTSYS_MANIFEST_PATH`.
- [x] 1.2 Add shared validation/helpers for reading `AGENTSYS_AGENT_DEF_DIR` from tmux session environment and rejecting missing, blank, relative, or stale values.

## 2. Rework name-based session control resolution

- [x] 2.1 Extend the existing `AgentIdentityResolution` type to carry the resolved manifest path plus tmux-derived `agent_def_dir` for name-based fallback.
- [x] 2.2 Split CLI `agent_def_dir` resolution paths so build/start and manifest-path control stay eager while name-based `send-prompt`, `send-keys`, and `stop-session` resolve identity first and then derive the effective `agent_def_dir`.
- [x] 2.3 Preserve explicit `--agent-def-dir` precedence, including legacy sessions that lack `AGENTSYS_AGENT_DEF_DIR`, and keep manifest-path control behavior unchanged.
- [x] 2.4 Update in-repo interactive demo prompt/control/stop flows to omit explicit `--agent-def-dir` when they target a live session by persisted agent name.

## 3. Validate behavior and update operator guidance

- [x] 3.1 Add unit and integration coverage for successful name-based control without `--agent-def-dir`, including `send-prompt` happy-path coverage and wrapper-level flows that now rely on the default.
- [x] 3.2 Add failure coverage for missing, blank, relative, and stale tmux `AGENTSYS_AGENT_DEF_DIR` values when no explicit override is provided, plus explicit-override coverage for legacy sessions missing the tmux pointer.
- [x] 3.3 Update runtime reference docs to distinguish ambient `agent_def_dir` resolution from name-based tmux-session-derived control defaults.
- [x] 3.4 Update interactive demo/operator docs to describe the new default path for prompt, control-input, and stop flows.
