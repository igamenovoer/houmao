## MODIFIED Requirements

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
- repeated persistent specialist env input `--env-set NAME=value`

When `--credential` is omitted, the command SHALL derive the credential bundle name as `<specialist-name>-creds`.

When no system prompt source is provided, the command SHALL still create a valid promptless role semantic object for that specialist.

Persistent specialist env records supplied through `--env-set` at specialist-create time SHALL be stored as specialist launch config and SHALL remain separate from the effective auth selection and the credential bundle's auth env file.

`project easy specialist create --env-set` SHALL accept only literal `NAME=value` entries. It SHALL reject:

- blank env names
- duplicate env names in the same specialist definition
- Houmao-owned reserved env names
- env names that belong to the selected tool adapter's auth-env allowlist

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

#### Scenario: Create uses the derived credential name by default
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --system-prompt "You are a precise repo researcher." --tool codex --api-key sk-test --with-skill /tmp/notes-skill`
- **THEN** the command persists specialist `researcher` into the project-local catalog
- **AND THEN** it records the derived credential selection `researcher-creds`
- **AND THEN** it records the selected prompt, tool, auth, and skill relationships without relying on directory nesting alone as the semantic graph

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

### Requirement: `project easy specialist list/get/remove` manages persisted specialist definitions

`houmao-mgr project easy specialist list` SHALL enumerate persisted specialist definitions from the project-local catalog.

`houmao-mgr project easy specialist get --name <specialist>` SHALL report one specialist's high-level semantic metadata plus the managed content or derived artifact references relevant to that specialist.

`houmao-mgr project easy specialist get` SHALL report persistent specialist env records separately from the credential selection and auth content path.

`houmao-mgr project easy specialist remove --name <specialist>` SHALL remove the persisted specialist definition from the project-local catalog and SHALL remove any specialist-owned derived projection state that exists only for that specialist.

`specialist remove` SHALL NOT delete shared skills, shared auth content, or other shared managed content only because one specialist referenced them.

#### Scenario: Get reports semantic specialist metadata and content references
- **WHEN** specialist `researcher` exists in the project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports the specialist's tool, credential, and skill selections
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

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance

`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the stored specialist definition from the project-local catalog and delegating to the existing native managed-agent launch flow.

The launch provider SHALL be derived from the specialist's selected tool:

- `claude` -> `claude_code`
- `codex` -> `codex`
- `gemini` -> `gemini_cli`

The operator SHALL NOT need to provide the provider identifier separately when launching an instance from a specialist.

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
