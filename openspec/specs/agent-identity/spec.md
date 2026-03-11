# agent-identity Specification

## Purpose
TBD - created by archiving change agent-identity-tmux-manifest-path. Update Purpose after archive.
## Requirements
### Requirement: `--agent-identity` accepts either an agent name or a session manifest path
The system SHALL accept `--agent-identity` values that address a session using either:
- a session manifest JSON file path, or
- an agent name (tmux-backed sessions only).

The system SHALL deterministically treat an identity value as a file path when it is path-like (for example contains `/` or `\\` or ends with `.json`).
If a path-like identity value does not resolve to an existing file, the system SHALL fail with an explicit "manifest not found" error and SHALL NOT interpret it as an agent name.

#### Scenario: Path-like identity resolves as a manifest path
- **WHEN** a caller provides `--agent-identity tmp/agents-runtime/sessions/cao_rest/session-20260101-000000Z-abcd1234.json`
- **AND WHEN** that file exists
- **THEN** the runtime loads the session manifest from that path and resumes the session

#### Scenario: Missing path-like identity fails fast
- **WHEN** a caller provides `--agent-identity tmp/agents-runtime/sessions/cao_rest/missing.json`
- **AND WHEN** that file does not exist
- **THEN** the runtime rejects the operation with an explicit "manifest not found" error

#### Scenario: Non-path-like identity resolves as an agent name
- **WHEN** a caller provides `--agent-identity gpu`
- **THEN** the runtime treats the identity as an agent name and applies agent-name normalization rules

### Requirement: Agent identities use an exact `AGENTSYS-` namespace prefix (no case conversion)
For tmux-backed sessions, the system SHALL normalize agent identities into canonical tmux session names using the namespace prefix `AGENTSYS-`.

Prefix matching SHALL be case-sensitive and exact. The system SHALL NOT apply any case conversion to user-provided identity strings.

Normalization rules:
- If the caller provides an identity that starts with exact `AGENTSYS-`, the canonical tmux session name SHALL be exactly that value.
- Otherwise, the canonical tmux session name SHALL be `AGENTSYS-<identity>`.

#### Scenario: Name without prefix is normalized
- **WHEN** a caller provides the agent name `gpu`
- **THEN** the canonical tmux session name is `AGENTSYS-gpu`

#### Scenario: Name with prefix is preserved
- **WHEN** a caller provides the agent name `AGENTSYS-gpu`
- **THEN** the canonical tmux session name is `AGENTSYS-gpu`

### Requirement: Inexact `AGENTSYS` look-alikes trigger a warning when the exact prefix is missing
When the caller provides an identity that does not start with exact `AGENTSYS-` and the identity contains the substring `AGENTSYS` in a case-insensitive way, the system SHALL emit a warning (to stderr) indicating that the namespace prefix did not match exactly.

The warning SHALL NOT change the canonicalization behavior (the identity is still treated as missing the namespace prefix and is normalized by prefixing `AGENTSYS-`).

#### Scenario: Inexact prefix casing triggers a warning but is still treated as missing prefix
- **WHEN** a caller provides the agent identity `agentsys-gpu`
- **THEN** the system emits a warning about an inexact `AGENTSYS-` prefix match
- **AND THEN** the canonical tmux session name is `AGENTSYS-agentsys-gpu`

### Requirement: User-provided agent names are validated and MUST NOT contain a standalone `AGENTSYS` token
The system SHALL validate the agent name portion for tmux-backed sessions using a conservative character set that is safe for both tmux session names and Unix-style filenames.

Allowed characters for the agent name portion are:
- ASCII letters `A-Z` and `a-z`,
- ASCII digits `0-9`,
- underscore (`_`) and hyphen (`-`).

The agent name portion MUST start with an ASCII letter or digit.
The system SHALL NOT enforce an additional length limit on the agent name portion beyond tmux constraints.

Additionally, the agent name portion MUST NOT contain `AGENTSYS` as a standalone token, where token boundaries are defined as string boundaries or any non-alphanumeric character (regex boundary class `[^0-9A-Za-z]`).
Substring occurrences inside a larger alphanumeric run (for example `MYAGENTSYS`, `AGENTSYSFOO`) are allowed.

This validation SHALL be applied to the agent name portion after stripping an optional exact `AGENTSYS-` namespace prefix.

#### Scenario: Reserved keyword alone is rejected
- **WHEN** a caller provides `--agent-identity AGENTSYS`
- **THEN** the system rejects the operation with an explicit reserved-name error

#### Scenario: Standalone token inside name portion is rejected
- **WHEN** a caller provides `--agent-identity foo-AGENTSYS-bar`
- **THEN** the system rejects the operation with an explicit invalid-name error

#### Scenario: Standalone token delimited by underscore is rejected
- **WHEN** a caller provides `--agent-identity foo_AGENTSYS_bar`
- **THEN** the system rejects the operation with an explicit invalid-name error

#### Scenario: Substring occurrences inside an alphanumeric run are allowed
- **WHEN** a caller provides `--agent-identity MYAGENTSYS`
- **THEN** the system accepts the identity

#### Scenario: Substring prefix inside an alphanumeric run is allowed
- **WHEN** a caller provides `--agent-identity AGENTSYSFOO`
- **THEN** the system accepts the identity

### Requirement: tmux-backed sessions expose their manifest path and agent-definition root via tmux session environment
For tmux-backed sessions, the system SHALL set tmux session environment
variables named:
- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_DEF_DIR`

`AGENTSYS_MANIFEST_PATH` SHALL be the absolute path of the persisted session
manifest JSON for that session.

`AGENTSYS_AGENT_DEF_DIR` SHALL be the absolute path of the agent-definition
root used for that session launch.

When tmux-backed backend code later resumes control of the same live session
with an effective agent-definition root available, it SHALL re-publish the
same two pointers into the tmux session environment.

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

### Requirement: tmux-backed non-CAO session manifests persist their tmux session identity
For tmux-backed non-CAO sessions (for example tmux-backed headless Claude/Gemini/Codex sessions), the persisted session manifest SHALL include the canonical tmux session name used for identity resolution.

The persisted tmux session name SHALL be stored in a deterministic field that can be validated on resume/control, for example:
- `payload.backend_state.tmux_session_name`

#### Scenario: Headless tmux-backed session persists its canonical tmux session name
- **WHEN** the runtime starts a tmux-backed headless session with tmux session name `AGENTSYS-gpu`
- **THEN** the persisted session manifest includes `backend_state.tmux_session_name="AGENTSYS-gpu"`

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

#### Scenario: Missing tmux session fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` does not exist
- **THEN** the runtime rejects the operation with an explicit "agent not found" error

#### Scenario: Missing tmux env pointer fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing or blank in the tmux session environment
- **THEN** the runtime rejects the operation with an explicit "manifest pointer missing" error

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
