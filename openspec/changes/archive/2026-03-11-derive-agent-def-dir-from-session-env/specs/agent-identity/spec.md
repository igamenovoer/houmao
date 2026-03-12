## MODIFIED Requirements

### Requirement: tmux-backed sessions expose their manifest path and agent-definition root via tmux session environment
For tmux-backed sessions, the system SHALL set tmux session environment variables named:
- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_DEF_DIR`

`AGENTSYS_MANIFEST_PATH` SHALL be the absolute path of the persisted session manifest JSON for that session.

`AGENTSYS_AGENT_DEF_DIR` SHALL be the absolute path of the agent-definition root used for that session launch.

When tmux-backed backend code later resumes control of the same live session with an effective agent-definition root available, it SHALL re-publish the same two pointers into the tmux session environment.

#### Scenario: Session start sets tmux env pointers
- **WHEN** the runtime starts a tmux-backed session with tmux session name `AGENTSYS-gpu`
- **THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the value is the absolute path of the session manifest persisted for that session
- **AND THEN** the tmux session environment contains `AGENTSYS_AGENT_DEF_DIR`
- **AND THEN** the value is the absolute path of the agent-definition root used for that session launch

#### Scenario: Resume re-publishes tmux env pointers when the effective agent-definition root is available
- **WHEN** the runtime resumes control of tmux session `AGENTSYS-gpu`
- **AND WHEN** resume has already determined the effective agent-definition root for that control operation
- **THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `AGENTSYS_AGENT_DEF_DIR`

### Requirement: Name-based agent identities resolve to a session manifest and agent-definition root via tmux environment
When a caller provides a non-path-like `--agent-identity` value, the system SHALL:
1) normalize it to a canonical tmux session name,
2) locate the tmux session with that name,
3) read `AGENTSYS_MANIFEST_PATH` from the tmux session environment,
4) validate that `AGENTSYS_MANIFEST_PATH` points to an existing manifest file,
5) load the session manifest from that path,
6) validate the loaded manifest matches the addressed tmux session:
   - manifest backend is a tmux-backed backend kind, and
   - the manifest contains a persisted canonical tmux session name equal to the canonical tmux session name used for resolution (for example `payload.cao.session_name` for CAO sessions or `payload.backend_state.tmux_session_name` for headless tmux-backed sessions),
7) determine the effective agent-definition root as follows:
   - when the caller provided explicit `--agent-def-dir`, use that explicit path as the effective agent-definition root after resolving it to an absolute existing directory,
   - otherwise read `AGENTSYS_AGENT_DEF_DIR` from the tmux session environment and validate that it is absolute and points to an existing directory,
8) proceed with resume/control operations using the resolved manifest path and effective agent-definition root.

#### Scenario: Resolve a name to manifest path and agent-definition root
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` are present in the tmux session environment
- **THEN** the runtime loads the session manifest from the pointed path
- **AND THEN** the runtime uses the resolved agent-definition root from `AGENTSYS_AGENT_DEF_DIR` for resume/control

#### Scenario: Explicit agent-def-dir overrides missing tmux pointer for legacy sessions
- **WHEN** a caller provides `--agent-identity gpu --agent-def-dir /abs/agents`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` points to a valid session manifest for that tmux session
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing from the tmux session environment
- **THEN** the runtime uses `/abs/agents` as the effective agent-definition root
- **AND THEN** the operation proceeds without requiring `AGENTSYS_AGENT_DEF_DIR` from tmux

#### Scenario: Missing tmux agent-definition pointer fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing or blank in the tmux session environment
- **THEN** the runtime rejects the operation with an explicit "agent definition pointer missing" error

#### Scenario: Non-absolute tmux agent-definition pointer fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` contains a relative path
- **THEN** the runtime rejects the operation with an explicit invalid-pointer error

#### Scenario: Stale tmux agent-definition pointer fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` points to a missing directory
- **THEN** the runtime rejects the operation with an explicit stale-pointer error
