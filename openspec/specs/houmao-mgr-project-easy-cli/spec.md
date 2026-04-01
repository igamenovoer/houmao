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

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance
`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the stored specialist definition from the active project-local catalog and delegating to the existing native managed-agent launch flow.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, the command SHALL ensure `<cwd>/.houmao` exists before launch preparation begins.

When no stronger explicit or env-var override is supplied, easy instance launch SHALL use overlay-local defaults for:

- runtime root: `<active-overlay>/runtime`
- jobs root: `<active-overlay>/jobs`
- mailbox root: `<active-overlay>/mailbox` for project-aware mailbox defaults

The launch provider SHALL still be derived from the specialist's selected tool, and the command SHALL still honor stored specialist launch posture and mailbox validation rules.

#### Scenario: Easy instance launch uses overlay-local runtime and jobs defaults
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** no stronger runtime-root or jobs-root override is supplied
- **THEN** the resulting brain build and runtime session use `/repo/.houmao/runtime`
- **AND THEN** the session-local job dir is derived under `/repo/.houmao/jobs/<session-id>/`

#### Scenario: Easy instance launch bootstraps the missing overlay before launch
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command ensures `<cwd>/.houmao` exists before resolving the specialist-backed launch
- **AND THEN** the launch uses that resulting overlay as the default local root family

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

