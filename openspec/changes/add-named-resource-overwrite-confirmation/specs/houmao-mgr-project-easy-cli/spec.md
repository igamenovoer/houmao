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
