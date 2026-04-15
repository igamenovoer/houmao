## ADDED Requirements

### Requirement: `houmao-specialist-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs

The packaged `houmao-specialist-mgr` skill SHALL ship three per-tool credential kinds reference pages under `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/references/`:

- `claude-credential-kinds.md`
- `codex-credential-kinds.md`
- `gemini-credential-kinds.md`

Each kinds reference page SHALL enumerate the user-facing credential kinds the selected tool accepts through `houmao-mgr project easy specialist create`, including at minimum the following kinds per tool:

- Claude: API key, auth token, OAuth token, and a vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present.
- Codex: API key, and a cached login state kind that carries an `auth.json` file.
- Gemini: API key, a Vertex AI kind that pairs a Google API key with the Vertex AI selector, and an OAuth creds kind that carries an `.gemini/oauth_creds.json` file.

Each kinds reference page SHALL for every enumerated kind state:

- a plain-language name for the kind that a first-time user can recognize,
- a description of what the user would provide for that kind (for example a string value, a file path, or a directory path),
- the `project easy specialist create` flag that the kind maps to in the `houmao-specialist-mgr` command surface,
- a short guidance line on when the user would pick that kind.

Each kinds reference page SHALL name discovery shortcuts (auto credentials, env lookup, directory scan) as alternatives to picking an explicit kind, and SHALL cite the matching `*-credential-lookup.md` reference for discovery-mode details rather than restating discovery rules inline.

The `houmao-specialist-mgr/actions/create.md` step that asks the user for missing auth inputs SHALL cite the kinds reference for the currently selected tool when the skill presents auth-input options to the user.

The `houmao-specialist-mgr/SKILL.md` References section SHALL list the three new kinds references.

The kinds reference pages SHALL NOT replace the existing `*-credential-lookup.md` references or remove discovery-mode behavior from the create action.

#### Scenario: Selected tool loads only its own kinds reference when asking the user

- **WHEN** the create action needs to present auth-input options to the user for one selected tool
- **THEN** the skill loads the kinds reference for that tool and presents the enumerated kinds as a menu
- **AND THEN** it does not load the kinds references for the other two tools in the same turn

#### Scenario: Kinds reference enumerates selectable kinds in user-facing language

- **WHEN** an agent reads one of the packaged credential kinds references
- **THEN** the page lists each kind by a plain-language name, what the user provides, the mapping flag, and when to pick that kind
- **AND THEN** the page does not collapse the menu into a bare flag table

#### Scenario: Kinds reference cites the existing lookup reference for discovery shortcuts

- **WHEN** an agent reads one of the packaged credential kinds references
- **THEN** the page describes discovery shortcuts (auto credentials, env lookup, directory scan) as alternatives to picking an explicit kind
- **AND THEN** the page cites the corresponding `*-credential-lookup.md` reference for discovery-mode detail rather than restating the discovery rules inline

#### Scenario: Kinds reference covers the Claude vendor-login config-directory kind

- **WHEN** the Claude kinds reference is presented to the user
- **THEN** it describes the vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present
- **AND THEN** it maps that kind to the `--claude-config-dir` create flag rather than inventing separate file flags

#### Scenario: Kinds reference covers the Gemini Vertex AI kind

- **WHEN** the Gemini kinds reference is presented to the user
- **THEN** it describes the Vertex AI kind as pairing a Google API key with the Vertex AI selector
- **AND THEN** it maps that kind to the `--google-api-key` plus `--use-vertex-ai` create flags rather than folding it into the generic API key kind
