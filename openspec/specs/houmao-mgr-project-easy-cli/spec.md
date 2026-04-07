# houmao-mgr-project-easy-cli Specification

## Purpose
Define the higher-level `houmao-mgr project easy` workflow for compiling reusable specialist definitions into the canonical repo-local `.houmao/agents/` tree.
## Requirements
### Requirement: `project easy specialist create` compiles one specialist into canonical project agent artifacts
`houmao-mgr project easy specialist create` SHALL create one project-local specialist by persisting the operator's intended specialist semantics into the active project-local catalog and managed content store.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, the command SHALL ensure `<cwd>/.houmao` exists before persisting that specialist state.

The rest of the specialist-create contract remains unchanged, including unattended defaults, persistent env records, and shared-content preservation rules.

#### Scenario: Specialist create bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test`
- **THEN** the command ensures `<cwd>/.houmao` exists before storing the specialist
- **AND THEN** the persisted specialist lands in the resulting project-local catalog and managed content store

### Requirement: Gemini easy specialists default to unattended headless launch posture
`houmao-mgr project easy specialist create --tool gemini` SHALL treat Gemini as a maintained unattended easy-launch lane for headless use.

By default, Gemini easy specialists SHALL persist `launch.prompt_mode: unattended` into both the project-local specialist metadata and the generated compatibility preset.

`--no-unattended` SHALL remain the explicit opt-out that persists `launch.prompt_mode: as_is`.

`houmao-mgr project easy instance launch` SHALL continue to require `--headless` for Gemini specialists even when the stored specialist launch posture is unattended.

#### Scenario: Default Gemini easy specialist persists unattended launch posture
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name gemini-reviewer --tool gemini --api-key gm-test`
- **THEN** the persisted specialist metadata records `launch.prompt_mode: unattended`
- **AND THEN** the generated compatibility preset records the same unattended launch posture

#### Scenario: Gemini easy specialist can still opt out to as-is launch posture
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name gemini-reviewer --tool gemini --api-key gm-test --no-unattended`
- **THEN** the persisted specialist metadata records `launch.prompt_mode: as_is`
- **AND THEN** the generated compatibility preset records the same `as_is` launch posture

#### Scenario: Gemini easy instance launch remains headless-only
- **WHEN** a Gemini specialist already exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist gemini-reviewer --name gemini-reviewer-1` without `--headless`
- **THEN** the command fails clearly
- **AND THEN** it identifies that Gemini specialists remain headless-only on the easy instance surface

### Requirement: `project easy specialist list/get/remove` manages persisted specialist definitions

`houmao-mgr project easy specialist list` SHALL enumerate persisted specialist definitions from the project-local catalog.

`houmao-mgr project easy specialist get --name <specialist>` SHALL report one specialist's high-level semantic metadata plus the managed content or derived artifact references relevant to that specialist.

When a specialist has stored launch posture, `specialist get` SHALL report that launch payload as part of the specialist's semantic metadata.

`houmao-mgr project easy specialist remove --name <specialist>` SHALL remove the persisted specialist definition from the project-local catalog and SHALL remove any specialist-owned derived projection state that exists only for that specialist.

`specialist remove` SHALL NOT delete shared skills, shared auth content, or other shared managed content only because one specialist referenced them.

`houmao-mgr project easy specialist get` SHALL report persistent specialist env records separately from the credential selection and auth content path.

Maintained `houmao-mgr project easy specialist list`, `get`, and `remove` flows SHALL resolve the active overlay through the shared non-creating project-aware resolver.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL fail clearly without bootstrapping a new overlay.

`project easy specialist remove` SHALL remain non-creating even though it mutates existing specialist state.

#### Scenario: Get reports semantic specialist metadata and content references
- **WHEN** specialist `researcher` exists in the project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports the specialist's tool, credential, skill, and launch selections
- **AND THEN** it reports the relevant managed content or derived artifact references for that specialist without requiring `.houmao/easy/specialists/researcher.toml` to be the source of truth

#### Scenario: Get reports persistent specialist env records separately from credential env
- **WHEN** specialist `researcher` exists in the project-local catalog with persistent env records
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports those specialist env records as specialist launch config
- **AND THEN** it does not merge them into the credential bundle summary as though they were auth env entries

#### Scenario: Remove preserves shared content references
- **WHEN** specialist `researcher` and another specialist both reference one shared skill package and one shared auth profile
- **AND WHEN** an operator runs `houmao-mgr project easy specialist remove --name researcher`
- **THEN** the command removes the persisted `researcher` specialist definition from the project-local catalog
- **AND THEN** it does not delete that shared skill package or shared auth content only because `researcher` was removed

#### Scenario: Specialist list fails clearly when no overlay exists
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist list`
- **THEN** the command fails clearly because no project overlay was discovered for the current invocation
- **AND THEN** it does not create `<cwd>/.houmao` only to return an empty specialist list

#### Scenario: Specialist remove does not bootstrap an empty overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist remove --name researcher`
- **THEN** the command fails clearly before attempting specialist removal
- **AND THEN** it does not create a new project overlay as a side effect of that remove command

### Requirement: `project easy profile create/list/get/remove` manages specialist-backed easy profiles
`houmao-mgr project easy profile create --name <profile> --specialist <specialist>` SHALL persist one reusable easy profile that targets exactly one existing specialist.

Easy profiles SHALL be specialist-backed birth-time launch configuration owned by the easy lane.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, `project easy profile create` SHALL ensure `<cwd>/.houmao` exists before persisting profile state.

`project easy profile list`, `get`, and `remove` SHALL resolve the active overlay through the shared non-creating project-aware resolver and SHALL fail clearly when no active overlay exists.

`project easy profile get --name <profile>` SHALL report the source specialist plus the stored easy-profile launch defaults.

`project easy profile remove --name <profile>` SHALL remove only the profile definition and SHALL NOT remove the referenced specialist only because that specialist was the profile source.

#### Scenario: Easy profile create bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder`
- **THEN** the command ensures `<cwd>/.houmao` exists before storing the profile
- **AND THEN** the persisted profile lands in the resulting project-local catalog and compatibility projection

#### Scenario: Easy profile remove preserves the referenced specialist
- **WHEN** easy profile `alice` targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy profile remove --name alice`
- **THEN** the command removes the persisted `alice` profile
- **AND THEN** it does not remove specialist `cuda-coder` only because `alice` referenced it

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance
`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the stored specialist definition from the active project-local catalog and delegating to the existing native managed-agent launch flow.

The command MAY accept `--workdir <path>` as an explicit runtime working directory for the launched agent session.

When `--workdir` is omitted, the launched runtime workdir SHALL default to the invocation cwd.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, the command SHALL ensure `<cwd>/.houmao` exists before launch preparation begins.

When no stronger explicit or env-var override is supplied, easy instance launch SHALL use overlay-local defaults for:

- runtime root: `<active-overlay>/runtime`
- jobs root: `<active-overlay>/jobs`
- mailbox root: `<active-overlay>/mailbox` for project-aware mailbox defaults

The launch provider SHALL still be derived from the specialist's selected tool, and the command SHALL still honor stored specialist launch posture and mailbox validation rules.

The selected project overlay and stored specialist source SHALL remain authoritative for easy launch source resolution even when `--workdir` points somewhere else.

The command SHALL NOT expose or require a separate launch-time workspace-trust bypass flag on this surface.

The delegated native launch SHALL proceed without a Houmao-managed workspace trust confirmation prompt.

When the stored specialist launch posture is `unattended`, any maintained no-prompt or full-autonomy provider startup posture SHALL remain owned by the resolved prompt mode and downstream launch policy.

When the stored specialist launch posture is `as_is`, easy instance launch SHALL NOT inject a separate yolo-style startup override and SHALL leave provider startup behavior untouched beyond the existing delegated launch contract.

#### Scenario: Easy instance launch uses overlay-local runtime and jobs defaults
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** no stronger runtime-root or jobs-root override is supplied
- **THEN** the resulting brain build and runtime session use `/repo/.houmao/runtime`
- **AND THEN** the session-local job dir is derived under `/repo/.houmao/jobs/<session-id>/`

#### Scenario: Easy instance launch keeps the selected project overlay when `--workdir` points outside the project
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** specialist `researcher` is stored in that project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --workdir /repo-b`
- **THEN** the launch resolves the specialist, runtime root, jobs root, and mailbox root from `/repo-a/.houmao`
- **AND THEN** it records `/repo-b` as the launched runtime workdir
- **AND THEN** it does not retarget specialist or overlay resolution to `/repo-b`

#### Scenario: Easy instance launch bootstraps the missing overlay before launch
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command ensures `<cwd>/.houmao` exists before resolving the specialist-backed launch
- **AND THEN** the launch uses that resulting overlay as the default local root family

#### Scenario: Easy instance launch does not bootstrap the runtime workdir as a project overlay
- **WHEN** no active project overlay exists for the invocation cwd
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --workdir /repo-b`
- **THEN** the command bootstraps the selected invocation overlay candidate before launch preparation begins
- **AND THEN** it does not bootstrap `/repo-b/.houmao` only because `/repo-b` was selected as the runtime workdir

#### Scenario: Stored as-is posture launches without a separate yolo-style override
- **WHEN** specialist `researcher` stores `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command delegates to native launch without a Houmao-managed workspace trust confirmation prompt
- **AND THEN** it does not inject a separate yolo-style startup override on top of the stored `as_is` posture

### Requirement: `project easy instance launch` supports easy-profile-backed launch
`houmao-mgr project easy instance launch` SHALL support selecting a reusable easy profile through `--profile <profile>`.

`--profile` and `--specialist` SHALL be mutually exclusive on this surface.

When `--profile` is used, the command SHALL derive the source specialist from the stored profile, SHALL apply easy-profile defaults before direct CLI overrides, and SHALL still use the selected project overlay as the authoritative source context.

When a selected profile stores a default managed-agent name, the command MAY omit `--name` and SHALL use the profile-owned default identity.

When a selected profile stores workdir, auth override, mailbox config, or launch posture, those values SHALL apply unless the operator supplies a direct launch-time override.

If the selected profile resolves to a Gemini specialist, the existing headless-only Gemini rule SHALL still apply.

#### Scenario: Easy-profile-backed launch uses stored instance name and workdir
- **WHEN** easy profile `alice` targets specialist `cuda-coder`
- **AND WHEN** `alice` stores default managed-agent name `alice` and default workdir `/repos/alice-cuda`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice`
- **THEN** the launch uses specialist `cuda-coder`
- **AND THEN** the launch uses managed-agent name `alice` and runtime workdir `/repos/alice-cuda`

#### Scenario: Direct CLI overrides still win for easy-profile-backed launch
- **WHEN** easy profile `alice` stores auth override `alice-creds` and workdir `/repos/alice-cuda`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --auth breakglass --workdir /tmp/debug`
- **THEN** the resulting launch uses auth bundle `breakglass`
- **AND THEN** the resulting launch records `/tmp/debug` as the runtime workdir instead of the profile default

### Requirement: `project easy instance launch` defaults gateway attach with explicit per-launch overrides
`houmao-mgr project easy instance launch` SHALL request launch-time gateway attach by default unless the operator explicitly passes `--no-gateway`.

For that default attached path, the easy launch surface SHALL use an opinionated gateway listener request of loopback host plus system-assigned port rather than requiring persisted specialist gateway config.

When an operator passes `--gateway-port <port>`, the easy launch surface SHALL request launch-time gateway attach for that explicit port on the current launch instead of using a system-assigned port.

`--no-gateway` and `--gateway-port` SHALL be mutually exclusive on this surface.

If launch-time gateway attach fails after the managed session has already started, `project easy instance launch` SHALL keep the session running and SHALL report the attach failure explicitly together with the launched session identity needed for retry.

#### Scenario: Default easy launch attaches a loopback gateway with a system-assigned port
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** the addressed specialist launch resolves to a gateway-capable supported backend
- **THEN** the command requests launch-time gateway attach by default
- **AND THEN** it requests loopback binding with a system-assigned port for that launch
- **AND THEN** the launch result reports the resolved gateway host and bound gateway port

#### Scenario: Operator skips launch-time gateway attach explicitly
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway`
- **THEN** the command does not request launch-time gateway attach for that launch
- **AND THEN** the launch result does not claim that a live gateway endpoint was attached automatically

#### Scenario: Operator requests a fixed gateway port for one easy launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-port 43123`
- **THEN** the command requests launch-time gateway attach for that launch
- **AND THEN** it requests gateway listener port `43123` instead of a system-assigned port
- **AND THEN** a successful launch reports the resolved gateway endpoint for that session

#### Scenario: Conflicting gateway launch flags fail clearly
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway --gateway-port 43123`
- **THEN** the command fails explicitly before launch
- **AND THEN** the error states that `--no-gateway` and `--gateway-port` cannot be combined

#### Scenario: Gateway auto-attach failure preserves the launched session
- **WHEN** `houmao-mgr project easy instance launch` starts the managed session successfully
- **AND WHEN** launch-time gateway attach fails afterward for that launch
- **THEN** the managed session remains running
- **AND THEN** the command reports the gateway attach failure explicitly
- **AND THEN** the failure surface includes the launched session identity or manifest path needed for later retry or stop

### Requirement: `project easy instance list/get/stop` presents runtime state by specialist and wraps existing runtime stop control

`houmao-mgr project easy instance list` SHALL present launched managed agents as instances, annotated by their originating specialist when that specialist can be resolved.

`houmao-mgr project easy instance get --name <instance>` SHALL report the current managed-agent runtime summary plus the originating specialist metadata when available.

`houmao-mgr project easy instance stop --name <instance>` SHALL stop one managed-agent instance after verifying that the resolved runtime session belongs to the current project overlay.

`project easy instance stop` SHALL delegate to the existing canonical managed-agent stop implementation rather than directly killing the resolved tmux session.

This change SHALL NOT define `project easy instance stop` semantics that differ from the current managed-agent stop behavior.

The instance view SHALL be derived from existing managed-agent runtime state and SHALL NOT require a second persisted per-instance config contract in v1.

Maintained `houmao-mgr project easy instance list`, `get`, and `stop` flows SHALL resolve the active overlay through the shared non-creating project-aware resolver before inspecting runtime state or verifying overlay ownership.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL fail clearly without bootstrapping a new overlay.

When the resolved runtime state includes a mailbox association, `project easy instance get` SHALL report the effective mailbox summary, including:

- the high-level mailbox transport,
- the mailbox address,
- the shared mailbox root,
- the mailbox kind,
- the resolved concrete mailbox directory.

`project easy instance list` SHALL surface whether each instance currently has a mailbox association and MAY present that information as a compact mailbox summary.

The `instance` group SHALL own launch, stop, and runtime inspection, while the `specialist` group remains limited to reusable configuration management.

#### Scenario: Instance list groups launched agents by specialist
- **WHEN** a launched managed agent was started from specialist `researcher`
- **AND WHEN** an operator runs `houmao-mgr project easy instance list`
- **THEN** the command reports that managed agent as an instance of `researcher`
- **AND THEN** the command derives that view from the existing runtime state rather than from a second stored instance definition

#### Scenario: Instance get reports the effective mailbox association
- **WHEN** launched instance `repo-research-1` was started with a filesystem mailbox association
- **AND WHEN** an operator runs `houmao-mgr project easy instance get --name repo-research-1`
- **THEN** the command reports the instance's runtime summary and originating specialist metadata
- **AND THEN** it also reports the effective mailbox transport, mailbox address, mailbox root, mailbox kind, and resolved mailbox directory from runtime-derived state

#### Scenario: Instance stop wraps the canonical managed-agent stop path
- **WHEN** launched instance `repo-research-1` belongs to the current project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command verifies that the resolved managed-agent manifest belongs to the discovered project overlay
- **AND THEN** it stops the instance by delegating to the existing managed-agent stop implementation rather than by directly killing tmux from the project CLI

#### Scenario: Instance stop rejects a managed agent outside the current project overlay
- **WHEN** managed agent `repo-research-1` resolves successfully
- **AND WHEN** its manifest does not belong to the discovered project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command fails clearly
- **AND THEN** it does not delegate stop control for a managed agent outside the current project overlay

#### Scenario: Instance list fails clearly when no overlay exists
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance list`
- **THEN** the command fails clearly because no project overlay was discovered for the current invocation
- **AND THEN** it does not create `<cwd>/.houmao` as a side effect of that inspection command

#### Scenario: Instance stop does not bootstrap before checking ownership
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command fails clearly before attempting runtime ownership verification or stop delegation
- **AND THEN** it does not create a new project overlay only to reject or stop an existing instance

### Requirement: Easy instance inspection reports easy-profile origin when available
When a managed-agent instance was launched from a project-easy profile, `project easy instance list` and `project easy instance get` SHALL report that originating easy-profile identity when it is resolvable from runtime-backed state.

The instance inspection surface SHALL continue to report the originating specialist when available.

#### Scenario: Easy instance get reports both easy-profile origin and specialist origin
- **WHEN** instance `alice` was launched from easy profile `alice`
- **AND WHEN** that profile targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy instance get --name alice`
- **THEN** the command reports easy profile `alice` as the originating reusable birth-time configuration
- **AND THEN** it also reports specialist `cuda-coder` as the underlying reusable source

### Requirement: `project easy specialist create` persists explicit tool setup selection
`houmao-mgr project easy specialist create` SHALL accept an optional `--setup <name>` input with a default of `default`.

The command SHALL validate that the selected setup exists for the selected tool before writing project-local specialist state.

The command SHALL persist the selected setup consistently into:

- the stored project catalog specialist metadata,
- the generated compatibility preset for that specialist,
- later project-aware launch inputs derived from that specialist definition.

The command SHALL NOT infer the selected setup from credential bundle names, auth payload shape, or API endpoint values.

This requirement SHALL apply to any project-easy specialist tool that uses setup bundles today or in the future.

#### Scenario: Explicit non-default setup is persisted through specialist creation
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --setup yunwu-openai --api-key sk-test`
- **THEN** the command persists specialist `researcher` successfully
- **AND THEN** the stored specialist metadata records `setup = yunwu-openai`
- **AND THEN** the generated preset for `researcher` records the same setup instead of silently substituting `default`

#### Scenario: Omitted setup still persists the default setup explicitly
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --api-key sk-test`
- **THEN** the command persists specialist `reviewer` successfully
- **AND THEN** the stored specialist metadata records `setup = default`
- **AND THEN** later project-aware launch resolves that same stored setup without inferring a different setup from credentials

### Requirement: Project easy inspection and stop wording follows the selected-overlay contract
Maintained `houmao-mgr project easy ...` help text, failures, and ownership-mismatch errors SHALL use the same selected-overlay and non-creating terminology as the broader project-aware contract.

Inspection, removal, and stop commands that resolve without creating an overlay SHALL say so explicitly when no project overlay is available for the current invocation.

Ownership-mismatch failures for project-easy runtime instances SHALL describe the selected project overlay rather than a generically discovered overlay.

#### Scenario: Specialist or instance inspection failure remains explicitly non-creating
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist list` or `houmao-mgr project easy instance list`
- **THEN** the failure identifies the selected or would-bootstrap overlay root for that invocation
- **AND THEN** it states that the command did not create that overlay because the surface is non-creating

#### Scenario: Instance ownership mismatch names the selected project overlay
- **WHEN** an operator runs a maintained `houmao-mgr project easy instance get` or `stop` command
- **AND WHEN** the resolved managed-agent manifest belongs to a different overlay
- **THEN** the failure states that the managed agent does not belong to the selected project overlay
- **AND THEN** it does not describe that mismatch as a problem with a generically discovered overlay

### Requirement: Claude easy specialists support vendor OAuth token and imported login state
`houmao-mgr project easy specialist create --tool claude` SHALL accept Claude vendor-auth inputs for:

- `CLAUDE_CODE_OAUTH_TOKEN`
- imported Claude login state from a Claude config root

When provided, the command SHALL persist those inputs into the selected or derived Claude credential bundle using the same Claude auth-bundle contract as `houmao-mgr project agents tools claude auth`.

These Claude vendor-auth lanes SHALL remain valid even when `--api-key`, `--claude-auth-token`, and `--claude-state-template-file` are omitted.

`--claude-state-template-file` MAY remain as an optional Claude runtime-state template input, but it SHALL NOT be described as one of the Claude credential-providing methods on this surface.

#### Scenario: Easy specialist create persists the Claude OAuth-token lane
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-oauth-token token123`
- **THEN** the derived Claude credential bundle `reviewer-creds` stores `CLAUDE_CODE_OAUTH_TOKEN`
- **AND THEN** the specialist persists successfully without requiring `--api-key`

#### Scenario: Easy specialist create imports Claude login state from a config root
- **WHEN** `/tmp/claude-home` contains vendor Claude login-state files
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-config-dir /tmp/claude-home`
- **THEN** the derived Claude credential bundle copies the supported vendor Claude login-state files
- **AND THEN** the specialist persists successfully without requiring `--claude-state-template-file`

#### Scenario: Easy specialist create preserves other explicit Claude settings with imported login state
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-config-dir /tmp/claude-home --claude-model claude-opus`
- **THEN** the derived Claude credential bundle copies the vendor Claude login-state files
- **AND THEN** it also preserves `ANTHROPIC_MODEL=claude-opus` in that credential bundle

#### Scenario: Claude state template remains optional on the easy-specialist surface
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-oauth-token token123`
- **AND WHEN** `--claude-state-template-file` is omitted
- **THEN** the specialist persists successfully
- **AND THEN** the operator-facing contract does not describe the omitted template as missing Claude credentials
