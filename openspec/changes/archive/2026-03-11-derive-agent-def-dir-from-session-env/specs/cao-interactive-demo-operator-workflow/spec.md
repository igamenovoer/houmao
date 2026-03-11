## MODIFIED Requirements

### Requirement: Demo pack SHALL provide wrapper scripts for the primary manual workflow
The interactive demo pack SHALL continue to provide shell entrypoints for launching the tutorial agent, sending one inline prompt, sending one control-input sequence, and stopping the active session, while delegating behavior through the existing `run_demo.sh` shell backend or shared helpers so the tutorial commands inherit the same workspace and environment defaults as the advanced interface.

For prompt, control-input, and stop flows that target the active session by persisted agent identity, the underlying runtime invocations SHALL omit explicit `--agent-def-dir` and rely on the runtime's name-addressed tmux-session-derived default instead. Build/start flows may still pass explicit `--agent-def-dir`.

#### Scenario: Interactive demo prompt and control flows rely on the runtime tmux-session default
- **WHEN** a developer runs the interactive demo prompt, control-input, or stop workflow against an already-running session addressed by name
- **THEN** the underlying `brain_launch_runtime send-prompt`, `send-keys`, or `stop-session` invocation omits explicit `--agent-def-dir`
- **AND THEN** the workflow relies on the addressed tmux session's published `AGENTSYS_AGENT_DEF_DIR` value instead of the caller's cwd-derived agents root

### Requirement: Tutorial and reference docs SHALL describe the split agent-definition-root resolution model
The interactive demo and runtime reference docs SHALL explain that build/start and manifest-path control still use ambient agent-definition-root resolution, while name-based tmux-backed `send-prompt`, `send-keys`, and `stop-session` default to the addressed session's tmux-published `AGENTSYS_AGENT_DEF_DIR` when explicit `--agent-def-dir` is omitted.

#### Scenario: Docs distinguish ambient resolution from name-based tmux-session fallback
- **WHEN** a developer reads the interactive demo or runtime reference documentation for session control
- **THEN** the docs explain that build/start flows still resolve `agent_def_dir` with ambient precedence rules
- **AND THEN** they explain that name-based `send-prompt`, `send-keys`, and `stop-session` use explicit `--agent-def-dir` when provided and otherwise recover the value from the addressed tmux session
