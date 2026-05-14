## Purpose
Define credential-source and auth-importability rules for the packaged specialist-management skill's create action.
## Requirements
### Requirement: `houmao-create-specialist` SHALL expose four credential-source modes

The create action within the packaged `houmao-specialist-mgr` system skill SHALL describe credential sourcing as four explicit modes:

1. fully explicit auth values or files supplied by the user,
2. user-directed environment lookup using explicit variable names or explicit variable-name patterns,
3. user-directed directory scan,
4. tool-specific automatic credential discovery.

The create action SHALL treat those as distinct credential-source modes unless the user explicitly asks to combine them.

If the selected action is not `create`, the packaged `houmao-specialist-mgr` skill SHALL NOT enter any credential-source mode.

Before any credential-source mode is selected, the create action SHALL recover the selected tool and credential from the current prompt, nearby context, or the registered Houmao credential defaulting strategy.

If the user does not request any credential-source mode and does not already provide enough auth input for `create`, the skill SHALL run the registered Houmao credential defaulting strategy before tool-specific automatic credential discovery.

When the user explicitly requests environment lookup for `create`, the skill SHALL limit inspection to the user-named variables or the user-specified variable-name patterns and SHALL NOT widen beyond that scope.

When the user explicitly points the agent at a directory for credential scanning during `create`, the skill SHALL limit scanning to that directory and SHALL treat that instruction as affirmative permission to scan without adding extra security warnings first.

When tool-specific automatic discovery is explicit or selected by default for `create`, the skill SHALL use the selected tool’s reference page to determine the supported search order and candidate credential surfaces.

#### Scenario: Explicit auth input does not trigger discovery

- **WHEN** the user provides all required credential values or credential files explicitly for the create action
- **THEN** the skill treats that as explicit-auth mode
- **AND THEN** it does not scan env vars, directories, or tool homes unless the user explicitly asks for an additional discovery mode

#### Scenario: User-directed env lookup stays inside the requested scope

- **WHEN** the user asks the agent to look for credentials in specific environment variables or explicit variable-name patterns during `create`
- **THEN** the skill allows inspection only within that requested env scope
- **AND THEN** it does not widen the search into unrelated env vars, directories, or automatic tool-home discovery

#### Scenario: User-directed directory scan stays inside the requested directory

- **WHEN** the user points the agent to a directory and asks it to scan for likely credentials for the selected tool during `create`
- **THEN** the skill allows scanning only inside that directory using the selected tool’s lookup guidance
- **AND THEN** it does not add extra security warnings before scanning because the user already granted that scope explicitly

#### Scenario: Missing tool defaults from registered credentials
- **WHEN** the user asks to create a specialist
- **AND WHEN** the selected tool is not explicit in the current prompt or nearby context
- **AND WHEN** an active Houmao project or `HOUMAO_AGENT_DEF_DIR` target has registered credentials
- **THEN** the skill picks a registered credential that matches the prompt or nearby context when possible
- **AND THEN** it otherwise picks the credential with the latest listed update time
- **AND THEN** it uses that credential's tool lane and name for `--tool` and `--credential`

#### Scenario: Missing Houmao credential target fails with suggestion
- **WHEN** the user asks to create a specialist without explicit tool or credential input
- **AND WHEN** no active Houmao project overlay or `HOUMAO_AGENT_DEF_DIR` target can be resolved
- **THEN** the skill stops before discovery
- **AND THEN** it suggests initializing or selecting a Houmao project, setting `HOUMAO_PROJECT_OVERLAY_DIR`, or setting `HOUMAO_AGENT_DEF_DIR`

#### Scenario: No registered credentials fails with suggestion
- **WHEN** the user asks to create a specialist without explicit tool or credential input
- **AND WHEN** a Houmao credential target is resolved
- **AND WHEN** no credentials are registered for that target
- **THEN** the skill stops before discovery
- **AND THEN** it suggests adding or logging in one credential through the credential manager

#### Scenario: Multiple registered tool lanes use context or recency
- **WHEN** the user asks to create a specialist without explicit tool or credential input
- **AND WHEN** registered credentials exist for multiple tool lanes
- **THEN** the skill selects a registered credential by prompt or nearby context when possible
- **AND THEN** it otherwise selects the credential with the latest listed update time across those tools

#### Scenario: Non-create action does not enter credential-source handling

- **WHEN** the user asks for `list`, `get`, or `remove`
- **THEN** the packaged `houmao-specialist-mgr` skill does not invoke credential-source mode handling
- **AND THEN** it keeps auth discovery scoped to specialist creation only

### Requirement: `houmao-create-specialist` SHALL keep tool-specific lookup guidance in deployment-realistic reference pages

The packaged `houmao-specialist-mgr` system skill SHALL keep create-action tool-specific credential lookup guidance outside the top-level `SKILL.md` in separate local reference pages for Claude, Codex, and Gemini.

The top-level skill SHALL route into the create action first, and the create action SHALL load only the reference page for the currently selected tool and only when the active credential-source mode requires tool-specific lookup guidance.

Each tool-specific reference page SHALL describe deployment-realistic credential lookup surfaces for that tool, including maintained tool-home selectors, relevant stored auth files, relevant config files, and relevant environment variables.

Each tool-specific reference page SHALL be authored from:

- official tool documentation,
- checked-in upstream source under `extern/orphan/`,
- direct inspection of the installed executable.

Each tool-specific reference page SHALL NOT instruct agents to use historical shared test-fixture roots, demo fixtures, or other repository-only paths as deployment lookup locations.

#### Scenario: Selected tool loads only its own lookup guide

- **WHEN** the user is creating a Claude specialist through a credential-discovery mode
- **THEN** the create action loads the Claude credential lookup reference page
- **AND THEN** it does not also load Codex or Gemini lookup pages for that request

#### Scenario: Reference pages use deployment-realistic lookup roots

- **WHEN** an agent reads a tool-specific credential lookup reference page from the create action
- **THEN** the page points the agent at real tool homes, redirected tool homes, maintained config files, and environment variables for that tool
- **AND THEN** it does not tell the agent to inspect Houmao test-fixture directories as if they were deployment credentials

#### Scenario: Reference pages describe maintained tool-home selectors

- **WHEN** an agent reads the selected tool’s credential lookup reference page from the create action
- **THEN** the page describes the maintained tool-home selector for that tool when one exists
- **AND THEN** it uses deployment-realistic selectors such as `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, or `GEMINI_CLI_HOME` instead of repo-only conventions

### Requirement: `houmao-create-specialist` SHALL only import discovered auth that the create command can represent

The create action within the packaged `houmao-specialist-mgr` system skill SHALL distinguish between:

- discovered auth that can be mapped into supported `houmao-mgr project easy specialist create` inputs for the selected tool,
- discovered auth that cannot be faithfully represented by those supported inputs.

The create action SHALL map discovered auth only into the selected tool’s supported create inputs.

If the current auth shape is discovered but cannot be faithfully represented by current create-command inputs, the skill SHALL report that limitation and ask the user for a supported explicit input instead of guessing.

This importability rule SHALL apply to both user-directed discovery and automatic discovery for the create action.

#### Scenario: Importable Codex env-only provider is accepted

- **WHEN** the selected tool is Codex
- **AND WHEN** create-action discovery finds a config-backed provider that is env-only, has `requires_openai_auth=false`, has `wire_api=responses`, and exposes enough data to map into supported create inputs
- **THEN** the skill may use that discovered auth to populate supported Codex create flags
- **AND THEN** it does not reject the source merely because it came from config plus env rather than `auth.json`

#### Scenario: Claude apiKeyHelper-only auth is reported as unsupported

- **WHEN** the selected tool is Claude
- **AND WHEN** create-action discovery determines that the current Claude auth depends on `apiKeyHelper` without a separately importable key or reusable state template
- **THEN** the skill reports that the currently active auth is not directly importable by the create command
- **AND THEN** it asks the user for a supported explicit input instead of guessing or trying to translate the helper configuration

#### Scenario: Gemini service-account-only auth is reported as unsupported

- **WHEN** the selected tool is Gemini
- **AND WHEN** create-action discovery finds only a service-account or ADC-based auth setup that is not directly representable by current create-command inputs
- **THEN** the skill reports that the currently active auth shape is not directly importable for easy specialist creation
- **AND THEN** it asks the user for a supported explicit input or another importable credential source instead of inventing a bundle

### Requirement: `houmao-create-specialist` treats vendor-supported Claude login state and OAuth tokens as importable
When the selected tool is Claude and the create action’s active credential-source mode permits discovery, the packaged `houmao-specialist-mgr` skill SHALL treat these discovered Claude auth shapes as importable:

- `CLAUDE_CODE_OAUTH_TOKEN`
- Claude login state rooted at `CLAUDE_CONFIG_DIR` or the maintained default Claude config root when that root contains the vendor files needed for the Claude login-state lane

The create action SHALL map those discovered Claude auth shapes only into supported create-command inputs for the Claude lane, including the Claude OAuth-token input and the Claude config-dir import input.

The skill SHALL continue to report non-importable Claude auth shapes, such as `apiKeyHelper`-only setups without separately reusable credential material, as unsupported instead of guessing.

An explicit or discovered `claude_state.template.json` MAY still be used as optional Claude runtime-state template input, but the create action SHALL classify that file separately from credential-providing Claude auth methods.

#### Scenario: Auto discovery imports Claude OAuth token from environment
- **WHEN** automatic credential discovery is active for `--tool claude` on the create action
- **AND WHEN** discovery finds `CLAUDE_CODE_OAUTH_TOKEN` in the supported Claude env lookup surfaces
- **THEN** the skill treats that token as importable Claude auth
- **AND THEN** it maps that result into the supported Claude OAuth-token create input rather than rejecting it as unsupported

#### Scenario: Auto discovery imports Claude login state from the maintained config root
- **WHEN** automatic credential discovery is active for `--tool claude` on the create action
- **AND WHEN** discovery finds a maintained Claude config root containing the vendor login-state files required by the Claude login-state lane
- **THEN** the skill treats that Claude login state as importable for specialist creation
- **AND THEN** it maps that result into the supported Claude config-dir create input rather than reporting "logged in but unsupported"

#### Scenario: Claude apiKeyHelper-only auth remains unsupported
- **WHEN** automatic credential discovery is active for `--tool claude` on the create action
- **AND WHEN** discovery determines that the current Claude auth depends only on `apiKeyHelper` without separately reusable import material
- **THEN** the skill reports that the current Claude auth is not directly importable for specialist creation
- **AND THEN** it asks the user for another supported Claude auth input instead of guessing

#### Scenario: State template alone does not count as discovered Claude credentials
- **WHEN** automatic credential discovery is active for `--tool claude` on the create action
- **AND WHEN** discovery finds only a reusable `claude_state.template.json` and no supported Claude credential or login-state material
- **THEN** the skill reports that usable Claude credentials were not discovered for specialist creation
- **AND THEN** it may mention the reusable state template only as optional bootstrap input rather than as a credential method

### Requirement: Specialist credential-source guidance moves under unified agent definition
The unified `houmao-agent-definition` skill SHALL own the credential-source guidance used when creating easy specialists or when `create-agent-fast-forward` creates a specialist.

The existing credential-source modes SHALL remain available under the unified `specialists` and `create-agent-fast-forward` paths:

1. explicit auth values or files;
2. user-directed environment lookup;
3. user-directed directory scan;
4. tool-specific automatic credential discovery.

Credential-source handling SHALL remain scoped to specialist creation or fast-forward flows that create a specialist. Non-create actions SHALL NOT enter credential discovery.

The unified skill SHALL recover the specialist-create tool and credential from the current prompt, nearby explicit context, or registered Houmao credentials.

When the user omits tool or credential input and a Houmao credential target contains registered credentials, the unified skill SHALL choose a registered credential by prompt or nearby explicit context when possible. The unified skill SHALL obtain listed update times through the supported `houmao-mgr ... credentials <tool> list` payloads. If context does not select one, the unified skill SHALL choose the credential with the latest listed update time across all registered tool lanes.

When the user omits tool or credential input, the unified skill SHALL stop with a suggested fix only if no Houmao credential target exists or if no credentials are registered.

#### Scenario: Fast-forward specialist creation uses registered credential defaulting
- **WHEN** a user asks the `create-agent-fast-forward` workflow to create a specialist without explicit tool or credential input
- **AND WHEN** registered Houmao credentials are available
- **THEN** the unified skill chooses a registered credential by context or recency
- **AND THEN** it keeps that choice scoped to the specialist creation portion of the fast-forward workflow

### Requirement: Tool-specific credential references are relocated or re-exported
The unified `houmao-agent-definition` skill SHALL provide or reference the Claude, Codex, and Gemini credential kinds and lookup pages needed by specialist creation and `create-agent-fast-forward`.

If `houmao-specialist-mgr` remains as a compatibility wrapper, the wrapper SHALL route to the unified references instead of maintaining a divergent copy.

#### Scenario: Only selected tool reference is loaded
- **WHEN** a user creates a Claude specialist through the unified skill and the active credential-source mode requires lookup guidance
- **THEN** the skill loads only the Claude credential reference
- **AND THEN** it does not also load Codex or Gemini credential references for that request
