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
- **WHEN** a caller provides `--agent-identity /abs/path/.houmao/runtime/sessions/cao_rest/session-20260101-000000Z-abcd1234/manifest.json`
- **AND WHEN** that file exists
- **THEN** the runtime loads the session manifest from that path and resumes the session

#### Scenario: Missing path-like identity fails fast
- **WHEN** a caller provides `--agent-identity /abs/path/.houmao/runtime/sessions/cao_rest/missing/manifest.json`
- **AND WHEN** that file does not exist
- **THEN** the runtime rejects the operation with an explicit "manifest not found" error

#### Scenario: Non-path-like identity resolves as an agent name
- **WHEN** a caller provides `--agent-identity gpu`
- **THEN** the runtime treats the identity as an agent name and applies agent-name normalization rules

### Requirement: Agent identities use an exact `AGENTSYS-` namespace prefix (no case conversion)
For tmux-backed sessions, the system SHALL normalize agent identities into canonical agent names using the namespace prefix `HOUMAO-`.

Prefix matching SHALL be case-sensitive and exact. The system SHALL NOT apply any case conversion to user-provided identity strings.

Normalization rules:
- If the caller provides an identity that starts with exact `HOUMAO-`, the canonical agent name SHALL be exactly that value.
- Otherwise, the canonical agent name SHALL be `HOUMAO-<identity>`.

Canonical agent names SHALL remain distinct from live tmux session handles. The system SHALL NOT require the canonical agent name to equal the actual tmux session name.

#### Scenario: Name without prefix is normalized
- **WHEN** a caller provides the agent name `gpu`
- **THEN** the canonical agent name is `HOUMAO-gpu`

#### Scenario: Name with prefix is preserved
- **WHEN** a caller provides the agent name `HOUMAO-gpu`
- **THEN** the canonical agent name is `HOUMAO-gpu`

### Requirement: Inexact `AGENTSYS` look-alikes trigger a warning when the exact prefix is missing
When the caller provides an identity that does not start with exact `HOUMAO-` and the identity contains the substring `HOUMAO` in a case-insensitive way, the system SHALL emit a warning indicating that the namespace prefix did not match exactly.

The warning SHALL NOT change canonicalization behavior. The identity is still treated as missing the exact prefix and is normalized by prefixing `HOUMAO-`.

#### Scenario: Inexact prefix casing triggers a warning but is still treated as missing prefix
- **WHEN** a caller provides the agent identity `houmao-gpu`
- **THEN** the system emits a warning about an inexact `HOUMAO-` prefix match
- **AND THEN** the canonical tmux session identity is `HOUMAO-houmao-gpu`

### Requirement: User-provided agent names are validated and MUST NOT contain a standalone `AGENTSYS` token
The system SHALL validate the user-provided agent name portion for tmux-backed managed launches using a conservative character set that is safe for both tmux session names and Unix-style filenames.

Allowed characters for the user-provided agent name portion are ASCII letters, ASCII digits, underscore (`_`), and hyphen (`-`). The user-provided agent name portion MUST start with an ASCII letter or digit.

Additionally, the user-provided agent name portion MUST NOT begin with a case-insensitive `HOUMAO` token immediately followed by a non-alphanumeric separator.

This validation SHALL be applied before the runtime canonicalizes the managed-agent name into `HOUMAO-<name>` form.

#### Scenario: Exact uppercase reserved prefix with hyphen is rejected
- **WHEN** a caller provides managed-agent name `HOUMAO-james`
- **THEN** the system rejects the operation with an explicit reserved-prefix error

#### Scenario: Lowercase reserved prefix with hyphen is rejected
- **WHEN** a caller provides managed-agent name `houmao-james`
- **THEN** the system rejects the operation with an explicit reserved-prefix error

### Requirement: tmux-backed sessions expose their manifest path and agent-definition root via tmux session environment
For tmux-backed sessions, the system SHALL set tmux session environment variables named:
- `HOUMAO_MANIFEST_PATH`
- `HOUMAO_AGENT_DEF_DIR`

`HOUMAO_MANIFEST_PATH` SHALL be the absolute path of the persisted session manifest JSON for that session.

`HOUMAO_AGENT_DEF_DIR` SHALL be the absolute path of the agent-definition root used for that session launch.

When tmux-backed backend code later resumes control of the same live session with an effective agent-definition root available, it SHALL re-publish the same two pointers into the tmux session environment.

#### Scenario: Session start sets tmux env pointers
- **WHEN** the runtime starts a tmux-backed session with tmux session name `HOUMAO-gpu-270b87`
- **THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `HOUMAO_AGENT_DEF_DIR`

#### Scenario: Resume re-publishes tmux env pointers
- **WHEN** the runtime resumes control of tmux session `HOUMAO-gpu-270b87`
- **THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `HOUMAO_AGENT_DEF_DIR`

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
3) read `HOUMAO_MANIFEST_PATH` from the resolved tmux session environment,
4) validate that `HOUMAO_MANIFEST_PATH` points to an existing manifest file,
5) load the session manifest from that path,
6) validate the loaded manifest matches the resolved tmux session:
   - manifest backend is a tmux-backed backend kind,
   - the manifest persists the canonical `agent_name` equal to the addressed canonical agent identity, and
   - the manifest contains a persisted `tmux_session_name` equal to the actual tmux session used for resolution,
7) determine the effective agent-definition root as follows:
   - when the caller provided explicit `--agent-def-dir`, use that explicit path as the effective agent-definition root after resolving it to an absolute existing directory,
   - otherwise read `HOUMAO_AGENT_DEF_DIR` from the resolved tmux session environment and validate that it is absolute and points to an existing directory,
8) proceed with resume/control operations using the resolved manifest path and effective agent-definition root.

The resolution path MAY accept an exact-canonical tmux session name as a legacy compatibility shortcut when such a session exists and its manifest matches the addressed canonical agent identity. For runtime-owned sessions whose tmux handle differs from the canonical agent identity, the system SHALL resolve the tmux session from tmux-local or shared-registry metadata rather than requiring the live tmux session name to equal the canonical agent identity.

Resolution and control SHALL use the persisted manifest fields and tmux/session metadata described above rather than reverse-parsing the tmux session name string.

If more than one live tmux session or shared-registry record matches the same canonical agent identity, the system SHALL fail with an explicit ambiguity error rather than silently choosing one.

#### Scenario: Resolve a canonical agent name to a suffixed tmux session
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** live tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** that tmux session publishes `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_DEF_DIR`
- **AND WHEN** the pointed manifest persists `agent_name="AGENTSYS-gpu"` and `tmux_session_name="AGENTSYS-gpu-270b87"`
- **THEN** the runtime loads the session manifest from the pointed path
- **AND THEN** the runtime uses the resolved agent-definition root from `HOUMAO_AGENT_DEF_DIR` for resume/control

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
- **AND WHEN** `HOUMAO_MANIFEST_PATH` is missing or blank in that tmux session environment
- **THEN** the runtime rejects the operation with an explicit "manifest pointer missing" error

#### Scenario: Missing tmux agent-definition pointer fails with an explicit resolution error
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `HOUMAO_AGENT_DEF_DIR` is missing or blank in that tmux session environment
- **THEN** the runtime rejects the operation with an explicit "agent definition pointer missing" error

#### Scenario: Non-absolute tmux agent-definition pointer fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `HOUMAO_AGENT_DEF_DIR` contains a relative path
- **THEN** the runtime rejects the operation with an explicit invalid-pointer error

#### Scenario: Stale tmux agent-definition pointer fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** the caller does not provide explicit `--agent-def-dir`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `HOUMAO_AGENT_DEF_DIR` points to a missing directory
- **THEN** the runtime rejects the operation with an explicit stale-pointer error

#### Scenario: Resolved manifest must match the resolved tmux session
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `HOUMAO_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest persists a different `tmux_session_name`
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Resolved manifest must preserve the addressed canonical agent name
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `HOUMAO_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest persists `agent_name="AGENTSYS-other"`
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Resolved manifest must be a tmux-backed session manifest
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** resolved tmux session `AGENTSYS-gpu-270b87` exists
- **AND WHEN** `HOUMAO_MANIFEST_PATH` points to an existing session manifest file
- **AND WHEN** the loaded manifest backend is not a tmux-backed backend kind
- **THEN** the runtime rejects the operation with an explicit manifest-mismatch error

#### Scenario: Ambiguous canonical-name resolution fails explicitly
- **WHEN** a caller provides `--agent-identity gpu`
- **AND WHEN** more than one live tmux session or fresh shared-registry record matches canonical agent identity `AGENTSYS-gpu`
- **THEN** the runtime rejects the operation with an explicit ambiguity error

### Requirement: Gateway-capable tmux-backed sessions expose stable attach pointers via tmux session environment
For gateway-capable tmux-backed sessions, the system SHALL publish stable gateway attach pointers through tmux session environment variables:
- `HOUMAO_GATEWAY_ATTACH_PATH`
- `HOUMAO_GATEWAY_ROOT`
- `HOUMAO_AGENT_GATEWAY_HOST`
- `HOUMAO_AGENT_GATEWAY_PORT`
- `HOUMAO_GATEWAY_STATE_PATH`
- `HOUMAO_GATEWAY_PROTOCOL_VERSION`

Those variables SHALL replace the old `AGENTSYS_*` gateway pointer family on supported live sessions.

#### Scenario: Runtime-owned session publishes stable gateway attach pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session with tmux session name `HOUMAO-gpu-270b87`
- **THEN** the tmux session environment contains `HOUMAO_GATEWAY_ATTACH_PATH` and `HOUMAO_GATEWAY_ROOT`

#### Scenario: Attached gateway publishes live gateway bindings
- **WHEN** a gateway instance is attached to tmux session `HOUMAO-gpu-270b87`
- **THEN** the tmux session environment contains `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, `HOUMAO_GATEWAY_STATE_PATH`, and `HOUMAO_GATEWAY_PROTOCOL_VERSION`

### Requirement: Name-resolved tmux identities allow optional gateway discovery for gateway-aware tools
When a caller resolves a non-path-like `--agent-identity` value to a live tmux-backed session, gateway-aware tools SHALL be able to discover stable gateway attachability and, when present, live gateway bindings from that tmux session environment.

Missing gateway pointers SHALL NOT make legacy non-gateway session resolution fail by themselves.

When a caller uses a gateway-aware lifecycle or control path that requires attachability or a live gateway instance and the required gateway pointers are missing or invalid, the system SHALL fail with an explicit gateway-discovery error rather than silently bypassing gateway discovery.

#### Scenario: Legacy session still resolves without gateway pointers
- **WHEN** a caller resolves a live tmux-backed session that publishes no gateway attach metadata
- **AND WHEN** `HOUMAO_GATEWAY_ATTACH_PATH`, `HOUMAO_GATEWAY_ROOT`, and related gateway pointers are absent from that tmux session environment
- **THEN** the existing non-gateway agent-identity resolution still succeeds
- **AND THEN** gateway-pointer absence alone does not make that legacy resolution fail

#### Scenario: Attach-aware resolution fails explicitly on missing attach metadata
- **WHEN** a caller uses a gateway attach-aware lifecycle path for a live tmux-backed session that is expected to be gateway-capable
- **AND WHEN** the tmux session environment is missing or contains invalid required attach pointers such as `HOUMAO_GATEWAY_ATTACH_PATH`
- **THEN** the system fails that lifecycle path with an explicit gateway-discovery error
- **AND THEN** it does not silently guess unrelated attach metadata for that session

### Requirement: Runtime-owned tmux session names use canonical agent name and launch timestamp by default
When the runtime derives a default tmux session name for a managed session, it SHALL use the canonical `HOUMAO-<name>` identity plus the launch timestamp suffix rather than the retired `AGENTSYS-<name>` prefix family.

#### Scenario: Default managed session name uses HOUMAO prefix
- **WHEN** the runtime starts a tmux-backed managed session with canonical agent name `HOUMAO-james`
- **AND WHEN** no live tmux session already occupies `HOUMAO-james-1760000123456`
- **THEN** the live tmux session name is `HOUMAO-james-1760000123456`

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
