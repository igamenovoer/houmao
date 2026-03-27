## MODIFIED Requirements

### Requirement: Canonical component directories
The system SHALL organize reusable agent-definition sources under a stable on-disk layout rooted at `agents/`.

At minimum, that canonical layout SHALL include:

- `agents/skills/<skill>/SKILL.md`
- `agents/roles/<role>/system-prompt.md`
- `agents/roles/<role>/presets/<tool>/<setup>.yaml`
- `agents/tools/<tool>/adapter.yaml`
- `agents/tools/<tool>/setups/<setup>/...`
- `agents/tools/<tool>/auth/<auth>/...`

User-facing reusable launch metadata SHALL live in role-scoped presets plus tool-scoped setup/auth directories rather than in a separate recipe plus blueprint layer.

#### Scenario: Developer locates canonical sources
- **WHEN** a developer needs to add or modify reusable agent-definition sources
- **THEN** skill packages SHALL live under `agents/skills/`
- **AND THEN** role prompts SHALL live under `agents/roles/`
- **AND THEN** launchable preset files SHALL live under `agents/roles/<role>/presets/`
- **AND THEN** tool-specific setup and auth material SHALL live under `agents/tools/<tool>/`

### Requirement: Brain construction inputs
The system SHALL support constructing an agent runtime from a resolved preset together with one effective auth selection.

A resolved preset SHALL define or derive:
1. a target CLI tool,
2. a role package,
3. a tool-specific setup,
4. a set of skills to install,
5. an optional default auth selection, and
6. optional launch and mailbox settings.

Callers MAY override the preset's default auth selection at build or launch time.

#### Scenario: Brain inputs are explicitly selected through preset resolution
- **WHEN** a developer constructs a runtime for an agent run from a preset
- **THEN** the resolved tool, role, setup, skills, and effective auth SHALL be explicit inputs to the construction process
- **AND THEN** the effective auth MAY come from the preset default or a caller override

### Requirement: Skill repository format and installation
Brain skills SHALL be stored as directories under `agents/skills/` in the Agent Skills format, and each skill directory SHALL contain a `SKILL.md`. Constructed brains SHALL install only the selected skills into the runtime tool home.

#### Scenario: Selected skills are installed
- **WHEN** a brain is constructed selecting skills `S1` and `S2`
- **THEN** the runtime tool home SHALL contain installed skill entries for `S1` and `S2`
- **AND THEN** the runtime tool home SHALL NOT contain skills that were not selected

### Requirement: Tool adapter definitions
For each supported CLI tool, the system SHALL define a tool adapter at `agents/tools/<tool>/adapter.yaml` that specifies the runtime home layout and projection rules for:
- tool setup placement,
- skill installation placement,
- auth file projection, and
- auth environment variable injection.

Auth file mappings SHALL support an explicit `required` boolean. Missing `required` values SHALL default to `true`. Missing required auth files SHALL fail brain construction explicitly. Missing mappings with `required: false` SHALL be skipped without error.

#### Scenario: New tool support is adapter-driven
- **WHEN** a new CLI tool is added to the system
- **THEN** the primary mechanism to support it SHALL be adding a new tool adapter definition

#### Scenario: Missing required auth file fails explicitly
- **WHEN** brain construction encounters a required auth file mapping whose source file is absent
- **THEN** it SHALL fail with an explicit error identifying the missing mapping

#### Scenario: Missing optional auth file is skipped
- **WHEN** brain construction encounters an auth file mapping whose source file is absent
- **AND WHEN** that mapping sets `required: false`
- **THEN** it SHALL continue without projecting that file
- **AND THEN** any remaining auth env and file projections SHALL still proceed

#### Scenario: Optional auth file is projected when present
- **WHEN** brain construction encounters an auth file mapping whose source file exists
- **AND WHEN** that mapping sets `required: false`
- **THEN** it SHALL project that file into the runtime home using the configured mode

### Requirement: Resolved runtime manifest
Each constructed runtime home SHALL produce a resolved manifest that records the selected inputs, including tool, preset path, setup identifier, effective auth identifier, selected skills, the output home directory path, and the launch environment contract. The manifest MUST NOT contain secret values.

#### Scenario: Runtime manifest supports audit and reproducibility
- **WHEN** a brain is constructed successfully
- **THEN** a resolved manifest SHALL be written for that constructed home
- **AND THEN** the manifest SHALL identify the preset path, setup, auth, and selected components without including credential secrets

## ADDED Requirements

### Requirement: Tool-specific setup bundles
Tool setup bundles SHALL be stored under `agents/tools/<tool>/setups/<setup>/...`. Brain construction SHALL apply the selected tool setup bundle into the runtime tool home.

Setup bundles MUST be secret-free and MAY include tool-owned configuration files, command packs, or minimal bootstrap state needed for supported current launches.

One tool MAY provide multiple setup bundles, and setup identifiers SHALL be unique only within that tool's `setups/` namespace.

#### Scenario: Setup bundle is applied
- **WHEN** a brain is constructed for tool `<tool>` selecting setup `<setup>`
- **THEN** the runtime tool home SHALL include the tool input derived from `agents/tools/<tool>/setups/<setup>/...`

#### Scenario: Same tool supports multiple setup bundles
- **WHEN** a tool provides setup bundles `default` and `research`
- **THEN** both bundles MAY coexist under `agents/tools/<tool>/setups/`
- **AND THEN** their names do not need to be globally unique across other tools

### Requirement: Local-only auth bundles
Auth bundles SHALL be stored under `agents/tools/<tool>/auth/<auth>/` and MUST be local-only whenever they contain secrets. Brain construction SHALL project the selected auth bundle into the runtime tool home according to the selected tool adapter's projection contract.

One tool MAY provide multiple auth bundles, and auth identifiers SHALL be unique only within that tool's `auth/` namespace.

#### Scenario: Auth bundle is selected without committing secrets
- **WHEN** a brain is constructed selecting auth bundle `<auth>`
- **THEN** the runtime tool home SHALL contain the tool's auth material projected from `agents/tools/<tool>/auth/<auth>/`
- **AND THEN** the project SHALL NOT require committing secret material to version control

#### Scenario: Setup and auth remain independent axes
- **WHEN** a tool offers multiple setup bundles and multiple auth bundles
- **THEN** the system MAY combine one selected setup with one selected auth for the same tool
- **AND THEN** selecting one setup does not imply exactly one auth bundle

### Requirement: Auth bundles support projected environment values
Auth bundles SHALL support local env files containing the values required by CLI tools for authentication and routing. The system SHALL provide a launch mechanism that applies only the allowlisted subset of those variables defined by the selected tool adapter.

#### Scenario: Launch applies allowlisted auth env values
- **WHEN** a developer launches a CLI tool using a constructed brain whose adapter requires env-based auth
- **THEN** the tool process SHALL have the required allowlisted environment variables set as specified by the tool adapter and selected auth bundle
- **AND THEN** the resolved runtime manifest SHALL NOT include secret values

### Requirement: Path-derived agent presets
The system SHALL support declarative agent presets stored under `agents/roles/<role>/presets/<tool>/<setup>.yaml`.

Preset identity SHALL be derived from path rather than from duplicated inline identity fields. The preset path SHALL determine role, tool, and setup.

#### Scenario: Preset identity comes from path
- **WHEN** a developer creates `agents/roles/gpu-kernel-coder/presets/claude/default.yaml`
- **THEN** the system SHALL treat role=`gpu-kernel-coder`, tool=`claude`, and setup=`default` as that preset's identity
- **AND THEN** the preset file SHALL NOT require top-level `name`, `role`, or `tool` fields

### Requirement: Agent preset schema is minimal and extensible
Agent presets SHALL include only fields required by current behavior: selected skills, optional default auth, optional launch settings, optional mailbox settings, and optional `extra`.

The system SHALL NOT require build-time `default_agent_name` or other duplicated identity fields in preset files.

Non-core extension data SHALL live under `extra` rather than through pre-allocated unused top-level schema fields.

#### Scenario: Minimal preset omits build-time identity fields
- **WHEN** a developer authors a preset for one role, tool, and setup
- **THEN** the preset MAY omit `name`, `role`, `tool`, and `default_agent_name`
- **AND THEN** the system SHALL still resolve the preset successfully from its path and required core fields

#### Scenario: Non-core preset extensions live under extra
- **WHEN** a consumer needs secret-free subsystem-specific preset metadata outside the core schema
- **THEN** that metadata SHALL be stored under `extra`
- **AND THEN** the core preset resolution path SHALL NOT depend on unsupported top-level extension fields

### Requirement: Tracked interactive-demo presets
The repository SHALL provide tracked, declarative, secret-free presets under `agents/roles/<role>/presets/` for the interactive demo launch variants that the repo documents and verifies.

At minimum, the tracked preset set SHALL include:

- `agents/roles/gpu-kernel-coder/presets/claude/default.yaml`
- `agents/roles/gpu-kernel-coder/presets/codex/default.yaml`
- `agents/roles/gpu-kernel-coder/presets/codex/yunwu-openai.yaml`

Each tracked preset SHALL select skills and optional default auth by identifier only and SHALL NOT embed secret material.

#### Scenario: Developer can locate tracked preset variants for the GPU demo role
- **WHEN** a developer needs to inspect or update the supported launch variants for `gpu-kernel-coder`
- **THEN** the repo SHALL contain tracked presets under that role's `presets/` subtree for the documented tool/setup variants
- **AND THEN** those presets SHALL remain declarative and secret-free

## REMOVED Requirements

### Requirement: Tool-specific config profiles
**Reason**: The checked-in runtime input bundle is renamed to `setup` and moved under the per-tool canonical layout so it is no longer one of several unrelated concepts called "config".

**Migration**: Move `agents/brains/cli-configs/<tool>/<profile>/...` to `agents/tools/<tool>/setups/<setup>/...` and update build-time references from config-profile selection to setup selection.

### Requirement: Local-only credential profiles
**Reason**: The user-facing model is simplified by renaming credential profiles to auth bundles and colocating them under a per-tool layout.

**Migration**: Move `agents/brains/api-creds/<tool>/<cred-profile>/` to `agents/tools/<tool>/auth/<auth>/` and update loaders, manifests, and docs to use auth selection terminology.

### Requirement: Credential environment variables
**Reason**: Env projection behavior remains, but it now belongs to auth bundles rather than to a separate credential-profile concept.

**Migration**: Read allowlisted env values from the selected auth bundle's env files under `agents/tools/<tool>/auth/<auth>/`.

### Requirement: Brain recipes are declarative and secret-free
**Reason**: Path-derived presets replace the separate brain-recipe layer.

**Migration**: Move recipe-owned selections into `agents/roles/<role>/presets/<tool>/<setup>.yaml` and rely on path-derived identity instead of inline recipe metadata.

### Requirement: Brain recipes MAY declare a default agent name
**Reason**: Managed-agent identity is a launch-time concern, not reusable preset metadata.

**Migration**: Remove `default_agent_name` from presets and continue using explicit launch-time `agent_name` or the runtime's existing fallback identity behavior when launch-time identity is omitted.

### Requirement: Tracked interactive-demo brain recipes
**Reason**: Tracked demo launch variants should be represented as presets under the simplified role/tool/setup layout instead of recipe files.

**Migration**: Replace tracked recipe files with tracked preset files under the matching role subtree.

### Requirement: Optional agent blueprints bind brain and role
**Reason**: Path-derived presets remove the need for a second reusable file layer whose main purpose was binding recipe plus role while carrying duplicated naming metadata.

**Migration**: Fold blueprint-owned launch metadata into the matching preset file or `extra` and resolve launch targets directly from preset paths.
