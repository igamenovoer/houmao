## MODIFIED Requirements

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

### Requirement: Runtime-owned tmux session names use canonical agent name and launch timestamp by default
When the runtime derives a default tmux session name for a managed session, it SHALL use the canonical `HOUMAO-<name>` identity plus the launch timestamp suffix rather than the retired `AGENTSYS-<name>` prefix family.

#### Scenario: Default managed session name uses HOUMAO prefix
- **WHEN** the runtime starts a tmux-backed managed session with canonical agent name `HOUMAO-james`
- **AND WHEN** no live tmux session already occupies `HOUMAO-james-1760000123456`
- **THEN** the live tmux session name is `HOUMAO-james-1760000123456`

