## ADDED Requirements

### Requirement: Claude config profile disables dangerous-mode prompt
The system SHALL provide tool configuration for Claude Code such that an orchestrated launch using `--dangerously-skip-permissions` does not block on a confirmation prompt.

#### Scenario: Dangerous-mode prompt is disabled via settings.json
- **WHEN** a Claude brain is constructed and `CLAUDE_CONFIG_DIR` is set to the constructed runtime home
- **THEN** the runtime home SHALL contain a `settings.json` file
- **AND THEN** `settings.json` SHALL set `skipDangerousModePermissionPrompt` to `true`

### Requirement: Claude credential profile provides `claude_state.template.json`
The Claude credential profile SHALL provide a Claude state template JSON file that acts as the base for runtime Claude global state in isolated brain homes.

#### Scenario: Template is available from selected credential profile
- **WHEN** a Claude brain is constructed with credential profile `<cred-profile>`
- **THEN** template material from `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` SHALL be available to launch-time preparation
- **AND THEN** the template input file MUST NOT be named `.claude.json` (it is an input, not the runtime state file)

#### Scenario: Missing template is surfaced as configuration error
- **WHEN** a Claude brain is launched and the selected credential profile does not provide `claude_state.template.json` template material
- **THEN** launch SHALL fail with a clear configuration error that identifies the missing template source

### Requirement: Launcher materializes runtime `.claude.json` from template (create-only)
The system SHALL support launching Claude Code with `CLAUDE_CONFIG_DIR` set to a fresh empty directory without requiring interactive onboarding or API-key approval by materializing a runtime `$CLAUDE_CONFIG_DIR/.claude.json` from the credential-profile template plus launcher-enforced overrides.

This contract is verified against Claude Code v2.1.62 (2026-02-27) and may need updates if upstream state schema changes.

#### Scenario: Materialized runtime config enforces onboarding/API-key invariants
- **WHEN** an orchestrated Claude session is started with a fresh `CLAUDE_CONFIG_DIR` and `ANTHROPIC_API_KEY` is set
- **THEN** the system SHALL create `$CLAUDE_CONFIG_DIR/.claude.json` from the credential-profile template before launching Claude Code (only when `.claude.json` is missing)
- **AND THEN** the final JSON payload SHALL include `"hasCompletedOnboarding": true`
- **AND THEN** the final JSON payload SHALL include `"numStartups": 1`
- **AND THEN** the final JSON payload SHALL include `"customApiKeyResponses": {"approved": ["<api_key_suffix>"], "rejected": []}`
- **AND THEN** `<api_key_suffix>` SHALL be the last 20 characters of `ANTHROPIC_API_KEY` (or the full key if shorter than 20 characters)
- **AND THEN** when `ANTHROPIC_API_KEY` is longer than 20 characters, the final JSON payload SHALL NOT contain the full `ANTHROPIC_API_KEY` value

#### Scenario: Materialized runtime config preserves template MCP settings
- **WHEN** the credential-profile template contains `mcpServers`
- **THEN** launch-time materialization SHALL preserve template `mcpServers` entries unless explicitly overwritten by launcher-enforced keys

#### Scenario: Materialized runtime config works without API key
- **WHEN** an orchestrated Claude session is started with a fresh `CLAUDE_CONFIG_DIR` and `ANTHROPIC_API_KEY` is not set
- **THEN** the system SHALL create `$CLAUDE_CONFIG_DIR/.claude.json` from the credential-profile template before launching Claude Code (only when `.claude.json` is missing)
- **AND THEN** the final JSON payload SHALL include `"hasCompletedOnboarding": true`
- **AND THEN** the final JSON payload SHALL include `"numStartups": 1`

#### Scenario: Existing `.claude.json` is not rewritten
- **WHEN** an orchestrated Claude session is started and `$CLAUDE_CONFIG_DIR/.claude.json` already exists
- **THEN** the system SHALL NOT overwrite or modify the existing `.claude.json` file as part of bootstrap

### Requirement: Orchestrated Claude launch is non-interactive
The system SHALL launch Claude Code in orchestrated sessions using non-interactive settings so startup does not block on trust dialogs or permission prompts.

#### Scenario: Launch includes non-interactive bypass flag
- **WHEN** the system launches Claude Code as part of an orchestrated session
- **THEN** it SHALL include a non-interactive bypass flag (for example `--dangerously-skip-permissions`) or an equivalent mechanism that prevents permission prompts from blocking startup

### Requirement: Claude headless launch args are tool-adapter-configurable
The system SHALL allow the Claude tool adapter to declare the base argument list for headless launches (for example `-p` and/or `--dangerously-skip-permissions`), and backend code SHALL inject only backend-reserved args tied to the headless protocol.

Backend-reserved args are: `--resume`, `--output-format`, and `--append-system-prompt`.

#### Scenario: Reserved-arg conflicts fail fast
- **WHEN** the Claude tool adapter declares `launch.args`
- **AND WHEN** the declared arg list contains a backend-reserved arg
- **THEN** launch plan construction SHALL fail with a clear configuration error naming the conflicting arg

### Requirement: Tmux environment policy is specified canonically at the platform layer
For tmux-isolated launches (for example CAO-backed sessions), the system SHALL follow the canonical environment inheritance policy defined by the `component-agent-construction` capability (inherit caller env, overlay credential-profile env, and avoid allowlist-gated injection).

### Requirement: Orchestrated Claude Code launches support env-based model selection
The system SHALL support selecting the Claude Code model for orchestrated
launches by supplying Claude Code model-selection environment variables.

At minimum, the system SHALL support:

- `ANTHROPIC_MODEL` (select effective model via alias or fully qualified name)

The system SHALL additionally support alias pinning variables so teams can
stabilize what an alias (for example `opus`) resolves to:

- `ANTHROPIC_DEFAULT_OPUS_MODEL`
- `ANTHROPIC_DEFAULT_SONNET_MODEL`
- `ANTHROPIC_DEFAULT_HAIKU_MODEL`

The system SHALL additionally support:

- `CLAUDE_CODE_SUBAGENT_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL` (when unset, the system SHALL NOT synthesize it and Claude Code defaults apply)

#### Scenario: Model env vars from credential profile are available to headless Claude
- **WHEN** a Claude brain is constructed and the credential profile env file defines `ANTHROPIC_MODEL` and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL`
- **THEN** the constructed launch plan SHALL include the corresponding model env var(s) in the selected env var set for headless launches

#### Scenario: Model env vars are preserved for tmux-isolated launches
- **WHEN** a Claude CAO-backed session is started and the caller environment defines `ANTHROPIC_MODEL` and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL`
- **THEN** the tmux session environment SHALL include the corresponding model env var(s) for the Claude Code process to consume
