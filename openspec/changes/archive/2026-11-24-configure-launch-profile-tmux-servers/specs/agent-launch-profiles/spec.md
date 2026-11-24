# Spec Delta

## ADDED Requirements

### Requirement: Project launch profiles can select a tmux server

Both project launch-profile lanes SHALL accept an optional `defaults.posture.tmux` selector with `server` set to `user-default`, `new`, `socket`, or `houmao-default`. An absolute `socket_path` SHALL be required for `socket` and invalid for the other modes. Profile inspection and the YAML projection SHALL report the stored selector.

#### Scenario: Both lanes author and inspect a shared default

- **WHEN** an operator creates a specialist-backed profile or a recipe-backed project launch profile with `--tmux-server houmao-default`
- **THEN** profile inspection and the YAML projection report `defaults.posture.tmux.server` as `houmao-default`
- **AND THEN** authoring the profile leaves tmux servers untouched

#### Scenario: Socket selection stores an absolute path

- **WHEN** an operator sets `--tmux-server socket --tmux-socket-path /run/user/1000/research.sock`
- **THEN** both values appear in the stored posture

#### Scenario: Invalid selector fails validation

- **WHEN** a profile uses an unknown server keyword, a missing or relative path for `socket`, or a path for another mode
- **THEN** validation rejects that selector with the invalid field identified

### Requirement: A launch-profile update treats the tmux selector as a unit

Profile patch operations SHALL preserve the existing tmux selector when omitted, replace it as a unit when supplied, and remove it through `--clear-tmux-server`. Clear and replacement inputs in the same operation SHALL be rejected.

#### Scenario: Switching modes drops the old socket path

- **GIVEN** a profile with `server: socket` and an absolute `socket_path`
- **WHEN** the operator sets `--tmux-server new`
- **THEN** inspection and projection show the `new` selection without a socket path

#### Scenario: Clearing the selector restores launch-time fallback

- **GIVEN** a profile with a stored tmux selector and other posture defaults
- **WHEN** the operator applies `--clear-tmux-server`
- **THEN** the profile omits `defaults.posture.tmux` and retains the other posture defaults
