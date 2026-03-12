# component-agent-construction Specification

## Purpose
Define the expected structure and semantics for reusable agent components, declarative brain recipes, and runtime brain construction inputs.

## Requirements

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
Brain construction SHALL create a fresh runtime CLI home directory with no pre-existing tool history, logs, or sessions at creation time. The system SHALL support pre-seeding minimal tool bootstrap configuration/state required for unattended startup, provided it is not copied from prior-run history/log/session artifacts.

#### Scenario: Fresh home has no pre-existing history
- **WHEN** a new runtime home is constructed
- **THEN** the constructed home SHALL NOT contain copied-in prior-run history/log/session artifacts
- **AND THEN** any history/log/session artifacts SHALL only appear after the CLI tool is started and begins writing state
- **AND THEN** any pre-seeded tool bootstrap configuration/state files present at creation time MUST NOT be copied from prior-run history/log/session artifacts
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
Credential profiles SHALL be stored under `agents/brains/api-creds/<tool>/<cred-profile>/` and MUST be local-only (gitignored). Brain construction SHALL project the selected credential profile into the runtime tool home according to the selected tool adapter's credential projection contract, including credential file mappings controlled by an explicit `required` flag plus credential env injection.

Env-backed profiles MUST NOT be forced to include placeholder credential files when the selected tool adapter marks those file mappings with `required: false`.

#### Scenario: Credentials are selected without committing secrets
- **WHEN** a brain is constructed selecting credential profile `<cred-profile>`
- **THEN** the runtime tool home SHALL contain the tool’s credential material projected from `agents/brains/api-creds/<tool>/<cred-profile>/` according to the selected tool adapter's required and optional mappings
- **AND THEN** the project SHALL NOT require committing credential files to version control

#### Scenario: Env-backed Codex profile omits optional auth.json
- **WHEN** a Codex credential profile relies on config plus env vars for authentication and does not provide `files/auth.json`
- **AND WHEN** the selected Codex tool adapter marks that mapping with `required: false`
- **THEN** brain construction SHALL still succeed
- **AND THEN** the constructed runtime home SHALL still receive the profile's env-based credentials

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

### Requirement: Brain recipes are declarative and secret-free
The system SHALL support declarative “brain recipes” that select the target tool, skill set, config profile, and credential profile by name/path. Brain recipes MUST NOT embed secret values.

#### Scenario: Brain recipe contains no secrets
- **WHEN** a brain recipe is created or modified
- **THEN** it SHALL reference credential profiles by identifier (e.g., `<cred-profile>`) rather than including API keys or tokens inline

### Requirement: Brain recipes MAY declare a default agent name
The system SHALL support an optional `default_agent_name` field in brain
recipes for consumers that want a recipe-owned default identity name in
addition to the recipe's tool, skill, config-profile, and
credential-profile selections.

When present, `default_agent_name` SHALL be secret-free metadata and SHALL be
valid input to the system's existing agent-name normalization and validation
rules.

#### Scenario: Brain recipe carries a reusable default agent name
- **WHEN** a developer creates or updates a brain recipe that is intended to launch directly without an external blueprint-provided name
- **THEN** the recipe may declare `default_agent_name`
- **AND** that field remains separate from the recipe identifier in `name`
- **AND** the recipe remains declarative and secret-free

#### Scenario: Shared recipe loading accepts a recipe with default_agent_name
- **WHEN** the system loads a brain recipe file that includes `default_agent_name`
- **THEN** shared recipe parsing succeeds
- **AND** the loaded recipe exposes that `default_agent_name` value to downstream consumers

#### Scenario: Shared recipe loading remains compatible with recipes that omit default_agent_name
- **WHEN** the system loads a brain recipe file that does not include `default_agent_name`
- **THEN** shared recipe parsing still succeeds
- **AND** downstream consumers can treat the default agent name as absent

### Requirement: Tracked interactive-demo brain recipes
The repository SHALL provide tracked, declarative, secret-free brain recipes
under `agents/brains/brain-recipes/` for the interactive CAO full-pipeline
demo launch variants that the repo documents and verifies.

The tracked interactive-demo recipe set SHALL include at minimum:

- `claude/gpu-kernel-coder-default`
- `codex/gpu-kernel-coder-default`
- `codex/gpu-kernel-coder-yunwu-openai`

Each tracked recipe SHALL continue to select its tool, skills, config profile,
and credential profile by identifier only and SHALL NOT embed secret material.
Each tracked interactive-demo recipe SHALL also declare
`default_agent_name` so the interactive demo can launch from the recipe without
requiring a separate hard-coded default identity. The tracked interactive-demo
recipe set SHALL use tool-specific `default_agent_name` values rather than one
shared cross-tool default name.

#### Scenario: Developer can locate the tracked default Claude demo recipe
- **WHEN** a developer needs to inspect or update the default Claude startup used by the interactive CAO demo
- **THEN** the repo contains a tracked recipe at `agents/brains/brain-recipes/claude/gpu-kernel-coder-default.yaml`
- **AND** that recipe declares the Claude tool plus the config-profile and credential-profile identifiers needed for the default interactive demo launch
- **AND** that recipe declares the default agent name used when the demo starts without `--agent-name`

#### Scenario: Developer can locate the tracked Codex demo recipes
- **WHEN** a developer needs to inspect or update the supported Codex startup variants used by the interactive CAO demo
- **THEN** the repo contains tracked recipes for `codex/gpu-kernel-coder-default` and `codex/gpu-kernel-coder-yunwu-openai`
- **AND** those recipes declare their default agent names for direct recipe-backed startup
- **AND** those recipes remain declarative and secret-free

#### Scenario: Tracked interactive-demo recipes use tool-distinguishable default names
- **WHEN** a developer compares the tracked Claude and Codex recipes used by the interactive CAO demo
- **THEN** the recipes do not all share one identical `default_agent_name`
- **AND** the default names distinguish the direct-launch identity defaults across the supported tools

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

### Requirement: Credential profiles can include runtime-state templates
The system SHALL allow tool-specific credential profiles to include local-only runtime-state templates required for launch preparation (for example a Claude state template under `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json`).

#### Scenario: Claude credential profile carries `claude_state.template.json` template
- **WHEN** a developer prepares a Claude credential profile
- **THEN** the profile SHALL support including a local-only `claude_state.template.json` template for launch-time materialization in runtime homes
- **AND THEN** the template SHALL be treated as credential-profile input, not as a committed runtime artifact

### Requirement: Tmux-based launches inherit the calling process environment
The system SHALL propagate the full calling process environment into tmux-based launches (for example CAO-backed sessions), and then apply brain-owned overlays.

Environment precedence is:
1) calling process environment (base),
2) credential-profile env file values (overlay), and
3) launch-specific env vars (overlay; for example tool home selector env vars).

Credential-profile env injection MUST NOT be gated by a tool-adapter allowlist; all entries declared in the env file MUST be injected.

#### Scenario: Tmux launch inherits caller env and overlays credential env
- **WHEN** the system starts a tool session in tmux
- **THEN** the tmux session environment SHALL inherit environment variables from the calling process
- **AND THEN** the tmux session environment SHALL include all variables declared in the selected credential profile env file (overriding inherited values when names collide)
