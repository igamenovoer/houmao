## ADDED Requirements

### Requirement: Easy profile env records are regression-tested through Codex TUI launch
The test suite SHALL include coverage for a profile-backed Codex TUI launch where durable env records are created through the public easy-profile CLI surface and then observed inside the launched tmux-backed runtime.

The test SHALL create an easy profile with repeatable `project easy profile create --env-set NAME=value` inputs, launch a managed agent from that profile with `project easy instance launch --profile <name>` using the Codex local interactive lane, and verify the profile env records reach the launched tmux session or provider process environment.

The test SHALL use non-secret env names and values. It SHALL include lowercase proxy env names matching the issue report.

#### Scenario: Profile env reaches Codex TUI launched from easy profile
- **WHEN** a project contains a Codex-backed specialist and an easy profile created with `--env-set http_proxy=http://127.0.0.1:7990`, `--env-set https_proxy=http://127.0.0.1:7990`, and `--env-set FEATURE_FLAG_X=profile-env`
- **AND WHEN** an operator launches the profile through `houmao-mgr project easy instance launch --profile <profile>`
- **THEN** the launched tmux-backed Codex TUI environment exposes `http_proxy=http://127.0.0.1:7990`
- **AND THEN** the launched tmux-backed Codex TUI environment exposes `https_proxy=http://127.0.0.1:7990`
- **AND THEN** the launched tmux-backed Codex TUI environment exposes `FEATURE_FLAG_X=profile-env`

#### Scenario: Regression uses the CLI profile storage path
- **WHEN** the regression prepares the launch profile for the Codex TUI env propagation check
- **THEN** it creates the profile through `project easy profile create --env-set` rather than direct catalog mutation
- **AND THEN** it launches through `project easy instance launch --profile` rather than calling the runtime backend directly
