## MODIFIED Requirements

### Requirement: `houmao-credential-mgr` routes credential login helper workflows
The packaged `houmao-credential-mgr` skill SHALL route requests to obtain fresh provider auth files through the supported credential `login` helper when the user asks to log in with a new Codex, Claude, or Gemini account and import the resulting credential into Houmao storage.

The top-level `SKILL.md` for that packaged skill SHALL include `login` in its action router alongside `list`, `get`, `add`, `set`, `rename`, and `remove`.

The skill SHALL instruct agents to use:

- `houmao-mgr project [--project-dir <dir>] credentials <tool> login --name <name>` when the selected project overlay is the intended target,
- `houmao-mgr internals native-agent credentials <tool> login --native-agent-root <path> --name <name>` when the user explicitly targets a direct native-agent credential root,
- the explicit update option only when the user intends to replace an existing credential.

The skill SHALL instruct agents to run provider credential login helper commands in a dedicated tmux session by default so the agent or operator can attach to, inspect, and interact with provider browser, device-code, console, or paste-back authentication steps.

The skill SHALL instruct agents to propagate the invoking shell's ambient proxy environment into the tmux login session by default. At minimum, when set in the current environment, the guidance SHALL carry these variables into the tmux session with explicit tmux environment arguments or an equivalent current-env-preserving tmux setup:

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `ALL_PROXY`
- `NO_PROXY`
- `http_proxy`
- `https_proxy`
- `all_proxy`
- `no_proxy`

The skill SHALL explain that `--inherit-auth-env` preserves provider auth-related variables for the maintained login command and SHALL NOT present that flag as the mechanism for ordinary proxy inheritance.

The skill SHALL explain that the command creates an isolated temporary provider home, invokes the installed provider CLI with inherited stdio, imports the expected auth artifact into Houmao storage, and deletes the temporary provider home after a successful import by default.

The skill SHALL tell agents not to hand-roll this workflow by manually creating provider home directories, running provider login commands, copying auth files into credential storage, or deleting temp directories outside the supported project or internal native-agent credential login surfaces unless the user explicitly asks for a lower-level recovery workflow after a failed login attempt.

#### Scenario: Login request routes to the project credential helper
- **WHEN** the current prompt asks the agent to log in to Codex with another account and import it into the current project as `work`
- **AND WHEN** no explicit plain agent-definition directory target is provided
- **THEN** the skill routes the work through `houmao-mgr project credentials codex login --name work`
- **AND THEN** it does not tell the agent to manually copy `auth.json` into Houmao storage

#### Scenario: Explicit native-agent login request includes the target root
- **WHEN** the current prompt asks the agent to obtain a new Gemini OAuth credential under native-agent root `tests/fixtures/plain-agent-def` as `personal`
- **THEN** the skill routes the work through `houmao-mgr internals native-agent credentials gemini login --native-agent-root tests/fixtures/plain-agent-def --name personal`
- **AND THEN** it does not reinterpret that request as project-local credential management

#### Scenario: Existing credential replacement requires user intent
- **WHEN** the current prompt asks the agent to log in and import a credential name that may already exist
- **AND WHEN** the user has not explicitly said to replace or update the existing credential
- **THEN** the skill tells the agent to use the default create-only login behavior
- **AND THEN** it does not add the explicit update option on the user's behalf

#### Scenario: Skill explains temp cleanup ownership
- **WHEN** an agent reads the login workflow guidance
- **THEN** the skill states that the supported credential login command owns the temporary provider home lifecycle
- **AND THEN** it states that successful imports delete the temp home by default while failed attempts preserve and report it for recovery

#### Scenario: Login helper runs in tmux with proxy variables
- **WHEN** an agent follows the login workflow guidance for Claude, Codex, or Gemini
- **AND WHEN** tmux is available
- **THEN** the skill directs the agent to start the maintained Houmao credential login command in a dedicated tmux session
- **AND THEN** the tmux session inherits any set uppercase and lowercase proxy variables from the invoking shell

#### Scenario: Proxy preservation does not require auth-env inheritance
- **WHEN** an agent follows the login workflow guidance with proxy variables set
- **THEN** the skill preserves proxy variables through the tmux session setup
- **AND THEN** it does not tell the agent to add `--inherit-auth-env` unless the user explicitly wants ambient provider auth variables preserved for the login command

### Requirement: `houmao-credential-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs

The packaged `houmao-credential-mgr` skill SHALL ship a `references/` directory under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` and four per-tool credential kinds reference pages inside that directory:

- `claude-credential-kinds.md`
- `codex-credential-kinds.md`
- `gemini-credential-kinds.md`
- `kimi-credential-kinds.md`

Each kinds reference page SHALL enumerate the user-facing credential kinds the selected tool accepts through `houmao-mgr project credentials <tool> add` and `houmao-mgr internals native-agent credentials <tool> add --native-agent-root <path>`, including at minimum the following kinds per tool:

- Claude: a long-lived Claude Code OAuth token generated by `claude setup-token` and stored as `CLAUDE_CODE_OAUTH_TOKEN`, API key, auth token, OAuth token, and a vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present.
- Codex: API key, and a cached login state kind that carries an `auth.json` file.
- Gemini: API key, a Vertex AI kind that pairs a Google API key with the Vertex AI selector, and an OAuth creds kind that carries an `.gemini/oauth_creds.json` file.
- Kimi: API key or provider-routing material that may include model name, base URL, provider type, Kimi Code base URL, Kimi Code OAuth host, OAuth host, telemetry disablement, `config.toml`, or credential JSON inputs according to the maintained Kimi credential CLI.

The Claude kinds reference SHALL identify the long-lived Claude Code token generated by `claude setup-token` as the preferred default when the user wants to create a new Claude credential but has not specified a credential kind.

The Claude kinds reference SHALL map the `claude setup-token` output to the existing credential-manager `--oauth-token` flag and `CLAUDE_CODE_OAUTH_TOKEN` environment value.

The Claude kinds reference SHALL describe `ANTHROPIC_AUTH_TOKEN` / `--auth-token` as a distinct bearer-token lane for explicit Anthropic auth-token or gateway/proxy-token use, not as the preferred unspecified Claude Code subscription credential lane.

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

#### Scenario: Unspecified Claude creation prefers setup-token
- **WHEN** a user asks the installed skill to create a new Claude credential
- **AND WHEN** the user has not specified API key, bearer auth token, existing vendor config directory, or another credential kind
- **THEN** the Claude kinds guidance presents `claude setup-token` and `--oauth-token` / `CLAUDE_CODE_OAUTH_TOKEN` as the preferred default path
- **AND THEN** it does not prefer `ANTHROPIC_AUTH_TOKEN` or vendor-login import ahead of the long-lived Claude Code token lane

#### Scenario: Claude bearer-token lane remains explicit
- **WHEN** a user provides or asks for `ANTHROPIC_AUTH_TOKEN`
- **THEN** the Claude kinds guidance maps that material to `--auth-token`
- **AND THEN** it distinguishes that bearer-token lane from the `CLAUDE_CODE_OAUTH_TOKEN` lane generated by `claude setup-token`
