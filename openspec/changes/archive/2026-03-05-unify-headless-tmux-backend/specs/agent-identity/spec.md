## ADDED Requirements

### Requirement: tmux-backed non-CAO session manifests persist their tmux session identity
For tmux-backed non-CAO sessions (for example tmux-backed headless Claude/Gemini/Codex sessions), the persisted session manifest SHALL include the canonical tmux session name used for identity resolution.

The persisted tmux session name SHALL be stored in a deterministic field that can be validated on resume/control, for example:
- `payload.backend_state.tmux_session_name`

#### Scenario: Headless tmux-backed session persists its canonical tmux session name
- **WHEN** the runtime starts a tmux-backed headless session with tmux session name `AGENTSYS-gpu`
- **THEN** the persisted session manifest includes `backend_state.tmux_session_name="AGENTSYS-gpu"`

## MODIFIED Requirements

### Requirement: Name-based agent identities resolve to a session manifest via tmux environment
When a caller provides a non-path-like `--agent-identity` value, the system SHALL:
1) normalize it to a canonical tmux session name,
2) locate the tmux session with that name,
3) read `AGENTSYS_MANIFEST_PATH` from the tmux session environment,
4) load the session manifest from that path,
5) validate the loaded manifest matches the addressed tmux session:
   - manifest backend is a tmux-backed backend kind, and
   - the manifest contains a persisted canonical tmux session name equal to the canonical tmux session name used for resolution (for example `payload.cao.session_name` for CAO sessions or `payload.backend_state.tmux_session_name` for headless tmux-backed sessions),
6) proceed with resume/control operations.

#### Scenario: Resolve a name to a manifest path and resume
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is present in the tmux session environment
- **THEN** the runtime loads the session manifest from the pointed path and resumes/control the session

#### Scenario: Missing tmux session fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` does not exist
- **THEN** the runtime rejects the operation with an explicit "agent not found" error

#### Scenario: Missing tmux env pointer fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing or blank in the tmux session environment
- **THEN** the runtime rejects the operation with an explicit "manifest pointer missing" error

#### Scenario: Resolved manifest must match the addressed tmux session
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest persists a different tmux session name (for example it is not `AGENTSYS-gpu`)
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Resolved manifest must be a tmux-backed session manifest
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest backend is not a tmux-backed backend kind
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error
