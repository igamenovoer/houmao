## MODIFIED Requirements

### Requirement: Local-only credential profiles
Credential profiles SHALL be stored under `agents/brains/api-creds/<tool>/<cred-profile>/` and MUST be local-only (gitignored). Brain construction SHALL project the selected credential profile into the runtime tool home according to the selected tool adapter’s credential projection contract, including credential file mappings controlled by an explicit `required` flag plus credential env injection.

Env-backed profiles MUST NOT be forced to include placeholder credential files when the selected tool adapter marks those file mappings with `required: false`.

#### Scenario: Credentials are selected without committing secrets
- **WHEN** a brain is constructed selecting credential profile `<cred-profile>`
- **THEN** the runtime tool home SHALL contain the tool’s credential material projected from `agents/brains/api-creds/<tool>/<cred-profile>/` according to the selected tool adapter’s required and optional mappings
- **AND THEN** the project SHALL NOT require committing credential files to version control

#### Scenario: Env-backed Codex profile omits optional auth.json
- **WHEN** a Codex credential profile relies on config plus env vars for authentication and does not provide `files/auth.json`
- **AND WHEN** the selected Codex tool adapter marks that mapping with `required: false`
- **THEN** brain construction SHALL still succeed
- **AND THEN** the constructed runtime home SHALL still receive the profile’s env-based credentials

### Requirement: Tool adapter definitions
For each supported CLI tool, the system SHALL define a tool adapter under `agents/brains/tool-adapters/` that specifies the runtime home layout and projection rules for:
- tool config placement,
- skill installation placement, and
- credential file projection, and
- credential environment variable injection.

Credential file mappings SHALL support an explicit `required` boolean. Missing `required` values SHALL default to `true`. Missing required credential files SHALL fail brain construction explicitly. Missing mappings with `required: false` SHALL be skipped without error.

#### Scenario: New tool support is adapter-driven
- **WHEN** a new CLI tool is added to the system
- **THEN** the primary mechanism to support it SHALL be adding a new tool adapter definition

#### Scenario: Missing required credential file fails explicitly
- **WHEN** brain construction encounters a required credential file mapping whose source file is absent
- **THEN** it SHALL fail with an explicit error identifying the missing mapping

#### Scenario: Missing optional credential file is skipped
- **WHEN** brain construction encounters a credential file mapping whose source file is absent
- **AND WHEN** that mapping sets `required: false`
- **THEN** it SHALL continue without projecting that file
- **AND THEN** any remaining credential env and file projections SHALL still proceed

#### Scenario: Optional credential file is projected when present
- **WHEN** brain construction encounters a credential file mapping whose source file exists
- **AND WHEN** that mapping sets `required: false`
- **THEN** it SHALL project that file into the runtime home using the configured mode

### Requirement: Codex launch prerequisites
Codex launch preparation SHALL refuse launch unless the effective runtime state contains at least one usable authentication path: a valid `auth.json` login state in the runtime home or `OPENAI_API_KEY` in the effective runtime environment. The Codex bootstrap path SHALL perform this validation using the same effective runtime environment that will be used for the launch.

A valid Codex `auth.json` login state SHALL parse as a non-empty top-level JSON object. Placeholder files such as `{}` SHALL NOT satisfy this requirement by themselves.

#### Scenario: Codex launch is rejected when no auth path exists
- **WHEN** a Codex runtime home has no usable `auth.json` login state
- **AND WHEN** `OPENAI_API_KEY` is absent from the effective runtime environment
- **THEN** the system SHALL refuse to launch Codex
- **AND THEN** the error SHALL state that Codex requires either valid `auth.json` or `OPENAI_API_KEY`

#### Scenario: Empty auth.json does not satisfy launch prerequisites
- **WHEN** a Codex runtime home contains `auth.json`
- **AND WHEN** that file parses as an empty top-level JSON object
- **AND WHEN** `OPENAI_API_KEY` is absent from the effective runtime environment
- **THEN** the system SHALL refuse to launch Codex
- **AND THEN** the error SHALL treat that file as unusable login state

#### Scenario: Env-only Codex launch remains valid
- **WHEN** a Codex runtime home has no `auth.json`
- **AND WHEN** `OPENAI_API_KEY` is present in the effective runtime environment
- **THEN** the system SHALL allow Codex launch preparation to continue
