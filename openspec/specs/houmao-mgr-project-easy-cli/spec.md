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

`project easy profile create` SHALL accept `--gateway-mail-notifier-appendix-text <text>` to store a reusable notifier appendix default on that easy profile.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, `project easy profile create` SHALL ensure `<cwd>/.houmao` exists before persisting profile state.

`project easy profile list`, `get`, and `remove` SHALL resolve the active overlay through the shared non-creating project-aware resolver and SHALL fail clearly when no active overlay exists.

`project easy profile get --name <profile>` SHALL report the source specialist plus the stored easy-profile launch defaults, including the stored notifier appendix default when present.

`project easy profile remove --name <profile>` SHALL remove only the profile definition and SHALL NOT remove the referenced specialist only because that specialist was the profile source.

#### Scenario: Easy profile create bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder`
- **THEN** the command ensures `<cwd>/.houmao` exists before storing the profile
- **AND THEN** the persisted profile lands in the resulting project-local catalog and compatibility projection

#### Scenario: Easy profile create stores notifier appendix default
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --gateway-mail-notifier-appendix-text "Watch billing-related inbox items first."`
- **THEN** the stored easy profile records that notifier appendix default
- **AND THEN** later `project easy profile get --name alice` reports the stored appendix default

#### Scenario: Easy profile remove preserves the referenced specialist
- **WHEN** easy profile `alice` targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy profile remove --name alice`
- **THEN** the command removes the persisted `alice` profile
- **AND THEN** it does not remove specialist `cuda-coder` only because `alice` referenced it

### Requirement: `project easy` surfaces support unified model configuration
`houmao-mgr project easy specialist create` SHALL accept optional `--model <name>` as a launch-owned default model selection for the created specialist.

`houmao-mgr project easy specialist create` SHALL accept optional `--reasoning-level <integer>=non-negative` as a launch-owned default reasoning preset index for the created specialist.

When supplied, those values SHALL be persisted in the specialist's launch metadata and in the generated compatibility preset as launch configuration rather than as auth-bundle content.

`houmao-mgr project easy profile create` SHALL accept optional `--model <name>` as a reusable easy-profile model override.

`houmao-mgr project easy profile create` SHALL accept optional `--reasoning-level <integer>=non-negative` as a reusable easy-profile reasoning override.

`houmao-mgr project easy instance launch` SHALL accept optional `--model <name>` and `--reasoning-level <integer>=non-negative` as one-off launch overrides for either `--specialist` or `--profile` launch.

For easy-profile-backed launch, the effective model configuration SHALL resolve with this precedence:

1. stored specialist or source recipe default
2. easy-profile model override
3. direct `project easy instance launch` override

Direct easy-instance override SHALL NOT rewrite the stored specialist or easy profile.

#### Scenario: Specialist create persists launch-owned model configuration
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool codex --api-key sk-test --model gpt-5.4 --reasoning-level 3`
- **THEN** the persisted specialist metadata records model `gpt-5.4` and reasoning level `3` as launch configuration
- **AND THEN** the generated compatibility preset records the same values under `launch`

#### Scenario: Easy profile create stores a reusable model override
- **WHEN** specialist `reviewer` already exists with source model `gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer --model gpt-5.4-mini --reasoning-level 2`
- **THEN** the stored easy profile records model override `gpt-5.4-mini` and reasoning override `2`
- **AND THEN** those values are treated as easy-profile launch configuration rather than as credential state

#### Scenario: Direct easy-instance model override wins over the easy-profile default
- **WHEN** easy profile `reviewer-fast` stores model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --name reviewer-fast-1 --model gpt-5.4-nano`
- **THEN** the resulting launch uses model `gpt-5.4-nano`
- **AND THEN** the stored easy profile still records `gpt-5.4-mini` as its reusable default

#### Scenario: Direct easy-instance reasoning override wins over the easy-profile default
- **WHEN** easy profile `reviewer-fast` stores reasoning override `2`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --name reviewer-fast-1 --reasoning-level 12`
- **THEN** the resulting launch uses launch-owned reasoning preset index `12`
- **AND THEN** the stored easy profile still records `2` as its reusable default

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

For tmux-backed managed sessions on that default attached path, the easy launch surface SHALL default the launch-time gateway execution mode to same-session foreground auxiliary-window execution.

When an operator passes `--gateway-port <port>`, the easy launch surface SHALL request launch-time gateway attach for that explicit port on the current launch instead of using a system-assigned port.

When an operator passes `--gateway-background`, the easy launch surface SHALL request launch-time gateway attach in detached background execution for that launch instead of the default foreground auxiliary-window execution.

`--no-gateway` and `--gateway-port` SHALL be mutually exclusive on this surface.

`--no-gateway` and `--gateway-background` SHALL be mutually exclusive on this surface.

If launch-time gateway attach succeeds in foreground mode, the launch result SHALL report the resolved gateway host, the bound gateway port, the gateway execution mode, and the authoritative tmux window index for the live gateway surface.

If launch-time gateway attach fails after the managed session has already started, `project easy instance launch` SHALL keep the session running and SHALL report the attach failure explicitly together with the launched session identity needed for retry.

#### Scenario: Default easy launch attaches a loopback foreground gateway with a system-assigned port
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** the addressed specialist launch resolves to a gateway-capable supported backend
- **THEN** the command requests launch-time gateway attach by default
- **AND THEN** it requests loopback binding with a system-assigned port for that launch
- **AND THEN** it requests same-session foreground auxiliary-window execution for that launch
- **AND THEN** the launch result reports the resolved gateway host, bound gateway port, execution mode, and authoritative tmux window index

#### Scenario: Operator skips launch-time gateway attach explicitly
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway`
- **THEN** the command does not request launch-time gateway attach for that launch
- **AND THEN** the launch result does not claim that a live gateway endpoint was attached automatically

#### Scenario: Operator requests a fixed gateway port for one easy launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-port 43123`
- **THEN** the command requests launch-time gateway attach for that launch
- **AND THEN** it requests gateway listener port `43123` instead of a system-assigned port
- **AND THEN** it still requests same-session foreground auxiliary-window execution unless `--gateway-background` is also supplied

#### Scenario: Operator requests background gateway execution for one easy launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-background`
- **THEN** the command requests launch-time gateway attach for that launch
- **AND THEN** it requests detached background gateway execution instead of the default foreground auxiliary-window execution

#### Scenario: Conflicting gateway launch flags fail clearly
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway --gateway-background`
- **THEN** the command fails explicitly before launch
- **AND THEN** the error states that `--no-gateway` cannot be combined with other gateway-attach overrides

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

### Requirement: `project easy profile create` supports stored managed-header policy
`houmao-mgr project easy profile create` SHALL accept:

- `--managed-header`
- `--no-managed-header`

Those flags SHALL be mutually exclusive.

When neither flag is supplied, the created easy profile SHALL store managed-header policy `inherit`.

`project easy profile get --name <profile>` SHALL report the stored managed-header policy.

#### Scenario: Easy profile create stores disabled managed-header policy
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer --no-managed-header`
- **THEN** the created easy profile stores managed-header policy `disabled`
- **AND THEN** later `project easy profile get --name reviewer-fast` reports that stored policy

### Requirement: `project easy instance launch` supports one-shot managed-header override
`houmao-mgr project easy instance launch` SHALL accept:

- `--managed-header`
- `--no-managed-header`

Those flags SHALL be mutually exclusive.

When neither flag is supplied, easy-instance launch SHALL inherit managed-header policy from the selected easy profile when one is present, otherwise from the system default.

Direct one-shot managed-header override SHALL NOT rewrite the stored easy profile.

#### Scenario: Easy-instance launch disables the managed header for one profile-backed launch
- **WHEN** easy profile `reviewer-fast` stores managed-header policy `enabled`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --no-managed-header`
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** easy profile `reviewer-fast` still records managed-header policy `enabled`

#### Scenario: Easy-instance launch enables the managed header despite stored disabled policy
- **WHEN** easy profile `reviewer-fast` stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header`
- **THEN** the resulting managed launch prepends the managed prompt header
- **AND THEN** easy profile `reviewer-fast` still records managed-header policy `disabled`

### Requirement: `project easy instance launch` supports launch-owned managed force takeover

`houmao-mgr project easy instance launch` SHALL accept optional `--force` for delegated managed takeover on the current easy-launch invocation.

`--force` MAY be supplied bare or with an explicit mode value.

Bare `--force` SHALL default to mode `keep-stale`.

The only supported explicit force mode values SHALL be `keep-stale` and `clean`.

The selected force mode SHALL be forwarded to the delegated native managed launch for the current invocation only and SHALL NOT be persisted into the stored specialist or easy profile.

When no force mode is supplied and the delegated native launch resolves a fresh existing owner for the target managed identity, easy instance launch SHALL fail rather than replacing it.

When `--force` is supplied, easy instance launch SHALL request the corresponding managed runtime takeover for the resolved managed identity whether that identity comes from direct `--name` or from an easy-profile default.

#### Scenario: Bare `--force` defaults to `keep-stale` for specialist-backed launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --force`
- **AND WHEN** a fresh live session already owns managed identity `repo-research-1`
- **THEN** the delegated launch requests managed takeover in mode `keep-stale`
- **AND THEN** the stored specialist remains unchanged

#### Scenario: Easy-profile-backed launch can request explicit `clean` without rewriting the profile
- **WHEN** easy profile `alice` stores default managed-agent name `alice`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --force clean`
- **AND WHEN** a fresh live session already owns managed identity `alice`
- **THEN** the delegated launch requests managed takeover in mode `clean`
- **AND THEN** stored easy profile `alice` remains unchanged and does not gain a persisted force mode

#### Scenario: Missing `--force` preserves the existing ownership conflict failure
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** a fresh live session already owns managed identity `repo-research-1`
- **THEN** the command fails rather than replacing that existing live owner

### Requirement: `project easy instance launch` supports one-shot launch-owned system-prompt appendix
`houmao-mgr project easy instance launch` SHALL accept optional launch-owned system-prompt appendix input through:

- `--append-system-prompt-text`
- `--append-system-prompt-file`

Those options SHALL be mutually exclusive.

When either option is supplied, the provided appendix SHALL affect only the current easy-instance launch and SHALL NOT rewrite the stored specialist or easy profile.

When the selected easy profile already contributes a launch-profile prompt overlay, the appendix SHALL be appended after overlay resolution within the delegated native managed launch.

#### Scenario: Easy-profile-backed launch appends one-shot prompt text without rewriting the profile
- **WHEN** easy profile `alice` stores a reusable prompt overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --append-system-prompt-text "Treat gateway diagnostics as high priority."`
- **THEN** the current easy-instance launch appends that prompt text after the resolved profile overlay
- **AND THEN** easy profile `alice` remains unchanged after the launch

#### Scenario: Specialist-backed launch appends file-based prompt content for one launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --append-system-prompt-file /tmp/appendix.md`
- **THEN** the delegated managed launch includes the file content as a launch appendix for that instance launch
- **AND THEN** a later easy-instance launch without the appendix option does not inherit that file content

#### Scenario: Easy-instance launch rejects conflicting appendix inputs
- **WHEN** an operator supplies both `--append-system-prompt-text` and `--append-system-prompt-file` on one `houmao-mgr project easy instance launch` invocation
- **THEN** the command fails clearly before delegating to native managed launch
- **AND THEN** it does not start a managed session for that invalid launch request

### Requirement: `project easy` auth relationships resolve through auth profile identity
`houmao-mgr project easy` SHALL resolve specialist-selected auth and easy-profile auth overrides through auth profile identity rather than through auth display-name text or auth projection path names as the authoritative key.

`project easy specialist create --credential <name>` SHALL continue to accept a display name for auth selection or creation.

When `--credential` is omitted, the existing `<specialist-name>-creds` behavior SHALL remain as a display-name default only.

Easy-specialist inspection and easy-profile-backed launch SHALL render or accept current auth display names while preserving the underlying auth-profile relationship across auth rename.

#### Scenario: Specialist get renders the current auth display name after rename
- **WHEN** specialist `reviewer` references one auth profile whose display name was changed from `reviewer-creds` to `reviewer-breakglass`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name reviewer`
- **THEN** the command reports `reviewer-breakglass` as the specialist's selected auth name
- **AND THEN** it does not require specialist recreation only because the auth profile was renamed

#### Scenario: Easy-profile-backed launch still resolves the same auth profile after rename
- **WHEN** easy profile `alice` stores an auth override referencing one auth profile currently named `alice-creds`
- **AND WHEN** that auth profile is renamed to `alice-breakglass`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice`
- **THEN** the launch still resolves the same underlying auth profile
- **AND THEN** the launch does not fail only because the stored auth relationship outlived a display-name change

### Requirement: `project easy profile set` patches specialist-backed easy profiles
`houmao-mgr project easy profile set --name <profile>` SHALL patch one existing specialist-backed easy profile in the active project overlay.

The command SHALL preserve the profile source specialist and SHALL preserve unspecified stored launch defaults.

At minimum, `project easy profile set` SHALL support the same stored launch-default field families as `project agents launch-profiles set`, including managed-agent identity defaults, workdir, auth, memory binding, model, reasoning level, prompt mode, env records, mailbox config, launch posture, managed-header policy, prompt overlay, and gateway mail-notifier appendix default.

The command SHALL expose clear flags for nullable or collection fields where the explicit launch-profile `set` surface already exposes matching clear behavior.

When no requested update or clear flag is supplied, the command SHALL fail clearly without rewriting the profile.

#### Scenario: Easy profile set updates auth without dropping prompt overlay
- **WHEN** easy profile `alice` targets specialist `reviewer` and stores auth override `work` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --auth breakglass`
- **THEN** easy profile `alice` stores auth override `breakglass`
- **AND THEN** easy profile `alice` still stores its prior prompt overlay text

#### Scenario: Easy profile set clears prompt overlay
- **WHEN** easy profile `alice` stores prompt overlay mode `append` with prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --clear-prompt-overlay`
- **THEN** easy profile `alice` no longer stores prompt overlay mode or prompt overlay text
- **AND THEN** future launches from `alice` fall back to the source specialist prompt unless a stronger launch-time prompt override is supplied

#### Scenario: Easy profile set clears notifier appendix default
- **WHEN** easy profile `alice` stores gateway mail-notifier appendix default
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --clear-gateway-mail-notifier-appendix`
- **THEN** easy profile `alice` no longer stores a notifier appendix default
- **AND THEN** future launches from `alice` do not inherit a profile-owned notifier appendix unless another source supplies one

#### Scenario: Easy profile set rejects empty update
- **WHEN** easy profile `alice` exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice` without any update or clear flags
- **THEN** the command fails clearly
- **AND THEN** easy profile `alice` remains unchanged

### Requirement: `project easy profile create --yes` replaces same-lane profiles
`houmao-mgr project easy profile create --name <profile> --specialist <specialist> --yes` SHALL replace an existing same-name easy profile in the active project overlay.

Replacement SHALL use create semantics: omitted optional launch defaults SHALL be cleared rather than preserved from the old profile.

When the same-name easy profile already exists and replacement confirmation is not supplied, the command SHALL prompt on interactive terminals or fail in non-interactive contexts with guidance to rerun using `--yes`.

When the same-name profile exists but is not an easy profile, the command SHALL fail clearly even when `--yes` is supplied.

#### Scenario: Easy profile create requires confirmation before replacement
- **WHEN** easy profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist reviewer` in a non-interactive context without `--yes`
- **THEN** the command fails clearly with guidance to rerun using `--yes`
- **AND THEN** easy profile `alice` remains unchanged

#### Scenario: Easy profile create yes replaces and clears omitted fields
- **WHEN** easy profile `alice` targets specialist `reviewer` and stores workdir `/repos/alice` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist reviewer-v2 --workdir /repos/alice-v2 --yes`
- **THEN** easy profile `alice` targets specialist `reviewer-v2` and stores workdir `/repos/alice-v2`
- **AND THEN** easy profile `alice` no longer stores the prior prompt overlay text

#### Scenario: Easy profile create yes rejects cross-lane conflict
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist reviewer --yes`
- **THEN** the command fails clearly because `alice` is not an easy profile
- **AND THEN** explicit launch profile `alice` remains unchanged

### Requirement: Easy-profile mutation refreshes the compatibility projection
After `project easy profile set` or same-lane `project easy profile create --yes` replacement updates stored profile state, the command SHALL rematerialize the project agent catalog projection.

The projected `.houmao/agents/launch-profiles/<profile>.yaml` resource SHALL reflect the updated stored profile.

#### Scenario: Easy profile set updates projected launch profile
- **WHEN** easy profile `alice` projects to `.houmao/agents/launch-profiles/alice.yaml`
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --workdir /repos/alice-next`
- **THEN** the stored easy profile records workdir `/repos/alice-next`
- **AND THEN** the projected `.houmao/agents/launch-profiles/alice.yaml` reflects workdir `/repos/alice-next`

### Requirement: Easy profiles store managed-header section policy
`houmao-mgr project easy profile create` and `houmao-mgr project easy profile set` SHALL accept repeatable managed-header section policy options using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

The stored section policy SHALL apply only to the named section. Omitted sections SHALL inherit the section default.

`houmao-mgr project easy profile set` SHALL also accept:

- `--clear-managed-header-section SECTION` to remove one stored section policy entry,
- `--clear-managed-header-sections` to remove all stored section policy entries.

Whole-header policy SHALL remain controlled by existing `--managed-header`, `--no-managed-header`, and `--clear-managed-header` behavior.

#### Scenario: Easy profile create stores disabled automation notice
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer --managed-header-section automation-notice=disabled`
- **THEN** easy profile `reviewer-fast` stores automation notice section policy `disabled`
- **AND THEN** omitted identity and Houmao runtime guidance section policy remain inherited default-enabled values
- **AND THEN** omitted task reminder and mail acknowledgement section policy remain inherited default-disabled

#### Scenario: Easy profile set clears one section policy
- **WHEN** easy profile `reviewer-fast` stores automation notice section policy `disabled` and identity section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-fast --clear-managed-header-section identity`
- **THEN** easy profile `reviewer-fast` no longer stores an identity section policy
- **AND THEN** easy profile `reviewer-fast` still stores automation notice section policy `disabled`

#### Scenario: Easy profile get reports stored section policy
- **WHEN** easy profile `reviewer-fast` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy profile get --name reviewer-fast`
- **THEN** the structured output reports the stored automation notice section policy
- **AND THEN** the output does not report omitted section-default policies as stored values

#### Scenario: Easy profile create enables default-off mail acknowledgement
- **WHEN** an operator runs `houmao-mgr project easy profile create --name mailer-fast --specialist reviewer --managed-header-section mail-ack=enabled`
- **THEN** easy profile `mailer-fast` stores mail acknowledgement section policy `enabled`
- **AND THEN** future launches from `mailer-fast` include the mail acknowledgement section when the whole managed header resolves to enabled

### Requirement: Easy-instance launch supports one-shot managed-header section overrides
`houmao-mgr project easy instance launch` SHALL accept repeatable one-shot managed-header section overrides using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

When neither `--managed-header-section` nor whole-header `--managed-header` / `--no-managed-header` is supplied, easy-instance launch SHALL inherit managed-header section policy from the selected easy profile when one is present, otherwise from the section default.

Direct one-shot managed-header section overrides SHALL influence only the current launch and SHALL NOT rewrite stored easy-profile state.

If the whole managed header resolves to disabled, section-level overrides SHALL NOT render managed-header sections for that launch.

#### Scenario: Easy-instance launch disables only automation notice for one launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header-section automation-notice=disabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the identity and Houmao runtime guidance sections
- **AND THEN** the resulting managed launch does not include the automation notice section

#### Scenario: Easy-instance section override does not rewrite easy profile
- **WHEN** easy profile `reviewer-fast` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header-section automation-notice=enabled`
- **THEN** the resulting managed launch includes the automation notice section
- **AND THEN** easy profile `reviewer-fast` still records automation notice section policy `disabled`

#### Scenario: Easy-instance launch enables mail acknowledgement for one launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header-section mail-ack=enabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the mail acknowledgement section
- **AND THEN** easy profile `reviewer-fast` is not rewritten

#### Scenario: Easy-instance launch includes automation notice for as-is specialist
- **WHEN** specialist `reviewer` stores `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer`
- **AND WHEN** the whole managed header is not disabled
- **THEN** the resulting managed launch includes the automation notice section
- **AND THEN** `as_is` does not disable agent-facing automation guidance

### Requirement: `project easy specialist set` patches existing specialists
`houmao-mgr project easy specialist set --name <specialist>` SHALL patch one existing project-local easy specialist in the active project overlay.

The command SHALL preserve unspecified stored specialist fields by default.

At minimum, `project easy specialist set` SHALL support mutation of specialist prompt content, skill bindings, setup selection, credential display-name selection, launch prompt mode, launch-owned model name, launch-owned reasoning level, and persistent specialist env records.

The command SHALL expose clear flags for nullable or collection fields, including prompt content, skill bindings, prompt mode, model name, reasoning level, and persistent env records.

When no requested update or clear flag is supplied, the command SHALL fail clearly without rewriting the specialist.

The command SHALL NOT accept specialist rename or tool-lane mutation in this initial surface.

#### Scenario: Specialist set updates prompt without dropping skills
- **WHEN** specialist `researcher` stores prompt content and skill binding `notes`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --system-prompt "You are a focused repo researcher."`
- **THEN** specialist `researcher` stores the new prompt content
- **AND THEN** specialist `researcher` still stores skill binding `notes`

#### Scenario: Specialist set rejects empty update
- **WHEN** specialist `researcher` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher` without any update or clear flags
- **THEN** the command fails clearly
- **AND THEN** specialist `researcher` remains unchanged

#### Scenario: Specialist set does not change tool lane
- **WHEN** specialist `researcher` uses tool lane `codex`
- **AND WHEN** an operator wants a Claude-backed replacement specialist
- **THEN** `project easy specialist set` does not provide a `--tool` mutation path
- **AND THEN** the operator must use specialist replacement or create a separate specialist instead

### Requirement: Specialist set supports targeted skill binding edits
`houmao-mgr project easy specialist set --name <specialist>` SHALL allow operators to edit specialist skill bindings without respecifying the entire specialist.

Repeatable `--add-skill <name>` SHALL bind an existing registered project skill by name.

Repeatable `--with-skill <dir>` SHALL register or update one canonical project skill entry using the provided skill directory and SHALL bind that registered skill to the specialist.

For `--with-skill <dir>`, the provided directory SHALL be treated as caller-owned input rather than Houmao-managed content.

`project easy specialist set --with-skill` SHALL NOT delete, move, rewrite, or partially consume the provided source directory, even when the underlying project skill registration refreshes an existing canonical entry or fails partway through.

Repeatable `--remove-skill <name>` SHALL remove the named skill binding from the specialist when present.

`--clear-skills` SHALL clear all skill bindings from the specialist.

Removing or clearing skill bindings SHALL NOT delete shared skill content only because one specialist no longer references it.

#### Scenario: Specialist set registers and adds a skill
- **WHEN** specialist `researcher` exists without skill `notes-skill`
- **AND WHEN** `/tmp/notes-skill/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --with-skill /tmp/notes-skill`
- **THEN** specialist `researcher` stores skill binding `notes-skill`
- **AND THEN** the canonical project skill entry exists at `.houmao/content/skills/notes-skill`

#### Scenario: Specialist set with-skill preserves caller-owned source content
- **WHEN** specialist `researcher` exists without skill `notes-skill`
- **AND WHEN** project skill `notes-skill` is already registered through a symlink-backed canonical entry
- **AND WHEN** `/repo/skillset/notes-skill/SKILL.md` exists before the command starts
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --with-skill /repo/skillset/notes-skill`
- **THEN** specialist `researcher` stores skill binding `notes-skill`
- **AND THEN** `/repo/skillset/notes-skill` still exists with its original content intact

#### Scenario: Specialist set removes one binding without deleting shared skill content
- **WHEN** specialist `researcher` and specialist `reviewer` both reference skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --remove-skill notes`
- **THEN** specialist `researcher` no longer stores skill binding `notes`
- **AND THEN** skill content for `notes` remains available for specialist `reviewer`

### Requirement: Specialist set updates launch-owned source defaults
`houmao-mgr project easy specialist set --name <specialist>` SHALL allow operators to update launch-owned source defaults stored on the specialist.

`--prompt-mode unattended|as_is` SHALL set the stored specialist launch prompt mode.

`--clear-prompt-mode` SHALL remove the stored specialist launch prompt mode so downstream build and launch policy can resolve its default behavior.

`--model <name>` and `--reasoning-level <integer>=non-negative` SHALL update the stored launch-owned model configuration using the same partial merge semantics as reusable profile patch commands.

`--clear-model` and `--clear-reasoning-level` SHALL clear the corresponding stored launch-owned model configuration fields.

Repeatable `--env-set NAME=value` SHALL replace the stored persistent specialist env records with the provided mapping after applying the same validation used during specialist creation.

`--clear-env` SHALL remove all stored persistent specialist env records.

#### Scenario: Specialist set updates model while preserving reasoning
- **WHEN** specialist `reviewer` stores launch model `gpt-5.4` and reasoning level `4`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name reviewer --model gpt-5.4-mini`
- **THEN** specialist `reviewer` stores launch model `gpt-5.4-mini`
- **AND THEN** specialist `reviewer` still stores reasoning level `4`

#### Scenario: Specialist set rejects credential-owned env names
- **WHEN** specialist `researcher` uses the Codex tool lane
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --env-set OPENAI_API_KEY=sk-test`
- **THEN** the command fails clearly because `OPENAI_API_KEY` belongs to credential env for the selected tool
- **AND THEN** specialist `researcher` remains unchanged

### Requirement: Specialist set refreshes catalog-backed compatibility projection
After `project easy specialist set` updates stored specialist state, the command SHALL rematerialize the project agent catalog projection.

The projected role prompt and specialist-backed preset under `.houmao/agents/` SHALL reflect the updated stored specialist state.

If a specialist setup change changes the generated preset name, the command SHALL remove the previous specialist-owned projected preset file when no longer referenced by the updated specialist.

`project easy specialist set` SHALL NOT mutate running managed-agent sessions, runtime homes, or already-written launch manifests in place.

#### Scenario: Specialist set updates projected preset skills
- **WHEN** specialist `researcher` projects to `.houmao/agents/presets/researcher-codex-default.yaml`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --add-skill notes`
- **THEN** the stored specialist records skill binding `notes`
- **AND THEN** `.houmao/agents/presets/researcher-codex-default.yaml` includes skill `notes`

#### Scenario: Specialist set affects future launch only
- **WHEN** managed agent `researcher-1` is already running from specialist `researcher`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --system-prompt "Use the new review policy."`
- **THEN** specialist `researcher` stores the new prompt for future builds and launches
- **AND THEN** the command does not rewrite the running `researcher-1` runtime home or manifest in place

### Requirement: `project easy instance launch` exposes gateway TUI tracking timings for auto-attach
`houmao-mgr project easy instance launch` SHALL accept optional one-shot gateway TUI tracking timing overrides for launch-time gateway auto-attach.

The launch surface SHALL expose the timing overrides as:

- `--gateway-tui-watch-poll-interval-seconds`
- `--gateway-tui-stability-threshold-seconds`
- `--gateway-tui-completion-stability-seconds`
- `--gateway-tui-unknown-to-stalled-timeout-seconds`
- `--gateway-tui-stale-active-recovery-seconds`
- `--gateway-tui-final-stable-active-recovery-seconds`

When launch-time gateway auto-attach is enabled, the command SHALL pass any supplied gateway TUI timing overrides to the delegated managed-agent launch and gateway attach path.

When `--no-gateway` is supplied, the command SHALL reject any gateway TUI timing override because no launch-time gateway attach will be requested.

Supplying gateway TUI timing overrides SHALL NOT rewrite the stored specialist or easy-profile launch defaults.

#### Scenario: Easy launch passes timing overrides to gateway auto-attach
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-tui-completion-stability-seconds 2.5`
- **AND WHEN** launch-time gateway auto-attach is enabled
- **THEN** the delegated managed-agent launch receives a gateway TUI tracking timing override for completion stability of `2.5` seconds
- **AND THEN** the attached gateway uses that override for gateway-owned TUI tracking

#### Scenario: Easy launch passes final stable-active recovery timing override
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-tui-final-stable-active-recovery-seconds 30`
- **AND WHEN** launch-time gateway auto-attach is enabled
- **THEN** the delegated managed-agent launch receives a gateway TUI tracking timing override for final stable-active recovery of `30` seconds
- **AND THEN** the attached gateway uses that override for final stable-active recovery

#### Scenario: Easy launch timing override does not mutate profile defaults
- **WHEN** an operator launches from easy profile `alice` with one or more `--gateway-tui-*` timing overrides
- **THEN** the launch uses those timing overrides for that launch-time gateway attach
- **AND THEN** the stored easy profile remains unchanged

#### Scenario: Easy launch rejects timing overrides when gateway attach is disabled
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway --gateway-tui-stale-active-recovery-seconds 10`
- **THEN** the command fails before launch
- **AND THEN** the error states that gateway TUI timing overrides require launch-time gateway attach

### Requirement: `project easy` surfaces use memo-pages managed memory
`houmao-mgr project easy profile create` and `project easy instance launch` SHALL NOT accept `--persist-dir` or `--no-persist-dir`.

`project easy instance get` SHALL report memory root, memo file, and pages directory when available.

`project easy profile get` SHALL NOT report reusable persist-lane defaults.

#### Scenario: Easy profile create rejects persist-dir
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --persist-dir ../shared/alice-persist`
- **THEN** the command fails before writing the profile
- **AND THEN** the error identifies `--persist-dir` as unsupported

#### Scenario: Easy instance get reports memory pages
- **WHEN** an operator runs `houmao-mgr project easy instance get --name researcher-1`
- **AND WHEN** the instance exposes managed memory metadata
- **THEN** the output reports the memory root
- **AND THEN** the output reports the memo file
- **AND THEN** the output reports the pages directory
- **AND THEN** the output does not report `persist_dir`

### Requirement: Easy profile CLI manages memo seeds
`houmao-mgr project easy profile create` SHALL accept at most one memo seed source option:
- `--memo-seed-text <text>`,
- `--memo-seed-file <path>`,
- `--memo-seed-dir <path>`.

`houmao-mgr project easy profile create` SHALL NOT accept a memo seed apply policy option.

`houmao-mgr project easy profile set` SHALL support the same source options. It SHALL also accept `--clear-memo-seed` to remove the stored memo seed from the easy profile.

`--clear-memo-seed` SHALL NOT be combined with a memo seed source.

`project easy profile get --name <profile>` SHALL report memo seed presence, source kind, and managed content reference metadata without printing full memo or page contents by default.

`project easy instance launch --profile <profile>` SHALL apply the selected easy profile's memo seed during managed launch when the profile stores one, using source-scoped replacement semantics from managed launch runtime.

#### Scenario: Easy profile create stores memo seed text
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-default --specialist reviewer --memo-seed-text "Read pages/review.md first."`
- **THEN** the easy profile stores the supplied text as a memo seed
- **AND THEN** later profile inspection reports memo seed source kind `memo`
- **AND THEN** later profile inspection does not report a memo seed policy

#### Scenario: Easy profile set preserves memo seed when patching workdir
- **WHEN** easy profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --workdir /repos/next`
- **THEN** the profile updates the stored workdir
- **AND THEN** the stored memo seed remains unchanged

#### Scenario: Easy profile set replaces memo seed content
- **WHEN** easy profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --memo-seed-file docs/reviewer-next.md`
- **THEN** the command replaces the stored memo seed content
- **AND THEN** the profile still records no memo seed policy

#### Scenario: Easy memo-only seed preserves pages
- **WHEN** easy profile `reviewer-default` stores memo-only seed text
- **AND WHEN** managed agent `reviewer-default` already has pages
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's `houmao-memo.md`
- **AND THEN** it leaves the launched agent's pages unchanged

#### Scenario: Memo seed policy option is unsupported
- **WHEN** an operator supplies `--memo-seed-policy replace`
- **THEN** `project easy profile create` or `project easy profile set` fails before mutating the stored profile

#### Scenario: Easy profile set rejects clear combined with source
- **WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --clear-memo-seed --memo-seed-file docs/reviewer.md`
- **THEN** the command fails clearly before mutating the easy profile

### Requirement: Easy instance stop preserves managed-agent cleanup locators
`houmao-mgr project easy instance stop --name <name>` SHALL preserve durable cleanup locator fields from the underlying managed-agent stop result when they are available.

At minimum, the successful easy-instance stop output SHALL include:

- `manifest_path`
- `session_root`

The command SHALL continue validating that the target belongs to the selected project overlay before stopping it. After stop, the emitted locator fields SHALL let the operator run `houmao-mgr agents cleanup session|logs|mailbox --manifest-path <path>` or `--session-root <path>` without relying on a live shared-registry record.

#### Scenario: Easy instance stop returns cleanup locators
- **WHEN** an operator runs `houmao-mgr project easy instance stop --name reviewer`
- **AND WHEN** the selected managed agent belongs to the active project overlay
- **AND WHEN** the underlying stop result exposes `manifest_path` and `session_root`
- **THEN** the easy-instance stop output includes those locator fields
- **AND THEN** the output still includes the selected project overlay metadata

#### Scenario: Easy instance stop keeps overlay validation before stop
- **WHEN** an operator runs `houmao-mgr project easy instance stop --name reviewer`
- **AND WHEN** the resolved managed agent manifest does not belong to the selected project overlay
- **THEN** the command fails before stopping the target
- **AND THEN** it does not emit cleanup locators for an unrelated managed session

### Requirement: Easy-specialist flows do not auto-upgrade legacy specialist metadata
Maintained `houmao-mgr project easy ...` specialist flows SHALL NOT silently import or rewrite legacy `.houmao/easy/specialists/*.toml` metadata during ordinary specialist inspection, mutation, or launch preparation.

When the selected project overlay still depends on legacy easy-specialist metadata that requires explicit migration, the command SHALL fail clearly and direct the operator to `houmao-mgr project migrate`.

#### Scenario: Specialist get rejects legacy specialist metadata with migration guidance
- **WHEN** the selected project overlay still contains one legacy `.houmao/easy/specialists/researcher.toml` specialist definition that has not been migrated
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command fails clearly
- **AND THEN** the diagnostic directs the operator to `houmao-mgr project migrate`

### Requirement: `project easy specialist create` can bind registered project skills
`houmao-mgr project easy specialist create` SHALL support binding existing registered project skills by name at create time.

Repeatable `--skill <name>` SHALL bind one existing registered project skill to the created specialist.

Repeatable `--with-skill <dir>` MAY remain as a convenience path, but its maintained meaning SHALL be to register or update one canonical project skill entry and then bind that registered skill to the created specialist.

For `--with-skill <dir>`, the provided directory SHALL be treated as caller-owned input rather than specialist-owned or Houmao-managed content.

`project easy specialist create --with-skill` SHALL NOT delete, move, rewrite, or partially consume the provided source directory, even when the underlying project skill registration refreshes an existing canonical entry or the create command later fails.

The created specialist SHALL persist skill relationships by registered project skill name rather than by treating an imported directory path as specialist-owned canonical storage.

#### Scenario: Specialist create binds one existing registered project skill
- **WHEN** project skill `notes` is already registered
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --skill notes`
- **THEN** specialist `researcher` stores a binding to registered project skill `notes`
- **AND THEN** the specialist does not create a second canonical project-owned copy of that skill outside the project skill registry

#### Scenario: Specialist create with-skill preserves caller-owned source content
- **WHEN** `/repo/skillset/notes/SKILL.md` exists before the command starts
- **AND WHEN** project skill `notes` is already registered through a symlink-backed canonical entry
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --with-skill /repo/skillset/notes`
- **THEN** specialist `researcher` stores a binding to registered project skill `notes`
- **AND THEN** `/repo/skillset/notes` still exists with its original content intact

### Requirement: Specialist get reports registry-backed skill references
`houmao-mgr project easy specialist get --name <specialist>` SHALL report each bound project skill by registered name.

When the bound project skill is registered in `copy` or `symlink` mode, `specialist get` SHALL report that mode and the canonical project skill path under `.houmao/content/skills/`.

#### Scenario: Specialist get reports canonical project skill references
- **WHEN** specialist `researcher` binds project skill `notes`
- **AND WHEN** `notes` is registered in `symlink` mode
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports bound project skill `notes`
- **AND THEN** it reports canonical path `.houmao/content/skills/notes` and mode `symlink`

### Requirement: `project easy profile` enforces easy-profile lane ownership
`houmao-mgr project easy profile list|get|set|remove` SHALL operate only on stored `easy_profile` entries even though explicit launch profiles share the same catalog-backed launch-profile family and compatibility projection path.

When `project easy profile get --name <profile>`, `set --name <profile>`, or `remove --name <profile>` targets a stored profile whose `profile_lane` is `launch_profile`, the command SHALL fail clearly instead of reading, mutating, or deleting that explicit launch profile through the easy lane.

That wrong-lane failure SHALL identify that the named resource belongs to the explicit launch-profile lane and SHALL direct the operator to the corresponding `houmao-mgr project agents launch-profiles <verb> --name <profile>` command.

`project easy profile list` SHALL continue returning only easy-profile entries in `profiles`. When that easy-lane result is empty and one or more explicit launch profiles exist in the selected overlay, the output SHALL include operator guidance to use `houmao-mgr project agents launch-profiles list`.

#### Scenario: Easy get rejects explicit launch profile with redirect guidance
- **WHEN** explicit launch profile `nightly` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy profile get --name nightly`
- **THEN** the command fails clearly instead of returning `nightly`
- **AND THEN** the error explains that `nightly` belongs to the explicit launch-profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project agents launch-profiles get --name nightly`

#### Scenario: Easy set rejects explicit launch profile with redirect guidance
- **WHEN** explicit launch profile `nightly` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name nightly --workdir /repos/nightly-next`
- **THEN** the command fails clearly before mutating `nightly`
- **AND THEN** the error explains that `nightly` belongs to the explicit launch-profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project agents launch-profiles set --name nightly`

#### Scenario: Easy remove rejects explicit launch profile with redirect guidance
- **WHEN** explicit launch profile `nightly` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy profile remove --name nightly`
- **THEN** the command fails clearly before deleting `nightly`
- **AND THEN** the error explains that `nightly` belongs to the explicit launch-profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project agents launch-profiles remove --name nightly`

#### Scenario: Easy list keeps lane filtering and adds note when only explicit launch profiles exist
- **WHEN** the selected project overlay contains one or more explicit launch profiles
- **AND WHEN** the selected project overlay contains no easy profiles that match the current easy-list query
- **AND WHEN** an operator runs `houmao-mgr project easy profile list`
- **THEN** the structured output reports an empty `profiles` list
- **AND THEN** the structured output includes guidance to use `houmao-mgr project agents launch-profiles list`
- **AND THEN** the easy list output does not inline explicit launch profiles under `profiles`

### Requirement: `project easy instance launch` supports explicit preserved-home reuse

`houmao-mgr project easy instance launch` SHALL accept optional `--reuse-home` for the current easy launch.

`--reuse-home` SHALL be launch-owned only and SHALL NOT be persisted into the stored specialist or easy profile.

When `--reuse-home` is supplied, easy instance launch SHALL treat the request as restart of one stopped logical managed agent on one compatible preserved home for the resolved managed identity instead of allocating a new home.

The command SHALL support `--reuse-home` for both specialist-backed launch and easy-profile-backed launch.

For easy-profile-backed launch, reused-home restart SHALL apply the currently stored easy-profile inputs, together with any stronger direct CLI overrides, onto the preserved home before startup. Updating the stored easy profile after the prior run SHALL therefore affect the restarted agent even though the prior stopped instance was not mutated in place.

The command SHALL require the prior runtime to already be down and its tmux session to already be absent. `--reuse-home` SHALL NOT by itself replace a fresh live owner of the same managed identity.

When the stopped lifecycle metadata carries a prior tmux session name and the operator does not provide `--session-name`, the command SHALL request restart using that same tmux session name.

When `--session-name` is provided, that explicit override SHALL take precedence over the stopped record's prior tmux session name.

The command SHALL use the stopped local lifecycle record and preserved manifest/home metadata as restart authority and SHALL NOT require separate registry cleanup before restarting.

If no compatible stopped preserved home can be resolved, the command SHALL fail clearly and SHALL NOT silently launch on a new home.

#### Scenario: Easy-profile-backed launch restarts one stopped preserved home with updated profile inputs
- **WHEN** easy profile `reviewer-default` resolves managed identity `reviewer-default`
- **AND WHEN** a stopped compatible preserved home exists for that identity with prior tmux session name `HOUMAO-reviewer-default-1700000000000`
- **AND WHEN** the stored easy profile `reviewer-default` has been updated since the prior run
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default --reuse-home`
- **THEN** the delegated native launch requests reused-home restart for that managed identity
- **AND THEN** the current stored easy-profile inputs are projected onto the preserved home before startup
- **AND THEN** the restart does not require separate registry cleanup
- **AND THEN** the restart requests tmux session name `HOUMAO-reviewer-default-1700000000000` by default

#### Scenario: Specialist-backed launch rejects reuse-home when no preserved home exists
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer --name reviewer-a --reuse-home`
- **AND WHEN** no compatible stopped preserved home exists for managed identity `reviewer-a`
- **THEN** the command fails clearly
- **AND THEN** it does not silently start a fresh-home launch

#### Scenario: Reuse-home does not bypass easy-launch ownership conflict on its own
- **WHEN** a fresh live session already owns managed identity `reviewer-a`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer --name reviewer-a --reuse-home`
- **THEN** the command fails rather than replacing that live owner
- **AND THEN** the failure tells the operator to stop the live owner before attempting reused-home restart

#### Scenario: Easy explicit session-name override wins over the stopped record
- **WHEN** easy profile `reviewer-default` resolves one stopped compatible preserved home
- **AND WHEN** the stopped lifecycle metadata carries prior tmux session name `HOUMAO-reviewer-default-1700000000000`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default --reuse-home --session-name reviewer-restart-debug`
- **THEN** the delegated native launch requests reused-home restart on the preserved home
- **AND THEN** the restart uses tmux session name `reviewer-restart-debug`
- **AND THEN** it does not silently force the old tmux session name when the operator supplied a stronger override
