## ADDED Requirements

### Requirement: Tmux-backed provider processes inherit launch-profile env records
For Houmao-created tmux-backed managed-agent sessions, launch-profile-derived env records SHALL be present in the effective environment inherited by the provider process started in the primary managed-agent pane.

The runtime SHALL preserve non-secret launch-profile env records when publishing tmux session environment values and when respawning the local interactive provider surface.

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
