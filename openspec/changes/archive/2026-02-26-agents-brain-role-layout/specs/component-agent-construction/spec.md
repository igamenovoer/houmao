## ADDED Requirements

### Requirement: Canonical component directories
The system SHALL organize reusable agent “brain” components and brain-agnostic “roles” under a stable on-disk layout rooted at `agents/`.

#### Scenario: Developer locates canonical sources
- **WHEN** a developer needs to add or modify reusable brain components (skills, tool configs, credentials, recipes)
- **THEN** they SHALL do so under `agents/brains/`
- **AND THEN** role packages SHALL be stored under `agents/roles/`

### Requirement: Brain construction inputs
The system SHALL support constructing an agent “brain” by selecting:
1) a target CLI tool,
2) a set of skills to install,
3) a tool-specific config profile, and
4) a credential profile.

#### Scenario: Brain inputs are explicitly selected
- **WHEN** a developer constructs a brain for an agent run
- **THEN** the selected tool, skills, config profile, and credential profile SHALL be explicit inputs to the construction process

### Requirement: Fresh-by-default runtime home creation
Brain construction SHALL create a fresh runtime CLI home directory with no pre-existing tool history, logs, or sessions at creation time.

#### Scenario: Fresh home has no pre-existing history
- **WHEN** a new runtime home is constructed
- **THEN** the constructed home SHALL NOT contain copied-in prior-run history/log/session artifacts
- **AND THEN** any history/log/session artifacts SHALL only appear after the CLI tool is started and begins writing state

### Requirement: Configurable runtime root location
The system SHALL support constructing runtime homes under a configurable runtime root directory. The runtime root directory MUST NOT be required to live under `agents/`.

#### Scenario: Build runtime home outside the repo
- **WHEN** a developer constructs a brain with `runtime_root` set to an arbitrary writable directory path
- **THEN** the constructed home, manifests, and optional locks SHALL be written under that runtime root

### Requirement: Runtime home lifecycle is manual-delete
The system SHALL treat constructed runtime homes as persistent until manually deleted by the developer.

#### Scenario: Preserve history by keeping the directory
- **WHEN** a developer wants to preserve tool history across runs
- **THEN** they SHALL be able to do so by reusing an existing constructed home directory
- **AND THEN** deletion of constructed homes SHALL be a manual developer action

### Requirement: Skill repository format and installation
Brain skills SHALL be stored as directories under `agents/brains/skills/` in the Agent Skills format (each skill directory contains a `SKILL.md`). Constructed brains SHALL install only the selected skills into the runtime tool home.

#### Scenario: Selected skills are installed
- **WHEN** a brain is constructed selecting skills `S1` and `S2`
- **THEN** the runtime tool home SHALL contain installed skill entries for `S1` and `S2`
- **AND THEN** the runtime tool home SHALL NOT contain skills that were not selected

### Requirement: Tool-specific config profiles
Tool configuration profiles SHALL be stored under `agents/brains/cli-configs/<tool>/<profile>/...`. Brain construction SHALL apply the selected tool config profile into the runtime tool home.

#### Scenario: Config profile is applied
- **WHEN** a brain is constructed for tool `<tool>` selecting config profile `<profile>`
- **THEN** the runtime tool home SHALL include the tool configuration derived from `agents/brains/cli-configs/<tool>/<profile>/...`

### Requirement: Local-only credential profiles
Credential profiles SHALL be stored under `agents/brains/api-creds/<tool>/<cred-profile>/` and MUST be local-only (gitignored). Brain construction SHALL project the selected credential profile into the runtime tool home as required by the target tool.

#### Scenario: Credentials are selected without committing secrets
- **WHEN** a brain is constructed selecting credential profile `<cred-profile>`
- **THEN** the runtime tool home SHALL contain the tool’s credential material projected from `agents/brains/api-creds/<tool>/<cred-profile>/`
- **AND THEN** the project SHALL NOT require committing credential files to version control

### Requirement: Credential environment variables
Credential profiles SHALL support storing environment variable values required by CLI tools for authentication and routing (for example API keys) in a local-only credential env file (for example `agents/brains/api-creds/<tool>/<cred-profile>/env/vars.env`). The system SHALL provide a launch mechanism that applies an allowlisted subset of those variables when starting the CLI tool for a constructed brain.

#### Scenario: Launch applies env-based credentials
- **WHEN** a developer launches a CLI tool using a constructed brain whose adapter requires env-based credentials
- **THEN** the tool process SHALL have the required environment variables set as specified by the tool adapter and credential profile
- **AND THEN** the resolved runtime manifest SHALL NOT include secret values (only env var names and local paths)

### Requirement: Tool adapter definitions
For each supported CLI tool, the system SHALL define a tool adapter under `agents/brains/tool-adapters/` that specifies the runtime home layout and projection rules for:
- tool config placement,
- skill installation placement, and
- credential file projection, and
- credential environment variable injection.

#### Scenario: New tool support is adapter-driven
- **WHEN** a new CLI tool is added to the system
- **THEN** the primary mechanism to support it SHALL be adding a new tool adapter definition

### Requirement: Brain recipes are declarative and secret-free
The system SHALL support declarative “brain recipes” that select the target tool, skill set, config profile, and credential profile by name/path. Brain recipes MUST NOT embed secret values.

#### Scenario: Brain recipe contains no secrets
- **WHEN** a brain recipe is created or modified
- **THEN** it SHALL reference credential profiles by identifier (e.g., `<cred-profile>`) rather than including API keys or tokens inline

### Requirement: Resolved runtime manifest
Each constructed runtime home SHALL produce a resolved manifest that records the selected inputs (tool, skills, config profile, credential profile identifier), the output home directory path, and the launch environment contract (env var names and local paths needed to source values). The manifest MUST NOT contain secret values.

#### Scenario: Runtime manifest supports audit and reproducibility
- **WHEN** a brain is constructed successfully
- **THEN** a resolved manifest SHALL be written for that constructed home
- **AND THEN** the manifest SHALL identify the selected components without including credential secrets

### Requirement: Brain-agnostic role packages
Roles SHALL be defined independently of the CLI tool (“brain-agnostic”). A role SHALL include a `system-prompt.md` and MAY include supporting files referenced by the prompt.

#### Scenario: Role prompt references supporting files
- **WHEN** a role’s `system-prompt.md` references a supporting file under the role directory
- **THEN** that supporting file SHALL exist within the role package

### Requirement: Optional agent blueprints bind brain and role
The system MAY support “agent blueprints” that bind a brain recipe and a role into a named agent definition. Blueprints MUST remain secret-free.

#### Scenario: Blueprint binds brain and role without secrets
- **WHEN** an agent blueprint is defined
- **THEN** it SHALL reference a brain recipe and a role by identifier/path
- **AND THEN** it SHALL NOT include credential material inline
