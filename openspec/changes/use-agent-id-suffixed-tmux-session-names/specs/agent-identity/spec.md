## UNCHANGED Requirements

The following existing requirements remain in force and are not changed by this delta:

- `--agent-identity` accepts either an agent name or a session manifest path.
- Inexact `AGENTSYS` prefix usage continues to emit the existing warning behavior.
- Agent-name validation rules, including standalone `AGENTSYS` token rejection, remain unchanged.

## ADDED Requirements

### Requirement: Runtime-owned tmux session names combine canonical agent name and authoritative agent-id prefix
For runtime-owned tmux-backed sessions in the current tmux-backed backend set (`codex_headless`, `claude_headless`, `gemini_headless`, and `cao_rest`), the system SHALL derive the live tmux session handle from:

- the canonical agent name in `AGENTSYS-<name>` form, and
- a prefix of the authoritative `agent_id`.

The default tmux session handle format SHALL be:

- `<canonical-agent-name>-<agent-id-prefix>`

The default `agent-id-prefix` length SHALL be 6 characters.

When the default 6-character prefix would collide with an already occupied tmux session name for another live session, the system SHALL extend the `agent_id` prefix one character at a time until the tmux session name becomes unique, up to the full authoritative `agent_id`. If uniqueness still cannot be achieved, session start SHALL fail explicitly.

The system SHALL treat the resulting tmux session name as an opaque transport handle. Runtime discovery and control SHALL rely on persisted metadata rather than reverse-parsing canonical agent identity or `agent_id` components from that tmux session name string.

#### Scenario: Default runtime-owned tmux handle uses the first 6 agent-id characters
- **WHEN** the runtime starts a tmux-backed session with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the authoritative `agent_id` is `270b8738f2f97092e572b73d19e6f923`
- **AND WHEN** no live tmux session already occupies `AGENTSYS-gpu-270b87`
- **THEN** the live tmux session name is `AGENTSYS-gpu-270b87`

#### Scenario: Explicit agent-id override contributes to the tmux session handle
- **WHEN** the runtime starts a tmux-backed session with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the caller explicitly provides `agent_id=deadbeefcafefeed`
- **THEN** the live tmux session name starts with `AGENTSYS-gpu-deadbe`

#### Scenario: Colliding short prefixes extend until the tmux handle is unique
- **WHEN** the runtime starts a tmux-backed session with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the 6-character candidate handle is already occupied by another live tmux session
- **THEN** the runtime extends the `agent_id` prefix until it can create a unique tmux session name
- **AND THEN** it does not silently create two live tmux sessions with the same tmux handle

## MODIFIED Requirements

### Requirement: Agent identities use an exact `AGENTSYS-` namespace prefix (no case conversion)
For tmux-backed sessions, the system SHALL normalize agent identities into canonical agent names using the namespace prefix `AGENTSYS-`.

Prefix matching SHALL be case-sensitive and exact. The system SHALL NOT apply any case conversion to user-provided identity strings.

Normalization rules:
- If the caller provides an identity that starts with exact `AGENTSYS-`, the canonical agent name SHALL be exactly that value.
- Otherwise, the canonical agent name SHALL be `AGENTSYS-<identity>`.

Canonical agent names SHALL remain distinct from live tmux session handles. The system SHALL NOT require the canonical agent name to equal the actual tmux session name.

#### Scenario: Name without prefix is normalized
- **WHEN** a caller provides the agent name `gpu`
- **THEN** the canonical agent name is `AGENTSYS-gpu`

#### Scenario: Name with prefix is preserved
- **WHEN** a caller provides the agent name `AGENTSYS-gpu`
- **THEN** the canonical agent name is `AGENTSYS-gpu`

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
- **WHEN** the runtime starts a tmux-backed session with tmux session name `AGENTSYS-gpu-270b87`
- **THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the value is the absolute path of the session manifest persisted for that session
- **AND THEN** the tmux session environment contains `AGENTSYS_AGENT_DEF_DIR`
- **AND THEN** the value is the absolute path of the agent-definition root used for that session launch

#### Scenario: Resume re-publishes tmux env pointers when the effective agent-definition root is available
- **WHEN** the runtime resumes control of tmux session `AGENTSYS-gpu-270b87`
- **AND WHEN** resume has already determined the effective agent-definition root for that control operation
- **THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `AGENTSYS_AGENT_DEF_DIR`

### Requirement: tmux-backed non-CAO session manifests persist their tmux session identity
For tmux-backed non-CAO sessions (for example tmux-backed headless Claude/Gemini/Codex sessions), the persisted session manifest SHALL include the actual tmux session name used for runtime control and identity resolution.

The persisted tmux session name SHALL be stored in a deterministic field that can be validated on resume/control, for example:
- `payload.backend_state.tmux_session_name`

#### Scenario: Headless tmux-backed session persists its actual tmux session name
- **WHEN** the runtime starts a tmux-backed headless session with tmux session name `AGENTSYS-gpu-270b87`
- **THEN** the persisted session manifest includes `backend_state.tmux_session_name="AGENTSYS-gpu-270b87"`

#### Scenario: Headless tmux-backed manifest keeps canonical identity distinct from the suffixed tmux handle
- **WHEN** the runtime starts a tmux-backed headless session with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the tmux session name is `AGENTSYS-gpu-270b87`
- **THEN** the persisted session manifest includes `agent_name="AGENTSYS-gpu"`
- **AND THEN** it does not persist `agent_name="AGENTSYS-gpu-270b87"`

### Requirement: Name-based agent identities resolve to a session manifest and agent-definition root via tmux environment
When a caller provides a non-path-like `--agent-identity` value, the system SHALL:
1) normalize it to a canonical agent name,
2) resolve a unique live tmux session associated with that canonical agent name,
3) read `AGENTSYS_MANIFEST_PATH` from the resolved tmux session environment,
4) validate that `AGENTSYS_MANIFEST_PATH` points to an existing manifest file,
5) load the session manifest from that path,
6) validate the loaded manifest matches the resolved tmux session:
   - manifest backend is a tmux-backed backend kind,
   - the manifest persists the canonical `agent_name` equal to the addressed canonical agent identity, and
   - the manifest contains a persisted `tmux_session_name` equal to the actual tmux session used for resolution,
7) determine the effective agent-definition root as follows:
   - when the caller provided explicit `--agent-def-dir`, use that explicit path as the effective agent-definition root after resolving it to an absolute existing directory,
   - otherwise read `AGENTSYS_AGENT_DEF_DIR` from the resolved tmux session environment and validate that it is absolute and points to an existing directory,
8) proceed with resume/control operations using the resolved manifest path and effective agent-definition root.

The resolution path MAY accept an exact-canonical tmux session name as a legacy compatibility shortcut when such a session exists and its manifest matches the addressed canonical agent identity. For runtime-owned sessions whose tmux handle includes an agent-id suffix, the system SHALL resolve the tmux session from tmux-local or shared-registry metadata rather than requiring the live tmux session name to equal the canonical agent identity.

Resolution and control SHALL use the persisted manifest fields and tmux/session metadata described above rather than reverse-parsing the tmux session name string.

If more than one live tmux session or shared-registry record matches the same canonical agent identity, the system SHALL fail with an explicit ambiguity error rather than silently choosing one.

#### Scenario: Resolve a canonical agent name to a suffixed tmux session
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** live tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** that tmux session publishes `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR`
- **AND WHEN** the pointed manifest persists `agent_name="AGENTSYS-gpu"` and `tmux_session_name="AGENTSYS-gpu-270b87"`
- **THEN** the runtime loads the session manifest from the pointed path
- **AND THEN** the runtime uses the resolved agent-definition root from `AGENTSYS_AGENT_DEF_DIR` for resume/control

#### Scenario: Legacy exact-name tmux session still resolves when the manifest matches
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** tmux session `AGENTSYS-gpu` exists
- **AND WHEN** its manifest persists `agent_name="AGENTSYS-gpu"` and `tmux_session_name="AGENTSYS-gpu"`
- **THEN** the runtime may use that exact-canonical tmux session as a compatibility resolution path

#### Scenario: Missing tmux session fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** no live tmux session or fresh shared-registry record matches canonical agent identity `AGENTSYS-gpu`
- **THEN** the runtime rejects the operation with an explicit "agent not found" error

#### Scenario: Missing tmux env pointer fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing or blank in that tmux session environment
- **THEN** the runtime rejects the operation with an explicit "manifest pointer missing" error

#### Scenario: Missing tmux agent-definition pointer fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing or blank in that tmux session environment
- **THEN** the runtime rejects the operation with an explicit "agent definition pointer missing" error

#### Scenario: Non-absolute tmux agent-definition pointer fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` contains a relative path
- **THEN** the runtime rejects the operation with an explicit invalid-pointer error

#### Scenario: Stale tmux agent-definition pointer fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` points to a missing directory
- **THEN** the runtime rejects the operation with an explicit stale-pointer error

#### Scenario: Resolved manifest must match the resolved tmux session
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest persists a different `tmux_session_name`
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Resolved manifest must preserve the addressed canonical agent name
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest persists `agent_name="AGENTSYS-other"`
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Resolved manifest must be a tmux-backed session manifest
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest backend is not a tmux-backed backend kind
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Ambiguous canonical-name resolution fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** more than one live tmux session or fresh shared-registry record matches canonical agent identity `AGENTSYS-gpu`
- **THEN** the runtime rejects the operation with an explicit ambiguity error

### Requirement: Gateway-capable tmux-backed sessions expose stable attach pointers via tmux session environment
For gateway-capable tmux-backed sessions, the system SHALL set tmux session environment variables named:

- `AGENTSYS_GATEWAY_ATTACH_PATH`
- `AGENTSYS_GATEWAY_ROOT`

`AGENTSYS_GATEWAY_ATTACH_PATH` SHALL be the absolute path of the secret-free attach-contract file for that session.

`AGENTSYS_GATEWAY_ROOT` SHALL be the absolute path of the per-agent gateway root for that session.

For runtime-owned sessions in v1, `AGENTSYS_GATEWAY_ROOT` SHALL point to the nested `gateway/` subdirectory under that session's runtime-owned session root, and `AGENTSYS_GATEWAY_ATTACH_PATH` SHALL point to `<AGENTSYS_GATEWAY_ROOT>/attach.json`.

When a live gateway instance is currently attached, the system SHALL additionally set:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

`AGENTSYS_AGENT_GATEWAY_HOST` SHALL be the active gateway bind host for the currently running gateway instance for that session. Allowed values in this change are exactly `127.0.0.1` and `0.0.0.0`.

`AGENTSYS_AGENT_GATEWAY_PORT` SHALL be the decimal port number of the active HTTP gateway listener for that running gateway instance.

`AGENTSYS_GATEWAY_STATE_PATH` SHALL be the absolute path of the current gateway state artifact for the running gateway instance.

`AGENTSYS_GATEWAY_PROTOCOL_VERSION` SHALL identify the gateway protocol version expected for that session's gateway root, including the shared schema for `state.json` and `GET /v1/status`.

When tmux-backed backend code later resumes control of the same live session with effective attach or live gateway bindings available, it SHALL re-publish the same gateway discovery pointers into the tmux session environment.

#### Scenario: Session start sets stable attach pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session with tmux session name `AGENTSYS-gpu-270b87`
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** those pointers are absolute paths for that session's attach contract and nested session-owned gateway root even if no gateway instance is currently running

#### Scenario: Live gateway attach sets active gateway pointers
- **WHEN** a gateway instance is attached to tmux session `AGENTSYS-gpu-270b87`
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those pointers describe the currently running gateway instance

#### Scenario: Resume re-publishes attach pointers
- **WHEN** the runtime resumes control of gateway-capable tmux session `AGENTSYS-gpu-270b87`
- **AND WHEN** resume has already determined the effective attach metadata for that control operation
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`

### Requirement: Repository documentation SHALL reflect the implemented tmux naming contract
Once this change is implemented, repository documentation under `docs/` that describes runtime agent identity, tmux attach targets, or tmux-oriented troubleshooting SHALL reflect the implemented tmux naming contract.

That documentation SHALL:

- describe live tmux session handles as the actual persisted tmux handle rather than assuming they equal the canonical `AGENTSYS-<name>` identity,
- explain that canonical `agent_name` and live `tmux_session_name` remain distinct fields, and
- direct operators to the surfaced attach command or persisted runtime metadata when they need the exact tmux target.

#### Scenario: Runtime and troubleshooting docs no longer assume canonical identity equals tmux session name
- **WHEN** this change has been implemented
- **AND WHEN** a developer reads the relevant repository docs under `docs/` for runtime session control, tmux attach flows, or troubleshooting
- **THEN** those docs describe live tmux session handles using the new persisted tmux-handle contract
- **AND THEN** they do not instruct the developer to assume the live tmux session name is exactly `AGENTSYS-<name>`
