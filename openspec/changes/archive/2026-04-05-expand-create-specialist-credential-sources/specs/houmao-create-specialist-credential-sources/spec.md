## ADDED Requirements

### Requirement: `houmao-create-specialist` SHALL expose four credential-source modes

The packaged `houmao-create-specialist` system skill SHALL describe credential sourcing as four explicit modes:

1. fully explicit auth values or files supplied by the user,
2. user-directed environment lookup using explicit variable names or explicit variable-name patterns,
3. user-directed directory scan,
4. tool-specific automatic credential discovery.

The skill SHALL treat those as distinct credential-source modes unless the user explicitly asks to combine them.

If the user does not request any credential-source mode and does not already provide enough auth input, the skill SHALL only:

- confirm whether the intended credential bundle already exists for the selected tool, or
- ask the user for the missing auth input.

In that no-mode case, the skill SHALL NOT scan environment variables, directories, repo-local tool homes, redirected tool homes, or user-home tool configs.

When the user explicitly requests environment lookup, the skill SHALL limit inspection to the user-named variables or the user-specified variable-name patterns and SHALL NOT widen beyond that scope.

When the user explicitly points the agent at a directory for credential scanning, the skill SHALL limit scanning to that directory and SHALL treat that instruction as affirmative permission to scan without adding extra security warnings first.

When the user explicitly requests tool-specific automatic discovery, the skill SHALL use the selected tool’s reference page to determine the supported search order and candidate credential surfaces.

#### Scenario: Explicit auth input does not trigger discovery

- **WHEN** the user provides all required credential values or credential files explicitly
- **THEN** the skill treats that as explicit-auth mode
- **AND THEN** it does not scan env vars, directories, or tool homes unless the user explicitly asks for an additional discovery mode

#### Scenario: User-directed env lookup stays inside the requested scope

- **WHEN** the user asks the agent to look for credentials in specific environment variables or explicit variable-name patterns
- **THEN** the skill allows inspection only within that requested env scope
- **AND THEN** it does not widen the search into unrelated env vars, directories, or automatic tool-home discovery

#### Scenario: User-directed directory scan stays inside the requested directory

- **WHEN** the user points the agent to a directory and asks it to scan for likely credentials for the selected tool
- **THEN** the skill allows scanning only inside that directory using the selected tool’s lookup guidance
- **AND THEN** it does not add extra security warnings before scanning because the user already granted that scope explicitly

#### Scenario: Missing mode falls back to bundle reuse check or user question

- **WHEN** the user has not requested any credential-source mode
- **AND WHEN** enough auth input is still missing to create the selected credential bundle
- **THEN** the skill first checks whether the intended credential bundle already exists for the selected tool
- **AND THEN** it asks the user for the missing auth input instead of scanning or guessing if the bundle is not already present

### Requirement: `houmao-create-specialist` SHALL keep tool-specific lookup guidance in deployment-realistic reference pages

The packaged `houmao-create-specialist` system skill SHALL keep tool-specific credential lookup guidance outside the main `SKILL.md` in separate local reference pages for Claude, Codex, and Gemini.

The main skill SHALL load only the reference page for the currently selected tool and only when the active credential-source mode requires tool-specific lookup guidance.

Each tool-specific reference page SHALL describe deployment-realistic credential lookup surfaces for that tool, including maintained tool-home selectors, relevant stored auth files, relevant config files, and relevant environment variables.

Each tool-specific reference page SHALL be authored from:

- official tool documentation,
- checked-in upstream source under `extern/orphan/`,
- direct inspection of the installed executable.

Each tool-specific reference page SHALL NOT instruct agents to use `tests/fixtures/agents`, demo fixtures, or other repository-only paths as deployment lookup locations.

#### Scenario: Selected tool loads only its own lookup guide

- **WHEN** the user is creating a Claude specialist through a credential-discovery mode
- **THEN** the skill loads the Claude credential lookup reference page
- **AND THEN** it does not also load Codex or Gemini lookup pages for that request

#### Scenario: Reference pages use deployment-realistic lookup roots

- **WHEN** an agent reads a tool-specific credential lookup reference page
- **THEN** the page points the agent at real tool homes, redirected tool homes, maintained config files, and environment variables for that tool
- **AND THEN** it does not tell the agent to inspect Houmao test-fixture directories as if they were deployment credentials

#### Scenario: Reference pages describe maintained tool-home selectors

- **WHEN** an agent reads the selected tool’s credential lookup reference page
- **THEN** the page describes the maintained tool-home selector for that tool when one exists
- **AND THEN** it uses deployment-realistic selectors such as `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, or `GEMINI_CLI_HOME` instead of repo-only conventions

### Requirement: `houmao-create-specialist` SHALL only import discovered auth that the create command can represent

The packaged `houmao-create-specialist` system skill SHALL distinguish between:

- discovered auth that can be mapped into supported `houmao-mgr project easy specialist create` inputs for the selected tool,
- discovered auth that cannot be faithfully represented by those supported inputs.

The skill SHALL map discovered auth only into the selected tool’s supported create inputs.

If the current auth shape is discovered but cannot be faithfully represented by current create-command inputs, the skill SHALL report that limitation and ask the user for a supported explicit input instead of guessing.

This importability rule SHALL apply to both user-directed discovery and automatic discovery.

#### Scenario: Importable Codex env-only provider is accepted

- **WHEN** the selected tool is Codex
- **AND WHEN** discovery finds a config-backed provider that is env-only, has `requires_openai_auth=false`, has `wire_api=responses`, and exposes enough data to map into supported create inputs
- **THEN** the skill may use that discovered auth to populate supported Codex create flags
- **AND THEN** it does not reject the source merely because it came from config plus env rather than `auth.json`

#### Scenario: Claude apiKeyHelper-only auth is reported as unsupported

- **WHEN** the selected tool is Claude
- **AND WHEN** discovery determines that the current Claude auth depends on `apiKeyHelper` without a separately importable key or reusable state template
- **THEN** the skill reports that the currently active auth is not directly importable by the create command
- **AND THEN** it asks the user for a supported explicit input instead of guessing or trying to translate the helper configuration

#### Scenario: Gemini service-account-only auth is reported as unsupported

- **WHEN** the selected tool is Gemini
- **AND WHEN** discovery finds only a service-account or ADC-based auth setup that is not directly representable by current create-command inputs
- **THEN** the skill reports that the currently active auth shape is not directly importable for easy specialist creation
- **AND THEN** it asks the user for a supported explicit input or another importable credential source instead of inventing a bundle
