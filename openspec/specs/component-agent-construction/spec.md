# component-agent-construction Specification

## Purpose
Define the expected structure and semantics for reusable agent components, declarative presets, and runtime brain construction inputs.

## Requirements

### Requirement: User-facing source directories

The system SHALL organize reusable agent-definition sources under a stable on-disk layout rooted at `agents/`.

At minimum, that source layout SHALL include:

- `agents/skills/<skill>/SKILL.md`
- `agents/roles/<role>/system-prompt.md`
- `agents/roles/<role>/presets/<tool>/<setup>.yaml`
- `agents/tools/<tool>/adapter.yaml`
- `agents/tools/<tool>/setups/<setup>/...`
- `agents/tools/<tool>/auth/<auth>/...`

User-facing reusable launch metadata SHALL live in role-scoped presets plus tool-scoped setup and auth directories rather than in a separate recipe plus blueprint layer.

#### Scenario: Developer locates source files

- **WHEN** a developer needs to add or modify reusable agent-definition sources
- **THEN** skill packages SHALL live under `agents/skills/`
- **AND THEN** role prompts SHALL live under `agents/roles/`
- **AND THEN** launchable preset files SHALL live under `agents/roles/<role>/presets/`
- **AND THEN** tool-specific setup and auth material SHALL live under `agents/tools/<tool>/`

### Requirement: Supported tracked agent-definition trees omit legacy layout mirrors

Repository-owned tracked agent-definition trees that remain part of the supported live system contract SHALL publish launchable source definitions through the canonical `skills/`, `roles/`, `tools/`, and optional `compatibility-profiles/` layout only.

Supported tracked trees SHALL NOT require or ship legacy `brains/`, `brain-recipes/`, `cli-configs/`, `api-creds/`, or `blueprints/` directories as parallel source-of-truth mirrors for the same launchable assets.

Archived historical material under `scripts/demo/legacy/` is not part of that supported live contract and does not define the maintained source-layout requirement.

#### Scenario: Maintainer inspects a supported repo-owned agent-definition tree

- **WHEN** a maintainer inspects a supported repo-owned agent-definition tree used by live fixtures, tests, or non-archived workflows
- **THEN** launchable role, preset, setup, auth, and skill assets live under the canonical `skills/`, `roles/`, `tools/`, and optional `compatibility-profiles/` directories
- **AND THEN** the tree does not ship tracked legacy mirror directories for the same launchable assets

#### Scenario: Canonical consumers do not need legacy directories

- **WHEN** selector resolution, brain construction, or supported live helper logic consumes a tracked repo-owned agent-definition tree
- **THEN** it resolves canonical preset, setup, auth, role, and skill inputs from that tree
- **AND THEN** successful resolution does not require legacy `brains/` or `blueprints/` directories to exist alongside the canonical source layout

### Requirement: Source parsing yields a canonical agent catalog

The system SHALL parse the user-facing `agents/` source tree into a canonical parsed model before selector resolution or brain construction.

That canonical parsed model SHALL capture semantic agent-definition data independently of source-layout-specific field names or file layering.

Downstream selector resolution, brain construction, and launch code SHALL consume only canonical parsed definitions or derived resolved launch and build specifications and SHALL NOT depend directly on raw preset-source mappings, legacy recipe files, or legacy blueprint files.

#### Scenario: Selector resolution uses the parsed catalog

- **WHEN** a launch selector is resolved
- **THEN** resolution SHALL operate on the canonical parsed catalog
- **AND THEN** downstream launch and build code SHALL NOT need to inspect raw source files directly

#### Scenario: Future source-layout revisions preserve downstream contracts

- **WHEN** a future user-facing source-layout parser is added that preserves the same role, tool, setup, auth, launch, mailbox, and `extra` semantics
- **THEN** downstream build and launch components SHALL continue to consume the same canonical parsed contract without layout-specific changes

### Requirement: Brain construction inputs

The system SHALL support constructing an agent runtime from a resolved build specification derived from one parsed preset together with one effective auth selection.

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
- **AND THEN** those explicit inputs SHALL come from the canonical parsed model rather than from raw source payloads

### Requirement: Fresh-by-default runtime home creation

Brain construction SHALL create a fresh runtime CLI home directory with no pre-existing tool history, logs, or sessions at creation time. The system SHALL support pre-seeding minimal tool bootstrap configuration or state required for unattended startup, provided it is not copied from prior-run history, log, or session artifacts.

#### Scenario: Fresh home has no pre-existing history

- **WHEN** a new runtime home is constructed
- **THEN** the constructed home SHALL NOT contain copied-in prior-run history, log, or session artifacts
- **AND THEN** any history, log, or session artifacts SHALL only appear after the CLI tool is started and begins writing state
- **AND THEN** any pre-seeded tool bootstrap configuration or state files present at creation time MUST NOT be copied from prior-run history, log, or session artifacts

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

The system SHALL support declarative source presets stored under `agents/roles/<role>/presets/<tool>/<setup>.yaml`.

Preset identity SHALL be derived from path rather than from duplicated inline identity fields. The source preset path SHALL determine role, tool, and setup before the parser emits the canonical parsed preset definition.

#### Scenario: Preset identity comes from path

- **WHEN** a developer creates `agents/roles/gpu-kernel-coder/presets/claude/default.yaml`
- **THEN** the system SHALL treat role=`gpu-kernel-coder`, tool=`claude`, and setup=`default` as that preset's identity
- **AND THEN** the preset file SHALL NOT require top-level `name`, `role`, or `tool` fields

### Requirement: Agent preset schema is minimal and extensible

Agent presets SHALL include only fields required by current behavior: selected skills, optional default auth, optional launch settings, optional mailbox settings, and optional `extra`.

The system SHALL NOT require build-time `default_agent_name` or other duplicated identity fields in preset files.

If present, preset `launch` SHALL be an object containing optional `prompt_mode` and optional `overrides`. `launch.overrides`, when present, SHALL use the existing launch-overrides shape of optional `args` and optional `tool_params`.

Unknown top-level preset fields SHALL be rejected. Non-core extension data SHALL live under `extra` rather than through pre-allocated unused top-level schema fields.

#### Scenario: Minimal preset omits build-time identity fields

- **WHEN** a developer authors a preset for one role, tool, and setup
- **THEN** the preset MAY omit `name`, `role`, `tool`, and `default_agent_name`
- **AND THEN** the system SHALL still resolve the preset successfully from its path and required core fields

#### Scenario: Launch settings use one explicit schema

- **WHEN** a developer authors preset-owned launch behavior
- **THEN** `prompt_mode` SHALL appear under `launch.prompt_mode`
- **AND THEN** any preset-owned launch overrides SHALL appear under `launch.overrides`
- **AND THEN** `launch.overrides` SHALL use only the supported `args` and `tool_params` sections

#### Scenario: Non-core preset extensions live under extra

- **WHEN** a consumer needs secret-free subsystem-specific preset metadata outside the core schema
- **THEN** that metadata SHALL be stored under `extra`
- **AND THEN** the core preset resolution path SHALL NOT depend on unsupported top-level extension fields
- **AND THEN** preserved gateway defaults, when needed for migrated blueprint behavior, SHALL live under `extra.gateway`

#### Scenario: Unknown top-level preset field fails validation

- **WHEN** a preset file declares an unsupported top-level field such as legacy `config_profile`
- **THEN** preset loading SHALL fail explicitly
- **AND THEN** the error SHALL direct authors toward the supported core fields and `extra`

### Requirement: Tracked canonical presets for live role variants

The repository SHALL provide tracked, declarative, secret-free presets under `agents/roles/<role>/presets/` for the live role variants that the repo documents and verifies.

At minimum, the tracked preset set SHALL include:

- `agents/roles/gpu-kernel-coder/presets/claude/default.yaml`
- `agents/roles/gpu-kernel-coder/presets/codex/default.yaml`
- `agents/roles/gpu-kernel-coder/presets/codex/yunwu-openai.yaml`

Each tracked preset SHALL select skills and optional default auth by identifier only and SHALL NOT embed secret material.

#### Scenario: Developer can locate tracked preset variants for the GPU demo role

- **WHEN** a developer needs to inspect or update the supported launch variants for `gpu-kernel-coder`
- **THEN** the repo SHALL contain tracked presets under that role's `presets/` subtree for the documented tool and setup variants
- **AND THEN** those presets SHALL remain declarative and secret-free

### Requirement: Resolved runtime manifest

Each constructed runtime home SHALL produce a resolved manifest that records the selected inputs, including tool, preset path, setup identifier, effective auth identifier, selected skills, the output home directory path, and the launch environment contract. The manifest MUST NOT contain secret values.

The resolved manifest SHALL use `schema_version: 3`.

#### Scenario: Runtime manifest supports audit and reproducibility

- **WHEN** a brain is constructed successfully
- **THEN** a resolved manifest SHALL be written for that constructed home
- **AND THEN** the manifest SHALL identify the preset path, setup, auth, and selected components without including credential secrets
- **AND THEN** the manifest SHALL record `schema_version: 3`

### Requirement: Brain-agnostic role packages

Roles SHALL be defined independently of the CLI tool. A role SHALL include a `system-prompt.md` and MAY include supporting files referenced by the prompt.

`system-prompt.md` MAY be intentionally empty to represent a role with no system prompt.

#### Scenario: Role prompt references supporting files

- **WHEN** a role's `system-prompt.md` references a supporting file under the role directory
- **THEN** that supporting file SHALL exist within the role package

#### Scenario: Empty role prompt remains a valid canonical role package

- **WHEN** a role's `system-prompt.md` exists but contains no prompt content
- **THEN** that role package remains valid
- **AND THEN** downstream build or launch consumers treat it as a role with no system prompt rather than a missing-role error

### Requirement: Auth bundles can include runtime-state templates

The system SHALL allow tool-specific auth bundles to include local-only runtime-state templates required for launch preparation, for example a Claude state template under `agents/tools/claude/auth/<auth>/files/claude_state.template.json`.

#### Scenario: Claude auth bundle carries `claude_state.template.json` template

- **WHEN** a developer prepares a Claude auth bundle
- **THEN** the bundle SHALL support including a local-only `claude_state.template.json` template for launch-time materialization in runtime homes
- **AND THEN** the template SHALL be treated as auth-bundle input, not as a committed runtime artifact

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

### Requirement: Runtime launches inherit the calling process environment

The system SHALL propagate the full calling process environment into tmux-based launches, and then apply brain-owned overlays.

Environment precedence is:
1. calling process environment (base),
2. auth-bundle env file values selected by the tool adapter allowlist (overlay), and
3. launch-specific env vars (overlay; for example tool home selector env vars).

Auth-bundle env injection SHALL respect the selected tool adapter's allowlist rather than exporting unrelated auth-bundle env entries.

#### Scenario: Tmux launch inherits caller env and overlays allowlisted auth env

- **WHEN** the system starts a tool session in tmux
- **THEN** the tmux session environment SHALL inherit environment variables from the calling process
- **AND THEN** the tmux session environment SHALL include the allowlisted variables declared in the selected auth bundle env file, overriding inherited values when names collide

### Requirement: Brain construction accepts operator prompt policy intent

The system SHALL let callers declare an operator prompt policy when constructing a brain, including a mode that requests unattended launch behavior where startup operator prompts are forbidden.

The selected policy SHALL be available through:

- declarative preset YAML at `launch.prompt_mode`
- direct build inputs at `BuildRequest.operator_prompt_mode`

Allowed values SHALL be `interactive` and `unattended`. Omitting the field SHALL preserve the normal interactive and default launch posture.

#### Scenario: Developer constructs a brain with unattended prompt policy

- **WHEN** a developer constructs a brain using direct inputs or a declarative preset that requests `launch.prompt_mode = unattended`
- **THEN** the construction input includes that requested launch policy alongside tool, skills, setup, and auth
- **AND THEN** the requested policy remains secret-free metadata that does not embed API keys, tokens, inline credential material, or credential file contents

### Requirement: Brain manifest persists unresolved launch policy intent

The system SHALL persist requested operator prompt policy in the resolved brain manifest as abstract launch intent rather than as pre-resolved provider-version-specific CLI flags or runtime state patches.

The resolved manifest SHALL store that request at `launch_policy.operator_prompt_mode`.

#### Scenario: Manifest records unattended intent without provider-specific patch details

- **WHEN** a brain is constructed with `operator_prompt_mode = unattended`
- **THEN** the resolved brain manifest records that requested policy at `launch_policy.operator_prompt_mode`
- **AND THEN** the manifest does not treat version-resolved strategy ids, provider trust entries, or concrete injected CLI args as construction-time inputs

### Requirement: Brain construction does not require tool-specific no-prompt config as input

The system SHALL allow callers to request unattended launch without supplying user-authored per-tool config or state files whose only purpose is suppressing startup prompts.

The resolved brain manifest SHALL continue to capture auth-bundle references and abstract unattended intent, while leaving runtime-owned prompt-suppression config synthesis to launch-time strategy resolution.

#### Scenario: Developer requests unattended launch with minimal auth inputs

- **WHEN** a developer constructs a brain with `operator_prompt_mode = unattended`
- **AND WHEN** they provide only the normal auth inputs for that tool family, such as API-key env vars, endpoint env vars, or `auth.json`
- **THEN** brain construction succeeds without requiring extra user-authored no-prompt config files
- **AND THEN** the manifest records abstract unattended intent rather than synthetic provider config contents

### Requirement: Brain construction accepts a structured launch-overrides contract

The system SHALL let callers declare secret-free launch-override intent as part of normal brain construction inputs instead of limiting preset-backed builds to tool-adapter launch defaults.

That construction input SHALL be available through:

- declarative preset YAML at `launch.overrides`
- direct build inputs at `BuildRequest.launch_overrides`

The supported construction-time launch-overrides model SHALL include at minimum:

- an `args` section with explicit merge behavior against tool-adapter defaults
- a `tool_params` section for typed, tool-specific launch settings

#### Scenario: Preset construction includes launch-overrides intent

- **WHEN** a developer constructs a brain from a preset that declares `launch.overrides`
- **THEN** the selected tool, skills, setup, auth, and launch-overrides request are all part of the construction input contract
- **AND THEN** the preset remains declarative and secret-free

#### Scenario: Direct build input uses the same structured launch-overrides model

- **WHEN** a developer constructs a brain without a preset and supplies `BuildRequest.launch_overrides`
- **THEN** the direct-build path accepts the same structured launch-overrides model used by presets
- **AND THEN** the system does not require a separate ad hoc launch-arg-only override path for parity

### Requirement: Brain manifests persist adapter defaults and requested launch overrides separately

The system SHALL persist launch-override state in the resolved brain manifest as structured data with separate fields for adapter-owned launch defaults and caller-requested launch overrides.

The resolved brain manifest SHALL store enough non-secret information to explain:

- which launch defaults came from the selected tool adapter
- which launch overrides were requested by the preset or direct build input
- which parts of the launch contract still require runtime resolution because backend applicability is selected later

The manifest MUST NOT embed credential material, inline secrets, backend-resolved effective args, or backend-reserved runtime continuity values as preset-owned launch overrides.

#### Scenario: Manifest records defaults and requested override without flattening them together

- **WHEN** a brain is constructed from a preset whose selected tool adapter has launch defaults and whose preset also declares `launch.overrides`
- **THEN** the resolved manifest records the adapter defaults snapshot separately from the requested launch-overrides payload
- **AND THEN** audit or debugging consumers can distinguish reusable defaults from preset-owned launch intent

#### Scenario: Manifest keeps backend applicability unresolved at build time

- **WHEN** a brain is constructed before a specific runtime backend has been chosen
- **THEN** the resolved manifest stores the requested launch-overrides contract as unresolved launch intent
- **AND THEN** the builder does not write backend-resolved effective args or mark every requested launch field as universally supported across later runtime backends

### Requirement: New builder output uses manifest schema version 3 for preset-backed inputs

Brain construction that supports the preset, setup, auth, and launch-overrides contract SHALL write resolved brain manifests with `schema_version = 3`.

New builder output for this contract SHALL NOT continue writing legacy schema-version-1 or schema-version-2 manifest layouts as though they were equivalent.

#### Scenario: Builder writes schema version 3 manifest for preset-backed output

- **WHEN** a developer constructs a brain using a builder that supports presets and `launch.overrides`
- **THEN** the resolved brain manifest is written with `schema_version = 3`
- **AND THEN** the manifest carries the structured preset-backed contract rather than relying on the old recipe-era layouts
