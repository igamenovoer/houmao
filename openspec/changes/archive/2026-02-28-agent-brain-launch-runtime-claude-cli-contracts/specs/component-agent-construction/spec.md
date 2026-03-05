## ADDED Requirements

### Requirement: Credential profiles can include runtime-state templates
The system SHALL allow tool-specific credential profiles to include local-only runtime-state templates required for launch preparation (for example a Claude state template under `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json`).

#### Scenario: Claude credential profile carries `claude_state.template.json` template
- **WHEN** a developer prepares a Claude credential profile
- **THEN** the profile SHALL support including a local-only `claude_state.template.json` template for launch-time materialization in runtime homes
- **AND THEN** the template SHALL be treated as credential-profile input, not as a committed runtime artifact

### Requirement: Tmux-based launches inherit the calling process environment
The system SHALL propagate the full calling process environment into tmux-based launches (for example CAO-backed sessions), and then apply brain-owned overlays.

Environment precedence is:
1) calling process environment (base),
2) credential-profile env file values (overlay), and
3) launch-specific env vars (overlay; for example tool home selector env vars).

Credential-profile env injection MUST NOT be gated by a tool-adapter allowlist; all entries declared in the env file MUST be injected.

#### Scenario: Tmux launch inherits caller env and overlays credential env
- **WHEN** the system starts a tool session in tmux
- **THEN** the tmux session environment SHALL inherit environment variables from the calling process
- **AND THEN** the tmux session environment SHALL include all variables declared in the selected credential profile env file (overriding inherited values when names collide)

## MODIFIED Requirements

### Requirement: Fresh-by-default runtime home creation
Brain construction SHALL create a fresh runtime CLI home directory with no pre-existing tool history, logs, or sessions at creation time. The system SHALL support pre-seeding minimal tool bootstrap configuration/state required for unattended startup, provided it is not copied from prior-run history/log/session artifacts.

#### Scenario: Fresh home has no pre-existing history
- **WHEN** a new runtime home is constructed
- **THEN** the constructed home SHALL NOT contain copied-in prior-run history/log/session artifacts
- **AND THEN** any history/log/session artifacts SHALL only appear after the CLI tool is started and begins writing state
- **AND THEN** any pre-seeded tool bootstrap configuration/state files present at creation time MUST NOT be copied from prior-run history/log/session artifacts
