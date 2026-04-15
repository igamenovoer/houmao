## ADDED Requirements

### Requirement: `houmao-credential-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs

The packaged `houmao-credential-mgr` skill SHALL ship a `references/` directory under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` and three per-tool credential kinds reference pages inside that directory:

- `claude-credential-kinds.md`
- `codex-credential-kinds.md`
- `gemini-credential-kinds.md`

Each kinds reference page SHALL enumerate the user-facing credential kinds the selected tool accepts through `houmao-mgr project credentials <tool> add` and `houmao-mgr credentials <tool> add --agent-def-dir <path>`, including at minimum the following kinds per tool:

- Claude: API key, auth token, OAuth token, and a vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present.
- Codex: API key, and a cached login state kind that carries an `auth.json` file.
- Gemini: API key, a Vertex AI kind that pairs a Google API key with the Vertex AI selector, and an OAuth creds kind that carries an `.gemini/oauth_creds.json` file.

Each kinds reference page SHALL for every enumerated kind state:

- a plain-language name for the kind that a first-time user can recognize,
- a description of what the user would provide for that kind (for example a string value, a file path, or a directory path),
- the `project credentials <tool> add` flag that the kind maps to in the `houmao-credential-mgr` command surface,
- a short guidance line on when the user would pick that kind.

Each kinds reference page SHALL state that `houmao-credential-mgr/actions/add.md` does not run discovery-mode credential creation, and SHALL point the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation.

The `houmao-credential-mgr/actions/add.md` step that asks the user for missing auth inputs SHALL cite the kinds reference for the currently selected tool when the skill presents auth-input options to the user.

The `houmao-credential-mgr/SKILL.md` top-level file SHALL list the three new kinds references as the credential kinds menu surface.

The kinds reference pages SHALL use flag spellings that match the `houmao-credential-mgr` command surface (for example `--oauth-token`, `--auth-json`, `--oauth-creds`, `--config-dir`) rather than the `houmao-specialist-mgr` create-command spellings (for example `--claude-oauth-token`, `--codex-auth-json`, `--gemini-oauth-creds`, `--claude-config-dir`).

#### Scenario: Selected tool loads only its own kinds reference when asking the user

- **WHEN** the add action needs to present auth-input options to the user for one selected tool
- **THEN** the skill loads the kinds reference for that tool from the `houmao-credential-mgr` references directory and presents the enumerated kinds as a menu
- **AND THEN** it does not load the kinds references for the other two tools in the same turn

#### Scenario: Kinds reference uses credential-mgr flag spellings

- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** each enumerated kind maps to a `project credentials <tool> add` flag such as `--api-key`, `--auth-token`, `--oauth-token`, `--auth-json`, `--oauth-creds`, `--config-dir`, or `--google-api-key` plus `--use-vertex-ai`
- **AND THEN** it does not use the `houmao-specialist-mgr` create-command spellings

#### Scenario: Kinds reference notes the credential-mgr discovery gap

- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** the page states that `houmao-credential-mgr/actions/add.md` does not run discovery-mode credential creation
- **AND THEN** the page points the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation

#### Scenario: Kinds reference covers the Claude vendor-login config-directory kind

- **WHEN** the Claude kinds reference for `houmao-credential-mgr` is presented to the user
- **THEN** it describes the vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present
- **AND THEN** it maps that kind to the `--config-dir` add flag rather than inventing separate file flags
