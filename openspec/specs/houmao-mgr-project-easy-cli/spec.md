# houmao-mgr-project-easy-cli Specification

## Purpose
Define the higher-level `houmao-mgr project easy` workflow for compiling reusable specialist definitions into the canonical repo-local `.houmao/agents/` tree.
## Requirements
### Requirement: `project easy specialist create` compiles one specialist into canonical project agent artifacts

`houmao-mgr project easy specialist create` SHALL create one project-local specialist by persisting the operator's intended specialist semantics into the project-local catalog and managed content store.

At minimum, `specialist create` SHALL require:

- `--name <specialist>`
- `--tool <claude|codex|gemini>`

At minimum, `specialist create` SHALL support:

- zero or one system prompt source from `--system-prompt <text>` or `--system-prompt-file <path>`
- optional `--credential <name>`
- common credential inputs `--api-key` and `--base-url`
- a tool-specific auth-file flag appropriate to the selected tool
- repeated `--with-skill <skill-dir>`
- `--no-unattended` as the explicit opt-out from the easy unattended default
- repeated persistent specialist env input `--env-set NAME=value`
- `--yes` to confirm replacement of an existing specialist definition without prompting

When `--credential` is omitted, the command SHALL derive the credential bundle name as `<specialist-name>-creds`.

When no system prompt source is provided, the command SHALL still create a valid promptless role semantic object for that specialist.

Persistent specialist env records supplied through `--env-set` at specialist-create time SHALL be stored as specialist launch config and SHALL remain separate from the effective auth selection and the credential bundle's auth env file.

The command SHALL persist one specialist into the project-local catalog as explicit relationships among at minimum:

- the specialist identity,
- the role identity,
- the selected tool,
- the selected setup or preset semantics,
- the effective auth selection,
- the selected skill package references,
- persistent specialist env records when present, and
- any managed content references required for prompt or auth payloads.

The resulting project-local catalog and managed content store SHALL remain the authoritative build and launch input for project-aware flows.

For tools whose maintained easy launch path supports unattended startup, `specialist create` SHALL persist `launch.prompt_mode: unattended` by default in both the catalog-backed specialist launch payload and the generated compatibility preset.

When the operator passes `--no-unattended`, the command SHALL persist `launch.prompt_mode: as_is` for that specialist rather than omitting launch prompt mode or storing a legacy `interactive` value.

For tools whose maintained easy launch path does not support unattended startup, the command SHALL NOT inject unattended launch posture solely because the tool was selected.

`project easy specialist create --env-set` SHALL accept only literal `NAME=value` entries. It SHALL reject:

- blank env names
- duplicate env names in the same specialist definition
- Houmao-owned reserved env names
- env names that belong to the selected tool adapter's auth-env allowlist

When `specialist create` detects an existing specialist definition with the same name, whether through the project catalog entry, an existing specialist-owned role projection, or both, the CLI SHALL require explicit operator confirmation before replacing that specialist-owned state.
When `--yes` is present, the command SHALL perform the confirmed replacement without prompting.
When `--yes` is absent and no interactive terminal is available, the command SHALL fail clearly before replacing specialist-owned generated state.
A confirmed replacement SHALL update the persisted specialist definition and regenerate the specialist-owned prompt and preset projection for that specialist name.
A confirmed replacement SHALL NOT delete shared skills, shared auth content, or unrelated live runtime sessions solely because the specialist was replaced.

#### Scenario: Create uses the derived credential name by default
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --system-prompt "You are a precise repo researcher." --tool codex --api-key sk-test --with-skill /tmp/notes-skill`
- **THEN** the command persists specialist `researcher` into the project-local catalog
- **AND THEN** it records the derived credential selection `researcher-creds`
- **AND THEN** it records the selected prompt, tool, auth, and skill relationships without relying on directory nesting alone as the semantic graph

#### Scenario: Claude easy specialist defaults to unattended startup posture
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name python-sde --tool claude --api-key sk-test`
- **THEN** the command persists specialist `python-sde` successfully
- **AND THEN** the stored specialist launch payload records `prompt_mode = unattended`
- **AND THEN** the generated preset stores `launch.prompt_mode: unattended`

#### Scenario: Operator can opt out of the easy unattended default
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name python-sde --tool claude --api-key sk-test --no-unattended`
- **THEN** the command persists specialist `python-sde` successfully
- **AND THEN** the stored specialist launch payload records `prompt_mode = as_is`
- **AND THEN** the generated preset stores `launch.prompt_mode: as_is`

#### Scenario: Promptless specialist still persists as a valid catalog-backed specialist
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool gemini --gemini-oauth-creds /tmp/oauth.json`
- **THEN** the command persists a valid project-local specialist for `reviewer`
- **AND THEN** the persisted role semantics may be promptless
- **AND THEN** later project-aware launch still derives the Gemini provider lane from that stored specialist semantics

#### Scenario: Create persists specialist-owned env records separately from credentials
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --env-set OPENAI_MODEL=gpt-5.4 --env-set FEATURE_FLAG_X=1`
- **THEN** the command persists specialist `researcher`
- **AND THEN** the persisted specialist launch config includes env records `OPENAI_MODEL=gpt-5.4` and `FEATURE_FLAG_X=1`
- **AND THEN** those records are stored separately from the credential bundle auth env contract

#### Scenario: Create rejects env-set names owned by credential env
- **WHEN** the selected Codex tool adapter allowlists `OPENAI_API_KEY` for auth env
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --env-set OPENAI_API_KEY=other`
- **THEN** the command fails clearly
- **AND THEN** the error identifies that `OPENAI_API_KEY` belongs to credential env rather than specialist env records

#### Scenario: Missing derived credential without auth input fails clearly
- **WHEN** no compatible local auth content exists for the derived credential `researcher-creds`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --system-prompt "You are a precise repo researcher."`
- **THEN** the command fails clearly
- **AND THEN** the error identifies the resolved credential name `researcher-creds`

#### Scenario: Operator replaces an existing specialist after confirmation
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test`
- **AND WHEN** the project already contains specialist `researcher`
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator confirms replacement
- **THEN** the command updates the persisted specialist definition for `researcher`
- **AND THEN** it regenerates the specialist-owned prompt and preset projection for `researcher`
- **AND THEN** it does not delete shared skills or shared auth content solely because the specialist was replaced

#### Scenario: Non-interactive specialist conflict without yes fails clearly
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test`
- **AND WHEN** the project already contains specialist `researcher`
- **AND WHEN** no interactive terminal is available
- **AND WHEN** `--yes` is not present
- **THEN** the command fails clearly before replacing specialist-owned generated state

#### Scenario: Yes replaces an existing specialist without prompting
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --yes`
- **AND WHEN** the project already contains specialist `researcher`
- **THEN** the command replaces the existing specialist definition without prompting
- **AND THEN** it regenerates the specialist-owned prompt and preset projection for `researcher`

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

`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the stored specialist definition from the project-local catalog and delegating to the existing native managed-agent launch flow.

The launch provider SHALL be derived from the specialist's selected tool:

- `claude` -> `claude_code`
- `codex` -> `codex`
- `gemini` -> `gemini_cli`

The operator SHALL NOT need to provide the provider identifier separately when launching an instance from a specialist.

When the selected specialist stores launch posture in its specialist configuration, `project easy instance launch` SHALL honor that stored posture for brain construction and runtime launch instead of injecting an additional prompt-mode policy of its own.

The command SHALL accept repeatable one-off `--env-set <env-spec>` input for extra env on the current started session.

For `project easy instance launch`, `env-spec` SHALL follow Docker `--env` style:

- `NAME=value` stores one literal binding
- `NAME` resolves one inherited binding from the invoking process environment

When an inherited `--env-set NAME` binding cannot be resolved at launch time, the command SHALL fail clearly before creating a managed-agent session.

One-off `--env-set` input on `project easy instance launch` SHALL apply to the current live session only. It SHALL NOT update the specialist definition, and it SHALL NOT survive a later relaunch of that started instance.

When launch-time mailbox association is requested, the command SHALL accept these high-level mailbox inputs:

- `--mail-transport <filesystem|email>`
- `--mail-root <dir>` when `--mail-transport filesystem`
- optional `--mail-account-dir <dir>` when `--mail-transport filesystem`

If mailbox validation or mailbox bootstrap fails during a mailbox-enabled easy launch, the command SHALL fail clearly and SHALL NOT report a successful managed-agent launch.

#### Scenario: Specialist launch derives the Codex provider automatically from catalog-backed specialist state
- **WHEN** specialist `researcher` exists in the project-local catalog with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command launches the managed agent using the stored `researcher` specialist semantics and the derived `codex` provider
- **AND THEN** the operator does not need to pass `--provider codex` explicitly

#### Scenario: Easy instance launch honors stored unattended specialist posture
- **WHEN** specialist `python-sde` exists in the project-local catalog with stored `launch.prompt_mode: unattended`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist python-sde --name python-sde`
- **THEN** the resulting brain build records unattended operator prompt mode
- **AND THEN** the runtime launch uses that stored unattended posture for the selected maintained launch surface

#### Scenario: Easy instance launch honors stored as-is specialist posture
- **WHEN** specialist `python-sde` exists in the project-local catalog with stored `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist python-sde --name python-sde`
- **THEN** the resulting brain build records `as_is` operator prompt mode
- **AND THEN** the command does not inject unattended startup behavior merely because the launch came through the easy instance surface

#### Scenario: One-off env-set applies to the current started session
- **WHEN** specialist `researcher` exists in the project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --env-set FEATURE_FLAG_X=1`
- **THEN** the command launches the managed agent successfully
- **AND THEN** the current live session starts with `FEATURE_FLAG_X=1` in its effective launch environment
- **AND THEN** the specialist definition itself remains unchanged

#### Scenario: One-off env-set can inherit from the invoking environment
- **WHEN** specialist `researcher` exists in the project-local catalog
- **AND WHEN** the invoking process environment contains `OPENAI_BASE_URL=https://example.invalid/v1`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --env-set OPENAI_BASE_URL`
- **THEN** the command launches the managed agent successfully
- **AND THEN** the current live session starts with `OPENAI_BASE_URL=https://example.invalid/v1`

#### Scenario: One-off env-set does not survive relaunch
- **WHEN** launched instance `repo-research-1` started with one-off `--env-set FEATURE_FLAG_X=1`
- **AND WHEN** the specialist definition itself does not contain persistent env record `FEATURE_FLAG_X`
- **AND WHEN** that started instance is later relaunched
- **THEN** the relaunched session does not inherit `FEATURE_FLAG_X=1` from the earlier one-off launch input
- **AND THEN** only persistent specialist launch config survives relaunch

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
