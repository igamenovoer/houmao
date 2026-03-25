## ADDED Requirements

### Requirement: `houmao-mgr agents launch` preserves recipe launch policy during local build
When `houmao-mgr agents launch` resolves a native recipe-backed target, it SHALL preserve the recipe's requested launch policy when building the brain manifest for local startup.

At minimum, recipe `launch_policy.operator_prompt_mode` SHALL be forwarded into brain construction so the built manifest and subsequent runtime launch use the same requested operator-prompt posture.

#### Scenario: Recipe unattended policy survives local `agents launch`
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected recipe requests `launch_policy.operator_prompt_mode: unattended`
- **THEN** the local brain build records `launch_policy.operator_prompt_mode: unattended` in the built brain manifest
- **AND THEN** the local runtime launch uses that preserved unattended intent for the selected launch surface

## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes
`houmao-mgr agents launch` SHALL support both headless (detached) and interactive (tmux-attached) modes.

When `--headless` is specified, the agent SHALL run as a detached headless process.
When `--headless` is not specified, the agent SHALL start the selected provider's interactive terminal UI in a tmux session and the CLI SHALL attach to that tmux session.

#### Scenario: Headless launch runs detached
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **THEN** the agent starts in a tmux-backed headless session without attaching the operator's terminal
- **AND THEN** the command prints the agent identity and manifest path, then exits

#### Scenario: Interactive launch attaches to a live provider TUI
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **THEN** the agent starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the CLI attaches the operator's terminal to that tmux session
- **AND THEN** the launch is not considered successful if the session falls back to an idle shell before the provider reaches its interactive ready posture

### Requirement: `houmao-mgr agents launch` resolves backend from provider and launch mode
`houmao-mgr agents launch` SHALL resolve the runtime launch surface from the provider identifier together with whether `--headless` was requested.

At minimum:
- headless Claude launch uses the `claude_headless` backend
- headless Codex launch uses the `codex_headless` backend
- headless Gemini launch uses the `gemini_headless` backend
- non-headless launch uses a local interactive runtime surface rather than a detached headless backend

#### Scenario: Headless Claude launch resolves to `claude_headless`
- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents gpu-kernel-coder --headless`
- **THEN** the agent is launched using the `claude_headless` backend

#### Scenario: Interactive Claude launch does not reuse the headless transport
- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents gpu-kernel-coder` without `--headless`
- **THEN** the agent is launched on the local interactive runtime surface
- **AND THEN** the session is treated as TUI transport rather than headless transport

#### Scenario: Unsupported provider is rejected
- **WHEN** an operator runs `houmao-mgr agents launch --provider unsupported_tool --agents gpu-kernel-coder`
- **THEN** the command fails with a clear error listing the supported providers
