## MODIFIED Requirements

### Requirement: Auth bundles support projected environment values

Auth bundles SHALL support local env files containing the values required by CLI tools for authentication and routing. The system SHALL provide a launch mechanism that applies only the allowlisted subset of those variables defined by the selected tool adapter.

Auth-bundle env SHALL remain a credential-owned channel distinct from specialist-owned launch env records. The system SHALL NOT require persistent specialist launch env to be stored in the auth bundle env file.

#### Scenario: Launch applies allowlisted auth env values

- **WHEN** a developer launches a CLI tool using a constructed brain whose adapter requires env-based auth
- **THEN** the tool process SHALL have the required allowlisted environment variables set as specified by the tool adapter and selected auth bundle
- **AND THEN** the resolved runtime manifest SHALL NOT include secret values

#### Scenario: Persistent specialist env records stay separate from auth env

- **WHEN** a specialist declares persistent launch env records
- **THEN** those records are treated as specialist launch config
- **AND THEN** the system does not require them to live inside the selected auth bundle env file as though they were credentials

### Requirement: Agent preset schema is minimal and extensible

Agent presets SHALL include only fields required by current behavior: selected skills, optional default auth, optional launch settings, optional mailbox settings, and optional `extra`.

The system SHALL NOT require build-time `default_agent_name` or other duplicated identity fields in preset files.

If present, preset `launch` SHALL be an object containing optional `prompt_mode`, optional `overrides`, and optional `env_records`.

`launch.overrides`, when present, SHALL use the existing launch-overrides shape of optional `args` and optional `tool_params`.

Allowed `launch.prompt_mode` values SHALL be `unattended` and `as_is`.

`launch.env_records`, when present, SHALL be a mapping of non-empty env names to string values representing persistent specialist-owned launch env records.

`launch.env_records` SHALL remain distinct from credential env:

- env names that belong to the selected tool adapter's auth-env allowlist SHALL be rejected
- Houmao-owned reserved env names SHALL be rejected

Unknown top-level preset fields SHALL be rejected. Non-core extension data SHALL live under `extra` rather than through pre-allocated unused top-level schema fields.

#### Scenario: Minimal preset omits build-time identity fields

- **WHEN** a developer authors a preset for one role, tool, and setup
- **THEN** the preset MAY omit `name`, `role`, `tool`, and `default_agent_name`
- **AND THEN** the system SHALL still resolve the preset successfully from its path and required core fields

#### Scenario: Launch settings use one explicit schema

- **WHEN** a developer authors preset-owned launch behavior
- **THEN** `prompt_mode` SHALL appear under `launch.prompt_mode`
- **AND THEN** `launch.prompt_mode` SHALL use only `unattended` or `as_is`
- **AND THEN** any preset-owned launch overrides SHALL appear under `launch.overrides`
- **AND THEN** persistent specialist env records SHALL appear under `launch.env_records`
- **AND THEN** `launch.overrides` SHALL use only the supported `args` and `tool_params` sections

#### Scenario: Specialist env record using a credential-owned env name is rejected

- **WHEN** a preset declares `launch.env_records.OPENAI_API_KEY`
- **AND WHEN** the selected tool adapter owns `OPENAI_API_KEY` through its auth-env allowlist
- **THEN** preset validation SHALL fail explicitly
- **AND THEN** the error SHALL identify that `OPENAI_API_KEY` belongs to credential env rather than persistent specialist env records

#### Scenario: Non-core preset extensions live under extra

- **WHEN** a consumer needs secret-free subsystem-specific preset metadata outside the core schema
- **THEN** that metadata SHALL be stored under `extra`
- **AND THEN** the core preset resolution path SHALL NOT depend on unsupported top-level extension fields
- **AND THEN** preserved gateway defaults, when needed for migrated blueprint behavior, SHALL live under `extra.gateway`

### Requirement: Resolved runtime manifest

Each constructed runtime home SHALL produce a resolved manifest that records the selected inputs, including tool, preset path, setup identifier, effective auth identifier, selected skills, the output home directory path, and the launch environment contract. The manifest MUST NOT contain secret values from credential env.

The resolved manifest SHALL use `schema_version: 3`.

When persistent specialist env records are present, the resolved manifest SHALL record them as a launch-owned env contract separate from the credential env contract.

That launch-owned env contract is additive to the existing launch-policy intent contract such as `launch_policy.operator_prompt_mode`; it SHALL NOT replace or redefine prompt-policy semantics.

#### Scenario: Runtime manifest supports audit and reproducibility

- **WHEN** a brain is constructed successfully
- **THEN** a resolved manifest SHALL be written for that constructed home
- **AND THEN** the manifest SHALL identify the preset path, setup, auth, and selected components without including credential secrets
- **AND THEN** the manifest SHALL record `schema_version: 3`

#### Scenario: Runtime manifest keeps persistent specialist env separate from credential env contract

- **WHEN** a specialist declares persistent launch env records
- **THEN** the resolved manifest records those env records as launch-owned persistent config
- **AND THEN** the credential env contract remains a separate auth-owned section rather than being merged with those specialist records

### Requirement: Runtime launches inherit the calling process environment

The system SHALL propagate the full calling process environment into tmux-based launches, and then apply brain-owned and operator-owned overlays.

Environment precedence is:
1. calling process environment (base),
2. auth-bundle env file values selected by the tool adapter allowlist (overlay),
3. persistent specialist `launch.env_records` (overlay),
4. one-off instance-launch additional env for the current live session (overlay), and
5. launch-specific runtime-owned env vars (overlay; for example tool home selector env vars).

Auth-bundle env injection SHALL respect the selected tool adapter's allowlist rather than exporting unrelated auth-bundle env entries.

Persistent specialist env records SHALL survive rebuild and relaunch because they are part of the built specialist launch contract.

One-off instance-launch `--env-set` additional env SHALL affect only the current live session and SHALL NOT become part of the durable specialist launch contract.

#### Scenario: Tmux launch inherits caller env and overlays allowlisted auth env

- **WHEN** the system starts a tool session in tmux
- **THEN** the tmux session environment SHALL inherit environment variables from the calling process
- **AND THEN** the tmux session environment SHALL include the allowlisted variables declared in the selected auth bundle env file, overriding inherited values when names collide

#### Scenario: Persistent specialist env overlays auth and inherited base env

- **WHEN** the calling process environment or selected auth bundle provides `FEATURE_FLAG_X=0`
- **AND WHEN** the selected specialist declares persistent launch env record `FEATURE_FLAG_X=1`
- **THEN** the effective launch environment SHALL use `FEATURE_FLAG_X=1`
- **AND THEN** that value survives later launch-plan rebuild for the same specialist

#### Scenario: One-off instance env-set overrides persistent specialist env for the current live session only

- **WHEN** the selected specialist declares persistent launch env record `FEATURE_FLAG_X=1`
- **AND WHEN** the operator starts one live session with one-off `--env-set FEATURE_FLAG_X=2`
- **THEN** that current live session uses `FEATURE_FLAG_X=2`
- **AND THEN** the specialist's durable launch config remains `FEATURE_FLAG_X=1`
