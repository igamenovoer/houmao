## ADDED Requirements

### Requirement: `houmao-specialist-mgr` preserves foreground-first launch-time gateway posture
The packaged `houmao-specialist-mgr` launch guidance SHALL explain that `project easy instance launch` enables launch-time gateway auto-attach by default unless `--no-gateway` or stored profile posture disables it.

The launch guidance SHALL state that default launch-time gateway auto-attach uses foreground same-session auxiliary-window execution when supported, and that detached background gateway execution is a separate gateway-sidecar posture.

The launch guidance SHALL NOT include `--gateway-background` in command examples or optional flag recommendations unless the current user prompt or recent conversation explicitly asks for background or detached gateway execution.

The launch guidance SHALL distinguish managed-agent `--headless` or `--no-headless` posture from gateway sidecar foreground or background execution, including for Gemini specialists whose managed-agent launch must remain headless.

#### Scenario: Specialist-backed launch keeps default foreground gateway posture
- **WHEN** an agent follows `houmao-specialist-mgr` guidance to launch an easy instance from an existing specialist
- **AND WHEN** the user has not explicitly requested detached background gateway execution
- **THEN** the guidance directs the agent to omit `--gateway-background`
- **AND THEN** it describes the resulting launch-time gateway auto-attach as foreground same-session auxiliary-window execution when supported

#### Scenario: Profile-backed launch keeps stored posture without inventing background mode
- **WHEN** an agent follows `houmao-specialist-mgr` guidance to launch through an easy profile
- **AND WHEN** the selected profile does not explicitly store or imply detached background gateway execution
- **THEN** the guidance does not add a background gateway flag as a one-shot override
- **AND THEN** it leaves profile-backed gateway posture to the stored profile defaults plus explicit user-provided CLI overrides

#### Scenario: Headless managed-agent launch does not imply background gateway execution
- **WHEN** the selected specialist or profile source requires or requests `--headless`
- **AND WHEN** the user has not explicitly requested background gateway execution
- **THEN** the guidance treats the managed-agent headless posture as separate from the gateway sidecar execution mode
- **AND THEN** it does not add `--gateway-background` merely because the managed-agent launch is headless

#### Scenario: Background gateway launch requires explicit user intent
- **WHEN** the user explicitly asks for background gateway execution, detached gateway process execution, or avoiding a gateway tmux window during easy launch
- **THEN** the guidance may include `--gateway-background` when the command surface supports it
- **AND THEN** it describes that flag as an explicit override rather than the normal launch posture
