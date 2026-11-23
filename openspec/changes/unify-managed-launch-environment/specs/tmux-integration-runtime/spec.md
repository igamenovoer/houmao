# Spec Delta

## ADDED Requirements

### Requirement: Owned tmux session launch values exclude credentials

The runtime SHALL write only publishable launch values to the owned tmux session. It SHALL prevent credential values from entering the session through Houmao-controlled tmux server startup or session inheritance.

#### Scenario: A credential is present in the launching environment

- **WHEN** a managed launch uses a provider credential that is also present in the owner environment
- **THEN** the credential value is absent from the owned tmux session environment and its pane command
- **AND THEN** a session launched on a fresh tmux server does not seed the server environment with that credential

#### Scenario: An existing server carries a credential name

- **WHEN** an existing tmux server has a selected credential name in its global environment
- **THEN** the owned session masks the inherited credential for its panes
- **AND THEN** the selected provider receives the value through its private launch input

### Requirement: Relaunch reconciles the owned tmux launch environment

Before a new managed generation starts, the runtime SHALL replace its published session values with the new effective values and mask expired managed keys from tmux inheritance. Writes SHALL target the owned session and preserve unrelated user-managed tmux values.

#### Scenario: A one-off setting expires while the server defines the same name

- **WHEN** the old generation published a one-off setting and the next generation does not use that key
- **AND WHEN** the tmux server has a global value for the same key
- **THEN** the relaunched session omits the old setting and panes started in that session do not inherit the global value
- **AND THEN** unrelated session settings are preserved

## MODIFIED Requirements

### Requirement: Houmao launch environment removes inherited color suppression when injection is enabled

When tmux configuration injection is enabled, Houmao SHALL publish terminal color environment values into launched tmux sessions that support rich color output.

The published environment SHALL set `TERM=tmux-256color`, set `COLORTERM=truecolor`, and prevent inherited `NO_COLOR` from suppressing color in managed provider processes.

The color overlay SHALL preserve unrelated environment values admitted by the launch environment contract.

#### Scenario: Inherited NO_COLOR does not suppress managed session color
- **WHEN** the launching process has `NO_COLOR=1`
- **AND WHEN** `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION` is unset
- **AND WHEN** Houmao launches a tmux-backed managed-agent session
- **THEN** the launched provider environment does not contain `NO_COLOR`
- **AND THEN** the launched provider environment contains `TERM=tmux-256color`
- **AND THEN** the launched provider environment contains `COLORTERM=truecolor`

#### Scenario: Unrelated environment values are preserved
- **WHEN** the resolved launch environment contains a declared `FEATURE_FLAG_X=enabled`
- **AND WHEN** Houmao launches a tmux-backed managed-agent session with tmux configuration injection enabled
- **THEN** the launched provider environment still contains `FEATURE_FLAG_X=enabled`
- **AND THEN** Houmao only changes the color-related environment variables it owns for the injection behavior

### Requirement: Tmux-backed provider processes inherit launch-profile env records

For Houmao-started tmux-backed agents, the owning session SHALL contain the resolved publishable launch values before the provider starts. Headless, Service, TUI, and Web SHALL receive those same values in the provider environment. Failure to publish a required value SHALL prevent that provider start.

#### Scenario: Profile proxy env is visible to provider process
- **WHEN** a launch plan for a local interactive Codex session contains launch-profile-derived env records `http_proxy=http://127.0.0.1:7990`, `https_proxy=http://127.0.0.1:7990`, and `FEATURE_FLAG_X=profile-env`
- **AND WHEN** Houmao creates the tmux-backed managed-agent session and starts the Codex TUI process in the primary pane
- **THEN** the provider process inherits `http_proxy=http://127.0.0.1:7990`
- **AND THEN** the provider process inherits `https_proxy=http://127.0.0.1:7990`
- **AND THEN** the provider process inherits `FEATURE_FLAG_X=profile-env`

#### Scenario: Tmux session environment contains profile env before provider startup
- **WHEN** Houmao prepares a tmux-backed managed-agent session for a launch plan containing launch-profile env records
- **THEN** the tmux session environment contains those launch-profile env records before the local interactive provider command is started
- **AND THEN** unrelated Houmao-owned tmux configuration injection does not remove those launch-profile env records

#### Scenario: A Web host or service supervisor starts after environment publication
- **WHEN** Houmao starts a Web or Service agent with non-secret root selectors, persistent settings, and one-off settings
- **THEN** the owning tmux session contains those values before the supervisor starts the native provider
- **AND THEN** the provider environment contains the same values

#### Scenario: A required session environment value cannot be set
- **WHEN** publication of a required launch value in the owning tmux session fails
- **THEN** the provider does not start for that generation
- **AND THEN** the error identifies the publication step and the affected name without printing the value
