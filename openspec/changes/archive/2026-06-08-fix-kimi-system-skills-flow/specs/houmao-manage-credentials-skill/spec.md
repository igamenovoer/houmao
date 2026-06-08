# houmao-manage-credentials-skill Specification

## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-credential-mgr` system skill

The system SHALL package a Houmao-owned system skill named `houmao-credential-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage credential CRUD through these supported commands for supported credential-CRUD tool families:

- `houmao-mgr project credentials <tool> list`
- `houmao-mgr project credentials <tool> get`
- `houmao-mgr project credentials <tool> add`
- `houmao-mgr project credentials <tool> set`
- `houmao-mgr project credentials <tool> rename`
- `houmao-mgr project credentials <tool> remove`
- `houmao-mgr internals native-agent credentials <tool> list --native-agent-root <path>`
- `houmao-mgr internals native-agent credentials <tool> get --native-agent-root <path> --name <name>`
- `houmao-mgr internals native-agent credentials <tool> add --native-agent-root <path> --name <name>`
- `houmao-mgr internals native-agent credentials <tool> set --native-agent-root <path> --name <name>`
- `houmao-mgr internals native-agent credentials <tool> rename --native-agent-root <path> --name <name> --to <new-name>`
- `houmao-mgr internals native-agent credentials <tool> remove --native-agent-root <path> --name <name>`

The packaged skill SHALL scope credential CRUD guidance to the supported tool families:

- `claude`
- `codex`
- `gemini`
- `kimi`

That skill SHALL instruct agents to use credential login helpers only for tool families with maintained login-helper support:

- `houmao-mgr project credentials <login-tool> login`
- `houmao-mgr internals native-agent credentials <login-tool> login --native-agent-root <path> --name <name>`

The packaged skill SHALL scope credential login-helper guidance to:

- `claude`
- `codex`
- `gemini`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `list`
- `get`
- `add`
- `set`
- `rename`
- `remove`
- `login`

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project specialist create|list|get|remove`
- `project agents launch|list|get|stop`
- `agents launch|join|list|stop|cleanup`
- `internals native-agent tools <tool> setups ...`
- `internals native-agent roles ...`
- `project mailbox ...`, `agents cleanup mailbox`, and `admin cleanup runtime ...`
- direct hand-editing of credential files under `.houmao/agents/tools/` or retained native-agent credential roots

#### Scenario: Installed skill points the agent at the supported credential commands

- **WHEN** an agent opens the installed `houmao-credential-mgr` skill
- **THEN** the skill directs the agent to use the supported `project [--project-dir <dir>] credentials ...` or `internals native-agent credentials ... --native-agent-root <path>` command surfaces for credential work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance including rename

- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `list`, `get`, `add`, `set`, `rename`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps non-credential project and runtime surfaces out of scope

- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the skill marks specialist CRUD, managed-agent lifecycle work, mailbox cleanup, and direct file editing as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of the supported credential-management guidance

#### Scenario: Kimi credential work is CRUD-only

- **WHEN** an agent reads `houmao-credential-mgr` guidance for tool `kimi`
- **THEN** the skill presents `list`, `get`, `add`, `set`, `rename`, and `remove` as supported credential actions
- **AND THEN** it does not present a Kimi credential `login` helper unless a maintained Kimi login helper is added in a later change

### Requirement: `houmao-credential-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs

The packaged `houmao-credential-mgr` skill SHALL ship a `references/` directory under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` and four per-tool credential kinds reference pages inside that directory:

- `claude-credential-kinds.md`
- `codex-credential-kinds.md`
- `gemini-credential-kinds.md`
- `kimi-credential-kinds.md`

Each kinds reference page SHALL enumerate the user-facing credential kinds the selected tool accepts through `houmao-mgr project credentials <tool> add` and `houmao-mgr internals native-agent credentials <tool> add --native-agent-root <path>`, including at minimum the following kinds per tool:

- Claude: API key, auth token, OAuth token, and a vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present.
- Codex: API key, and a cached login state kind that carries an `auth.json` file.
- Gemini: API key, a Vertex AI kind that pairs a Google API key with the Vertex AI selector, and an OAuth creds kind that carries an `.gemini/oauth_creds.json` file.
- Kimi: API key or provider-routing material that may include model name, base URL, provider type, Kimi Code base URL, Kimi Code OAuth host, OAuth host, telemetry disablement, `config.toml`, or credential JSON inputs according to the maintained Kimi credential CLI.

Each kinds reference page SHALL for every enumerated kind state:

- a plain-language name for the kind that a first-time user can recognize,
- a description of what the user would provide for that kind,
- the `project credentials <tool> add` flag that the kind maps to in the `houmao-credential-mgr` command surface,
- a short guidance line on when the user would pick that kind.

Each kinds reference page SHALL state that `houmao-credential-mgr/actions/add.md` does not run discovery-mode credential creation, and SHALL point the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation.

The `houmao-credential-mgr/actions/add.md` step that asks the user for missing auth inputs SHALL cite the kinds reference for the currently selected tool when the skill presents auth-input options to the user.

The `houmao-credential-mgr/SKILL.md` top-level file SHALL list the four kinds references as the credential kinds menu surface.

The kinds reference pages SHALL use flag spellings that match the `houmao-credential-mgr` command surface rather than the `houmao-specialist-mgr` create-command spellings.

#### Scenario: Selected tool loads only its own kinds reference when asking the user

- **WHEN** the add action needs to present auth-input options to the user for one selected tool
- **THEN** the skill loads the kinds reference for that tool from the `houmao-credential-mgr` references directory and presents the enumerated kinds as a menu
- **AND THEN** it does not load the kinds references for other tools in the same turn

#### Scenario: Kinds reference uses credential-mgr flag spellings

- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** each enumerated kind maps to a `project credentials <tool> add` flag such as `--api-key`, `--auth-token`, `--oauth-token`, `--auth-json`, `--oauth-creds`, `--config-dir`, `--google-api-key`, `--use-vertex-ai`, `--base-url`, `--provider-type`, `--config-toml`, or `--credential-json`
- **AND THEN** it does not use the corresponding `houmao-specialist-mgr` create-command flag spellings

#### Scenario: Kinds reference notes the credential-mgr discovery gap

- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** the page states that `houmao-credential-mgr/actions/add.md` does not run discovery-mode credential creation
- **AND THEN** the page points the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation

#### Scenario: Kimi kinds reference covers Kimi credential inputs

- **WHEN** the Kimi kinds reference for `houmao-credential-mgr` is presented to the user
- **THEN** it describes the Kimi credential inputs accepted by the maintained credential add/set surfaces
- **AND THEN** it maps those inputs to credential-manager flag spellings such as `--api-key`, `--model-name`, `--base-url`, `--provider-type`, `--code-base-url`, `--code-oauth-host`, `--oauth-host`, `--disable-telemetry`, `--config-toml`, or `--credential-json`

## ADDED Requirements

### Requirement: `houmao-credential-mgr` action guidance includes Kimi credential CRUD

The packaged `houmao-credential-mgr` action pages for `list`, `get`, `add`, `set`, `rename`, and `remove` SHALL include Kimi as a supported tool family wherever those pages enumerate supported tools or show tool-specific credential examples.

Kimi `add` and `set` guidance SHALL describe only documented Kimi credential flags and SHALL NOT invent provider-neutral flags that the CLI does not support.

Kimi `login` guidance SHALL state that Kimi does not have a maintained Houmao credential login helper in this change.

#### Scenario: Add guidance offers Kimi credential inputs

- **WHEN** a user asks the installed skill to add a Kimi credential
- **THEN** the `add` action can route to `houmao-mgr project credentials kimi add --name <name>` or `houmao-mgr internals native-agent credentials kimi add --native-agent-root <path> --name <name>`
- **AND THEN** the guidance offers Kimi-specific supported credential inputs rather than Claude, Codex, or Gemini-only options

#### Scenario: Set guidance offers Kimi credential updates

- **WHEN** a user asks the installed skill to update a Kimi credential
- **THEN** the `set` action can route to the Kimi credential set command for the selected target
- **AND THEN** the guidance presents Kimi-specific update flags from the maintained CLI surface

#### Scenario: Login guidance excludes Kimi helper workflow

- **WHEN** a user asks the installed skill to log in to Kimi through Houmao credential helpers
- **THEN** the skill explains that no maintained Kimi credential login helper is available in this change
- **AND THEN** it does not direct the agent to run a Claude, Codex, or Gemini login helper for Kimi
