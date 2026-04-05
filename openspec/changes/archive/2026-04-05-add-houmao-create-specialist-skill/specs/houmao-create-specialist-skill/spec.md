## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-create-specialist` system skill
The system SHALL package a Houmao-owned system skill named `houmao-create-specialist` under the maintained system-skill asset root.

That skill SHALL instruct agents to create reusable specialists through `houmao-mgr project easy specialist create` rather than through deprecated or lower-level authoring surfaces.

The skill SHALL describe the documented project-easy defaults that matter for authoring behavior, including:

- `--credential` defaults to `<specialist-name>-creds`,
- `--system-prompt` and `--system-prompt-file` are optional and mutually exclusive,
- `--no-unattended` opts out of the easy unattended default.

#### Scenario: Installed skill points the agent at the project-easy create command
- **WHEN** an agent opens the installed `houmao-create-specialist` skill
- **THEN** the skill directs the agent to use `houmao-mgr project easy specialist create`
- **AND THEN** it does not redirect the agent to deprecated entrypoints or ad hoc filesystem editing

#### Scenario: Installed skill preserves the documented easy-specialist defaults
- **WHEN** an agent reads the installed `houmao-create-specialist` skill
- **THEN** the skill states that `--credential` defaults to `<specialist-name>-creds`
- **AND THEN** it states that system-prompt input is optional and that `--no-unattended` is the explicit opt-out from the easy unattended default

### Requirement: `houmao-create-specialist` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-create-specialist` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace in this order:

1. repo-local `.venv` executable,
2. Pixi-managed project invocation,
3. project-local `uv run`,
4. globally installed `houmao-mgr` from uv tools.

The skill SHALL treat global uv-tools installation as the default end-user case when no development-project hints justify a repo-local launcher.

The skill SHALL tell the agent to look for development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` before choosing a repo-local launcher.

#### Scenario: Repo-local `.venv` takes precedence over other launchers
- **WHEN** the current workspace provides `.venv/bin/houmao-mgr`
- **THEN** the skill tells the agent to use that repo-local executable first
- **AND THEN** it does not prefer Pixi, project-local `uv run`, or the global uv-tools install for that workspace

#### Scenario: Pixi-managed project takes precedence when no `.venv` launcher exists
- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** the current workspace has Pixi development-project hints
- **THEN** the skill tells the agent to use `pixi run houmao-mgr`
- **AND THEN** it does not skip directly to project-local `uv run` or the global uv-tools install

#### Scenario: Project-local uv run is used when Pixi is absent
- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** no Pixi-managed project hints are present
- **AND WHEN** the current workspace has project-local uv hints such as `uv.lock`
- **THEN** the skill tells the agent to use `uv run houmao-mgr`
- **AND THEN** it does not skip directly to the global uv-tools install

#### Scenario: Global uv-tools install remains the end-user default
- **WHEN** the current workspace does not provide repo-local `.venv`, Pixi, or project-local uv hints
- **THEN** the skill tells the agent to use the globally installed `houmao-mgr` command from uv tools
- **AND THEN** it treats that path as the ordinary end-user launcher

### Requirement: `houmao-create-specialist` recovers explicit inputs from conversation context and asks before guessing
The packaged `houmao-create-specialist` skill SHALL tell the agent to recover omitted specialist-create inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

At minimum, the skill SHALL require the agent to obtain:

- specialist name,
- tool lane,
- enough auth information to create the selected credential bundle unless an existing credential bundle for the intended credential name has already been confirmed.

When the user omits `--credential`, the skill MAY rely on the documented CLI default `<specialist-name>-creds` without treating that default as a guess.

When required inputs remain unresolved after checking prompt and recent conversation context, the skill SHALL instruct the agent to ask the user for the missing inputs before proceeding.

When the user explicitly requests `auto credentials`, the skill SHALL treat that as an opt-in auth-discovery mode rather than as a literal CLI flag or replacement credential-bundle name.

In that `auto credentials` mode, the skill SHALL instruct the agent to scan likely currently active credentials for the selected tool in this order:

1. the selected tool's repo-root tool home, including maintained tool-home env redirection when it resolves inside the current repo,
2. tool-specific home-dir configs, including maintained tool-home env redirection when it resolves under the user home,
3. current process environment variables for the selected tool.

The skill SHALL describe the maintained tool-home env selectors used for that scan:

- `CLAUDE_CONFIG_DIR` for Claude,
- `CODEX_HOME` for Codex,
- `GEMINI_CLI_HOME` for Gemini.

The skill SHALL limit the scan to supported tool-specific auth surfaces:

- Claude auth env such as `ANTHROPIC_API_KEY`, optional `ANTHROPIC_BASE_URL`, optional `ANTHROPIC_AUTH_TOKEN`, and an existing reusable `claude_state.template.json`,
- Codex `auth.json` plus OpenAI env such as `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, and optional `OPENAI_ORG_ID`,
- Gemini `oauth_creds.json` plus Gemini env such as `GEMINI_API_KEY`, optional `GOOGLE_GEMINI_BASE_URL`, optional `GOOGLE_API_KEY`, and optional `GOOGLE_GENAI_USE_VERTEXAI=true`.

If that scan does not find enough selected-tool auth to create the bundle, the skill SHALL tell the agent to report failure and ask the user for explicit auth inputs instead of guessing.

If the user did not explicitly request `auto credentials`, the skill SHALL NOT direct the agent to scan repo-local tool homes, home-dir configs, redirected homes, or environment variables for likely current credentials. In that case the skill MAY tell the agent to mention that `auto credentials` is available.

The skill SHALL NOT instruct the agent to crawl arbitrary repository subdirectories for credentials during `auto credentials`; repo-local scanning is limited to the selected tool's repo-root candidate home plus its maintained redirected home when present.

#### Scenario: Recent conversation supplies an omitted explicit tool selection
- **WHEN** the current prompt asks the agent to create a specialist without restating the tool
- **AND WHEN** the recent conversation explicitly established that tool selection
- **THEN** the skill allows the agent to reuse that explicit recent-context value
- **AND THEN** it does not ask the user to restate the same tool unnecessarily

#### Scenario: Existing credential bundle makes auth re-entry unnecessary
- **WHEN** the current prompt or recent conversation establishes the specialist name and tool
- **AND WHEN** the skill confirms that the intended credential bundle already exists for that tool
- **THEN** the skill allows the agent to proceed without asking the user to restate API-key or auth inputs
- **AND THEN** it treats the confirmed credential bundle as satisfying the auth requirement for specialist creation

#### Scenario: Missing unresolved auth requires a user question
- **WHEN** the current prompt omits auth inputs
- **AND WHEN** recent conversation context does not provide them
- **AND WHEN** the intended credential bundle has not been confirmed to exist
- **THEN** the skill tells the agent to ask the user for the missing auth inputs before proceeding
- **AND THEN** it does not guess API keys, bundle names beyond the documented default, or provider-specific auth files

#### Scenario: Explicit auto credentials request enables maintained tool scan
- **WHEN** the user explicitly asks for `auto credentials`
- **AND WHEN** the selected tool is already known
- **THEN** the skill tells the agent to scan maintained repo-local and home-dir tool credential surfaces before falling back to selected-tool environment variables
- **AND THEN** it uses the maintained tool-home env selector for that tool when one is already set

#### Scenario: Missing auto credentials result is reported as failure
- **WHEN** the user explicitly asks for `auto credentials`
- **AND WHEN** the selected tool scan does not find enough auth to create the intended bundle
- **THEN** the skill tells the agent to report that auto-discovery failed for the selected tool
- **AND THEN** it asks the user for explicit auth inputs instead of guessing

#### Scenario: Missing explicit auto credentials request prevents credential scan
- **WHEN** the user does not explicitly ask for `auto credentials`
- **AND WHEN** auth inputs are still missing and the intended credential bundle has not been confirmed to exist
- **THEN** the skill tells the agent not to scan repo-local tool homes, home-dir configs, redirected tool homes, or environment variables
- **AND THEN** it may mention that `auto credentials` is available if the user wants that behavior
