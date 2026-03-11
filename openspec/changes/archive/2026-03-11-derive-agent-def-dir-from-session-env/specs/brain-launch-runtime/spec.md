## ADDED Requirements

### Requirement: Name-addressed tmux-backed session control SHALL recover `agent_def_dir` from session environment
For tmux-backed session-control commands that accept `--agent-identity` (`send-prompt`, `send-keys`, and `stop-session`), the system SHALL allow callers to omit `--agent-def-dir` when the identity is name-based rather than path-like.

When `--agent-identity` is name-based and `--agent-def-dir` is omitted, the system SHALL:
- resolve the addressed tmux session by canonical agent identity,
- recover the session manifest path from `AGENTSYS_MANIFEST_PATH`,
- recover the agent-definition root from `AGENTSYS_AGENT_DEF_DIR`, and
- use that recovered absolute agents root for resume/control operations.

When `--agent-def-dir` is provided explicitly, the system SHALL use the explicit CLI value instead of the tmux-published fallback.

Manifest-path control flows are unchanged by this requirement.

#### Scenario: Name-based send-prompt omits explicit agent-def-dir
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hello"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and delivers the prompt without requiring explicit `--agent-def-dir`

#### Scenario: Name-based stop-session omits explicit agent-def-dir
- **WHEN** a developer runs `stop-session --agent-identity chris`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and stops the addressed session without requiring explicit `--agent-def-dir`

#### Scenario: Name-based send-keys omits explicit agent-def-dir
- **WHEN** a developer runs `send-keys --agent-identity chris --sequence "<[Escape]>"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and delivers the control-input request without requiring explicit `--agent-def-dir`

#### Scenario: Explicit CLI agent-def-dir overrides tmux fallback
- **WHEN** a developer runs `stop-session --agent-identity chris --agent-def-dir /abs/custom/agents`
- **AND WHEN** tmux session `AGENTSYS-chris` publishes a different `AGENTSYS_AGENT_DEF_DIR`
- **THEN** the runtime uses `/abs/custom/agents` as the effective agent-definition root

#### Scenario: Name-based fallback fails on missing tmux agent-def-dir pointer
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hi"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing or blank in that tmux session environment
- **THEN** the runtime rejects the operation with an explicit resolution error
- **AND THEN** it does not silently fall back to cwd-derived agent-definition defaults

#### Scenario: Manifest-path control does not depend on tmux fallback
- **WHEN** a developer runs `stop-session --agent-identity /abs/runtime/sessions/cao_rest/session.json`
- **THEN** the runtime keeps the existing manifest-path control flow
- **AND THEN** this change does not require tmux session environment lookup for that request
