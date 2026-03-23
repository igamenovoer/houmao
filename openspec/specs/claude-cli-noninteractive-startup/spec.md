## ADDED Requirements

### Requirement: Claude config profile disables dangerous-mode prompt
The system SHALL provide tool configuration for Claude Code such that an orchestrated launch using `--dangerously-skip-permissions` does not block on a confirmation prompt.

#### Scenario: Dangerous-mode prompt is disabled via settings.json
- **WHEN** a Claude brain is constructed and `CLAUDE_CONFIG_DIR` is set to the constructed runtime home
- **THEN** the runtime home SHALL contain a `settings.json` file
- **AND THEN** `settings.json` SHALL set `skipDangerousModePermissionPrompt` to `true`

### Requirement: Claude credential profile MAY provide `claude_state.template.json`
The Claude credential profile SHALL support an optional Claude state template JSON file that can act as seed state for runtime Claude global state in isolated brain homes.

#### Scenario: Template is available from selected credential profile
- **WHEN** a Claude brain is constructed with credential profile `<cred-profile>`
- **THEN** template material from `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` SHALL be available to launch-time preparation
- **AND THEN** the template input file MUST NOT be named `.claude.json` (it is an input, not the runtime state file)

#### Scenario: Missing template does not block unattended startup
- **WHEN** a Claude brain is launched and the selected credential profile does not provide `claude_state.template.json` template material
- **AND WHEN** the selected unattended strategy can synthesize required runtime state from minimal credentials
- **THEN** launch preparation SHALL continue without treating the missing template as a configuration error

### Requirement: Orchestrated Claude launch is non-interactive
The system SHALL support an unattended startup path for orchestrated Claude Code launches that prevents startup from blocking on dangerous-mode prompts, API-key approval prompts, workspace trust dialogs, onboarding, or equivalent operator confirmation surfaces.

When that unattended path is requested, the system SHALL detect the actual Claude Code version, resolve a compatible Claude launch policy strategy, and apply that strategy before starting Claude Code.

#### Scenario: Compatible Claude strategy prevents up-front operator prompts
- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** the detected Claude Code version matches a compatible strategy
- **THEN** the system applies the selected Claude launch strategy before starting Claude Code
- **AND THEN** Claude Code startup does not block on up-front API-key approval, trust, dangerous-mode, or onboarding prompts

#### Scenario: Unsupported Claude version fails unattended launch before process start
- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version
- **THEN** the system fails the launch before starting Claude Code
- **AND THEN** the error identifies the detected Claude Code version and unattended policy request

### Requirement: Claude unattended startup works from fresh isolated homes with minimal credentials
The system SHALL support unattended interactive Claude launches starting from a fresh isolated `CLAUDE_CONFIG_DIR` using only minimal credential inputs and minimal caller launch args.

The system SHALL NOT require the caller to pre-create Claude no-prompt config files such as `settings.json` or `.claude.json`.

#### Scenario: Fresh isolated Claude home launches unattended from API-key-only credentials
- **WHEN** an orchestrated Claude launch uses a fresh isolated `CLAUDE_CONFIG_DIR`
- **AND WHEN** `operator_prompt_mode = unattended`
- **AND WHEN** the available credentials are limited to normal Claude inputs such as `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or equivalent endpoint/auth env vars
- **THEN** the selected Claude strategy synthesizes or patches the runtime-owned settings/state it requires before process start
- **AND THEN** Claude startup does not depend on user-prepared no-prompt config files

### Requirement: Claude unattended strategy manages workspace trust in isolated homes
The system SHALL let the selected Claude unattended strategy seed or update the version-appropriate workspace trust state for the resolved launch workdir inside an isolated `CLAUDE_CONFIG_DIR`.

Each Claude unattended strategy SHALL declare the exact runtime-owned JSON/settings paths it treats as mutable trust-related surface for that version.

#### Scenario: Fresh isolated Claude home trusts the resolved workdir for unattended launch
- **WHEN** an orchestrated Claude launch uses a fresh isolated `CLAUDE_CONFIG_DIR`
- **AND WHEN** `operator_prompt_mode = unattended`
- **THEN** the selected Claude strategy seeds or updates the version-appropriate trust state for the resolved launch workdir before process start
- **AND THEN** Claude Code does not stop at the initial workspace trust confirmation surface

### Requirement: Claude unattended strategy manages custom API-key approval state
When unattended Claude startup uses API-key-based authentication in interactive mode, the selected strategy SHALL seed or update the version-appropriate approval memory needed to prevent Claude from stopping at the custom API-key confirmation prompt.

The strategy SHALL avoid persisting the full API key value in runtime state.

#### Scenario: Fresh isolated Claude home does not stop at API-key confirmation
- **WHEN** an orchestrated Claude launch uses a fresh isolated `CLAUDE_CONFIG_DIR`
- **AND WHEN** `operator_prompt_mode = unattended`
- **AND WHEN** `ANTHROPIC_API_KEY` is present for an interactive Claude launch
- **THEN** the selected Claude strategy seeds or updates the version-compatible API-key approval state before process start
- **AND THEN** Claude Code does not stop at the “Detected a custom API key in your environment” confirmation surface
- **AND THEN** the resulting runtime state does not store the full API key value

### Requirement: Claude unattended strategy manages dangerous-mode warning suppression
When unattended Claude startup requires bypass-permissions mode, the selected strategy SHALL ensure the version-appropriate dangerous-mode confirmation suppression state exists in the isolated runtime home.

#### Scenario: Fresh isolated Claude home does not stop at bypass-permissions confirmation
- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected Claude strategy launches interactive Claude in bypass-permissions mode
- **AND WHEN** the runtime home does not already contain the needed suppression state
- **THEN** the strategy creates or patches the version-compatible settings needed to suppress that confirmation surface before process start
- **AND THEN** Claude Code does not stop at the “running in Bypass Permissions mode” warning

### Requirement: Claude unattended strategy manages runtime state idempotently
The system SHALL let the selected Claude unattended strategy create or update strategy-owned runtime Claude state in `CLAUDE_CONFIG_DIR` idempotently while preserving unrelated existing or template-derived state.

Strategy-owned runtime state SHALL continue to enforce onboarding and API-key approval invariants required for unattended startup without leaking full secret values into persisted runtime state.

The set of strategy-owned paths SHALL come from the selected strategy entry rather than from one global Claude-owned field list.

#### Scenario: Strategy creates Claude runtime state from template when missing
- **WHEN** an orchestrated Claude launch uses a fresh `CLAUDE_CONFIG_DIR`
- **AND WHEN** the selected strategy requires runtime Claude state
- **THEN** the system creates version-compatible runtime state from template and strategy-owned overrides before launch
- **AND THEN** the resulting state includes required unattended startup invariants without storing the full API key value

#### Scenario: Strategy suppresses onboarding on a fresh isolated Claude home
- **WHEN** an orchestrated Claude launch uses a fresh `CLAUDE_CONFIG_DIR`
- **AND WHEN** the selected Claude strategy requires startup state to bypass first-run onboarding
- **THEN** the system creates or patches the version-compatible onboarding state before launch
- **AND THEN** Claude Code does not stop at first-run theme or onboarding selection

#### Scenario: Strategy preserves unrelated template-derived state
- **WHEN** the Claude template or existing runtime state contains unrelated fields such as `mcpServers`
- **AND WHEN** the selected unattended strategy does not explicitly own those fields
- **THEN** the system preserves those unrelated fields while applying strategy-owned updates

#### Scenario: Strategy updates only strategy-owned state when runtime state already exists
- **WHEN** an orchestrated Claude launch reuses a `CLAUDE_CONFIG_DIR` that already contains runtime Claude state
- **AND WHEN** the selected unattended strategy requires additional trust or startup invariants for the resolved workdir
- **THEN** the system updates only the strategy-owned portions of that runtime state
- **AND THEN** unrelated existing Claude state remains preserved

#### Scenario: Claude strategy declares owned JSON and settings paths explicitly
- **WHEN** a developer inspects a Claude unattended strategy for a supported version
- **THEN** the strategy entry declares which paths in `.claude.json` and `settings.json` it may mutate for onboarding, API-key approval, dangerous-mode suppression, and trust
- **AND THEN** Claude runtime fields outside those declared paths remain outside the strategy-owned merge surface

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
