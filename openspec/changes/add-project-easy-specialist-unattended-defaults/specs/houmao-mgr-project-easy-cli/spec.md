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

When `--credential` is omitted, the command SHALL derive the credential bundle name as `<specialist-name>-creds`.

When no system prompt source is provided, the command SHALL still create a valid promptless role semantic object for that specialist.

The command SHALL persist one specialist into the project-local catalog as explicit relationships among at minimum:

- the specialist identity,
- the role identity,
- the selected tool,
- the selected setup or preset semantics,
- the effective auth selection,
- the selected skill package references,
- any managed content references required for prompt or auth payloads.

The resulting project-local catalog and managed content store SHALL remain the authoritative build and launch input for project-aware flows.

For tools whose maintained easy launch path supports unattended startup, `specialist create` SHALL persist `launch.prompt_mode: unattended` by default in both the catalog-backed specialist launch payload and the generated compatibility preset.

When the operator passes `--no-unattended`, the command SHALL persist explicit interactive startup posture for that specialist instead of omitting launch prompt mode entirely.

For tools whose maintained easy launch path does not support unattended startup, the command SHALL NOT inject unattended launch posture solely because the tool was selected.

#### Scenario: Create uses the derived credential name by default
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --system-prompt "You are a precise repo researcher." --tool codex --api-key sk-test --with-skill /tmp/notes-skill`
- **THEN** the command persists specialist `researcher` into the project-local catalog
- **AND THEN** it records the derived credential selection `researcher-creds`
- **AND THEN** it records the selected prompt, tool, auth, skill, and launch relationships without relying on directory nesting alone as the semantic graph

#### Scenario: Claude easy specialist defaults to unattended startup posture
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name python-sde --tool claude --api-key sk-test`
- **THEN** the command persists specialist `python-sde` successfully
- **AND THEN** the stored specialist launch payload records `prompt_mode = unattended`
- **AND THEN** the generated preset stores `launch.prompt_mode: unattended`

#### Scenario: Operator can opt out of the easy unattended default
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name python-sde --tool claude --api-key sk-test --no-unattended`
- **THEN** the command persists specialist `python-sde` successfully
- **AND THEN** the stored specialist launch payload records interactive startup posture explicitly
- **AND THEN** the generated preset stores `launch.prompt_mode: interactive`

#### Scenario: Promptless specialist still persists as a valid catalog-backed specialist
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool gemini --gemini-oauth-creds /tmp/oauth.json`
- **THEN** the command persists a valid project-local specialist for `reviewer`
- **AND THEN** the persisted role semantics may be promptless
- **AND THEN** later project-aware launch still derives the Gemini provider lane from that stored specialist semantics

#### Scenario: Missing derived credential without auth input fails clearly
- **WHEN** no compatible local auth content exists for the derived credential `researcher-creds`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --system-prompt "You are a precise repo researcher."`
- **THEN** the command fails clearly
- **AND THEN** the error identifies the resolved credential name `researcher-creds`

### Requirement: `project easy specialist list/get/remove` manages persisted specialist definitions

`houmao-mgr project easy specialist list` SHALL enumerate persisted specialist definitions from the project-local catalog.

`houmao-mgr project easy specialist get --name <specialist>` SHALL report one specialist's high-level semantic metadata plus the managed content or derived artifact references relevant to that specialist.

`houmao-mgr project easy specialist remove --name <specialist>` SHALL remove the persisted specialist definition from the project-local catalog and SHALL remove any specialist-owned derived projection state that exists only for that specialist.

`specialist remove` SHALL NOT delete shared skills, shared auth content, or other shared managed content only because one specialist referenced them.

When a specialist has stored launch posture, `specialist get` SHALL report that launch payload as part of the specialist's semantic metadata.

#### Scenario: Get reports semantic specialist metadata and content references
- **WHEN** specialist `researcher` exists in the project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports the specialist's tool, credential, skill, and launch selections
- **AND THEN** it reports the relevant managed content or derived artifact references for that specialist without requiring `.houmao/easy/specialists/researcher.toml` to be the source of truth

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

When the selected specialist stores launch posture in its specialist configuration, `project easy instance launch` SHALL honor that stored posture for brain construction and runtime launch instead of injecting an additional prompt-mode policy of its own.

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

#### Scenario: Easy instance launch honors stored interactive specialist posture
- **WHEN** specialist `python-sde` exists in the project-local catalog with stored `launch.prompt_mode: interactive`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist python-sde --name python-sde`
- **THEN** the resulting brain build records interactive operator prompt mode
- **AND THEN** the command does not inject unattended startup behavior merely because the launch came through the easy instance surface
